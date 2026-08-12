from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models.enums import OutcomeEnum, ProcessingStatusEnum
from models.extraction import Evidence, ExtractedField
from models.order import Order


def _make_order(db: Session, pdf_url: str, subject_raw: str) -> Order:
    order = Order(
        subject_raw=subject_raw,
        case_number="CP (IB)/1/AB/2025",
        pdf_url=pdf_url,
        order_date=date(2025, 1, 1),
        outcome=OutcomeEnum.admitted,
        processing_status=ProcessingStatusEnum.text_extracted,
        retrieved_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.flush()
    return order


class TestGetOrder:
    def test_returns_order(self, db_session: Session, api_client: TestClient) -> None:
        order = _make_order(db_session, "https://x/a.pdf", "In the matter of Test Co")

        response = api_client.get(f"/api/v1/orders/{order.id}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == order.id
        assert body["subject_raw"] == "In the matter of Test Co"

    def test_404_for_missing_order(self, api_client: TestClient) -> None:
        response = api_client.get("/api/v1/orders/999999")
        assert response.status_code == 404


class TestGetOrderEvidence:
    def test_returns_verified_fields_only(
        self, db_session: Session, api_client: TestClient
    ) -> None:
        order = _make_order(db_session, "https://x/b.pdf", "In the matter of Test Co")

        verified_field = ExtractedField(
            order_id=order.id,
            field_name="corporate_debtor",
            value_text="Test Co",
            verified=True,
            extraction_method="llm",
            extracted_at=datetime.now(timezone.utc),
        )
        db_session.add(verified_field)
        db_session.flush()
        db_session.add(
            Evidence(
                extracted_field_id=verified_field.id,
                order_id=order.id,
                page_number=2,
                quote="the corporate debtor Test Co is",
                char_start=10,
                char_end=40,
            )
        )
        db_session.flush()

        response = api_client.get(f"/api/v1/orders/{order.id}/evidence")

        assert response.status_code == 200
        body = response.json()
        assert body["order_id"] == order.id
        assert len(body["fields"]) == 1
        assert body["fields"][0]["field_name"] == "corporate_debtor"
        assert body["fields"][0]["quote"] == "the corporate debtor Test Co is"
        assert body["fields"][0]["page_number"] == 2

    def test_empty_when_no_extraction_yet(
        self, db_session: Session, api_client: TestClient
    ) -> None:
        order = _make_order(
            db_session, "https://x/c.pdf", "In the matter of No Extraction Co"
        )

        response = api_client.get(f"/api/v1/orders/{order.id}/evidence")

        assert response.status_code == 200
        assert response.json()["fields"] == []

    def test_404_for_missing_order(self, api_client: TestClient) -> None:
        response = api_client.get("/api/v1/orders/999999/evidence")
        assert response.status_code == 404
