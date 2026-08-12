from collections import Counter
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    CaseDetail,
    CaseSummary,
    EvidenceItem,
    OrderSummary,
    OutcomeCount,
    PaginatedCases,
)
from linking.lookup import build_case_orders_index, orders_for_case
from models.case import Case
from models.enums import OutcomeEnum
from models.extraction import Evidence, ExtractedField
from models.order import Order

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


@router.get("", response_model=PaginatedCases)
def list_cases(
    q: str | None = Query(None, description="Search corporate debtor name"),
    outcome: OutcomeEnum | None = Query(None),
    bench: str | None = Query(None),
    year: int | None = Query(None, description="Any linked order in this year"),
    min_amount: float | None = Query(
        None, description="Any linked order's verified claim_amount >= this"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PaginatedCases:
    stmt = select(Case)
    if outcome is not None:
        stmt = stmt.where(Case.current_outcome == outcome)
    if bench is not None:
        stmt = stmt.where(Case.bench == bench)
    if q:
        stmt = stmt.where(Case.corporate_debtor_name.ilike(f"%{q}%"))

    cases = list(db.execute(stmt).scalars())

    case_orders_index = build_case_orders_index(db)

    if year is not None:
        cases = [
            c
            for c in cases
            if any(
                o.order_date and o.order_date.year == year
                for o in case_orders_index.get(c.id, [])
            )
        ]

    if min_amount is not None:
        order_ids_over_amount = _order_ids_with_claim_amount_at_least(db, min_amount)
        cases = [
            c
            for c in cases
            if any(
                o.id in order_ids_over_amount for o in case_orders_index.get(c.id, [])
            )
        ]

    cases.sort(
        key=lambda c: c.latest_order_date or date_type.min,
        reverse=True,
    )

    total = len(cases)
    start = (page - 1) * page_size
    page_cases = cases[start : start + page_size]

    items = [
        CaseSummary(
            id=c.id,
            corporate_debtor_name=c.corporate_debtor_name,
            canonical_case_number=c.canonical_case_number,
            bench=c.bench,
            current_outcome=c.current_outcome,
            first_order_date=c.first_order_date,
            latest_order_date=c.latest_order_date,
            order_count=len(case_orders_index.get(c.id, [])),
        )
        for c in page_cases
    ]

    all_cases = list(db.execute(select(Case)).scalars())
    outcome_counts = Counter(c.current_outcome for c in all_cases if c.current_outcome)
    outcome_counts_list = [
        OutcomeCount(outcome=outcome_value, count=count)
        for outcome_value, count in outcome_counts.items()
    ]

    return PaginatedCases(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        outcome_counts=outcome_counts_list,
    )


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(case_id: int, db: Session = Depends(get_db)) -> CaseDetail:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    orders = orders_for_case(db, case_id)
    order_ids = [o.id for o in orders]

    evidence = _evidence_for_orders(db, order_ids)

    return CaseDetail(
        id=case.id,
        corporate_debtor_name=case.corporate_debtor_name,
        canonical_case_number=case.canonical_case_number,
        bench=case.bench,
        current_outcome=case.current_outcome,
        first_order_date=case.first_order_date,
        latest_order_date=case.latest_order_date,
        orders=[OrderSummary.model_validate(o) for o in orders],
        evidence=evidence,
    )


@router.get("/{case_id}/orders", response_model=list[OrderSummary])
def get_case_orders(case_id: int, db: Session = Depends(get_db)) -> list[OrderSummary]:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    orders = orders_for_case(db, case_id)
    return [OrderSummary.model_validate(o) for o in orders]


def _order_ids_with_claim_amount_at_least(db: Session, min_amount: float) -> set[int]:
    rows = db.execute(
        select(ExtractedField.order_id).where(
            ExtractedField.field_name == "claim_amount",
            ExtractedField.value_numeric.isnot(None),
            ExtractedField.value_numeric >= min_amount,
            ExtractedField.verified.is_(True),
        )
    ).scalars()
    return {order_id for order_id in rows if order_id is not None}


def _evidence_for_orders(db: Session, order_ids: list[int]) -> list[EvidenceItem]:
    if not order_ids:
        return []

    rows = db.execute(
        select(ExtractedField, Evidence, Order)
        .join(Evidence, Evidence.extracted_field_id == ExtractedField.id)
        .join(Order, Order.id == ExtractedField.order_id)
        .where(
            ExtractedField.order_id.in_(order_ids), ExtractedField.verified.is_(True)
        )
    ).all()

    return [
        EvidenceItem(
            field_name=field.field_name,
            value_text=field.value_text,
            value_numeric=field.value_numeric,
            order_id=order.id,
            order_date=order.order_date,
            page_number=evidence.page_number,
            quote=evidence.quote,
            char_start=evidence.char_start,
            char_end=evidence.char_end,
        )
        for field, evidence, order in rows
    ]
