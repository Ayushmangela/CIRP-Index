from parsing.bench import extract_bench


class TestRealCaseNumbersFromDb:
    """Sampled from the live DB after Prompt 2's scrape."""

    def test_slash_separated_suffix(self) -> None:
        assert extract_bench("C.P. (IB)/93/MP/2023") == "MP"

    def test_ia_in_parent_case_with_bench_before_slash(self) -> None:
        assert extract_bench("IA-05 & 06/2023 in (IB) 2060 & 2061 (PB)/2019") == "PB"

    def test_mb_slash_year(self) -> None:
        assert extract_bench("C.P. (IB)/1225/MB/2025") == "MB"

    def test_ibc_prefix_then_bench(self) -> None:
        assert extract_bench("CP/IB(IBC)/20/CB/2026") == "CB"

    def test_ib_dash_then_bench(self) -> None:
        assert extract_bench("IB-534/ND/2025") == "ND"

    def test_no_dot_prefix(self) -> None:
        assert extract_bench("C.P. (IB) No. 184/BB/2025") == "BB"

    def test_bench_in_parens_no_slash_before_year(self) -> None:
        assert extract_bench("CP(IB)/72(MP)2025") == "MP"

    def test_bench_in_parens_che(self) -> None:
        assert extract_bench("CP(IB)/28(CHE)2022") == "CHE"

    def test_plan_in_parens_is_not_mistaken_for_bench(self) -> None:
        assert (
            extract_bench(
                "I.A No. 3678 (Plan) of 2021 in C.P.(I.B.) No. 2695 (ND)/2019"
            )
            == "ND"
        )

    def test_repeated_bench_liq_prefix(self) -> None:
        assert extract_bench("IA(Liq.)/7(AHM)2025 in CP(IB)/258(AHM)2022") == "AHM"

    def test_kb_slash_year(self) -> None:
        assert extract_bench("C.P. (IB)/151/KB/2025") == "KB"

    def test_liq_dot_prefix(self) -> None:
        assert extract_bench("I.A(Liq.)/87/2024 in C.P. (IB)/987/MB/2020") == "MB"

    def test_no_dot_number_dot(self) -> None:
        assert extract_bench("CP (IB) No.1361/MB/2025") == "MB"

    def test_upper_no_period(self) -> None:
        assert extract_bench("C.P. (IB) NO. 26/KB/2026") == "KB"

    def test_bare_number_slash_bench_slash_year(self) -> None:
        assert extract_bench("61/KB/2026") == "KB"

    def test_no_space_no_period(self) -> None:
        assert extract_bench("CP (IB) NO 101/ALD/2022") == "ALD"

    def test_bench_in_parens_no_space(self) -> None:
        assert extract_bench("C.P. (IB)/515(MB)2025") == "MB"

    def test_hdb_after_extra_number_segment(self) -> None:
        assert extract_bench("CP (IB) No.224/09/HDB/2024") == "HDB"

    def test_ibc_dot_no_space(self) -> None:
        assert extract_bench("C.P.(IB)/143/MB/2026") == "MB"

    def test_mp_in_parens(self) -> None:
        assert extract_bench("CP(IB)/20(MP)2025") == "MP"

    def test_spaced_parens_bench(self) -> None:
        assert extract_bench("C.P. (I.B.)/138 (KB) 2025") == "KB"

    def test_jpr_slash_year(self) -> None:
        assert extract_bench("C.P. (IB)/14/JPR/2026") == "JPR"


class TestDocumentedFormats:
    def test_hdb_from_spec_example(self) -> None:
        assert extract_bench("CP(IB) No. 155/9/HDB/2020") == "HDB"

    def test_ia_ibc_dash_in_cp_ib(self) -> None:
        assert extract_bench("IA(IBC)-66-2022 in CP(IB) No. 155-9-HDB-2020") == "HDB"

    def test_kob_paren_dash(self) -> None:
        assert extract_bench("CP(IBC)-24(KOB)-2021") == "KOB"

    def test_ib_no_dash_bench(self) -> None:
        assert extract_bench("IB No. 3013-ND-2019") == "ND"


class TestFalsePositivesFoundAgainstFullCorpus:
    """Regressions found by running the backfill against all 97 real
    scraped orders, not just the curated sample above."""

    def test_ibc_next_to_application_number_is_not_a_bench(self) -> None:
        # "1146" here is an IA number, not a year, and there's no real
        # bench segment in this case number at all.
        assert extract_bench("IA (IBC) 1146/2026") is None

    def test_roman_numeral_sub_application_marker_is_not_a_bench(self) -> None:
        # The real bench "MB" isn't structurally adjacent to the year (an
        # intervening "/C-III/" breaks it) - correct behaviour is to
        # abstain, not to guess "MB" or wrongly return "III".
        assert extract_bench("C.P.(IB)-597(MB)/C-III/2024") is None


class TestEdgeCases:
    def test_none_returns_none(self) -> None:
        assert extract_bench(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert extract_bench("") is None

    def test_no_year_present_returns_none(self) -> None:
        assert extract_bench("CP(IB) No. 155/9/HDB") is None

    def test_no_bench_like_token_returns_none(self) -> None:
        assert extract_bench("2020") is None
