"""PDF acquisition and text extraction.

Downloads each discovered order's PDF to a temp file, extracts per-page text
with pdfplumber, and deletes the temp file. PDFs are never persisted - only
source_url, sha256, and extracted text land in the database, per AGENTS.md
rule 6. See docs/DATA_SOURCE.md's PDF handling section and
docs/decisions/0002-skip-scanned-orders.md.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import re
import tempfile
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
import pdfplumber
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from models.enums import ProcessingStatusEnum
from models.ingestion import IngestionRun
from models.order import Order, OrderPage

logger = logging.getLogger(__name__)

MIN_REQUEST_INTERVAL_SECONDS = 2.0
SCANNED_CHARS_PER_PAGE_THRESHOLD = 100
PDF_MAGIC_BYTES = b"%PDF-"


class PdfDownloadError(Exception):
    """A distinct, named reason a PDF could not be acquired or read."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class RateLimitedDownloader:
    """Single-connection httpx client enforcing >=2s between requests."""

    def __init__(self, contact_email: str) -> None:
        user_agent = f"CIRPIndex/0.1 (research project; {contact_email})"
        self._client = httpx.Client(
            headers={"User-Agent": user_agent},
            timeout=30.0,
            follow_redirects=True,
        )
        self._last_request_at: float | None = None

    def close(self) -> None:
        self._client.close()

    def download(self, url: str) -> bytes:
        if self._last_request_at is not None:
            elapsed = time.monotonic() - self._last_request_at
            remaining = MIN_REQUEST_INTERVAL_SECONDS - elapsed
            if remaining > 0:
                time.sleep(remaining)

        try:
            response = self._client.get(url)
        except httpx.TimeoutException as exc:
            self._last_request_at = time.monotonic()
            raise PdfDownloadError("timeout") from exc
        except httpx.TransportError as exc:
            self._last_request_at = time.monotonic()
            raise PdfDownloadError(f"connection error: {exc}") from exc

        self._last_request_at = time.monotonic()

        if response.status_code == 404:
            raise PdfDownloadError("404")
        if response.status_code != 200:
            raise PdfDownloadError(f"http {response.status_code}")

        content = response.content
        if len(content) == 0:
            raise PdfDownloadError("zero-byte response")
        if not content.startswith(PDF_MAGIC_BYTES):
            raise PdfDownloadError("not a pdf (html error page or similar)")

        return content


@dataclass
class ExtractionResult:
    page_count: int
    is_scanned: bool
    pages: list[str]


def extract_text(pdf_path: str) -> ExtractionResult:
    with pdfplumber.open(pdf_path) as pdf:
        pages = [_normalise_page_text(page.extract_text() or "") for page in pdf.pages]

    page_count = len(pages)
    total_chars = sum(len(p) for p in pages)
    avg_chars_per_page = total_chars / page_count if page_count else 0
    is_scanned = avg_chars_per_page < SCANNED_CHARS_PER_PAGE_THRESHOLD

    return ExtractionResult(page_count=page_count, is_scanned=is_scanned, pages=pages)


def _normalise_page_text(text: str) -> str:
    lines = text.split("\n")
    normalised_lines = [re.sub(r"[ \t]+", " ", line).strip() for line in lines]
    return "\n".join(normalised_lines)


def _check_not_encrypted(pdf_path: str) -> None:
    try:
        reader = PdfReader(pdf_path)
    except PdfReadError as exc:
        raise PdfDownloadError(f"unreadable pdf: {exc}") from exc

    if reader.is_encrypted:
        raise PdfDownloadError("password-protected")


