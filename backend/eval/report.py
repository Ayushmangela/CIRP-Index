"""Accuracy report against the human-labelled gold set. See
docs/EVALUATION.md.

python -m eval.report

Per field: precision (of what we claimed, how much was right), recall (of
what's actually in the document per gold, how much we found), exact-match,
and within-1% for the numeric claim_amount field. Table to stdout, full
report to eval/latest.json.

Verification rejection rate is reported separately from
eval/latest_extraction_run.json (written by extraction/run.py) if present -
it reflects the most recent extraction run, not specifically the gold-set
orders, since a rejected field is never persisted anywhere queryable by
design (see docs/EXTRACTION_CONTRACT.md and the /span-verify skill).
"""

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from extraction.contract import FIELDS_TO_EXTRACT
from models.extraction import ExtractedField, GoldLabel
from parsing.indian_numbers import parse_amount

logger = logging.getLogger(__name__)

NUMERIC_FIELDS = {"claim_amount"}
WITHIN_PERCENT_TOLERANCE = 0.01


@dataclass
class RejectionSummary:
    generated_at: str
    orders_processed: int
    attempted: int
    verified: int
    rejected: int
    not_found: int
    rejection_reasons: dict[str, int]


@dataclass
class FieldMetrics:
    field_name: str
    gold_present: int
    claimed: int
    correct_exact: int
    correct_within_tolerance: int | None
    precision: float | None
    recall: float | None
    exact_match_rate: float | None
    within_tolerance_rate: float | None


def _matches_exact(extracted_value: str, gold_value: str) -> bool:
    return extracted_value.strip() == gold_value.strip()


def _matches_within_tolerance(extracted_value: str, gold_value: str) -> bool | None:
    extracted_amount = parse_amount(extracted_value)
    gold_amount = parse_amount(gold_value)
    if extracted_amount is None or gold_amount is None or gold_amount == 0:
        return None
    return abs(extracted_amount - gold_amount) / abs(gold_amount) <= (
        WITHIN_PERCENT_TOLERANCE
    )


def compute_field_metrics(db: Session, field_name: str) -> FieldMetrics:
    gold_rows = list(
        db.execute(
            select(GoldLabel).where(GoldLabel.field_name == field_name)
        ).scalars()
    )
    gold_by_order = {row.order_id: row.expected_value for row in gold_rows}

    extracted_rows = list(
        db.execute(
            select(ExtractedField).where(
                ExtractedField.field_name == field_name,
                ExtractedField.order_id.in_(gold_by_order.keys()),
            )
        ).scalars()
    )

    claimed = len(extracted_rows)
    correct_exact = 0
    correct_within_tolerance = 0
    tolerance_applicable = field_name in NUMERIC_FIELDS

    for row in extracted_rows:
        if row.order_id is None or row.value_text is None:
            continue
        gold_value = gold_by_order.get(row.order_id)
        if gold_value is None:
            continue
        if _matches_exact(row.value_text, gold_value):
            correct_exact += 1
        if tolerance_applicable:
            within = _matches_within_tolerance(row.value_text, gold_value)
            if within:
                correct_within_tolerance += 1

    precision = correct_exact / claimed if claimed else None
    recall = claimed / len(gold_rows) if gold_rows else None
    exact_match_rate = correct_exact / claimed if claimed else None
    within_tolerance_rate = (
        (correct_within_tolerance / claimed if claimed else None)
        if tolerance_applicable
        else None
    )

    return FieldMetrics(
        field_name=field_name,
        gold_present=len(gold_rows),
        claimed=claimed,
        correct_exact=correct_exact,
        correct_within_tolerance=(
            correct_within_tolerance if tolerance_applicable else None
        ),
        precision=precision,
        recall=recall,
        exact_match_rate=exact_match_rate,
        within_tolerance_rate=within_tolerance_rate,
    )


def _fmt_pct(value: float | None) -> str:
    return f"{value * 100:.1f}%" if value is not None else "n/a"


def print_table(metrics: list[FieldMetrics]) -> None:
    header = (
        f"{'field':<30} {'gold':>5} {'claimed':>8} {'precision':>10} "
        f"{'recall':>8} {'exact':>8} {'within1%':>9}"
    )
    print(header)
    print("-" * len(header))
    for m in metrics:
        print(
            f"{m.field_name:<30} {m.gold_present:>5} {m.claimed:>8} "
            f"{_fmt_pct(m.precision):>10} {_fmt_pct(m.recall):>8} "
            f"{_fmt_pct(m.exact_match_rate):>8} "
            f"{_fmt_pct(m.within_tolerance_rate):>9}"
        )


def load_rejection_summary(path: Path) -> RejectionSummary | None:
    if not path.exists():
        return None
    raw = json.loads(path.read_text())
    return RejectionSummary(
        generated_at=raw["generated_at"],
        orders_processed=raw["orders_processed"],
        attempted=raw["attempted"],
        verified=raw["verified"],
        rejected=raw["rejected"],
        not_found=raw["not_found"],
        rejection_reasons=raw["rejection_reasons"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report accuracy against the gold set."
    )
    parser.add_argument("--out", type=str, default="eval/latest.json")
    parser.add_argument(
        "--rejection-summary", type=str, default="eval/latest_extraction_run.json"
    )
    args = parser.parse_args()

    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")

    db = SessionLocal()
    try:
        metrics = [compute_field_metrics(db, field) for field in FIELDS_TO_EXTRACT]
    finally:
        db.close()

    print_table(metrics)

    rejection_summary = load_rejection_summary(Path(args.rejection_summary))
    if rejection_summary is None:
        print(
            "\nverification rejection rate: not available - run "
            "extraction/run.py at least once to populate "
            f"{args.rejection_summary}"
        )
    else:
        print("\nverification rejection rate (most recent extraction run):")
        print(f"  attempted: {rejection_summary.attempted}")
        print(f"  verified:  {rejection_summary.verified}")
        print(f"  rejected:  {rejection_summary.rejected}")
        if rejection_summary.attempted:
            rate = rejection_summary.rejected / rejection_summary.attempted
            print(f"  rate:      {rate * 100:.1f}%")

    total_gold = sum(m.gold_present for m in metrics)
    if total_gold == 0:
        print(
            "\nNo gold labels found yet - run eval.sample, hand-label the "
            "worksheet, then eval.import before this report has real numbers."
        )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fields": [asdict(m) for m in metrics],
        "rejection_summary": (
            asdict(rejection_summary) if rejection_summary is not None else None
        ),
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))
    logger.info("wrote %s", out_path)


if __name__ == "__main__":
    main()
