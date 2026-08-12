import csv
import importlib
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.enums import ProcessingStatusEnum
from models.extraction import GoldLabel
from models.order import Order

# "eval.import" isn't importable via normal `from x import y` syntax since
# `import` is a reserved word - importlib resolves it fine by module-name
# string, same mechanism `python -m eval.import` uses.
eval_import = importlib.import_module("eval.import")


def _make_order(db: Session, pdf_url: str) -> Order:
    order = Order(
        subject_raw="In the matter of Test Co",
        pdf_url=pdf_url,
        processing_status=ProcessingStatusEnum.discovered,
        retrieved_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.flush()
    return order


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "order_id",
                "subject_raw",
                "case_number",
                "bench",
                "outcome",
                "field_name",
                "expected_value",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


class TestImportWorksheet:
    def test_imports_non_blank_rows(
        self, db_session: Session, tmp_path: object
    ) -> None:
        order = _make_order(db_session, "https://x/a.pdf")
        csv_path = Path(str(tmp_path)) / "worksheet.csv"
        _write_csv(
            csv_path,
            [
                {
                    "order_id": str(order.id),
                    "subject_raw": "x",
                    "case_number": "",
                    "bench": "MB",
                    "outcome": "admitted",
                    "field_name": "corporate_debtor",
                    "expected_value": "Test Manufacturing Pvt Ltd",
                }
            ],
        )

        imported, skipped = eval_import.import_worksheet(csv_path, "tester", db_session)
        db_session.flush()

        assert imported == 1
        assert skipped == 0
        gold = db_session.execute(select(GoldLabel)).scalars().one()
        assert gold.expected_value == "Test Manufacturing Pvt Ltd"
        assert gold.labelled_by == "tester"

    def test_skips_blank_expected_value(
        self, db_session: Session, tmp_path: object
    ) -> None:
        order = _make_order(db_session, "https://x/b.pdf")
        csv_path = Path(str(tmp_path)) / "worksheet.csv"
        _write_csv(
            csv_path,
            [
                {
                    "order_id": str(order.id),
                    "subject_raw": "x",
                    "case_number": "",
                    "bench": "MB",
                    "outcome": "admitted",
                    "field_name": "claim_amount",
                    "expected_value": "",
                }
            ],
        )

        imported, skipped = eval_import.import_worksheet(csv_path, "tester", db_session)

        assert imported == 0
        assert skipped == 1
        count = db_session.execute(select(GoldLabel)).scalars().all()
        assert len(count) == 0

    def test_reimport_updates_changed_value(
        self, db_session: Session, tmp_path: object
    ) -> None:
        order = _make_order(db_session, "https://x/c.pdf")
        csv_path = Path(str(tmp_path)) / "worksheet.csv"
        _write_csv(
            csv_path,
            [
                {
                    "order_id": str(order.id),
                    "subject_raw": "x",
                    "case_number": "",
                    "bench": "MB",
                    "outcome": "admitted",
                    "field_name": "corporate_debtor",
                    "expected_value": "Original Name",
                }
            ],
        )
        eval_import.import_worksheet(csv_path, "tester", db_session)
        db_session.flush()

        _write_csv(
            csv_path,
            [
                {
                    "order_id": str(order.id),
                    "subject_raw": "x",
                    "case_number": "",
                    "bench": "MB",
                    "outcome": "admitted",
                    "field_name": "corporate_debtor",
                    "expected_value": "Corrected Name",
                }
            ],
        )
        imported, _ = eval_import.import_worksheet(csv_path, "tester", db_session)
        db_session.flush()

        assert imported == 1
        gold = db_session.execute(select(GoldLabel)).scalars().one()
        assert gold.expected_value == "Corrected Name"

    def test_reimport_identical_value_is_noop(
        self, db_session: Session, tmp_path: object
    ) -> None:
        order = _make_order(db_session, "https://x/d.pdf")
        csv_path = Path(str(tmp_path)) / "worksheet.csv"
        _write_csv(
            csv_path,
            [
                {
                    "order_id": str(order.id),
                    "subject_raw": "x",
                    "case_number": "",
                    "bench": "MB",
                    "outcome": "admitted",
                    "field_name": "corporate_debtor",
                    "expected_value": "Same Name",
                }
            ],
        )
        eval_import.import_worksheet(csv_path, "tester", db_session)
        db_session.flush()
        imported, _ = eval_import.import_worksheet(csv_path, "tester", db_session)

        assert imported == 0
