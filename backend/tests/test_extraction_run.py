from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from extraction.contract import Evidence, ExtractedFieldLLM, LLMResponse
from extraction.run import process_order_extraction
from models.enums import ProcessingStatusEnum
from models.extraction import Evidence as EvidenceModel
from models.extraction import ExtractedField
from models.order import Order


def _make_order(db: Session) -> Order:
    order = Order(
        subject_raw="In the matter of Test Co [CP (IB) 1/AB/2024]",
        pdf_url="https://ibbi.gov.in/uploads/order/test.pdf",
        processing_status=ProcessingStatusEnum.text_extracted,
        retrieved_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.flush()
    return order


class TestProcessOrderExtractionVerified:
    def test_verified_field_persists_field_and_evidence(
        self, db_session: Session
    ) -> None:
        order = _make_order(db_session)
        pages = {4: "the tribunal directed refund of Rs. 26,42,000/- towards costs"}
        response = LLMResponse(
            fields=[
                ExtractedFieldLLM(
                    field="claim_amount",
                    value_text="Rs. 26,42,000/-",
                    evidence=Evidence(
                        quote="directed refund of Rs. 26,42,000/- towards costs",
                        page=4,
                    ),
                )
            ],
            not_found=[],
        )

        summary = process_order_extraction(order, pages, response, db_session)
        db_session.flush()

        assert summary.attempted == 1
        assert summary.verified == 1
        assert summary.rejected == []

        stored = (
            db_session.query(ExtractedField)
            .filter(ExtractedField.order_id == order.id)
            .one()
        )
        assert stored.field_name == "claim_amount"
        assert stored.value_text == "Rs. 26,42,000/-"
        assert stored.verified is True
        assert stored.extraction_method == "llm"

        evidence = (
            db_session.query(EvidenceModel)
            .filter(EvidenceModel.extracted_field_id == stored.id)
            .one()
        )
        assert evidence.page_number == 4
        assert evidence.char_start is not None

    def test_claim_amount_routed_through_indian_numbers_parser(
        self, db_session: Session
    ) -> None:
        order = _make_order(db_session)
        pages = {1: "the amount claimed was Rs. 26.42 lakhs as per the ledger"}
        response = LLMResponse(
            fields=[
                ExtractedFieldLLM(
                    field="claim_amount",
                    value_text="Rs. 26.42 lakhs",
                    evidence=Evidence(
                        quote="the amount claimed was Rs. 26.42 lakhs as per",
                        page=1,
                    ),
                )
            ],
            not_found=[],
        )

        process_order_extraction(order, pages, response, db_session)
        db_session.flush()

        stored = (
            db_session.query(ExtractedField)
            .filter(ExtractedField.order_id == order.id)
            .one()
        )
        assert stored.value_numeric == Decimal("2642000")

    def test_non_money_field_leaves_value_numeric_null(
        self, db_session: Session
    ) -> None:
        order = _make_order(db_session)
        pages = {2: "the corporate debtor is Test Manufacturing Private Limited"}
        response = LLMResponse(
            fields=[
                ExtractedFieldLLM(
                    field="corporate_debtor",
                    value_text="Test Manufacturing Private Limited",
                    evidence=Evidence(
                        quote=(
                            "the corporate debtor is Test Manufacturing Private Limited"
                        ),
                        page=2,
                    ),
                )
            ],
            not_found=[],
        )

        process_order_extraction(order, pages, response, db_session)
        db_session.flush()

        stored = (
            db_session.query(ExtractedField)
            .filter(ExtractedField.order_id == order.id)
            .one()
        )
        assert stored.value_numeric is None


class TestProcessOrderExtractionRejected:
    def test_unverified_quote_persists_no_value(self, db_session: Session) -> None:
        order = _make_order(db_session)
        pages = {1: "completely different text with no relation to the quote"}
        response = LLMResponse(
            fields=[
                ExtractedFieldLLM(
                    field="claim_amount",
                    value_text="Rs. 99,00,000/-",
                    evidence=Evidence(
                        quote="a quote that does not appear anywhere on the page",
                        page=1,
                    ),
                )
            ],
            not_found=[],
        )

        summary = process_order_extraction(order, pages, response, db_session)
        db_session.flush()

        assert summary.verified == 0
        assert len(summary.rejected) == 1
        assert summary.rejected[0][0] == "claim_amount"

        count = (
            db_session.query(ExtractedField)
            .filter(ExtractedField.order_id == order.id)
            .count()
        )
        assert count == 0

    def test_not_found_fields_are_tracked_not_persisted(
        self, db_session: Session
    ) -> None:
        order = _make_order(db_session)
        response = LLMResponse(fields=[], not_found=["resolution_professional"])

        summary = process_order_extraction(order, {}, response, db_session)

        assert summary.attempted == 0
        assert summary.not_found == ["resolution_professional"]
        count = (
            db_session.query(ExtractedField)
            .filter(ExtractedField.order_id == order.id)
            .count()
        )
        assert count == 0
