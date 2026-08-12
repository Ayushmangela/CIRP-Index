# Extraction contract

This document defines the product. If span verification is weakened, the
project has no reason to exist.

## The rule

Every field the LLM extracts must carry a verbatim quote and the page it came
from. Before persisting, the quote is string-matched against the stored text of
that page. No match, no value.

## JSON the model must return

Response is JSON only — no prose, no markdown fences.

```json
{
  "fields": [
    {
      "field": "claim_amount",
      "value_text": "Rs. 26,42,000/-",
      "evidence": { "quote": "directed refund of Rs. 26,42,000/- towards managerial remuneration", "page": 4 }
    }
  ],
  "not_found": ["resolution_professional"]
}
```

- `value_text` is the literal string from the document. Never a computed number.
- `quote` is 10–40 words, verbatim, including the value.
- Fields the model cannot find go in `not_found`. An empty string is a bug.

## Verification algorithm

1. Normalise both sides: collapse runs of whitespace, strip zero-width chars,
   normalise unicode dashes and quotes. Do **not** lowercase — casing carries
   meaning in case numbers.
2. Exact substring match against `order_pages.text` for the cited page.
3. On miss, retry against page ± 1 (models often off-by-one on page numbers).
4. On match: store `char_start`, `char_end`, set `verified = true`.
5. On miss: set `verified = false`, store no value, log the field name and the
   first 60 characters of the failed quote.

Fuzzy matching is not permitted at this step. A near-match is a miss.

## Fields to extract

`corporate_debtor`, `applicant_creditor`, `creditor_type`
(financial | operational | corporate_applicant), `claim_amount`,
`section_invoked`, `resolution_professional`,
`adjudicating_authority_bench`, `admission_date`, `order_type`

## Money

`value_text` goes to `parsing/indian_numbers.py`. That module owns every
conversion. The model is never asked to output a number.

## Rejection rate

Report verified vs rejected counts on every extraction run, with rejection
reasons grouped. If rejection exceeds 25%, stop and investigate the documents.
Do not tune the prompt until the number looks acceptable — that converts a
measurable problem into an invisible one.

## Model configuration

Gemini Flash / Flash-Lite, free tier. JSON response mode. Temperature 0.
Read live rate limits from AI Studio; never hardcode RPM or RPD. Token-bucket
limiter, max 3 concurrent, backoff with jitter on 429, resume from a watermark
when the daily budget is exhausted — a partial run is a success.
