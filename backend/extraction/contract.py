"""The extraction contract - see docs/EXTRACTION_CONTRACT.md.

Every field the model returns carries a verbatim quote and the page it came
from. This module only validates shape; the verifier (verifier.py) is what
decides whether a quote is trustworthy.
"""

from pydantic import BaseModel, ConfigDict, field_validator

FIELDS_TO_EXTRACT: list[str] = [
    "corporate_debtor",
    "applicant_creditor",
    "creditor_type",
    "claim_amount",
    "section_invoked",
    "resolution_professional",
    "adjudicating_authority_bench",
    "admission_date",
    "order_type",
]


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quote: str
    page: int

    @field_validator("quote")
    @classmethod
    def quote_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("evidence.quote must not be blank")
        return value

    @field_validator("page")
    @classmethod
    def page_is_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("evidence.page must be a 1-based page number")
        return value


class ExtractedFieldLLM(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    value_text: str
    evidence: Evidence

    @field_validator("value_text")
    @classmethod
    def value_text_not_empty(cls, value: str) -> str:
        if not value.strip():
            # Per docs/EXTRACTION_CONTRACT.md: "An empty string is a bug."
            # A field the model can't find belongs in `not_found`, not here
            # with an empty value_text.
            raise ValueError("value_text must not be empty - use not_found instead")
        return value


class LLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields: list[ExtractedFieldLLM] = []
    not_found: list[str] = []

    @field_validator("not_found")
    @classmethod
    def not_found_entries_not_blank(cls, value: list[str]) -> list[str]:
        for entry in value:
            if not entry.strip():
                raise ValueError("not_found entries must not be blank")
        return value
