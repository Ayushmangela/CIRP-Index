import pytest
from pydantic import ValidationError

from extraction.contract import Evidence, ExtractedFieldLLM, LLMResponse


class TestEvidence:
    def test_valid_evidence(self) -> None:
        ev = Evidence(quote="directed refund of Rs. 26,42,000/-", page=4)
        assert ev.page == 4

    def test_blank_quote_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Evidence(quote="   ", page=4)

    def test_zero_page_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Evidence(quote="some quote text here", page=0)

    def test_negative_page_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Evidence(quote="some quote text here", page=-1)

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Evidence(quote="some quote", page=1, confidence=0.9)  # type: ignore[call-arg]


class TestExtractedFieldLLM:
    def test_valid_field(self) -> None:
        item = ExtractedFieldLLM(
            field="claim_amount",
            value_text="Rs. 26,42,000/-",
            evidence=Evidence(quote="directed refund of Rs. 26,42,000/-", page=4),
        )
        assert item.field == "claim_amount"

    def test_empty_value_text_is_a_bug_and_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExtractedFieldLLM(
                field="claim_amount",
                value_text="",
                evidence=Evidence(quote="some quote here", page=1),
            )

    def test_whitespace_only_value_text_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExtractedFieldLLM(
                field="claim_amount",
                value_text="   ",
                evidence=Evidence(quote="some quote here", page=1),
            )


class TestLLMResponse:
    def test_valid_response(self) -> None:
        response = LLMResponse.model_validate(
            {
                "fields": [
                    {
                        "field": "claim_amount",
                        "value_text": "Rs. 26,42,000/-",
                        "evidence": {
                            "quote": "directed refund of Rs. 26,42,000/-",
                            "page": 4,
                        },
                    }
                ],
                "not_found": ["resolution_professional"],
            }
        )
        assert len(response.fields) == 1
        assert response.not_found == ["resolution_professional"]

    def test_defaults_to_empty_lists(self) -> None:
        response = LLMResponse.model_validate({})
        assert response.fields == []
        assert response.not_found == []

    def test_empty_string_in_not_found_is_a_bug(self) -> None:
        with pytest.raises(ValidationError):
            LLMResponse.model_validate({"fields": [], "not_found": [""]})

    def test_extra_top_level_key_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LLMResponse.model_validate({"fields": [], "not_found": [], "confidence": 1})