def process_order(order: Order, downloader: RateLimitedDownloader, db: Session) -> str:
    """Process one order. Returns a short outcome label for reporting."""
    try:
        content = downloader.download(order.pdf_url)
    except PdfDownloadError as exc:
        logger.warning("order %s: download failed: %s", order.id, exc.reason)
        order.processing_status = ProcessingStatusEnum.failed
        return exc.reason

    sha256 = hashlib.sha256(content).hexdigest()

    duplicate_of = db.execute(
        select(Order).where(
            Order.pdf_sha256 == sha256,
            Order.processing_status == ProcessingStatusEnum.text_extracted,
            Order.id != order.id,
        )
    ).scalar_one_or_none()
    if duplicate_of is not None:
        return _copy_from_duplicate(order, duplicate_of, sha256, db)

    fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
    try:
        with os.fdopen(fd, "wb") as tmp_file:
            tmp_file.write(content)

        try:
            _check_not_encrypted(tmp_path)
            result = extract_text(tmp_path)
        except PdfDownloadError as exc:
            logger.warning("order %s: extraction failed: %s", order.id, exc.reason)
            order.pdf_sha256 = sha256
            order.processing_status = ProcessingStatusEnum.failed
            return exc.reason
    finally:
        os.unlink(tmp_path)

    order.pdf_sha256 = sha256
    order.page_count = result.page_count
    order.is_scanned = result.is_scanned

    if result.is_scanned:
        order.processing_status = ProcessingStatusEnum.scanned_skipped
        return "scanned"

    for page_number, text in enumerate(result.pages, start=1):
        db.add(OrderPage(order_id=order.id, page_number=page_number, text=text))
    order.processing_status = ProcessingStatusEnum.text_extracted
    return "text_extracted"


def _copy_from_duplicate(
    order: Order, duplicate_of: Order, sha256: str, db: Session
) -> str:
    duplicate_pages = db.execute(
        select(OrderPage)
        .where(OrderPage.order_id == duplicate_of.id)
        .order_by(OrderPage.page_number)
    ).scalars()
    for page in duplicate_pages:
        db.add(
            OrderPage(order_id=order.id, page_number=page.page_number, text=page.text)
        )

    order.pdf_sha256 = sha256
    order.page_count = duplicate_of.page_count
    order.is_scanned = duplicate_of.is_scanned
    order.processing_status = ProcessingStatusEnum.text_extracted
    return "duplicate_content"


def run(limit: int, db: Session) -> None:
    started_at = datetime.now(timezone.utc)
    ingestion_run = IngestionRun(started_at=started_at)
    db.add(ingestion_run)
    db.flush()

    orders = list(
        db.execute(
            select(Order)
            .where(Order.processing_status == ProcessingStatusEnum.discovered)
            .order_by(Order.id)
            .limit(limit)
        ).scalars()
    )

    downloader = RateLimitedDownloader(settings.IBBI_CONTACT_EMAIL)
    outcomes: Counter[str] = Counter()

    try:
        for order in orders:
            outcome = process_order(order, downloader, db)
            outcomes[outcome] += 1
            db.commit()
    finally:
        downloader.close()

    processed = len(orders)
    scanned = outcomes.get("scanned", 0)
    failed = sum(
        count
        for label, count in outcomes.items()
        if label not in ("text_extracted", "scanned", "duplicate_content")
    )
    scanned_pct = scanned / processed * 100 if processed else 0.0

    ingestion_run.finished_at = datetime.now(timezone.utc)
    ingestion_run.orders_processed = processed
    ingestion_run.orders_failed = failed
    ingestion_run.notes = "outcomes: " + ", ".join(
        f"{label}={count}" for label, count in outcomes.most_common()
    )
    db.commit()

    logger.info("orders processed: %d", processed)
    logger.info("scanned: %d/%d (%.1f%%)", scanned, processed, scanned_pct)
    logger.info("failed: %d", failed)
    logger.info("outcome breakdown:")
    for label, count in outcomes.most_common():
        logger.info("  %4d  %s", count, label)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and extract text from discovered IBBI order PDFs."
    )
    parser.add_argument("--limit", type=int, required=True)
    args = parser.parse_args()

    logging.basicConfig(
        level=settings.LOG_LEVEL, format="%(asctime)s %(levelname)s %(message)s"
    )

    db = SessionLocal()
    try:
        run(args.limit, db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
