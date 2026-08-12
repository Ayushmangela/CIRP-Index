from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    case_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("cases.id", ondelete="SET NULL"), nullable=True
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_numeric: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    value_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    confidence_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    evidences: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="extracted_field", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("extracted_fields_case_id_field_name_idx", "case_id", "field_name"),
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    extracted_field_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("extracted_fields.id", ondelete="CASCADE"),
        nullable=False,
    )
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    char_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    extracted_field: Mapped["ExtractedField"] = relationship(
        "ExtractedField", back_populates="evidences"
    )


class GoldLabel(Base):
    __tablename__ = "gold_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    expected_value: Mapped[str] = mapped_column(Text, nullable=False)
    labelled_by: Mapped[str] = mapped_column(String(100), nullable=False)
    labelled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
