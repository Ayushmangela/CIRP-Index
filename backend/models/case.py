from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from models.enums import LinkReviewStatusEnum, OutcomeEnum


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    canonical_case_number: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    corporate_debtor_name: Mapped[str] = mapped_column(String(512), nullable=False)
    bench: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_order_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    latest_order_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    current_outcome: Mapped[Optional[OutcomeEnum]] = mapped_column(
        Enum(OutcomeEnum, name="outcome_enum"), nullable=True
    )

    aliases: Mapped[List["CaseAlias"]] = relationship(
        "CaseAlias", back_populates="case", cascade="all, delete-orphan"
    )


class CaseAlias(Base):
    __tablename__ = "case_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False
    )
    alias_text: Mapped[str] = mapped_column(String(512), nullable=False)
    alias_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    case: Mapped["Case"] = relationship("Case", back_populates="aliases")


class LinkReviewQueue(Base):
    __tablename__ = "link_review_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    candidate_case_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False
    )
    similarity: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[LinkReviewStatusEnum] = mapped_column(
        Enum(LinkReviewStatusEnum, name="link_review_status_enum"),
        default=LinkReviewStatusEnum.pending,
        nullable=False,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
