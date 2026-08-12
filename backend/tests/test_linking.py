from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from linking.run import (
    canonical_case_number,
    grouping_key,
    link_by_case_number,
    link_by_fuzzy_name,
    run,
)
from models.case import Case, CaseAlias, LinkReviewQueue
from models.enums import OutcomeEnum, ProcessingStatusEnum
from models.order import Order


def _make_order(
    db: Session,
    pdf_url: str,
    subject_raw: str,
    case_number: str | None,
    bench: str | None = None,
    order_date: date | None = None,
    outcome: OutcomeEnum = OutcomeEnum.admitted,
) -> Order:
    order = Order(
        subject_raw=subject_raw,
        case_number=case_number,
        bench=bench,
        pdf_url=pdf_url,
        order_date=order_date,
        outcome=outcome,
        processing_status=ProcessingStatusEnum.discovered,
        retrieved_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.flush()
    return order


class TestGroupingKey:
    def test_direct_case_number(self, db_session: Session) -> None:
        order = _make_order(
            db_session, "https://x/a.pdf", "In the matter of X", "CP (IB)/1/AB/2020"
        )
        assert grouping_key(order) == normalise_expected("CP (IB)/1/AB/2020")

    def test_child_ia_groups_under_parent(self, db_session: Session) -> None:
        order = _make_order(
            db_session,
            "https://x/b.pdf",
            "In the matter of X",
            "IA No. 51/ND/2024 in CP (IB) No. 300/ND/2021",
        )
        assert grouping_key(order) == normalise_expected("CP (IB) 300/ND/2021")

    def test_no_case_number_returns_none(self, db_session: Session) -> None:
        order = _make_order(db_session, "https://x/c.pdf", "In the matter of X", None)
        assert grouping_key(order) is None


def normalise_expected(s: str) -> str:
    from parsing.case_number import normalise_case_number

    return normalise_case_number(s)


class TestLinkByCaseNumber:
    def test_direct_reference_and_child_ia_share_one_case(
        self, db_session: Session
    ) -> None:
        parent = _make_order(
            db_session,
            "https://x/parent.pdf",
            "In the matter of Test Co [CP (IB) No. 300/ND/2021]",
            "CP (IB) No. 300/ND/2021",
            bench="ND",
            order_date=date(2021, 1, 1),
        )
        child = _make_order(
            db_session,
            "https://x/child.pdf",
            "In the matter of Test Co [IA No. 51/ND/2024 in CP (IB) No. 300/ND/2021]",
            "IA No. 51/ND/2024 in CP (IB) No. 300/ND/2021",
            bench="ND",
            order_date=date(2024, 1, 1),
        )

        cases_created, orders_linked, unlinked = link_by_case_number(
            db_session, [parent, child]
        )
        db_session.flush()

        assert cases_created == 1
        assert orders_linked == 2
        assert unlinked == []

        cases = db_session.execute(select(Case)).scalars().all()
        assert len(cases) == 1
        assert cases[0].corporate_debtor_name == "Test Co"

    def test_two_different_cases_stay_separate(self, db_session: Session) -> None:
        a = _make_order(
            db_session,
            "https://x/a.pdf",
            "In the matter of Alpha Co [CP (IB)/1/AB/2020]",
            "CP (IB)/1/AB/2020",
        )
        b = _make_order(
            db_session,
            "https://x/bb.pdf",
            "In the matter of Beta Co [CP (IB)/2/AB/2020]",
            "CP (IB)/2/AB/2020",
        )

        cases_created, orders_linked, unlinked = link_by_case_number(db_session, [a, b])

        assert cases_created == 2
        assert orders_linked == 2
        assert unlinked == []

    def test_orders_without_case_number_are_returned_unlinked(
        self, db_session: Session
    ) -> None:
        order = _make_order(
            db_session, "https://x/none.pdf", "In the matter of X", None
        )
        cases_created, orders_linked, unlinked = link_by_case_number(
            db_session, [order]
        )
        assert cases_created == 0
        assert orders_linked == 0
        assert unlinked == [order]

    def test_current_outcome_from_most_recent_order_by_date_not_insertion(
        self, db_session: Session
    ) -> None:
        # Insert the LATER-dated order first, to prove insertion order
        # doesn't drive current_outcome - only order_date does.
        later = _make_order(
            db_session,
            "https://x/later.pdf",
            "In the matter of Test Co [CP (IB)/9/AB/2020]",
            "CP (IB)/9/AB/2020",
            order_date=date(2024, 6, 1),
            outcome=OutcomeEnum.liquidation,
        )
        earlier = _make_order(
            db_session,
            "https://x/earlier.pdf",
            "In the matter of Test Co [IA No. 1/2019 in CP (IB)/9/AB/2020]",
            "IA No. 1/2019 in CP (IB)/9/AB/2020",
            order_date=date(2019, 1, 1),
            outcome=OutcomeEnum.admitted,
        )

        link_by_case_number(db_session, [later, earlier])
        db_session.flush()

        case = db_session.execute(select(Case)).scalars().one()
        assert case.current_outcome == OutcomeEnum.liquidation
        assert case.first_order_date == date(2019, 1, 1)
        assert case.latest_order_date == date(2024, 6, 1)

    def test_rerun_is_idempotent_no_duplicate_cases(self, db_session: Session) -> None:
        order = _make_order(
            db_session,
            "https://x/idem.pdf",
            "In the matter of Test Co [CP (IB)/5/AB/2020]",
            "CP (IB)/5/AB/2020",
        )
        link_by_case_number(db_session, [order])
        db_session.flush()
        link_by_case_number(db_session, [order])
        db_session.flush()

        cases = db_session.execute(select(Case)).scalars().all()
        assert len(cases) == 1

    def test_aliases_written_for_every_distinct_case_number_in_group(
        self, db_session: Session
    ) -> None:
        parent = _make_order(
            db_session,
            "https://x/p2.pdf",
            "In the matter of Test Co [CP (IB)/7/AB/2020]",
            "CP (IB)/7/AB/2020",
        )
        child = _make_order(
            db_session,
            "https://x/c2.pdf",
            "In the matter of Test Co [IA No. 1/2021 in CP (IB)/7/AB/2020]",
            "IA No. 1/2021 in CP (IB)/7/AB/2020",
        )
        link_by_case_number(db_session, [parent, child])
        db_session.flush()

        aliases = db_session.execute(select(CaseAlias)).scalars().all()
        alias_texts = {a.alias_text for a in aliases}
        assert normalise_expected("CP (IB)/7/AB/2020") in alias_texts
        assert normalise_expected("IA No. 1/2021 in CP (IB)/7/AB/2020") in alias_texts


class TestCanonicalCaseNumber:
    def test_prefers_direct_reference_over_child(self, db_session: Session) -> None:
        child = _make_order(
            db_session,
            "https://x/child2.pdf",
            "In the matter of X",
            "IA No. 1/2021 in CP (IB)/7/AB/2020",
        )
        parent = _make_order(
            db_session,
            "https://x/parent2.pdf",
            "In the matter of X",
            "CP (IB)/7/AB/2020",
        )
        assert canonical_case_number([child, parent]) == "CP (IB)/7/AB/2020"

    def test_falls_back_to_parent_extracted_from_child_when_no_direct_ref(
        self,
    ) -> None:
        class Fake:
            case_number = "IA No. 1/2021 in CP (IB)/7/AB/2020"

        assert canonical_case_number([Fake()]) == "CP (IB)/7/AB/2020"  # type: ignore[list-item]


class TestLinkByFuzzyName:
    def test_similar_debtor_name_same_bench_creates_review_queue_entry(
        self, db_session: Session
    ) -> None:
        existing_case = Case(
            corporate_debtor_name="Alpha Manufacturing Private Limited", bench="MB"
        )
        db_session.add(existing_case)
        db_session.flush()

        candidate_order = _make_order(
            db_session,
            "https://x/fuzzy.pdf",
            "In the matter of Alpha Manufacturing Privte Limited",
            None,
            bench="MB",
        )

        entries, no_candidate = link_by_fuzzy_name(db_session, [candidate_order])
        db_session.flush()

        assert entries == 1
        assert no_candidate == 0

        queue = db_session.execute(select(LinkReviewQueue)).scalars().one()
        assert queue.order_id == candidate_order.id
        assert queue.candidate_case_id == existing_case.id
        assert queue.similarity > 0.85

    def test_never_auto_links_only_writes_review_queue(
        self, db_session: Session
    ) -> None:
        existing_case = Case(corporate_debtor_name="Beta Textiles Limited", bench="KB")
        db_session.add(existing_case)
        db_session.flush()

        candidate_order = _make_order(
            db_session,
            "https://x/fuzzy2.pdf",
            "In the matter of Beta Textiles Limited",
            None,
            bench="KB",
        )
        link_by_fuzzy_name(db_session, [candidate_order])
        db_session.flush()

        # order was NOT linked into the case directly - only a review
        # candidate exists
        queue = db_session.execute(select(LinkReviewQueue)).scalars().one()
        assert queue.status.value == "pending"

    def test_different_bench_does_not_match(self, db_session: Session) -> None:
        existing_case = Case(corporate_debtor_name="Gamma Foods Limited", bench="MB")
        db_session.add(existing_case)
        db_session.flush()

        candidate_order = _make_order(
            db_session,
            "https://x/fuzzy3.pdf",
            "In the matter of Gamma Foods Limited",
            None,
            bench="ND",
        )
        entries, no_candidate = link_by_fuzzy_name(db_session, [candidate_order])
        assert entries == 0
        assert no_candidate == 1

    def test_dissimilar_name_no_candidate(self, db_session: Session) -> None:
        existing_case = Case(
            corporate_debtor_name="Completely Different Company Ltd", bench="MB"
        )
        db_session.add(existing_case)
        db_session.flush()

        candidate_order = _make_order(
            db_session,
            "https://x/fuzzy4.pdf",
            "In the matter of Totally Unrelated Enterprises",
            None,
            bench="MB",
        )
        entries, no_candidate = link_by_fuzzy_name(db_session, [candidate_order])
        assert entries == 0
        assert no_candidate == 1

    def test_rerun_does_not_duplicate_review_queue_entries(
        self, db_session: Session
    ) -> None:
        existing_case = Case(
            corporate_debtor_name="Delta Chemicals Limited", bench="MB"
        )
        db_session.add(existing_case)
        db_session.flush()

        candidate_order = _make_order(
            db_session,
            "https://x/fuzzy5.pdf",
            "In the matter of Delta Chemicals Pvt Limited",
            None,
            bench="MB",
        )
        link_by_fuzzy_name(db_session, [candidate_order])
        db_session.flush()
        entries_second_run, _ = link_by_fuzzy_name(db_session, [candidate_order])
        db_session.flush()

        assert entries_second_run == 0
        queue = db_session.execute(select(LinkReviewQueue)).scalars().all()
        assert len(queue) == 1


class TestRunEndToEnd:
    def test_full_run_links_and_queues(self, db_session: Session) -> None:
        _make_order(
            db_session,
            "https://x/e2e1.pdf",
            "In the matter of Zeta Co [CP (IB)/1/ZZ/2020]",
            "CP (IB)/1/ZZ/2020",
            bench="ZZ",
        )
        existing_case = Case(
            corporate_debtor_name="Eta Manufacturing Limited", bench="ZZ"
        )
        db_session.add(existing_case)
        db_session.flush()
        _make_order(
            db_session,
            "https://x/e2e2.pdf",
            "In the matter of Etta Manufacturing Limited",
            None,
            bench="ZZ",
        )

        run(db_session)
        db_session.flush()

        cases = db_session.execute(select(Case)).scalars().all()
        assert len(cases) >= 2
        queue = db_session.execute(select(LinkReviewQueue)).scalars().all()
        assert len(queue) >= 1
