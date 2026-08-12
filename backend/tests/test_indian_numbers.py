from decimal import Decimal

from parsing.indian_numbers import parse_amount


class TestIndianDigitGrouping:
    def test_crore_lakh_grouping(self) -> None:
        assert parse_amount("1,24,56,000") == Decimal(12456000)

    def test_simple_lakh_grouping(self) -> None:
        assert parse_amount("26,42,000") == Decimal(2642000)

    def test_western_grouping_also_accepted(self) -> None:
        assert parse_amount("12,456,000") == Decimal(12456000)

    def test_no_grouping_plain_digits(self) -> None:
        assert parse_amount("2642000") == Decimal(2642000)


class TestScaleWordsNumeric:
    def test_lakhs_decimal(self) -> None:
        assert parse_amount("Rs. 26.42 lakhs") == Decimal(2642000)

    def test_crore_with_comma_grouped_number(self) -> None:
        assert parse_amount("Rs. 5,000 crore") == Decimal(50_000_000_000)

    def test_rupee_symbol_and_short_crore_form(self) -> None:
        assert parse_amount("₹5000 Cr") == Decimal(50_000_000_000)

    def test_lakh_singular(self) -> None:
        assert parse_amount("Rs. 1 lakh") == Decimal(100_000)

    def test_lac_spelling(self) -> None:
        assert parse_amount("Rs. 26.42 lacs") == Decimal(2642000)

    def test_thousand_suffix(self) -> None:
        assert parse_amount("Rs. 500 thousand") == Decimal(500_000)

    def test_trailing_slash_dash(self) -> None:
        assert parse_amount("Rs. 26,42,000/-") == Decimal(2642000)

    def test_inr_prefix(self) -> None:
        assert parse_amount("INR 26,42,000") == Decimal(2642000)


class TestWordsToNumber:
    def test_rupees_words_only(self) -> None:
        assert parse_amount("Rupees Twenty Six Lakh Forty Two Thousand only") == (
            Decimal(2642000)
        )

    def test_words_without_rupees_prefix(self) -> None:
        assert parse_amount("Twenty Six Lakh Forty Two Thousand") == Decimal(2642000)

    def test_words_with_hundred(self) -> None:
        assert parse_amount("One Hundred Twenty Three") == Decimal(123)

    def test_words_crore_and_lakh_combined(self) -> None:
        assert parse_amount("Two Crore Fifty Lakh") == Decimal(25_000_000)

    def test_words_single_digit(self) -> None:
        assert parse_amount("Five Thousand") == Decimal(5000)

    def test_words_hyphenated(self) -> None:
        assert parse_amount("Twenty-Six Lakh") == Decimal(2_600_000)


class TestMixedNumericAndWords:
    def test_numeric_leading_with_words_in_parens(self) -> None:
        text = "Rs. 26.42 lakhs (Rupees Twenty Six Lakh Forty Two Thousand)"
        assert parse_amount(text) == Decimal(2642000)


class TestNegatives:
    def test_bracketed_negative(self) -> None:
        assert parse_amount("(1,24,000)") == Decimal(-124000)

    def test_leading_minus(self) -> None:
        assert parse_amount("-1,24,000") == Decimal(-124000)

    def test_bracketed_negative_with_currency(self) -> None:
        assert parse_amount("(Rs. 26.42 lakhs)") == Decimal(-2642000)


class TestScaleHint:
    def test_scale_hint_applied_when_no_explicit_scale(self) -> None:
        assert parse_amount("26.42", scale_hint="lakhs") == Decimal(2642000)

    def test_scale_hint_crore(self) -> None:
        assert parse_amount("5,000", scale_hint="crore") == Decimal(50_000_000_000)

    def test_explicit_scale_wins_over_hint(self) -> None:
        assert parse_amount("26.42 lakhs", scale_hint="crore") == Decimal(2642000)

    def test_unrecognised_scale_hint_is_ignored_not_raised(self) -> None:
        assert parse_amount("100", scale_hint="bajillion") == Decimal(100)

    def test_no_scale_hint_no_scale_word_returns_plain_value(self) -> None:
        assert parse_amount("100") == Decimal(100)


class TestAbsentOrMalformedInput:
    def test_none_returns_none(self) -> None:
        assert parse_amount(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert parse_amount("") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert parse_amount("   ") is None

    def test_no_digits_or_number_words_returns_none(self) -> None:
        assert parse_amount("Not a number") is None

    def test_currency_symbol_alone_returns_none(self) -> None:
        assert parse_amount("Rs.") is None

    def test_only_word_alone_returns_none(self) -> None:
        assert parse_amount("only") is None

    def test_empty_parens_returns_none(self) -> None:
        assert parse_amount("()") is None

    def test_double_decimal_point_returns_none_not_a_guess(self) -> None:
        # "26..42" is ambiguous garbage, not a valid amount - must not
        # silently return a truncated 26.
        assert parse_amount("26..42 lakhs") is None

    def test_scale_word_with_no_number_returns_none(self) -> None:
        assert parse_amount("lakh") is None

    def test_bare_hundred_with_no_number_returns_none(self) -> None:
        assert parse_amount("Hundred") is None

    def test_gibberish_word_sequence_returns_none(self) -> None:
        assert parse_amount("Twenty Banana Lakh") is None

    def test_does_not_raise_on_weird_unicode(self) -> None:
        assert parse_amount("💰💰💰") is None


class TestNeverRaises:
    def test_large_number_of_digits_does_not_raise(self) -> None:
        result = parse_amount("1" * 200)
        assert result is not None

    def test_malformed_bracket_mismatch_does_not_raise(self) -> None:
        # Not a clean "(...)"-wrapped negative - starts with '(' but
        # doesn't end with ')', so it isn't treated as bracketed-negative.
        result = parse_amount("(1,24,000")
        assert result == Decimal(124000)

    def test_multiple_scale_words_uses_first_only(self) -> None:
        assert parse_amount("5 lakh crore") == Decimal(500_000)
