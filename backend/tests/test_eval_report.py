from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from eval.report import compute_field_metrics
from models.enums import ProcessingStatusEnum
from models.extraction import ExtractedField, GoldLabel
from models.order import Order


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


def _gold(db: Session, order_id: int, field_name: str, expected: str) -> None:
    db.add(
        GoldLabel(
            order_id=order_id,
            field_name=field_name,
            expected_value=expected,
            labelled_by="tester",
            labelled_at=datetime.now(timezone.utc),
        )
    )


def _extracted(
    db: Session,
    order_id: int,
    field_name: str,
    value_text: str,
    value_numeric: Decimal | None = None,
) -> None:
    db.add(
        ExtractedField(
            order_id=order_id,
            field_name=field_name,
            value_text=value_text,
            value_numeric=value_numeric,
            verified=True,
            extraction_method="llm",
            model_name="test-model",
            extracted_at=datetime.now(timezone.utc),
        )
    )


class TestComputeFieldMetrics:
    def test_perfect_match_gives_full_precision_and_recall(
        self, db_session: Session
    ) -> None:
        order = _make_order(db_session, "https://x/a.pdf")
        _gold(db_session, order.id, "corporate_debtor", "Test Co Ltd")
        _extracted(db_session, order.id, "corporate_debtor", "Test Co Ltd")
        db_session.flush()

        metrics = compute_field_metrics(db_session, "corporate_debtor")

        assert metrics.gold_present == 1
        assert metrics.claimed == 1
        assert metrics.correct_exact == 1
        assert metrics.precision == 1.0
        assert metrics.recall == 1.0

    def test_wrong_value_hurts_precision_not_recall(self, db_session: Session) -> None:
        order = _make_order(db_session, "https://x/b.pdf")
        _gold(db_session, order.id, "corporate_debtor", "Correct Name Ltd")
        _extracted(db_session, order.id, "corporate_debtor", "Wrong Name Ltd")
        db_session.flush()

        metrics = compute_field_metrics(db_session, "corporate_debtor")

        assert metrics.precision == 0.0
        assert metrics.recall == 1.0  # we did claim something for this field

    def test_missing_extraction_hurts_recall_not_precision(
        self, db_session: Session
    ) -> None:
        order = _make_order(db_session, "https://x/c.pdf")
        _gold(db_session, order.id, "corporate_debtor", "Some Name Ltd")
        db_session.flush()

        metrics = compute_field_metrics(db_session, "corporate_debtor")

        assert metrics.claimed == 0
        assert metrics.precision is None
        assert metrics.recall == 0.0

    def test_no_gold_labels_reports_none(self, db_session: Session) -> None:
        metrics = compute_field_metrics(db_session, "resolution_professional")
        assert metrics.gold_present == 0
        assert metrics.recall is None

    def test_claim_amount_within_tolerance_counts_as_correct(
        self, db_session: Session
    ) -> None:
        order = _make_order(db_session, "https://x/d.pdf")
        _gold(db_session, order.id, "claim_amount", "26,42,000")
        _extracted(
            db_session,
            order.id,
            "claim_amount",
            "Rs. 26.42 lakhs",
            value_numeric=Decimal("2642000"),
        )
        db_session.flush()

        metrics = compute_field_metrics(db_session, "claim_amount")

        assert metrics.correct_within_tolerance == 1
        assert metrics.within_tolerance_rate == 1.0
        # exact string match fails ("Rs. 26.42 lakhs" != "26,42,000") even
        # though the underlying value is identical - exact and tolerance
        # are genuinely different metrics.
        assert metrics.correct_exact == 0

    def test_claim_amount_outside_tolerance_is_wrong(self, db_session: Session) -> None:
        order = _make_order(db_session, "https://x/e.pdf")
        _gold(db_session, order.id, "claim_amount", "26,42,000")
        _extracted(
            db_session,
            order.id,
            "claim_amount",
            "Rs. 50,00,000",
            value_numeric=Decimal("5000000"),
        )
        db_session.flush()

        metrics = compute_field_metrics(db_session, "claim_amount")

        assert metrics.correct_within_tolerance == 0

    def test_non_numeric_field_has_no_tolerance_rate(self, db_session: Session) -> None:
        order = _make_order(db_session, "https://x/f.pdf")
        _gold(db_session, order.id, "section_invoked", "Section 7")
        _extracted(db_session, order.id, "section_invoked", "Section 7")
        db_session.flush()

        metrics = compute_field_metrics(db_session, "section_invoked")

        assert metrics.within_tolerance_rate is None
        assert metrics.correct_within_tolerance is None
