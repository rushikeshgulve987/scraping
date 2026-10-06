import csv
import json

import requests

import config
import main as main_module
from pipeline import run_pipeline
from scrapers.books_scraper import BooksScraper
from scrapers.quotes_scraper import QuotesScraper
from tests import fakes


def build(books_pages=None, quotes_pages=None):
    return [BooksScraper(session=fakes.FakeSession(books_pages or fakes.books_site()), delay=0),
            QuotesScraper(session=fakes.FakeSession(quotes_pages or fakes.quotes_site()), delay=0)]


def test_end_to_end_counts_and_files(tmp_path):
    summary = run_pipeline(build(), output_dir=tmp_path)

    books = summary["sources"][config.SOURCE_BOOKS]
    quotes = summary["sources"][config.SOURCE_QUOTES]
    assert (books["collected"], books["rejected"], books["duplicates"], books["final"]) == (4, 1, 1, 2)
    assert books["rejected_by_reason"] == {"missing_price": 1}
    assert books["detail_pages_failed"] == 1
    assert (quotes["collected"], quotes["rejected"], quotes["duplicates"], quotes["final"]) == (5, 1, 1, 3)
    assert quotes["rejected_by_reason"] == {"missing_author": 1}
    assert summary["totals"]["final"] == 5
    assert all(summary["reconciliation"]["per_source"].values())

    with open(tmp_path / "final_dataset.csv", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == summary["totals"]["final"] == 5
    assert list(rows[0].keys()) == config.OUTPUT_COLUMNS
    assert {r["source"] for r in rows} == config.VALID_SOURCES

    book_row = next(r for r in rows if r["name_or_title"] == "A Light in the Attic")
    assert book_row["price"] == "51.77" and book_row["rating"] == "3" and book_row["category"] == "Poetry"
    assert book_row["author"] == "" and book_row["tags"] == ""   # not applicable -> empty, not invented
    quote_row = next(r for r in rows if r["author"] == "Albert Einstein")
    assert quote_row["tags"] == "change;deep-thoughts" and quote_row["price"] == ""
    assert not quote_row["name_or_title"].startswith("\u201c")   # curly quotes stripped

    saved = json.loads((tmp_path / "summary_report.json").read_text(encoding="utf-8"))
    assert saved["totals"] == summary["totals"] and "duration_seconds" in saved["run"]


def test_one_source_failing_does_not_stop_the_other(tmp_path):
    broken = {fakes.B1: requests.ConnectionError("down")}
    summary = run_pipeline(build(books_pages=broken), output_dir=tmp_path)
    assert summary["sources"][config.SOURCE_BOOKS]["final"] == 0
    assert summary["sources"][config.SOURCE_BOOKS]["pages_failed"] == 1
    assert summary["sources"][config.SOURCE_QUOTES]["final"] == 3


def test_crashing_scraper_is_contained(tmp_path):
    class Exploding(QuotesScraper):
        def scrape(self):
            raise RuntimeError("unexpected")
    scrapers = [Exploding(session=fakes.FakeSession({}), delay=0),
                BooksScraper(session=fakes.FakeSession(fakes.books_site()), delay=0, fetch_details=False)]
    summary = run_pipeline(scrapers, output_dir=tmp_path)
    assert summary["sources"][config.SOURCE_QUOTES]["scrape_crashed"] is True
    assert summary["sources"][config.SOURCE_BOOKS]["final"] == 2


def test_cli_rejects_bad_arguments():
    for argv in (["--delay", "-1"], ["--max-pages", "0"]):
        try:
            main_module.parse_args(argv)
        except SystemExit as exit_info:
            assert exit_info.code == 2
        else:
            raise AssertionError("expected argparse error")
