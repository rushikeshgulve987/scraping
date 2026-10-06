"""Books to Scrape: selectors and detail-page logic live ONLY here."""
import logging
from urllib.parse import urljoin

import requests

import config
from scrapers.base_scraper import BaseScraper, utc_now_iso

logger = logging.getLogger(__name__)


class BooksScraper(BaseScraper):
    source_name = config.SOURCE_BOOKS
    start_url = config.BOOKS_START_URL

    def __init__(self, *args, fetch_details=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fetch_details = fetch_details

    # ---- listing pages ----------------------------------------------
    def parse_page(self, soup, page_url):
        records = []
        for index, article in enumerate(soup.select("article.product_pod"), start=1):
            try:
                records.append(self.parse_book(article, page_url))
            except Exception:
                logger.exception("[%s] skipping record #%d on %s", self.source_name, index, page_url)
        return records

    @staticmethod
    def parse_book(article, page_url):
        """Raw (uncleaned) values; a missing element becomes None, never an exception."""
        link = article.select_one("h3 > a")
        price = article.select_one("p.price_color")
        rating = article.select_one("p.star-rating")
        href = link.get("href") if link else None
        return {
            "title": (link.get("title") or link.get_text()) if link else None,
            "source_url": urljoin(page_url, href) if href else None,
            "price_raw": price.get_text() if price else None,
            "rating_raw": " ".join(rating.get("class", [])) if rating else None,
            "category_raw": None,
            "description_raw": None,
            "scraped_at": utc_now_iso(),
        }

    # ---- detail pages -----------------------------------------------
    @staticmethod
    def parse_detail(soup):
        crumbs = soup.select("ul.breadcrumb li")
        category = crumbs[2].get_text() if len(crumbs) >= 3 else None
        description = soup.select_one("#product_description + p")
        return {
            "category_raw": category,
            "description_raw": description.get_text() if description else None,
        }

    def enrich(self, records):
        if not self.fetch_details:
            logger.info("[%s] detail pages skipped (category/description stay empty)", self.source_name)
            return records
        total = len(records)
        for number, record in enumerate(records, start=1):
            url = record.get("source_url")
            if not url:
                continue
            try:
                record.update(self.parse_detail(self.fetch_soup(url)))
            except requests.RequestException as exc:
                self.detail_failures += 1
                logger.warning("[%s] detail page failed %s: %s", self.source_name, url, exc)
            except Exception:
                self.detail_failures += 1
                logger.exception("[%s] could not parse detail page %s", self.source_name, url)
            if number % 100 == 0:
                logger.info("[%s] detail pages: %d/%d", self.source_name, number, total)
        return records
