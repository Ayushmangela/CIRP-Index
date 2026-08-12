import re

# Matches the point where a case-number token starts: CP/C.P., IA/I.A.,
# IB/IBC, or the spelled-out "Interlocutory Application"/"Company Petition"
# variants seen in IBBI subject lines. Everything from that point to the end
# of the string is taken as the case number.
_CASE_NUMBER_START = re.compile(
    r"""(?:
        C\.?\s*P\.?\s*(?:\(|/|-|\s)*I\.?\s*B\.?
        |I\.?\s*A\.?\s*(?:\(|/|-|\s)*I\.?\s*B\.?
        |I\.?\s*A\.?\s*(?:\(|/|-|\s)*(?:No\.?\s*)?\d
        |IBC?\b
        |Interlocutory\s+Application
        |Company\s+Petition
    )""",
    re.IGNORECASE | re.VERBOSE,
)

# A `[...]` group at the very end of the subject line, e.g.
# "In the matter of X [CP (IB) No. 1/AB/2020]". Allows one level of
# nesting, e.g. "[TP(lBC)/1(MP)2024 [CP 11 of 2015]]".
_TRAILING_BRACKET = re.compile(r"\[((?:[^\[\]]|\[[^\[\]]*\])*)\]\s*$")

_HAS_DIGIT = re.compile(r"\d")


def extract_case_number(subject_raw: str) -> str | None:
    """Pull the case number out of an IBBI subject line.

    Handles both the bracketed form ("... [CP (IB) No. 1/AB/2020]") and the
    unbracketed form where the case number simply trails the party names
    ("... CP(IB)-08-KOB-2021"). Returns None rather than guessing when
    neither shape is found.
    """
    if not subject_raw or not subject_raw.strip():
        return None

    text = subject_raw.strip()

    bracket_match = _TRAILING_BRACKET.search(text)
    if bracket_match:
        candidate = _clean(bracket_match.group(1))
        if candidate and _HAS_DIGIT.search(candidate):
            return candidate

    start_match = _CASE_NUMBER_START.search(text)
    if start_match:
        candidate = _clean(text[start_match.start() :])
        if candidate:
            return candidate

    return None


def _clean(value: str) -> str:
    collapsed = re.sub(r"\s+", " ", value).strip()
    return collapsed.strip(" ,.")


_NON_ALNUM = re.compile(r"[^A-Za-z0-9]+")
_STANDALONE_NO = re.compile(r"\bNO\b", re.IGNORECASE)


def normalise_case_number(case_number: str) -> str:
    """Canonical form for exact-match case linking: strip every
    punctuation/whitespace variant and the optional "No."/"No" word (its
    presence is inconsistent across documents referencing the same case),
    uppercase. "CP (IB)/93/MP/2023", "C.P. (IB) No. 93/MP/2023" and
    "CP IB 93 MP 2023" all collapse to the same string.
    """
    if not case_number:
        return ""
    without_no = _STANDALONE_NO.sub("", case_number)
    return _NON_ALNUM.sub("", without_no).upper()


_IN_CLAUSE = re.compile(r"\s+in\s+", re.IGNORECASE)


def split_parent_case(case_number: str) -> tuple[str, str] | None:
    """Split "X in Y" into (child, parent), e.g. an interlocutory
    application filed within a parent company petition. Returns None when
    the case number isn't a sub-application reference."""
    if not case_number:
        return None

    match = _IN_CLAUSE.search(case_number)
    if not match:
        return None

    child = _clean(case_number[: match.start()])
    parent = _clean(case_number[match.end() :])
    if not child or not parent:
        return None

    return child, parent
