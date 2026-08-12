from extraction.verifier import normalise_text, verify_field


class TestNormaliseText:
    def test_collapses_whitespace_runs(self) -> None:
        assert normalise_text("a   b\t\tc") == "a b c"

    def test_collapses_newlines_to_space(self) -> None:
        assert normalise_text("directed refund\nof Rs. 26,42,000/-") == (
            "directed refund of Rs. 26,42,000/-"
        )

    def test_strips_zero_width_characters(self) -> None:
        assert normalise_text("Rs.​26,42,000") == "Rs.26,42,000"

    def test_normalises_unicode_dashes_to_hyphen(self) -> None:
        assert normalise_text("2020–21") == "2020-21"
        assert normalise_text("2020‑21") == "2020-21"

    def test_normalises_curly_quotes_to_straight(self) -> None:
        assert normalise_text("the “Corporate Debtor”") == ('the "Corporate Debtor"')
        assert normalise_text("respondent’s counsel") == "respondent's counsel"

    def test_does_not_lowercase(self) -> None:
        assert normalise_text("CP (IB) No. 155/9/HDB/2020") == (
            "CP (IB) No. 155/9/HDB/2020"
        )

    def test_strips_leading_and_trailing_whitespace(self) -> None:
        assert normalise_text("  hello world  ") == "hello world"


class TestVerifyFieldExactMatch:
    def test_exact_match_on_cited_page(self) -> None:
        pages = {
            4: "the tribunal directed refund of Rs. 26,42,000/- towards "
            "managerial remuneration"
        }
        result = verify_field(
            "directed refund of Rs. 26,42,000/- towards managerial remuneration",
            page=4,
            order_pages=pages,
        )
        assert result.verified is True
        assert result.page_used == 4
        assert result.char_start is not None
        assert result.char_end is not None

    def test_char_offsets_are_correct(self) -> None:
        pages = {1: "prefix text here quote target end text"}
        result = verify_field("quote target", page=1, order_pages=pages)
        assert result.verified is True
        normalised = pages[1]
        assert normalised[result.char_start : result.char_end] == "quote target"


class TestVerifyFieldPageRetry:
    def test_falls_back_to_page_minus_one(self) -> None:
        pages = {3: "the actual quote lives here", 4: "unrelated content"}
        result = verify_field("the actual quote lives here", page=4, order_pages=pages)
        assert result.verified is True
        assert result.page_used == 3

    def test_falls_back_to_page_plus_one(self) -> None:
        pages = {4: "unrelated content", 5: "the actual quote lives here"}
        result = verify_field("the actual quote lives here", page=4, order_pages=pages)
        assert result.verified is True
        assert result.page_used == 5

    def test_prefers_exact_page_over_neighbours(self) -> None:
        pages = {
            3: "shared phrase appears here too",
            4: "shared phrase appears here too",
            5: "shared phrase appears here too",
        }
        result = verify_field(
            "shared phrase appears here too", page=4, order_pages=pages
        )
        assert result.page_used == 4

    def test_does_not_retry_page_plus_two(self) -> None:
        pages = {6: "the quote is only on page six"}
        result = verify_field(
            "the quote is only on page six", page=4, order_pages=pages
        )
        assert result.verified is False

    def test_does_not_retry_page_minus_two(self) -> None:
        pages = {2: "the quote is only on page two"}
        result = verify_field(
            "the quote is only on page two", page=4, order_pages=pages
        )
        assert result.verified is False


class TestVerifyFieldNeverFuzzy:
    def test_paraphrase_is_rejected(self) -> None:
        pages = {1: "the tribunal admitted the petition under section 7"}
        result = verify_field(
            "the tribunal approved the application under section 7",
            page=1,
            order_pages=pages,
        )
        assert result.verified is False

    def test_one_word_different_is_rejected(self) -> None:
        pages = {1: "claim amount of Rs. 26,42,000 was directed to be refunded"}
        result = verify_field(
            "claim amount of Rs. 26,43,000 was directed to be refunded",
            page=1,
            order_pages=pages,
        )
        assert result.verified is False

    def test_case_mismatch_is_rejected_never_lowercased(self) -> None:
        pages = {1: "CP (IB) No. 155/9/HDB/2020"}
        result = verify_field("cp (ib) no. 155/9/hdb/2020", page=1, order_pages=pages)
        assert result.verified is False

    def test_missing_page_is_rejected_not_guessed(self) -> None:
        result = verify_field("some quote", page=99, order_pages={1: "some quote"})
        assert result.verified is False


class TestVerifyFieldNormalisationTolerance:
    def test_matches_despite_newline_in_page_text(self) -> None:
        pages = {1: "directed refund of Rs.\n26,42,000/- towards remuneration"}
        result = verify_field(
            "directed refund of Rs. 26,42,000/- towards remuneration",
            page=1,
            order_pages=pages,
        )
        assert result.verified is True

    def test_matches_despite_curly_quote_variant(self) -> None:
        pages = {1: "the term “Corporate Debtor” is defined in section 3"}
        result = verify_field(
            'the term "Corporate Debtor" is defined in section 3',
            page=1,
            order_pages=pages,
        )
        assert result.verified is True
