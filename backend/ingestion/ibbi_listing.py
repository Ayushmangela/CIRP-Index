"""IBBI NCLT order listing scraper.

Fetches https://ibbi.gov.in/orders/nclt?page=N, parses each row into an
Order, and upserts (dedup on pdf_url) into the database. See
docs/DATA_SOURCE.md for the confirmed table shape and rate-limit rules.
"""

from __future__ import annotations

import argparse
import logging
import re
import time
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag
from sqlalchemy import select
from sqlalchemy.orm import Session
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.config import settings
from app.database import SessionLocal
from models.enums import OutcomeEnum, ProcessingStatusEnum
from models.ingestion import IngestionRun
from models.order import Order
from parsing.case_number import extract_case_number

logger = logging.getLogger(__name__)

BASE_URL = "https://ibbi.gov.in"
LISTING_PATH = "/orders/nclt"
MIN_REQUEST_INTERVAL_SECONDS = 2.0

# Explicit mapping only. Anything not listed here becomes `unclassified` and
# is logged with the raw string, per AGENTS.md rule 3 - never guess an enum.
# Keys are normalised (stripped, lower-cased) before lookup.
OUTCOME_MAP: dict[str, OutcomeEnum] = {
    "admitted": OutcomeEnum.admitted,
    "admission - final order": OutcomeEnum.admitted,
    "liquidation": OutcomeEnum.liquidation,
    "appointment - appointment of liquidator": OutcomeEnum.liquidation,
    "dissolution": OutcomeEnum.dissolved,
    "approval of resolution plan": OutcomeEnum.resolution_approved,
    "resolution plan": OutcomeEnum.resolution_approved,
    "extension of cirp period": OutcomeEnum.cirp_ongoing,
    "extension of time (cirp)": OutcomeEnum.cirp_ongoing,
    "cirp-withdrawn": OutcomeEnum.withdrawn,
    "cirp withdrawn": OutcomeEnum.withdrawn,
    # Observed typo variant of "cirp-withdrawn" on the live site - an
    # explicit dictionary entry, not fuzzy matching.
    "cipr-withdrawn": OutcomeEnum.withdrawn,
    "withdrawn": OutcomeEnum.withdrawn,
    "12a-withdrawn": OutcomeEnum.withdrawn,
    "others": OutcomeEnum.unclassified,
}

_SIZE_PATTERN = re.compile(r"\(([\d.]+)\s*(KB|MB|GB)\)\s*$", re.IGNORECASE)
_SIZE_MULTIPLIERS = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}
_DATE_FORMAT = "%d %b, %Y"


class PageFetchError(Exception):
    """Raised when a listing page could not be fetched after all retries."""


@dataclass
class ParsedRow:
    order_date: date | None
    subject_raw: str
    case_number: str | None
    pdf_url: str
    file_size_bytes: int | None
    remarks_raw: str
    outcome: OutcomeEnum


class RateLimitedFetcher:
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

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
        stop=stop_after_attempt(4),
        wait=wait_exponential_jitter(initial=1, max=30),
        reraise=True,
    )
    def _get(self, url: str, params: dict[str, int]) -> httpx.Response:
        response = self._client.get(url, params=params)
        if response.status_code >= 500:
            response.raise_for_status()
        return response

    def fetch_listing_page(self, page: int) -> str:
        if self._last_request_at is not None:
            elapsed = time.monotonic() - self._last_request_at
            remaining = MIN_REQUEST_INTERVAL_SECONDS - elapsed
            if remaining > 0:
                time.sleep(remaining)

        try:
            response = self._get(f"{BASE_URL}{LISTING_PATH}", params={"page": page})
        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            self._last_request_at = time.monotonic()
            raise PageFetchError(f"page {page}: {exc}") from exc

        self._last_request_at = time.monotonic()

        if response.status_code != 200:
            raise PageFetchError(f"page {page}: HTTP {response.status_code}")

        return response.text


def _parse_date(text: str) -> date | None:
    try:
        return datetime.strptime(text.strip(), _DATE_FORMAT).date()
    except ValueError:
        logger.warning("could not parse order date %r", text)
        return None


def _parse_subject_and_size(link: Tag) -> tuple[str, int | None]:
    raw_text = link.get_text(separator=" ", strip=True)
    raw_text = re.sub(r"\s+", " ", raw_text).strip()

    size_match = _SIZE_PATTERN.search(raw_text)
    if size_match is None:
        return raw_text, None

    subject = raw_text[: size_match.start()].strip()
    value = float(size_match.group(1))
    unit = size_match.group(2).upper()
    file_size_bytes = round(value * _SIZE_MULTIPLIERS[unit])
    return subject, file_size_bytes


def resolve_outcome(remarks_raw: str) -> OutcomeEnum:
    normalised = re.sub(r"\s+", " ", remarks_raw.strip().lower())
    return OUTCOME_MAP.get(normalised, OutcomeEnum.unclassified)


