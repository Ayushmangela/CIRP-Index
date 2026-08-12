import re
from pathlib import Path

from ingestion.ibbi_listing import (
    OUTCOME_MAP,
    ParsedRow,
    parse_page,
    resolve_outcome,
)
from models.enums import OutcomeEnum

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "ibbi"


def _load(name: str) -> str:
    return (FIXTURES_DIR / name).read_text()


class TestParsePage:
    def test_parses_expected_row_count(self) -> None:
        rows = parse_page(_load("page_0.html"))
        assert len(rows) == 20

    def test_row_fields_are_populated(self) -> None:
        rows = parse_page(_load("page_0.html"))
        first = rows[0]
        assert isinstance(first, ParsedRow)
        assert first.order_date is not None
        assert first.subject_raw.startswith("In the matter of")
        assert first.pdf_url.startswith("https://ibbi.gov.in/uploads/order/")
        assert first.pdf_url.endswith(".pdf")
        assert first.remarks_raw != ""

    def test_subject_raw_excludes_file_size_and_img(self) -> None:
        rows = parse_page(_load("page_0.html"))
        first = rows[0]
        assert "KB" not in first.subject_raw
        assert "MB" not in first.subject_raw
        assert first.file_size_bytes is not None
        assert first.file_size_bytes > 0

    def test_bench_is_populated_when_case_number_parses(self) -> None:
        # Real misses in this fixture set: two case numbers have no bench
        # segment at all, one uses an alphanumeric code ("C8"), one has an
        # inserted "/C of " qualifier breaking year-adjacency, and one
        # writes the bench in mixed case ("Chd/Pb"). All genuine source
        # irregularities, not parser bugs - see parsing/bench.py.
        all_rows: list[ParsedRow] = []
        for fixture in ("page_0.html", "page_100.html", "page_800.html"):
            all_rows.extend(parse_page(_load(fixture)))

        with_case_number = [r for r in all_rows if r.case_number is not None]
        with_bench = [r for r in with_case_number if r.bench is not None]
        rate = len(with_bench) / len(with_case_number)
        assert rate > 0.85, f"bench parse rate too low: {rate:.1%}"
        assert len({r.bench for r in with_bench}) >= 4

    def test_case_number_parse_rate_above_90_percent(self) -> None:
        all_rows: list[ParsedRow] = []
        for fixture in ("page_0.html", "page_100.html", "page_800.html"):
            all_rows.extend(parse_page(_load(fixture)))

        with_case_number = sum(1 for r in all_rows if r.case_number is not None)
        rate = with_case_number / len(all_rows)
        assert rate > 0.9, f"case number parse rate too low: {rate:.1%}"

    def test_unmapped_remarks_become_unclassified_not_guessed(self) -> None:
        rows = parse_page(_load("page_0.html"))
        for row in rows:
            normalised = re.sub(r"\s+", " ", row.remarks_raw.strip().lower())
            if normalised not in OUTCOME_MAP:
                assert row.outcome == OutcomeEnum.unclassified

    def test_mapped_remark_resolves_to_expected_outcome(self) -> None:
        assert resolve_outcome("Admission - Final Order") == OutcomeEnum.admitted
        assert resolve_outcome("ADMITTED") == OutcomeEnum.admitted
        assert resolve_outcome("Liquidation") == OutcomeEnum.liquidation
        assert resolve_outcome("Dissolution") == OutcomeEnum.dissolved

    def test_unmapped_remark_never_guesses(self) -> None:
        assert resolve_outcome("Rejected") == OutcomeEnum.unclassified
        assert resolve_outcome("Dismissed") == OutcomeEnum.unclassified
        assert resolve_outcome("Some new remark IBBI adds tomorrow") == (
            OutcomeEnum.unclassified
        )

    def test_all_three_fixtures_parse_without_error(self) -> None:
        for fixture in ("page_0.html", "page_100.html", "page_800.html"):
            rows = parse_page(_load(fixture))
            assert len(rows) > 0, f"{fixture} produced no rows"
