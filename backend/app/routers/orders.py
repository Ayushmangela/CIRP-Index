from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import EvidenceItem, OrderEvidenceResponse, OrderSummary
from models.extraction import Evidence, ExtractedField
from models.order import Order

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.get("/{order_id}", response_model=OrderSummary)
def get_order(order_id: int, db: Session = Depends(get_db)) -> OrderSummary:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderSummary.model_validate(order)


@router.get("/{order_id}/evidence", response_model=OrderEvidenceResponse)
def get_order_evidence(
    order_id: int, db: Session = Depends(get_db)
) -> OrderEvidenceResponse:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    rows = db.execute(
        select(ExtractedField, Evidence)
        .join(Evidence, Evidence.extracted_field_id == ExtractedField.id)
        .where(ExtractedField.order_id == order_id, ExtractedField.verified.is_(True))
    ).all()

    fields = [
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
        for field, evidence in rows
    ]

    return OrderEvidenceResponse(order_id=order_id, fields=fields)
