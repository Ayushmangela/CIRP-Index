from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from linking.run import link_by_case_number
from models.enums import OutcomeEnum, ProcessingStatusEnum
from models.extraction import Evidence, ExtractedField
from models.order import Order


def _make_order(
    db: Session,
    pdf_url: str,
    case_number: str,
    subject_raw: str = "In the matter of Test Co",
    bench: str | None = "MB",
    order_date: date | None = date(2025, 1, 1),
    outcome: OutcomeEnum = OutcomeEnum.admitted,
) -> Order:
    order = Order(
        subject_raw=subject_raw,
        case_number=case_number,
        bench=bench,
        pdf_url=pdf_url,
        order_date=order_date,
        outcome=outcome,
        processing_status=ProcessingStatusEnum.text_extracted,
        retrieved_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.flush()
    return order


class TestListCases:
    def test_returns_linked_cases(
        self, db_session: Session, api_client: TestClient
    ) -> None:
        order = _make_order(
            db_session,
            "https://x/a.pdf",
            "CP (IB)/1/AB/2025",
            "In the matter of Alpha Co",
        )
        link_by_case_number(db_session, [order])
        db_session.flush()

        response = api_client.get("/api/v1/cases")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] >= 1
        names = [c["corporate_debtor_name"] for c in body["items"]]
        assert "Alpha Co" in names

    def test_filters_by_outcome(
        self, db_session: Session, api_client: TestClient
    ) -> None:
        admitted_order = _make_order(
            db_session,
            "https://x/b.pdf",
            "CP (IB)/2/AB/2025",
            "In the matter of Beta Co",
            outcome=OutcomeEnum.admitted,
        )
        liquidation_order = _make_order(
            db_session,
            "https://x/c.pdf",
            "CP (IB)/3/AB/2025",
            "In the matter of Gamma Co",
            outcome=OutcomeEnum.liquidation,
        )
        link_by_case_number(db_session, [admitted_order, liquidation_order])
        db_session.flush()

        response = api_client.get("/api/v1/cases", params={"outcome": "liquidation"})

        assert response.status_code == 200
        names = [c["corporate_debtor_name"] for c in response.json()["items"]]
        assert "Gamma Co" in names
        assert "Beta Co" not in names

    def test_filters_by_bench(
        self, db_session: Session, api_client: TestClient
    ) -> None:
        order = _make_order(
            db_session,
            "https://x/d.pdf",
            "CP (IB)/4/ND/2025",
            "In the matter of Delta Co",
            bench="ND",
        )
        link_by_case_number(db_session, [order])
        db_session.flush()

        response = api_client.get("/api/v1/cases", params={"bench": "ND"})
        names = [c["corporate_debtor_name"] for c in response.json()["items"]]
        assert "Delta Co" in names

        response2 = api_client.get("/api/v1/cases", params={"bench": "KB"})
        names2 = [c["corporate_debtor_name"] for c in response2.json()["items"]]
        assert "Delta Co" not in names2

    def test_search_by_debtor_name(
        self, db_session: Session, api_client: TestClient
    ) -> None:
        order = _make_order(
            db_session,
            "https://x/e.pdf",
            "CP (IB)/5/AB/2025",
            "In the matter of Uniquely Named Enterprises Ltd",
        )
        link_by_case_number(db_session, [order])
        db_session.flush()

        response = api_client.get("/api/v1/cases", params={"q": "Uniquely Named"})
        names = [c["corporate_debtor_name"] for c in response.json()["items"]]
        assert "Uniquely Named Enterprises Ltd" in names

    def test_pagination(self, db_session: Session, api_client: TestClient) -> None:
        response = api_client.get("/api/v1/cases", params={"page": 1, "page_size": 2})
        assert response.status_code == 200
        body = response.json()
        assert body["page"] == 1
        assert body["page_size"] == 2
        assert len(body["items"]) <= 2

    def test_outcome_counts_present(
        self, db_session: Session, api_client: TestClient
    ) -> None:
        order = _make_order(
            db_session,
            "https://x/f.pdf",
            "CP (IB)/6/AB/2025",
            "In the matter of Epsilon Co",
        )
        link_by_case_number(db_session, [order])
        db_session.flush()

        response = api_client.get("/api/v1/cases")
        body = response.json()
        assert "outcome_counts" in body
        assert isinstance(body["outcome_counts"], list)


class TestGetCase:
    def test_returns_case_with_orders_and_evidence(
        self, db_session: Session, api_client: TestClient
    ) -> None:
        order = _make_order(
            db_session,
            "https://x/g.pdf",
            "CP (IB)/7/AB/2025",
            "In the matter of Zeta Co",
        )
        link_by_case_number(db_session, [order])
        db_session.flush()

        field = ExtractedField(
            order_id=order.id,
            field_name="corporate_debtor",
            value_text="Zeta Co",
            verified=True,
            extraction_method="llm",
            extracted_at=datetime.now(timezone.utc),
        )
        db_session.add(field)
        db_session.flush()
        db_session.add(
            Evidence(
                extracted_field_id=field.id,
                order_id=order.id,
                page_number=1,
                quote="the corporate debtor Zeta Co",
            )
        )
        db_session.flush()

        cases_response = api_client.get("/api/v1/cases", params={"q": "Zeta Co"})
        case_id = cases_response.json()["items"][0]["id"]

        response = api_client.get(f"/api/v1/cases/{case_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["corporate_debtor_name"] == "Zeta Co"
        assert len(body["orders"]) == 1
        assert len(body["evidence"]) == 1
        assert body["evidence"][0]["quote"] == "the corporate debtor Zeta Co"

    def test_404_for_missing_case(self, api_client: TestClient) -> None:
        response = api_client.get("/api/v1/cases/999999")
        assert response.status_code == 404


class TestGetCaseOrders:
    def test_returns_orders_including_child_ia(
        self, db_session: Session, api_client: TestClient
    ) -> None:
        parent = _make_order(
            db_session,
            "https://x/h.pdf",
            "CP (IB)/8/AB/2025",
            "In the matter of Theta Co",
        )
        child = _make_order(
            db_session,
            "https://x/i.pdf",
            "IA No. 1/2025 in CP (IB)/8/AB/2025",
            "In the matter of Theta Co",
        )
        link_by_case_number(db_session, [parent, child])
        db_session.flush()

        cases_response = api_client.get("/api/v1/cases", params={"q": "Theta Co"})
        case_id = cases_response.json()["items"][0]["id"]

        response = api_client.get(f"/api/v1/cases/{case_id}/orders")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_404_for_missing_case(self, api_client: TestClient) -> None:
        response = api_client.get("/api/v1/cases/999999/orders")
        assert response.status_code == 404
