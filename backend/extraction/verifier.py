"""Span verification - see docs/EXTRACTION_CONTRACT.md and the
/span-verify skill. This is the rule the product depends on:

    A field without a matching verbatim quote is never persisted with a
    value. Matching is exact substring after whitespace and unicode
    normalisation. Fuzzy matching is not permitted. A near-match is a miss.

`char_start`/`char_end` are offsets into `normalise_text(page_text)`, not the
raw stored `order_pages.text` - callers that need to slice/highlight the
quote must normalise the page text the same way first. This is a deliberate
choice: PDF extraction preserves line breaks, but a verbatim quote read back
by an LLM commonly loses them (a genuine off-by-whitespace failure mode, not
a paraphrase), so both sides of the comparison live in normalised space.
"""

import re
from dataclasses import dataclass

_ZERO_WIDTH_CHARS = "​‌‍﻿"
_DASH_CHARS = "‐‑‒–—−"
_SINGLE_QUOTE_CHARS = "‘’"
_DOUBLE_QUOTE_CHARS = "“”"

_ZERO_WIDTH_TABLE = {ord(c): None for c in _ZERO_WIDTH_CHARS}
_DASH_TABLE = {ord(c): "-" for c in _DASH_CHARS}
_SINGLE_QUOTE_TABLE = {ord(c): "'" for c in _SINGLE_QUOTE_CHARS}
_DOUBLE_QUOTE_TABLE = {ord(c): '"' for c in _DOUBLE_QUOTE_CHARS}

_WHITESPACE_RUN = re.compile(r"\s+")


def normalise_text(text: str) -> str:
    """Whitespace + unicode normalisation only. Never lowercases - casing
    carries meaning in case numbers and party names."""
    without_zero_width = text.translate(_ZERO_WIDTH_TABLE)
    without_dashes = without_zero_width.translate(_DASH_TABLE)
    without_single_quotes = without_dashes.translate(_SINGLE_QUOTE_TABLE)
    without_double_quotes = without_single_quotes.translate(_DOUBLE_QUOTE_TABLE)
    collapsed = _WHITESPACE_RUN.sub(" ", without_double_quotes)
    return collapsed.strip()


@dataclass
class VerificationResult:
    verified: bool
    page_used: int | None
    char_start: int | None
    char_end: int | None


def verify_field(
    quote: str, page: int, order_pages: dict[int, str]
) -> VerificationResult:
    """Try `page`, then `page - 1`, then `page + 1` (models are commonly
    off by one). Page ± 2 is not attempted - that's a different page, not a
    rounding error."""
    normalised_quote = normalise_text(quote)

    for candidate_page in (page, page - 1, page + 1):
        page_text = order_pages.get(candidate_page)
        if page_text is None:
            continue

        normalised_page = normalise_text(page_text)
        index = normalised_page.find(normalised_quote)
        if index != -1:
            return VerificationResult(
                verified=True,
                page_used=candidate_page,
                char_start=index,
                char_end=index + len(normalised_quote),
            )

    return VerificationResult(
        verified=False, page_used=None, char_start=None, char_end=None
    )
