import re
from decimal import Decimal, InvalidOperation

# Suffix words recognised directly after a digit run, e.g. "26.42 lakhs".
# Includes the short forms ("cr", "k") seen in compact table headers.
_NUMERIC_SCALE_SUFFIXES: dict[str, Decimal] = {
    "crore": Decimal(10_000_000),
    "crores": Decimal(10_000_000),
    "cr": Decimal(10_000_000),
    "lakh": Decimal(100_000),
    "lakhs": Decimal(100_000),
    "lac": Decimal(100_000),
    "lacs": Decimal(100_000),
    "thousand": Decimal(1_000),
    "k": Decimal(1_000),
}

# Scale words recognised in the spelled-out word form, e.g. "Twenty Six
# Lakh". Deliberately excludes the "cr"/"k" abbreviations - those never
# appear as standalone spoken words, so allowing them here would risk
# treating a stray letter as a scale marker.
_WORD_SCALE_WORDS: dict[str, Decimal] = {
    "crore": Decimal(10_000_000),
    "crores": Decimal(10_000_000),
    "lakh": Decimal(100_000),
    "lakhs": Decimal(100_000),
    "lac": Decimal(100_000),
    "lacs": Decimal(100_000),
    "thousand": Decimal(1_000),
}

_WORD_NUMBERS: dict[str, int] = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

_FILLER_WORDS = {"rupees", "rupee", "inr", "only", "and", "rs"}

_NUMBER_PATTERN = re.compile(r"\d[\d,]*(?:\.\d+)?")
_SCALE_SUFFIX_PATTERN = re.compile(
    r"\s*(crores?|lakhs?|lacs?|thousand|cr|k)\b", re.IGNORECASE
)


def parse_amount(text: str | None, scale_hint: str | None = None) -> Decimal | None:
    """Convert an LLM-extracted amount string to a Decimal.

    Handles Indian digit grouping, lakh/crore scale words (numeric and
    spelled-out), Rs./INR/rupee-symbol prefixes, trailing "/-", and
    parenthesised or leading-minus negatives. Returns None rather than
    guessing on absent or malformed input - never raises.
    """
    if text is None:
        return None

    stripped = text.strip()
    if not stripped:
        return None

    negative, inner = _extract_sign(stripped)
    cleaned = _strip_currency_noise(inner)
    if not cleaned:
        return None

    value = _parse_numeric(cleaned, scale_hint)
    if value is None:
        value = _parse_words(cleaned)

    if value is None:
        return None

    return -value if negative else value


def _extract_sign(text: str) -> tuple[bool, str]:
    if text.startswith("(") and text.endswith(")"):
        return True, text[1:-1].strip()
    if text.startswith("-"):
        return True, text[1:].strip()
    return False, text


def _strip_currency_noise(text: str) -> str:
    cleaned = re.sub(r"(?i)\brs\.?\b", "", text)
    cleaned = re.sub(r"(?i)\binr\b", "", cleaned)
    cleaned = cleaned.replace("₹", "")
    cleaned = re.sub(r"/-\s*$", "", cleaned.strip())
    return cleaned.strip()


def _parse_numeric(text: str, scale_hint: str | None) -> Decimal | None:
    match = _NUMBER_PATTERN.search(text)
    if match is None:
        return None

    remainder_before_scale = text[match.end() :]
    if remainder_before_scale and remainder_before_scale[0] in ".0123456789":
        # The digit run continues past what we matched in a way our pattern
        # didn't account for (e.g. "26..42") - ambiguous, don't guess.
        return None

    raw_number = match.group(0).replace(",", "")
    try:
        value = Decimal(raw_number)
    except InvalidOperation:
        return None

    scale_match = _SCALE_SUFFIX_PATTERN.match(remainder_before_scale)
    if scale_match:
        scale_key = scale_match.group(1).lower()
        return value * _NUMERIC_SCALE_SUFFIXES[scale_key]

    if scale_hint:
        hint_scale = _NUMERIC_SCALE_SUFFIXES.get(scale_hint.strip().lower())
        if hint_scale is not None:
            return value * hint_scale

    return value


def _parse_words(text: str) -> Decimal | None:
    normalised = text.lower().replace("-", " ")
    tokens = [t for t in re.findall(r"[a-z]+", normalised) if t not in _FILLER_WORDS]
    if not tokens:
        return None

    total = Decimal(0)
    group = 0

    for token in tokens:
        if token == "hundred":
            if group == 0:
                return None
            group = group * 100
        elif token in _WORD_SCALE_WORDS:
            if group == 0:
                # A bare scale word with no preceding quantity ("Lakh" on
                # its own) has no defensible value - defaulting to 1 would
                # be a guess, not a parse.
                return None
            total += Decimal(group) * _WORD_SCALE_WORDS[token]
            group = 0
        elif token in _WORD_NUMBERS:
            group += _WORD_NUMBERS[token]
        else:
            # Unrecognised word - the text isn't a clean number-in-words
            # string, so don't guess at a partial result.
            return None

    total += group
    return total
