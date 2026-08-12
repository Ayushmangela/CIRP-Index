"""Gold-set worksheet generator. See docs/EVALUATION.md.

python -m eval.sample --n 25 --out eval/worksheet.csv

Samples orders stratified across bench and outcome, and dumps each sampled
order's page text alongside the worksheet so labelling never requires
opening a PDF. Never writes to gold_labels itself - a human fills in
`expected_value` by hand afterwards.
"""

import argparse
import csv
import logging
import random
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from extraction.contract import FIELDS_TO_EXTRACT
from models.enums import ProcessingStatusEnum
from models.order import Order, OrderPage

logger = logging.getLogger(__name__)

DEFAULT_SEED = 42
MIN_DISTINCT_BENCHES = 4
MIN_DISTINCT_OUTCOMES = 4

WORKSHEET_COLUMNS = [
    "order_id",
    "subject_raw",
    "case_number",
    "bench",
    "outcome",
    "field_name",
    "expected_value",
]


def stratified_sample(orders: list[Order], n: int, seed: int) -> list[Order]:
    """Round-robin over (bench, outcome) buckets so the sample spans as
    many distinct benches and outcomes as the eligible pool allows,
    without requiring a full bench x outcome cross-product."""
    buckets: dict[tuple[str, str], list[Order]] = defaultdict(list)
    for order in orders:
        buckets[(order.bench or "", order.outcome.value)].append(order)

    rng = random.Random(seed)
    for bucket in buckets.values():
        rng.shuffle(bucket)

    bucket_keys = list(buckets.keys())
    rng.shuffle(bucket_keys)

    sample: list[Order] = []
    while len(sample) < n and any(buckets[key] for key in bucket_keys):
        for key in bucket_keys:
            if len(sample) >= n:
                break
            if buckets[key]:
                sample.append(buckets[key].pop())

    return sample


def write_worksheet(sample: list[Order], out_path: Path, pages_dir: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=WORKSHEET_COLUMNS)
        writer.writeheader()
        for order in sample:
            for field_name in FIELDS_TO_EXTRACT:
                writer.writerow(
                    {
                        "order_id": order.id,
                        "subject_raw": order.subject_raw,
                        "case_number": order.case_number or "",
                        "bench": order.bench or "",
                        "outcome": order.outcome.value,
                        "field_name": field_name,
                        "expected_value": "",
                    }
                )


def dump_page_text(order: Order, pages_dir: Path, db_pages: list[OrderPage]) -> None:
    text = "\n\n".join(
        f"=== Page {p.page_number} ===\n{p.text}"
        for p in sorted(db_pages, key=lambda p: p.page_number)
    )
    (pages_dir / f"order_{order.id}.txt").write_text(text)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the gold-set labelling worksheet."
    )
    parser.add_argument("--n", type=int, default=25)
    parser.add_argument("--out", type=str, default="eval/worksheet.csv")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")

    db = SessionLocal()
    try:
        eligible = list(
            db.execute(
                select(Order).where(
                    Order.processing_status.in_(
                        [
                            ProcessingStatusEnum.text_extracted,
                            ProcessingStatusEnum.extracted,
                        ]
                    ),
                    Order.bench.isnot(None),
                )
            ).scalars()
        )

        sample = stratified_sample(eligible, args.n, args.seed)

        out_path = Path(args.out)
        pages_dir = out_path.parent / "worksheet_pages"
        write_worksheet(sample, out_path, pages_dir)

        for order in sample:
            db_pages = list(
                db.execute(
                    select(OrderPage).where(OrderPage.order_id == order.id)
                ).scalars()
            )
            dump_page_text(order, pages_dir, db_pages)

        distinct_benches = {o.bench for o in sample if o.bench}
        distinct_outcomes = {o.outcome.value for o in sample}

        logger.info("eligible orders: %d", len(eligible))
        logger.info("sampled: %d", len(sample))
        logger.info("worksheet: %s", out_path)
        logger.info("page text: %s/", pages_dir)
        logger.info(
            "distinct benches in sample: %d (%s)",
            len(distinct_benches),
            ", ".join(sorted(distinct_benches)),
        )
        logger.info(
            "distinct outcomes in sample: %d (%s)",
            len(distinct_outcomes),
            ", ".join(sorted(distinct_outcomes)),
        )

        if len(distinct_benches) < MIN_DISTINCT_BENCHES:
            logger.warning(
                "only %d distinct benches in sample, target is >=%d - the "
                "eligible pool doesn't have enough bench diversity yet",
                len(distinct_benches),
                MIN_DISTINCT_BENCHES,
            )
        if len(distinct_outcomes) < MIN_DISTINCT_OUTCOMES:
            logger.warning(
                "only %d distinct outcomes in sample, target is >=%d - the "
                "eligible pool doesn't have enough outcome diversity yet",
                len(distinct_outcomes),
                MIN_DISTINCT_OUTCOMES,
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
