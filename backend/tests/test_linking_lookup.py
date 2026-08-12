from datetime import datetime, timezone

from sqlalchemy.orm import Session

from linking.lookup import (
    build_alias_index,
    build_case_orders_index,
    orders_for_case,
    resolve_case_id,
)
from linking.run import link_by_case_number
from models.enums import ProcessingStatusEnum
from models.order import Order


def _make_order(db: Session, pdf_url: str, case_number: str | None) -> Order:
    order = Order(
        subject_raw="In the matter of Test Co",
        case_number=case_number,
        pdf_url=pdf_url,
        processing_status=ProcessingStatusEnum.discovered,
        retrieved_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.flush()
    return order


class TestResolveCaseId:
    def test_linked_order_resolves_to_its_case(self, db_session: Session) -> None:
        order = _make_order(db_session, "https://x/a.pdf", "CP (IB)/1/AB/2020")
        link_by_case_number(db_session, [order])
        db_session.flush()

        alias_index = build_alias_index(db_session)
        case_id = resolve_case_id(order, alias_index)

        assert case_id is not None

    def test_order_without_case_number_resolves_to_none(
        self, db_session: Session
    ) -> None:
        order = _make_order(db_session, "https://x/b.pdf", None)
        alias_index = build_alias_index(db_session)
        assert resolve_case_id(order, alias_index) is None

    def test_unlinked_order_with_case_number_resolves_to_none(
        self, db_session: Session
    ) -> None:
        order = _make_order(db_session, "https://x/c.pdf", "CP (IB)/99/ZZ/2099")
        alias_index = build_alias_index(db_session)
        assert resolve_case_id(order, alias_index) is None


class TestOrdersForCase:
    def test_returns_all_orders_in_the_case(self, db_session: Session) -> None:
        parent = _make_order(db_session, "https://x/parent.pdf", "CP (IB)/2/AB/2020")
        child = _make_order(
            db_session,
            "https://x/child.pdf",
            "IA No. 1/2021 in CP (IB)/2/AB/2020",
        )
        link_by_case_number(db_session, [parent, child])
        db_session.flush()

        alias_index = build_alias_index(db_session)
        case_id = resolve_case_id(parent, alias_index)
        assert case_id is not None

        result = orders_for_case(db_session, case_id)
        result_ids = {o.id for o in result}
        assert result_ids == {parent.id, child.id}


class TestBuildCaseOrdersIndex:
    def test_groups_orders_by_case(self, db_session: Session) -> None:
        a = _make_order(db_session, "https://x/d.pdf", "CP (IB)/3/AB/2020")
        b = _make_order(db_session, "https://x/e.pdf", "CP (IB)/4/AB/2020")
        link_by_case_number(db_session, [a, b])
        db_session.flush()

        index = build_case_orders_index(db_session)
        all_order_ids = {o.id for orders in index.values() for o in orders}
        assert a.id in all_order_ids
        assert b.id in all_order_ids
        # each in its own case (different case numbers)
        cases_with_a = [cid for cid, orders in index.items() if a in orders]
        cases_with_b = [cid for cid, orders in index.items() if b in orders]
        assert cases_with_a != cases_with_b
