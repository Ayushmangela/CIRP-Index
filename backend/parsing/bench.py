import re

# A bench code is a 2-5 letter uppercase token that appears structurally
# adjacent to a bare 4-digit year (e.g. "(MB)2025", "/ND/2025", "-ND-2019",
# "(KB) 2025"). Statute/procedural abbreviations that also appear in
# parentheses in these case numbers - IB, CP, Plan, Liq, No - are usually
# never adjacent to a bare year in the observed formats, so most fall out
# naturally without needing an explicit exclusion list (same philosophy as
# case_number.py: structural, not a hardcoded whitelist of bench names).
#
# Two exceptions found empirically against the full scraped corpus (not
# just curated samples), where the structural test alone isn't enough:
# - "IBC" can land immediately before a 4-digit *application* number
#   (e.g. "IA (IBC) 1146/2026" - 1146 isn't a year), so it's excluded
#   explicitly.
# - Roman-numeral sub-application markers (e.g. "C.P.(IB)-597(MB)/C-III/
#   2024") can be structurally adjacent to the real year while the actual
#   bench code ("MB" here) isn't, due to an intervening fragment. Excluding
#   roman numerals is a narrow, checkable pattern, not a name lookup.
_BENCH_NEAR_YEAR = re.compile(r"\(?([A-Z]{2,5})\)?[\s/-]*(\d{4})\b")

_NON_BENCH_STATUTE_TOKENS = {"IB", "IBC", "CP", "IA"}

_ROMAN_NUMERAL = re.compile(r"^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$")


def extract_bench(case_number: str | None) -> str | None:
    """Pull the bench code out of a case number, e.g.
    "C.P. (IB)/93/MP/2023" -> "MP". Returns None rather than guessing when
    no token is structurally adjacent to a year."""
    if not case_number:
        return None

    matches = list(_BENCH_NEAR_YEAR.finditer(case_number))
    for match in reversed(matches):
        token = match.group(1)
        if token in _NON_BENCH_STATUTE_TOKENS:
            continue
        if _ROMAN_NUMERAL.fullmatch(token):
            continue
        return token

    return None
