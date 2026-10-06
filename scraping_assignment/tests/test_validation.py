import config
from processing.validation import validate_record


def good_book(**over):
    rec = {"source": config.SOURCE_BOOKS, "source_url": "https://books.toscrape.com/x/index.html",
           "name_or_title": "T", "price": 10.0, "rating": 3, "author": None}
    return {**rec, **over}


def good_quote(**over):
    rec = {"source": config.SOURCE_QUOTES, "source_url": "https://quotes.toscrape.com/",
           "name_or_title": "Q", "author": "A", "price": None, "rating": None}
    return {**rec, **over}


def test_valid_records_have_no_problems():
    assert validate_record(good_book()) == []
    assert validate_record(good_quote()) == []


def test_each_rule_reports_its_reason():
    assert "unknown_source" in validate_record(good_book(source="Elsewhere"))
    assert "missing_name" in validate_record(good_book(name_or_title=None))
    assert "invalid_url" in validate_record(good_book(source_url="ftp://x"))
    assert "invalid_url" in validate_record(good_book(source_url=None))
    assert "invalid_price" in validate_record(good_book(price=-1))
    assert "invalid_price" in validate_record(good_book(price=float("nan")))
    assert "invalid_rating" in validate_record(good_book(rating=7))
    assert "missing_price" in validate_record(good_book(price=None))
    assert "missing_rating" in validate_record(good_book(rating=None))
    assert "missing_author" in validate_record(good_quote(author=None))


def test_multiple_problems_are_all_reported():
    assert set(validate_record(good_book(name_or_title=None, price=None))) == {"missing_name", "missing_price"}
