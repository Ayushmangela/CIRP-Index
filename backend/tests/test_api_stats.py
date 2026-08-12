from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from linking.run import link_by_case_number
from models.enums import OutcomeEnum, ProcessingStatusEnum
from models.order import Order


def _make_order(
    db: Session,
    pdf_url: str,
    case_number: str,
    bench: str,
    order_date: date,
    outcome: OutcomeEnum = OutcomeEnum.admitted,
) -> Order:
    order = Order(
        subject_raw="In the matter of Test Co",
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


class TestBenchStats:
    def test_returns_case_count_per_bench(
        self, db_session: Session, api_client: TestClient
    ) -> None:
        a = _make_order(
            db_session, "https://x/a.pdf", "CP (IB)/1/QQ/2025", "QQ", date(2025, 1, 1)
        )
        b = _make_order(
            db_session, "https://x/b.pdf", "CP (IB)/2/QQ/2025", "QQ", date(2025, 6, 1)
        )
        link_by_case_number(db_session, [a, b])
        db_session.flush()

        response = api_client.get("/api/v1/stats/benches")

        assert response.status_code == 200
        qq_stat = next(s for s in response.json() if s["bench"] == "QQ")
        assert qq_stat["case_count"] == 2

    def test_median_duration_computed(
        self, db_session: Session, api_client: TestClient
    ) -> None:
        parent = _make_order(
            db_session,
            "https://x/c.pdf",
            "CP (IB)/3/RR/2025",
            "RR",
            date(2025, 1, 1),
        )
        child = _make_order(
            db_session,
            "https://x/d.pdf",
            "IA No. 1/2025 in CP (IB)/3/RR/2025",
            "RR",
            date(2025, 1, 31),
        )
        link_by_case_number(db_session, [parent, child])
        db_session.flush()

        response = api_client.get("/api/v1/stats/benches")
        rr_stat = next(s for s in response.json() if s["bench"] == "RR")
        assert rr_stat["median_duration_days"] == 30


class TestOutcomesByYear:
    def test_groups_by_year_and_outcome(
        self, db_session: Session, api_client: TestClient
    ) -> None:
        _make_order(
            db_session,
            "https://x/e.pdf",
            "CP (IB)/5/SS/2024",
            "SS",
            date(2024, 3, 1),
            outcome=OutcomeEnum.admitted,
        )
        _make_order(
            db_session,
            "https://x/f.pdf",
            "CP (IB)/6/SS/2024",
            "SS",
            date(2024, 5, 1),
            outcome=OutcomeEnum.liquidation,
        )
        db_session.flush()

        response = api_client.get("/api/v1/stats/outcomes-by-year")

        assert response.status_code == 200
        rows = response.json()
        matching = [r for r in rows if r["year"] == 2024]
        outcomes = {r["outcome"] for r in matching}
        assert "admitted" in outcomes
        assert "liquidation" in outcomes
