import config
from processing.deduplication import find_duplicates, make_fingerprint


def book(title, price=10.0):
    return {"source": config.SOURCE_BOOKS, "name_or_title": title, "price": price, "author": None}


def quote(text, author="Albert Einstein"):
    return {"source": config.SOURCE_QUOTES, "name_or_title": text, "author": author, "price": None}


def test_duplicates_ignore_case_spaces_and_punctuation():
    records = [book("Example Book Title"), book("  Example Book Title "),
               book("EXAMPLE BOOK TITLE"), book("Example, Book Title!")]
    unique, dupes = find_duplicates(records)
    assert len(unique) == 1 and len(dupes) == 3
    assert unique[0]["name_or_title"] == "Example Book Title"  # first occurrence kept


def test_same_title_different_price_is_not_a_duplicate():
    unique, dupes = find_duplicates([book("Same", 10.0), book("Same", 12.0)])
    assert len(unique) == 2 and not dupes


def test_quotes_use_author_plus_first_50_characters():
    base = "x" * 50
    unique, dupes = find_duplicates([quote(base + " ending one"), quote(base.upper() + " ENDING two")])
    assert len(unique) == 1 and len(dupes) == 1


def test_same_quote_different_author_is_not_a_duplicate():
    unique, dupes = find_duplicates([quote("Hi", "A"), quote("Hi", "B")])
    assert len(unique) == 2 and not dupes


def test_same_text_in_different_sources_is_not_a_duplicate():
    assert make_fingerprint(book("Hello")) != make_fingerprint(quote("Hello", None))
