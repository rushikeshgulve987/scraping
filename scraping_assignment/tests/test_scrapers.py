import requests

from scrapers.books_scraper import BooksScraper
from scrapers.quotes_scraper import QuotesScraper
from tests import fakes


def test_books_pagination_follows_next_link_until_it_disappears():
    session = fakes.FakeSession(fakes.books_site())
    scraper = BooksScraper(session=session, delay=0, fetch_details=False)
    records = scraper.scrape()
    assert [r["title"] for r in records] == [
        "A Light in the Attic", "Tipping the Velvet", "Soumission", "A LIGHT IN THE ATTIC"]
    assert session.requested == [fakes.B1, fakes.B2]  # no hard-coded page list, stopped at last page
    assert scraper.pages_fetched == 2 and scraper.pages_failed == 0
    assert records[0]["source_url"] == "https://books.toscrape.com/catalogue/a-light_1000/index.html"
    assert records[2]["source_url"] == "https://books.toscrape.com/catalogue/soumission_998/index.html"


def test_books_missing_price_element_does_not_crash():
    records = BooksScraper(session=fakes.FakeSession(fakes.books_site()), delay=0, fetch_details=False).scrape()
    assert records[1]["title"] == "Tipping the Velvet" and records[1]["price_raw"] is None


def test_books_detail_pages_add_category_and_description_and_count_failures():
    scraper = BooksScraper(session=fakes.FakeSession(fakes.books_site()), delay=0)
    records = scraper.scrape()
    assert records[0]["category_raw"] == "Poetry" and records[0]["description_raw"] == "A poetry book."
    assert records[1]["category_raw"] is None       # its detail page returned 404
    assert scraper.detail_failures == 1


def test_failed_second_page_keeps_first_page_records():
    pages = fakes.books_site()
    pages[fakes.B2] = requests.ConnectionError("boom")
    scraper = BooksScraper(session=fakes.FakeSession(pages), delay=0, fetch_details=False)
    records = scraper.scrape()
    assert len(records) == 2 and scraper.pages_failed == 1 and scraper.pages_fetched == 1


def test_http_error_on_first_page_returns_nothing_without_raising():
    scraper = QuotesScraper(session=fakes.FakeSession({}), delay=0)  # everything 404
    assert scraper.scrape() == [] and scraper.pages_failed == 1


def test_max_pages_limits_pagination():
    session = fakes.FakeSession(fakes.books_site())
    BooksScraper(session=session, delay=0, fetch_details=False, max_pages=1).scrape()
    assert session.requested == [fakes.B1]


def test_pagination_loop_is_detected():
    pages = {fakes.Q1: fakes.page([fakes.quote("a", "b", [])], next_href="/")}
    session = fakes.FakeSession(pages)
    QuotesScraper(session=session, delay=0).scrape()
    assert session.requested == [fakes.Q1]


def test_quotes_parsing_handles_missing_author_and_empty_tags():
    records = QuotesScraper(session=fakes.FakeSession(fakes.quotes_site()), delay=0).scrape()
    assert len(records) == 5
    assert records[1]["tags_raw"] == [] and records[2]["author_raw"] is None
    assert records[0]["tags_raw"] == ["change", "Deep-Thoughts"]
    assert records[0]["source_url"] == fakes.Q1 and records[3]["source_url"] == fakes.Q2
