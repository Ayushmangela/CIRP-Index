from parsing.case_number import extract_case_number


class TestDocumentedFormats:
    """Formats explicitly listed in docs/DATA_SOURCE.md."""

    def test_cp_ib_no_slash_format(self) -> None:
        assert (
            extract_case_number("CP(IB) No. 155/9/HDB/2020")
            == "CP(IB) No. 155/9/HDB/2020"
        )

    def test_ia_in_cp_format(self) -> None:
        assert (
            extract_case_number("IA(IBC)-66-2022 in CP(IB) No. 155-9-HDB-2020")
            == "IA(IBC)-66-2022 in CP(IB) No. 155-9-HDB-2020"
        )

    def test_cp_ibc_paren_bench_format(self) -> None:
        assert extract_case_number("CP(IBC)-24(KOB)-2021") == "CP(IBC)-24(KOB)-2021"

    def test_ia_multi_number_format(self) -> None:
        text = "IA(IBC)/170,171 & 172/KOB/2021 in IBA/43,44,45/KOB/2021"
        assert extract_case_number(text) == text

    def test_ia_no_of_in_cp_no_format(self) -> None:
        assert (
            extract_case_number("I.A. No. 4692 of 2021 in C.P. No. (IB)-1644 (PB)-2018")
            == "I.A. No. 4692 of 2021 in C.P. No. (IB)-1644 (PB)-2018"
        )

    def test_ib_no_format(self) -> None:
        assert extract_case_number("IB No. 3013-ND-2019") == "IB No. 3013-ND-2019"


class TestBracketedLiveSubjects:
    """Real subject lines pulled from https://ibbi.gov.in/orders/nclt."""

    def test_simple_bracketed(self) -> None:
        assert (
            extract_case_number(
                "In the matter of TEERTH GOPICON LIMITED [CP (IB) 408(AHM)2025]"
            )
            == "CP (IB) 408(AHM)2025"
        )

    def test_ia_in_cp_bracketed(self) -> None:
        assert (
            extract_case_number(
                "In the matter of M. I. BUILDTECH PRIVATE LIMITED "
                "[IA No. 51/ND/2024 in CP (IB) No. 300/ND/2021]"
            )
            == "IA No. 51/ND/2024 in CP (IB) No. 300/ND/2021"
        )

    def test_bracket_with_trailing_space(self) -> None:
        assert (
            extract_case_number(
                "In the matter of KVK NILACHAL POWER PRIVATE LIMITED "
                "[IA (IBC) 1146/2026 ]"
            )
            == "IA (IBC) 1146/2026"
        )

    def test_ia_liq_prefix_bracketed(self) -> None:
        assert (
            extract_case_number(
                "In the matter of Sapphire Land Development Private Limited "
                "[I.A(Liq.)/87/2024 in C.P. (IB)/987/MB/2020]"
            )
            == "I.A(Liq.)/87/2024 in C.P. (IB)/987/MB/2020"
        )

    def test_malformed_leading_bracket_still_extracts_tail(self) -> None:
        # Source data is missing the opening "[" before "IA 238 of 2025 in TP
        # 230 of 2019" - only the trailing case number is recoverable, which
        # is the correct, non-guessing behaviour.
        assert (
            extract_case_number(
                "In the matter of JSM Devcons India Pvt. Ltd. "
                "[IA 238 of 2025 in TP 230 of 2019 [CP (IB) 192 of 2017]"
            )
            == "CP (IB) 192 of 2017"
        )


class TestUnbracketedLiveSubjects:
    """Older-style subject lines with no [...] wrapper at all."""

    def test_cp_ib_slash_trailing(self) -> None:
        assert (
            extract_case_number(
                "In the matter of State Bank of India Vs. Mr. R Ram Kumar, "
                "CP (IB)/17/CHE/2022"
            )
            == "CP (IB)/17/CHE/2022"
        )

    def test_cp_ib_dash_trailing_no_comma(self) -> None:
        assert (
            extract_case_number(
                "In the matter of Foodco Delicacies India Private Limited "
                "CP(IB)-08-KOB-2021"
            )
            == "CP(IB)-08-KOB-2021"
        )

    def test_ia_no_of_in_cp_trailing(self) -> None:
        assert (
            extract_case_number(
                "In the matter of Ahinsa Buildtech Private Limited "
                "IA No. 2230 of 2021 in CP (IB) 3562-MB-2018"
            )
            == "IA No. 2230 of 2021 in CP (IB) 3562-MB-2018"
        )

    def test_spelled_out_interlocutory_application(self) -> None:
        assert (
            extract_case_number(
                "In the matter of Ahinsa Buildtech Private Limited "
                "Interlocutory Application 2718-2021 In Company Petition "
                "No. 3562-I&B-NCLT-MAH-2018"
            )
            == "Interlocutory Application 2718-2021 In Company Petition "
            "No. 3562-I&B-NCLT-MAH-2018"
        )

    def test_ia_dash_in_ib_dash_trailing(self) -> None:
        assert (
            extract_case_number(
                "In the matter of Gurmohan Garments Pvt. Ltd. "
                "IA-4604-ND-2021 in IB-3232-ND-2019"
            )
            == "IA-4604-ND-2021 in IB-3232-ND-2019"
        )


class TestEdgeCases:
    def test_none_input_returns_none(self) -> None:
        assert extract_case_number("") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert extract_case_number("   ") is None

    def test_no_case_number_present_returns_none(self) -> None:
        assert (
            extract_case_number("In the matter of Some Company With No Case Number")
            is None
        )

    def test_bracket_without_digits_falls_through_to_none(self) -> None:
        assert extract_case_number("In the matter of X [not a case number]") is None
