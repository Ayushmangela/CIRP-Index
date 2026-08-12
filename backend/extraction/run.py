"""LLM extraction orchestration. See docs/EXTRACTION_CONTRACT.md.

process_order_extraction() is the reusable core: given an order, its page
text, and an already-obtained LLMResponse, it verifies every field and
persists only what verifies. It does not care how the LLMResponse was
produced - the CLI below gets one from GeminiClient; a manual demo run can
construct one by hand. Same verification and persistence path either way.
"""

import argparse
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from extraction.contract import LLMResponse
from extraction.gemini_client import ExtractionRequestError, GeminiClient
from extraction.prompt import build_prompt, chunk_pages
from extraction.verifier import verify_field
from models.enums import ProcessingStatusEnum
from models.extraction import Evidence, ExtractedField
from models.ingestion import IngestionRun
from models.order import Order, OrderPage
from parsing.indian_numbers import parse_amount

logger = logging.getLogger(__name__)

REJECTION_RATE_WARNING_THRESHOLD = 0.25


@dataclass
class ExtractionSummary:
    attempted: int = 0
    verified: int = 0
    rejected: list[tuple[str, str]] = field(default_factory=list)
    not_found: list[str] = field(default_factory=list)


def process_order_extraction(
    order: Order, pages: dict[int, str], llm_response: LLMResponse, db: Session
) -> ExtractionSummary:
    summary = ExtractionSummary()
    now = datetime.now(timezone.utc)

    for item in llm_response.fields:
        summary.attempted += 1
        result = verify_field(item.evidence.quote, item.evidence.page, pages)

        if not result.verified:
            reason = item.evidence.quote[:60]
            summary.rejected.append((item.field, reason))
            logger.warning(
                "order %s field %r rejected, quote not found near page %d: %r",
                order.id,
                item.field,
                item.evidence.page,
                reason,
            )
            continue

        summary.verified += 1
        value_numeric = (
            parse_amount(item.value_text) if item.field == "claim_amount" else None
        )

        extracted_field = ExtractedField(
            order_id=order.id,
            field_name=item.field,
            value_text=item.value_text,
            value_numeric=value_numeric,
            verified=True,
            extraction_method="llm",
            model_name=settings.GEMINI_MODEL_NAME,
            extracted_at=now,
        )
        db.add(extracted_field)
        db.flush()

        db.add(
            Evidence(
                extracted_field_id=extracted_field.id,
                order_id=order.id,
                page_number=result.page_used,
                quote=item.evidence.quote,
                char_start=result.char_start,
                char_end=result.char_end,
            )
        )

    summary.not_found.extend(llm_response.not_found)
    return summary


def _merge(total: ExtractionSummary, part: ExtractionSummary) -> None:
    total.attempted += part.attempted
    total.verified += part.verified
    total.rejected.extend(part.rejected)
    total.not_found.extend(part.not_found)


def run(limit: int, db: Session) -> None:
    started_at = datetime.now(timezone.utc)
    ingestion_run = IngestionRun(started_at=started_at)
    db.add(ingestion_run)
    db.flush()

    orders = list(
        db.execute(
            select(Order)
            .where(Order.processing_status == ProcessingStatusEnum.text_extracted)
            .order_by(Order.id)
            .limit(limit)
        ).scalars()
    )

    client = GeminiClient()
    totals = ExtractionSummary()
    rejection_reasons: Counter[str] = Counter()
    llm_calls = 0

    try:
        for order in orders:
            page_rows = db.execute(
                select(OrderPage)
                .where(OrderPage.order_id == order.id)
                .order_by(OrderPage.page_number)
            ).scalars()
            pages = {p.page_number: p.text for p in page_rows}
            if not pages:
                continue

            for chunk in chunk_pages(pages):
                prompt = build_prompt(chunk)
                try:
                    llm_response = client.extract(prompt)
                except ExtractionRequestError as exc:
                    logger.error(
                        "order %s: extraction request failed: %s", order.id, exc
                    )
                    continue
                finally:
                    llm_calls += 1

                summary = process_order_extraction(order, pages, llm_response, db)
                _merge(totals, summary)
                for field_name, reason in summary.rejected:
                    rejection_reasons[f"{field_name}: {reason!r}"] += 1

            order.processing_status = ProcessingStatusEnum.extracted
            db.commit()
    finally:
        client.close()

    rejected_count = totals.attempted - totals.verified
    rejection_rate = rejected_count / totals.attempted if totals.attempted else 0.0

    ingestion_run.finished_at = datetime.now(timezone.utc)
    ingestion_run.llm_calls = llm_calls
    ingestion_run.orders_processed = len(orders)
    ingestion_run.notes = (
        f"attempted={totals.attempted} verified={totals.verified} "
        f"rejected={rejected_count} not_found={len(totals.not_found)}"
    )
    db.commit()

    logger.info("orders processed: %d", len(orders))
    logger.info("fields attempted: %d", totals.attempted)
    logger.info("fields verified: %d", totals.verified)
    logger.info("fields rejected: %d", rejected_count)
    logger.info("fields model reported not_found: %d", len(totals.not_found))
    if rejection_reasons:
        logger.info("rejection reasons:")
        for reason, count in rejection_reasons.most_common():
            logger.info("  %4d  %s", count, reason)

    if totals.attempted and rejection_rate > REJECTION_RATE_WARNING_THRESHOLD:
        logger.warning(
            "rejection rate %.1f%% exceeds %.0f%% - stop and investigate the "
            "documents, per docs/EXTRACTION_CONTRACT.md. Do not tune the "
            "prompt to make this number look better.",
            rejection_rate * 100,
            REJECTION_RATE_WARNING_THRESHOLD * 100,
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run LLM extraction with span verification."
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
