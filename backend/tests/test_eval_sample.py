from datetime import datetime, timezone

from sqlalchemy.orm import Session

from eval.sample import stratified_sample, write_worksheet
from models.enums import OutcomeEnum, ProcessingStatusEnum
from models.order import Order


def _make_order(db: Session, pdf_url: str, bench: str, outcome: OutcomeEnum) -> Order:
    order = Order(
        subject_raw=f"In the matter of Test Co {pdf_url}",
        pdf_url=pdf_url,
        bench=bench,
        outcome=outcome,
        processing_status=ProcessingStatusEnum.text_extracted,
        retrieved_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.flush()
    return order


class TestStratifiedSample:
    def test_spans_multiple_benches_and_outcomes(self, db_session: Session) -> None:
        orders = []
        combos = [
            ("MB", OutcomeEnum.admitted),
            ("ND", OutcomeEnum.liquidation),
            ("KB", OutcomeEnum.resolution_approved),
            ("HDB", OutcomeEnum.dissolved),
        ]
        for i, (bench, outcome) in enumerate(combos):
            for j in range(3):
                orders.append(
                    _make_order(db_session, f"https://x/{i}-{j}.pdf", bench, outcome)
                )

        sample = stratified_sample(orders, n=8, seed=1)

        assert len(sample) == 8
        benches = {o.bench for o in sample}
        outcomes = {o.outcome for o in sample}
        assert len(benches) == 4
        assert len(outcomes) == 4

    def test_does_not_exceed_available_orders(self, db_session: Session) -> None:
        orders = [
            _make_order(db_session, "https://x/only.pdf", "MB", OutcomeEnum.admitted)
        ]
        sample = stratified_sample(orders, n=25, seed=1)
        assert len(sample) == 1

    def test_no_duplicate_orders_in_sample(self, db_session: Session) -> None:
        orders = [
            _make_order(db_session, f"https://x/{i}.pdf", "MB", OutcomeEnum.admitted)
            for i in range(10)
        ]
        sample = stratified_sample(orders, n=5, seed=1)
        ids = [o.id for o in sample]
        assert len(ids) == len(set(ids))

    def test_deterministic_with_fixed_seed(self, db_session: Session) -> None:
        orders = [
            _make_order(db_session, f"https://x/{i}.pdf", "MB", OutcomeEnum.admitted)
            for i in range(10)
        ]
        sample1 = stratified_sample(orders, n=5, seed=7)
        sample2 = stratified_sample(orders, n=5, seed=7)
        assert [o.id for o in sample1] == [o.id for o in sample2]


class TestWriteWorksheet:
    def test_writes_one_row_per_field_per_order(
        self, db_session: Session, tmp_path: "object"
    ) -> None:
        from pathlib import Path

        orders = [
            _make_order(db_session, "https://x/a.pdf", "MB", OutcomeEnum.admitted),
            _make_order(db_session, "https://x/b.pdf", "ND", OutcomeEnum.liquidation),
        ]
        out_path = Path(str(tmp_path)) / "worksheet.csv"
        pages_dir = Path(str(tmp_path)) / "pages"
        write_worksheet(orders, out_path, pages_dir)

        content = out_path.read_text()
        lines = [line for line in content.splitlines() if line]
        # header + 2 orders * 9 fields
        assert len(lines) == 1 + 2 * 9

    def test_expected_value_column_is_blank(
        self, db_session: Session, tmp_path: "object"
    ) -> None:
        import csv
        from pathlib import Path

        orders = [
            _make_order(db_session, "https://x/a.pdf", "MB", OutcomeEnum.admitted)
        ]
        out_path = Path(str(tmp_path)) / "worksheet.csv"
        pages_dir = Path(str(tmp_path)) / "pages"
        write_worksheet(orders, out_path, pages_dir)

        with out_path.open() as f:
            rows = list(csv.DictReader(f))
        assert all(row["expected_value"] == "" for row in rows)
