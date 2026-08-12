"""API response models. Pydantic v2 on every boundary - see AGENTS.md."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from models.enums import OutcomeEnum, ProcessingStatusEnum


class CaseSummary(BaseModel):
    """One row in the search-results table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    corporate_debtor_name: str
    canonical_case_number: str | None
    bench: str | None
    current_outcome: OutcomeEnum | None
    first_order_date: date | None
    latest_order_date: date | None
    order_count: int


class OutcomeCount(BaseModel):
    outcome: OutcomeEnum
    count: int


class PaginatedCases(BaseModel):
    items: list[CaseSummary]
    total: int
    page: int
    page_size: int
    outcome_counts: list[OutcomeCount]


class OrderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_date: date | None
    subject_raw: str
    case_number: str | None
    pdf_url: str
    outcome: OutcomeEnum
    page_count: int | None
    is_scanned: bool
    processing_status: ProcessingStatusEnum


class EvidenceItem(BaseModel):
    """A verified extracted field with the verbatim span it was matched
    against - the evidence panel's data source, the whole point of the
    product."""

    model_config = ConfigDict(from_attributes=True)

    field_name: str
    value_text: str | None
    value_numeric: Decimal | None
    order_id: int
    order_date: date | None
    page_number: int
    quote: str
    char_start: int | None
    char_end: int | None


class CaseDetail(BaseModel):
    id: int
    corporate_debtor_name: str
    canonical_case_number: str | None
    bench: str | None
    current_outcome: OutcomeEnum | None
    first_order_date: date | None
    latest_order_date: date | None
    orders: list[OrderSummary]
    evidence: list[EvidenceItem]


class OrderEvidenceResponse(BaseModel):
    order_id: int
    fields: list[EvidenceItem]


class BenchStat(BaseModel):
    bench: str
    case_count: int
    median_duration_days: float | None


class OutcomesByYear(BaseModel):
    year: int
    outcome: OutcomeEnum
    count: int
