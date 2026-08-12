"""Order <-> case resolution for the API layer.

There's no orders.case_id column (see docs/SCHEMA.md) - membership is via
case_aliases (normalised case_number -> case_id), populated by
linking/run.py. This module is the single place that resolves it, reused
by every endpoint that needs to cross the order/case boundary, so the
normalisation logic never has to be duplicated in SQL.

Deliberately Python-side, not a SQL join: the corpus is currently ~100
orders/cases. If it grows into the thousands, this mapping should move into
either a materialised lookup table or SQL-side normalisation - a schema
change to propose then, not something to pre-optimise now.
"""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.case import CaseAlias
from models.order import Order
from parsing.case_number import normalise_case_number


def build_alias_index(db: Session) -> dict[str, int]:
    return {
        row.alias_text: row.case_id for row in db.execute(select(CaseAlias)).scalars()
    }


def resolve_case_id(order: Order, alias_index: dict[str, int]) -> int | None:
    if not order.case_number:
        return None
    return alias_index.get(normalise_case_number(order.case_number))


def build_case_orders_index(db: Session) -> dict[int, list[Order]]:
    """case_id -> every order that resolves to it."""
    alias_index = build_alias_index(db)
    orders = db.execute(select(Order)).scalars().all()

    index: dict[int, list[Order]] = defaultdict(list)
    for order in orders:
        case_id = resolve_case_id(order, alias_index)
        if case_id is not None:
            index[case_id].append(order)

    return dict(index)


def orders_for_case(db: Session, case_id: int) -> list[Order]:
    alias_index = build_alias_index(db)
    orders = db.execute(select(Order)).scalars().all()
    return [o for o in orders if resolve_case_id(o, alias_index) == case_id]
