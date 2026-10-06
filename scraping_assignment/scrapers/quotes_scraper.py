"""Quotes to Scrape: selectors live ONLY here."""
import logging

import config
from scrapers.base_scraper import BaseScraper, utc_now_iso

logger = logging.getLogger(__name__)


class QuotesScraper(BaseScraper):
    source_name = config.SOURCE_QUOTES
    start_url = config.QUOTES_START_URL

    def parse_page(self, soup, page_url):
        records = []
        for index, block in enumerate(soup.select("div.quote"), start=1):
            try:
                records.append(self.parse_quote(block, page_url))
            except Exception:
                logger.exception("[%s] skipping record #%d on %s", self.source_name, index, page_url)
        return records

    @staticmethod
    def parse_quote(block, page_url):
        text = block.select_one("span.text")
        author = block.select_one("small.author")
        return {
            "text_raw": text.get_text() if text else None,
            "author_raw": author.get_text() if author else None,
            "tags_raw": [tag.get_text() for tag in block.select("div.tags a.tag")],
            "source_url": page_url,  # the page the quote appeared on
            "scraped_at": utc_now_iso(),
        }
