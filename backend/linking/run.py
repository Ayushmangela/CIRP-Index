"""Case linking. See docs/BUILD_PROMPTS.md Prompt 7.

Links orders into cases, in priority order:
1+2. Exact case_number match after normalisation - a sub-application's
     "X in Y" parent reference groups it under the same case as a direct
     mention of Y, via case_aliases (no orders.case_id column exists per
     docs/SCHEMA.md - membership is an alias lookup, not a foreign key).
3.   Corporate-debtor-name fuzzy match within the same bench (pg_trgm,
     threshold 0.85). Never auto-links - writes a LinkReviewQueue row with
     the similarity score for a human to confirm.

cases.current_outcome is derived from the most recent order **by
order_date**, not insertion order.
"""

import argparse
import logging
from collections import defaultdict
from datetime import date

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from models.case import Case, CaseAlias, LinkReviewQueue
from models.enums import LinkReviewStatusEnum
from models.order import Order
from parsing.case_number import normalise_case_number, split_parent_case
from parsing.subject_debtor import extract_debtor_name

logger = logging.getLogger(__name__)

FUZZY_SIMILARITY_THRESHOLD = 0.85


def grouping_key(order: Order) -> str | None:
    """Normalised case number this order groups under - the parent's
    number for a sub-application, otherwise its own. None if the order has
    no parsed case_number at all."""
    if not order.case_number:
        return None
    split = split_parent_case(order.case_number)
    target = split[1] if split else order.case_number
    return normalise_case_number(target) or None


def canonical_case_number(group_orders: list[Order]) -> str:
    """Prefer a direct (non-child) reference within the group; fall back to
    the parent portion of the first child reference if every order in the
    group is itself a sub-application."""
    for order in group_orders:
        if order.case_number and split_parent_case(order.case_number) is None:
            return order.case_number

    first = group_orders[0]
    split = split_parent_case(first.case_number) if first.case_number else None
    return split[1] if split else (first.case_number or "")


def update_case_aggregates(case: Case, group_orders: list[Order]) -> None:
    if not case.bench:
        for order in group_orders:
            if order.bench:
                case.bench = order.bench
                break

    dated_orders = [o for o in group_orders if o.order_date]
    if dated_orders:
        dates: list[date] = [o.order_date for o in dated_orders if o.order_date]
        case.first_order_date = min(dates)
        case.latest_order_date = max(dates)
        most_recent = max(dated_orders, key=lambda o: o.order_date)  # type: ignore[arg-type,return-value]
        case.current_outcome = most_recent.outcome


def link_by_case_number(
    db: Session, orders: list[Order]
) -> tuple[int, int, list[Order]]:
    """Rule 1+2. Returns (cases_created, orders_linked, orders_without_case_number)."""
    groups: dict[str, list[Order]] = defaultdict(list)
    without_case_number: list[Order] = []

    for order in orders:
        key = grouping_key(order)
        if key is None:
            without_case_number.append(order)
        else:
            groups[key].append(order)

    existing_aliases: dict[str, int] = {
        row.alias_text: row.case_id for row in db.execute(select(CaseAlias)).scalars()
    }
    existing_canonical: dict[str, int] = {
        normalise_case_number(c.canonical_case_number): c.id
        for c in db.execute(select(Case)).scalars()
        if c.canonical_case_number
    }

    cases_created = 0
    orders_linked = 0

    for normalised_key, group_orders in groups.items():
        case_id = existing_aliases.get(normalised_key) or existing_canonical.get(
            normalised_key
        )

        if case_id is None:
            first = group_orders[0]
            debtor_name = extract_debtor_name(first.subject_raw) or "Unknown"
            new_case = Case(
                canonical_case_number=canonical_case_number(group_orders),
                corporate_debtor_name=debtor_name,
            )
            db.add(new_case)
            db.flush()
            case_id = new_case.id
            cases_created += 1
            existing_canonical[normalised_key] = case_id
            case = new_case
        else:
            existing_case = db.get(Case, case_id)
            assert existing_case is not None
            case = existing_case

        raw_numbers = {o.case_number for o in group_orders if o.case_number}
        for raw in raw_numbers:
            norm = normalise_case_number(raw)
            if norm and norm not in existing_aliases:
                db.add(
                    CaseAlias(
                        case_id=case_id, alias_text=norm, alias_type="case_number"
                    )
                )
                existing_aliases[norm] = case_id

        update_case_aggregates(case, group_orders)
        orders_linked += len(group_orders)

    return cases_created, orders_linked, without_case_number


def find_fuzzy_candidates(db: Session, order: Order) -> list[tuple[int, float]]:
    debtor_name = extract_debtor_name(order.subject_raw)
    if not debtor_name or not order.bench:
        return []

    rows = db.execute(
        text(
            """
            SELECT id, similarity(corporate_debtor_name, :name) AS sim
            FROM cases
            WHERE bench = :bench
              AND similarity(corporate_debtor_name, :name) > :threshold
            ORDER BY sim DESC
            """
        ),
        {
            "name": debtor_name,
            "bench": order.bench,
            "threshold": FUZZY_SIMILARITY_THRESHOLD,
        },
    ).all()
    return [(row.id, row.sim) for row in rows]


def link_by_fuzzy_name(db: Session, orders: list[Order]) -> tuple[int, int]:
    """Rule 3. Never auto-links. Returns (review_queue_entries,
    orders_with_no_candidate)."""
    existing_queue_pairs: set[tuple[int, int]] = {
        (row.order_id, row.candidate_case_id)
        for row in db.execute(select(LinkReviewQueue)).scalars()
    }

    review_queue_entries = 0
    orders_with_no_candidate = 0

    for order in orders:
        candidates = find_fuzzy_candidates(db, order)
        if not candidates:
            orders_with_no_candidate += 1
            continue

        for case_id, similarity in candidates:
            if (order.id, case_id) in existing_queue_pairs:
                continue
            db.add(
                LinkReviewQueue(
                    order_id=order.id,
                    candidate_case_id=case_id,
                    similarity=similarity,
                    status=LinkReviewStatusEnum.pending,
                )
            )
            existing_queue_pairs.add((order.id, case_id))
            review_queue_entries += 1

    return review_queue_entries, orders_with_no_candidate


def run(db: Session) -> None:
    orders = list(db.execute(select(Order)).scalars())

    cases_created, orders_linked, without_case_number = link_by_case_number(db, orders)
    db.commit()

    review_queue_entries, orders_with_no_candidate = link_by_fuzzy_name(
        db, without_case_number
    )
    db.commit()

    logger.info("orders considered: %d", len(orders))
    logger.info("cases created/updated: %d", cases_created)
    logger.info("orders linked by case_number (rules 1+2): %d", orders_linked)
    logger.info(
        "orders without a case_number, sent to fuzzy matching (rule 3): %d",
        len(without_case_number),
    )
    logger.info("review queue candidates written: %d", review_queue_entries)
    logger.info(
        "orders left completely unlinked (no case_number, no fuzzy candidate): %d",
        orders_with_no_candidate,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Link orders into cases.")
    parser.parse_args()

    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")

    db = SessionLocal()
    try:
        run(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
