"""Builds the extraction prompt from order page text. See
docs/EXTRACTION_CONTRACT.md for the exact JSON shape the model must return.
"""

from extraction.contract import FIELDS_TO_EXTRACT

# Conservative character budget per prompt chunk, well under Gemini
# Flash/Flash-Lite's context window, leaving room for the instructions and
# the model's own JSON response.
DEFAULT_CHUNK_CHAR_BUDGET = 60_000

_INSTRUCTIONS = """\
You are extracting structured fields from an Indian insolvency (IBC) order.

Return JSON only - no prose, no markdown code fences. The JSON must match
this exact shape:

{{
  "fields": [
    {{
      "field": "claim_amount",
      "value_text": "Rs. 26,42,000/-",
      "evidence": {{
        "quote": "directed refund of Rs. 26,42,000/- towards managerial remuneration",
        "page": 4
      }}
    }}
  ],
  "not_found": ["resolution_professional"]
}}

Rules:
- value_text is the literal string from the document. Never compute or
  convert a number yourself - copy it exactly as written.
- evidence.quote must be VERBATIM, 10-40 words, copied exactly from the
  page text below, including the value. Do not paraphrase, summarise, or
  fix apparent typos in the source text.
- evidence.page is the 1-indexed page number the quote appears on, exactly
  as labelled in the "=== Page N ===" markers below.
- Every field you cannot find with a verbatim quote goes in not_found as a
  plain string. Do not put an empty string in value_text - use not_found
  instead.
- Extract only these fields: {fields}

Order pages follow, each marked with its page number.
"""


def build_prompt(pages: dict[int, str]) -> str:
    instructions = _INSTRUCTIONS.format(fields=", ".join(FIELDS_TO_EXTRACT))
    page_blocks = [
        f"=== Page {page_number} ===\n{text}"
        for page_number, text in sorted(pages.items())
    ]
    return instructions + "\n\n" + "\n\n".join(page_blocks)


def chunk_pages(
    pages: dict[int, str], char_budget: int = DEFAULT_CHUNK_CHAR_BUDGET
) -> list[dict[int, str]]:
    """Split an order's pages into chunks that each fit under char_budget,
    without splitting a single page's text across chunks."""
    chunks: list[dict[int, str]] = []
    current: dict[int, str] = {}
    current_size = 0

    for page_number, text in sorted(pages.items()):
        page_size = len(text)
        if current and current_size + page_size > char_budget:
            chunks.append(current)
            current = {}
            current_size = 0
        current[page_number] = text
        current_size += page_size

    if current:
        chunks.append(current)

    return chunks
