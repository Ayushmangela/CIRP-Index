from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from models.enums import OutcomeEnum, ProcessingStatusEnum


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    subject_raw: Mapped[str] = mapped_column(Text, nullable=False)
    case_number: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    bench: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    pdf_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    pdf_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    remarks_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outcome: Mapped[OutcomeEnum] = mapped_column(
        Enum(OutcomeEnum, name="outcome_enum"),
        default=OutcomeEnum.unclassified,
        nullable=False,
        index=True,
    )
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_scanned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processing_status: Mapped[ProcessingStatusEnum] = mapped_column(
        Enum(ProcessingStatusEnum, name="processing_status_enum"),
        default=ProcessingStatusEnum.discovered,
        nullable=False,
    )
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    source_listing_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    pages: Mapped[List["OrderPage"]] = relationship(
        "OrderPage", back_populates="order", cascade="all, delete-orphan"
    )


class OrderPage(Base):
    __tablename__ = "order_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="pages")
