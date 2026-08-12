"""Loads a completed gold-set worksheet into gold_labels. See
docs/EVALUATION.md.

python -m eval.import --file eval/worksheet.csv --labelled-by "your name"

A blank `expected_value` means the field is genuinely absent from that
order's document, not "not yet labelled" - those rows are skipped, they
don't become gold facts. This script never writes to gold_labels on its
own initiative; it only transcribes what a human already filled in.
"""

import argparse
import csv
import getpass
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from models.extraction import GoldLabel

logger = logging.getLogger(__name__)


def import_worksheet(csv_path: Path, labelled_by: str, db: Session) -> tuple[int, int]:
    imported = 0
    skipped_blank = 0

    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            expected_value = row["expected_value"].strip()
            if not expected_value:
                skipped_blank += 1
                continue

            order_id = int(row["order_id"])
            field_name = row["field_name"]

            existing = db.execute(
                select(GoldLabel).where(
                    GoldLabel.order_id == order_id,
                    GoldLabel.field_name == field_name,
                )
            ).scalar_one_or_none()

            if existing is not None:
                if existing.expected_value == expected_value:
                    continue
                logger.info(
                    "order %s field %s: updating gold label %r -> %r",
                    order_id,
                    field_name,
                    existing.expected_value,
                    expected_value,
                )
                existing.expected_value = expected_value
                existing.labelled_by = labelled_by
                existing.labelled_at = datetime.now(timezone.utc)
                imported += 1
                continue

            db.add(
                GoldLabel(
                    order_id=order_id,
                    field_name=field_name,
                    expected_value=expected_value,
                    labelled_by=labelled_by,
                    labelled_at=datetime.now(timezone.utc),
                )
            )
            imported += 1

    return imported, skipped_blank


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import a completed gold-set worksheet into gold_labels."
    )
    parser.add_argument("--file", type=str, required=True)
    parser.add_argument("--labelled-by", type=str, default=getpass.getuser())
    args = parser.parse_args()

    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")

    db = SessionLocal()
    try:
        imported, skipped_blank = import_worksheet(
            Path(args.file), args.labelled_by, db
        )
        db.commit()
        logger.info("imported/updated: %d", imported)
        logger.info(
            "skipped (blank - field not present in document): %d", skipped_blank
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
