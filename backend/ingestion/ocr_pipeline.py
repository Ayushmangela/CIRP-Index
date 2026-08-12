"""OCR for scanned orders.

See docs/decisions/0004-ocr-as-separate-labelled-pipeline.md.

Runs against orders pdf_pipeline.py already marked scanned_skipped. The PDF
is re-downloaded (never persisted, per AGENTS.md rule 6), rasterized per
page with pymupdf, and OCR'd with pytesseract. Results land under a
distinct processing_status (ocr_extracted) so this text is never conflated
with pdfplumber's real-extracted text_extracted rows - a bad OCR read must
be able to fail span verification like any other unmatched quote, not be
silently trusted as ground truth. See docs/decisions/0002 for why that
distinction matters.

This is a standing pipeline step, not a one-off backfill: it selects by
processing_status, so any order that lands in scanned_skipped in a future
ingestion run becomes eligible the next time this script runs.
"""

from __future__ import annotations

import argparse
import logging
import os
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone

import pymupdf
import pytesseract
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from ingestion.pdf_pipeline import (
    PdfDownloadError,
    RateLimitedDownloader,
    _normalise_page_text,
)
from models.enums import ProcessingStatusEnum
from models.ingestion import IngestionRun
from models.order import Order, OrderPage

logger = logging.getLogger(__name__)

OCR_DPI = 300
# A page that OCRs to near-nothing (blank scan, all-noise) is still a
# failure - leave the order scanned_skipped rather than record empty pages.
MIN_OCR_CHARS_PER_PAGE = 20


class OcrError(Exception):
    """A distinct, named reason a PDF could not be OCR'd."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass
class OcrResult:
    page_count: int
    pages: list[str]


def ocr_pdf(pdf_path: str) -> OcrResult:
    try:
        doc = pymupdf.open(pdf_path)
    except Exception as exc:
        raise OcrError(f"unreadable pdf: {exc}") from exc

    pages: list[str] = []
    try:
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            pixmap = page.get_pixmap(dpi=OCR_DPI)
            size = (pixmap.width, pixmap.height)
            image = Image.frombytes("RGB", size, pixmap.samples)
            text = pytesseract.image_to_string(image)
            pages.append(_normalise_page_text(text))
    finally:
        doc.close()

    return OcrResult(page_count=len(pages), pages=pages)


def process_order(order: Order, downloader: RateLimitedDownloader, db: Session) -> str:
    """Process one scanned_skipped order. Returns a short outcome label."""
    try:
        content = downloader.download(order.pdf_url)
    except PdfDownloadError as exc:
        logger.warning("order %s: download failed: %s", order.id, exc.reason)
        return exc.reason

    fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
    try:
        with os.fdopen(fd, "wb") as tmp_file:
            tmp_file.write(content)

        try:
            result = ocr_pdf(tmp_path)
        except OcrError as exc:
            logger.warning("order %s: OCR failed: %s", order.id, exc.reason)
            return exc.reason
    finally:
        os.unlink(tmp_path)

    total_chars = sum(len(p) for p in result.pages)
    avg_chars_per_page = total_chars / result.page_count if result.page_count else 0
    if avg_chars_per_page < MIN_OCR_CHARS_PER_PAGE:
        logger.warning(
            "order %s: OCR produced near-empty text (%.1f chars/page avg), "
            "leaving as scanned_skipped",
            order.id,
            avg_chars_per_page,
        )
        return "ocr_empty"

    for page_number, text in enumerate(result.pages, start=1):
        db.add(OrderPage(order_id=order.id, page_number=page_number, text=text))
    order.page_count = result.page_count
    order.processing_status = ProcessingStatusEnum.ocr_extracted
    return "ocr_extracted"


def run(limit: int, db: Session) -> None:
    started_at = datetime.now(timezone.utc)
    ingestion_run = IngestionRun(started_at=started_at)
    db.add(ingestion_run)
    db.flush()

    orders = list(
        db.execute(
            select(Order)
            .where(Order.processing_status == ProcessingStatusEnum.scanned_skipped)
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
    succeeded = outcomes.get("ocr_extracted", 0)
    failed = processed - succeeded

    ingestion_run.finished_at = datetime.now(timezone.utc)
    ingestion_run.orders_processed = processed
    ingestion_run.orders_failed = failed
    ingestion_run.notes = "outcomes: " + ", ".join(
        f"{label}={count}" for label, count in outcomes.most_common()
    )
    db.commit()

    logger.info("orders processed: %d", processed)
    logger.info("ocr_extracted: %d/%d", succeeded, processed)
    logger.info("outcome breakdown:")
    for label, count in outcomes.most_common():
        logger.info("  %4d  %s", count, label)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OCR scanned_skipped order PDFs into a distinct, "
        "clearly-labelled text source - see docs/decisions/0004."
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
