from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pages_scanned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    orders_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    orders_new: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    orders_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    orders_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llm_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    watermark: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
