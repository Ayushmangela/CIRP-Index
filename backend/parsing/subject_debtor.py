import re

from parsing.case_number import _CASE_NUMBER_START

# Case-grouping metadata only, not an evidentiary fact - see linking/run.py.
# Structural parse of the party name out of an IBBI subject line, same
# philosophy as case_number.py: strip known prefixes, then cut at the
# trailing "[...]" case-number group if present, or at wherever the case
# number itself starts (reusing case_number.py's boundary) if not.
_APPROVAL_PREFIX = re.compile(
    r"^Approval\s+of\s+Resolution\s+Plan\s*-\s*", re.IGNORECASE
)
_IN_THE_MATTER_PREFIX = re.compile(r"^In\s+the\s+matter\s+of:?\s*", re.IGNORECASE)
# Allows one level of nesting, e.g. "[TP(lBC)/1(MP)2024 [CP 11 of 2015]]".
_TRAILING_BRACKET_GROUP = re.compile(r"\s*\[(?:[^\[\]]|\[[^\[\]]*\])*\]\s*$")


def extract_debtor_name(subject_raw: str | None) -> str | None:
    """Best-effort party name for case grouping/display. Not extracted
    evidence - if a verified corporate_debtor field exists for the case,
    prefer that instead. Returns None rather than guessing when nothing
    usable remains after stripping known boilerplate."""
    if not subject_raw or not subject_raw.strip():
        return None

    text = subject_raw.strip()
    text = _APPROVAL_PREFIX.sub("", text)
    text = _IN_THE_MATTER_PREFIX.sub("", text)

    bracket_match = _TRAILING_BRACKET_GROUP.search(text)
    if bracket_match:
        text = text[: bracket_match.start()]
    else:
        case_start = _CASE_NUMBER_START.search(text)
        if case_start:
            text = text[: case_start.start()]

    text = text.replace("&amp;", "&")
    text = re.sub(r"\s+", " ", text).strip().strip(",")

    return text or None
