"""Run the whole job:  python main.py   (see --help for options)."""
import argparse
import logging
import sys
from pathlib import Path

import config
from pipeline import run_pipeline
from scrapers.books_scraper import BooksScraper
from scrapers.quotes_scraper import QuotesScraper


def setup_logging(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "scraper.log"
    formatter = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    handlers = [logging.StreamHandler(), logging.FileHandler(log_file, mode="w", encoding="utf-8")]
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)
    for handler in handlers:
        handler.setFormatter(formatter)
        root.addHandler(handler)
    return log_file


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Multi-source scraping and consolidation pipeline")
    parser.add_argument("--sources", nargs="+", choices=["books", "quotes"],
                        default=["books", "quotes"], help="which sources to scrape (default: both)")
    parser.add_argument("--skip-details", action="store_true",
                        help="do not visit each book's detail page (faster; category/description stay empty)")
    parser.add_argument("--max-pages", type=int, default=None,
                        help="stop each source after N listing pages (useful for quick tests)")
    parser.add_argument("--delay", type=float, default=config.REQUEST_DELAY,
                        help="seconds to pause after each request (default: %(default)s)")
    parser.add_argument("--output-dir", default=config.OUTPUT_DIR)
    parser.add_argument("--log-dir", default=config.LOG_DIR)
    args = parser.parse_args(argv)
    if args.delay < 0:
        parser.error("--delay must be >= 0")
    if args.max_pages is not None and args.max_pages < 1:
        parser.error("--max-pages must be >= 1")
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    log_file = setup_logging(Path(args.log_dir))
    logger = logging.getLogger("main")
    logger.info("Starting run with options: %s", vars(args))

    common = {"delay": args.delay, "max_pages": args.max_pages}
    scrapers = []
    if "books" in args.sources:
        scrapers.append(BooksScraper(fetch_details=not args.skip_details, **common))
    if "quotes" in args.sources:
        scrapers.append(QuotesScraper(**common))

    summary = run_pipeline(scrapers, output_dir=args.output_dir)
    logger.info("Log written to %s", log_file)
    return 0 if summary["totals"]["final"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
