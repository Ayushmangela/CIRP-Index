from parsing.subject_debtor import extract_debtor_name


class TestBracketedSubjects:
    def test_simple_bracketed(self) -> None:
        assert (
            extract_debtor_name(
                "In the matter of SOCRUS PHARMACEUTICALS LIMITED [CP(IB)/47(MP)2026]"
            )
            == "SOCRUS PHARMACEUTICALS LIMITED"
        )

    def test_mixed_case_company(self) -> None:
        assert (
            extract_debtor_name(
                "In the matter of Matoshree Infrastructure Private Limited "
                "[C.P. (IB)/824/MB/2025]"
            )
            == "Matoshree Infrastructure Private Limited"
        )

    def test_html_ampersand_entity_decoded(self) -> None:
        assert (
            extract_debtor_name(
                "In the matter of V&amp;RO HOSPITALITY PRIVATE LIMITED "
                "[C.P. (IB) No. 184/BB/2025]"
            )
            == "V&RO HOSPITALITY PRIVATE LIMITED"
        )

    def test_nested_brackets_uses_outer_group(self) -> None:
        assert (
            extract_debtor_name(
                "In the matter of KRISHNA ELECTRICAL INDUSTRIES LIMITED "
                "[TP(lBC)/1(MP)2024 [CP 11 of 2015]]"
            )
            == "KRISHNA ELECTRICAL INDUSTRIES LIMITED"
        )

    def test_trailing_space_before_bracket(self) -> None:
        assert (
            extract_debtor_name(
                "In the matter of NEXTGEN TEXTILE PARK PRIVATE LIMITED "
                "[IB-534/ND/2025 ]"
            )
            == "NEXTGEN TEXTILE PARK PRIVATE LIMITED"
        )


class TestApprovalOfResolutionPlanPrefix:
    def test_approval_prefix_stripped(self) -> None:
        assert (
            extract_debtor_name(
                "Approval of Resolution Plan - Dion Global Solutions Limited "
                "[I.A No. 3678 (Plan) of 2021 in C.P.(I.B.) No. 2695 (ND)/2019]"
            )
            == "Dion Global Solutions Limited"
        )

    def test_approval_prefix_with_ampersand(self) -> None:
        assert (
            extract_debtor_name(
                "Approval of Resolution Plan - Radius & Deserve Land Developers "
                "Private Limited [I.A. (Plan) No. 82 of 2025 in CP (IB) No. 892 "
                "of 2022]"
            )
            == "Radius & Deserve Land Developers Private Limited"
        )


class TestUnbracketedSubjects:
    """Older-style subject lines with no [...] wrapper at all."""

    def test_case_number_tail_stripped(self) -> None:
        assert (
            extract_debtor_name(
                "In the matter of Ahinsa Buildtech Private Limited IA No. 2230 "
                "of 2021 in CP (IB) 3562-MB-2018"
            )
            == "Ahinsa Buildtech Private Limited"
        )

    def test_cp_ib_dash_tail_stripped(self) -> None:
        assert (
            extract_debtor_name(
                "In the matter of Foodco Delicacies India Private Limited "
                "CP(IB)-08-KOB-2021"
            )
            == "Foodco Delicacies India Private Limited"
        )

    def test_vs_style_combines_both_parties_known_limitation(self) -> None:
        # No clean separator between applicant/respondent in this older
        # personal-guarantor style subject line - both names end up in the
        # result. Documented, not silently "fixed" by guessing which half
        # is the debtor.
        assert (
            extract_debtor_name(
                "In the matter of State Bank of India vs. Vijay Latha Jain, "
                "[CP(IB) NO. 156/95/HYD/2023]"
            )
            == "State Bank of India vs. Vijay Latha Jain"
        )


class TestEdgeCases:
    def test_none_returns_none(self) -> None:
        assert extract_debtor_name(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert extract_debtor_name("") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert extract_debtor_name("   ") is None

    def test_bracket_only_no_name_returns_none(self) -> None:
        assert extract_debtor_name("In the matter of [CP(IB)/1/AB/2020]") is None