def parse_page(html: str) -> list[ParsedRow]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="reporttable")
    if table is None:
        logger.warning("no reporttable found on page")
        return []

    rows: list[ParsedRow] = []
    tbody = table.find("tbody")
    if tbody is None:
        return rows

    for tr in tbody.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) != 4:
            continue

        order_date = _parse_date(tds[1].get_text())

        link = tds[2].find("a")
        if link is None or not link.get("href"):
            logger.warning("row missing PDF link, skipping: %r", tds[2].get_text())
            continue

        subject_raw, file_size_bytes = _parse_subject_and_size(link)
        pdf_url = urljoin(BASE_URL, str(link["href"]).strip())
        remarks_raw = tds[3].get_text(strip=True)

        rows.append(
            ParsedRow(
                order_date=order_date,
                subject_raw=subject_raw,
                case_number=extract_case_number(subject_raw),
                pdf_url=pdf_url,
                file_size_bytes=file_size_bytes,
                remarks_raw=remarks_raw,
                outcome=resolve_outcome(remarks_raw),
            )
        )

    return rows


def upsert_row(db: Session, row: ParsedRow, source_listing_page: int) -> bool:
    """Insert the row if pdf_url is new. Returns True if a new row was added."""
    existing = db.execute(
        select(Order.id).where(Order.pdf_url == row.pdf_url)
    ).scalar_one_or_none()
    if existing is not None:
        return False

    db.add(
        Order(
            order_date=row.order_date,
            subject_raw=row.subject_raw,
            case_number=row.case_number,
            pdf_url=row.pdf_url,
            file_size_bytes=row.file_size_bytes,
            remarks_raw=row.remarks_raw,
            outcome=row.outcome,
            processing_status=ProcessingStatusEnum.discovered,
            retrieved_at=datetime.now(timezone.utc),
            source_listing_page=source_listing_page,
        )
    )
    return True


def run(start_page: int, end_page: int, db: Session) -> None:
    started_at = datetime.now(timezone.utc)
    ingestion_run = IngestionRun(started_at=started_at)
    db.add(ingestion_run)
    db.flush()

    fetcher = RateLimitedFetcher(settings.IBBI_CONTACT_EMAIL)
    unmapped_remarks: Counter[str] = Counter()
    pages_scanned = 0
    orders_found = 0
    orders_new = 0
    orders_with_case_number = 0
    last_page_scanned: int | None = None

    try:
        for page in range(start_page, end_page + 1):
            try:
                html = fetcher.fetch_listing_page(page)
            except PageFetchError as exc:
                logger.error("giving up on page %s: %s", page, exc)
                ingestion_run.orders_failed += 1
                continue

            pages_scanned += 1
            last_page_scanned = page
            rows = parse_page(html)
            orders_found += len(rows)

            for parsed_row in rows:
                if parsed_row.case_number is not None:
                    orders_with_case_number += 1
                if parsed_row.outcome == OutcomeEnum.unclassified:
                    unmapped_remarks[parsed_row.remarks_raw] += 1
                if upsert_row(db, parsed_row, source_listing_page=page):
                    orders_new += 1

            db.commit()
    finally:
        fetcher.close()

    ingestion_run.finished_at = datetime.now(timezone.utc)
    ingestion_run.pages_scanned = pages_scanned
    ingestion_run.orders_found = orders_found
    ingestion_run.orders_new = orders_new
    ingestion_run.watermark = (
        str(last_page_scanned) if last_page_scanned is not None else None
    )
    ingestion_run.notes = (
        "unmapped remarks: "
        + ", ".join(f"{value!r}={count}" for value, count in unmapped_remarks.items())
        if unmapped_remarks
        else "no unmapped remarks"
    )
    db.commit()

    case_number_rate = (
        orders_with_case_number / orders_found * 100 if orders_found else 0.0
    )
    logger.info("pages scanned: %d", pages_scanned)
    logger.info("orders found: %d, new: %d", orders_found, orders_new)
    logger.info(
        "case numbers parsed: %d/%d (%.1f%%)",
        orders_with_case_number,
        orders_found,
        case_number_rate,
    )
    if unmapped_remarks:
        logger.info("unmapped remarks:")
        for value, count in unmapped_remarks.most_common():
            logger.info("  %4d  %r", count, value)
    else:
        logger.info("no unmapped remarks")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape IBBI NCLT order listings.")
    parser.add_argument("--start-page", type=int, required=True)
    parser.add_argument("--end-page", type=int, required=True)
    args = parser.parse_args()

    logging.basicConfig(
        level=settings.LOG_LEVEL, format="%(asctime)s %(levelname)s %(message)s"
    )

    db = SessionLocal()
    try:
        run(args.start_page, args.end_page, db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
