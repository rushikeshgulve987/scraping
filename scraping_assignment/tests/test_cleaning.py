import pytest

from processing.cleaning import (clean_price, clean_rating, clean_tags, clean_text,
                                 normalize_url, strip_quotes)


def test_clean_text_collapses_whitespace_and_nbsp():
    assert clean_text("  Hello \n\t World\xa0! ") == "Hello World !"


@pytest.mark.parametrize("value", [None, "", "   ", "\xa0"])
def test_clean_text_empty_becomes_none(value):
    assert clean_text(value) is None


@pytest.mark.parametrize("raw,expected", [
    ("\u00a351.77", 51.77), ("\u00c2\u00a351.77", 51.77), ("\u00a31,234.50", 1234.5),
    ("10", 10.0), ("free", None), ("", None), (None, None)])
def test_clean_price(raw, expected):
    assert clean_price(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("star-rating Three", 3), ("Five", 5), ("one", 1), ("4", 4), ("star-rating", None), (None, None)])
def test_clean_rating(raw, expected):
    assert clean_rating(raw) == expected


def test_clean_tags_lowercases_sorts_dedupes():
    assert clean_tags([" Love ", "books", "LOVE", ""]) == "books;love"
    assert clean_tags([]) is None and clean_tags(None) is None


def test_strip_quotes_removes_only_wrapping_pair():
    assert strip_quotes("\u201cHello\u201d") == "Hello"
    assert strip_quotes('"Hello"') == "Hello"
    assert strip_quotes("Say \u201chi\u201d") == "Say \u201chi\u201d"


def test_normalize_url():
    assert normalize_url("/page/2/", base="https://Quotes.ToScrape.com/") == "https://quotes.toscrape.com/page/2/"
    assert normalize_url("https://x.com/a#frag") == "https://x.com/a"
    assert normalize_url("ftp://x.com") is None
    assert normalize_url("not a url") is None
    assert normalize_url(None) is None
