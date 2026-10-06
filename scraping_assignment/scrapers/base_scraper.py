"""Shared networking + pagination logic. Knows nothing about any specific site."""
import logging
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

import config

logger = logging.getLogger(__name__)


def create_session() -> requests.Session:
    """Session with a User-Agent and automatic retries (exponential backoff)."""
    session = requests.Session()
    session.headers.update({"User-Agent": config.USER_AGENT})
    retries = Retry(
        total=config.MAX_RETRIES,
        backoff_factor=config.RETRY_BACKOFF,
        status_forcelist=config.RETRY_STATUSES,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class BaseScraper:
    """Subclasses set source_name/start_url and implement parse_page()."""

    source_name = ""
    start_url = ""
    next_selector = "li.next > a"

    def __init__(self, session=None, delay=config.REQUEST_DELAY,
                 timeout=config.REQUEST_TIMEOUT, max_pages=None):
        self.session = session or create_session()
        self.delay = delay
        self.timeout = timeout
        self.max_pages = max_pages
        self.pages_fetched = 0
        self.pages_failed = 0
        self.detail_failures = 0

    # ---- networking -------------------------------------------------
    def fetch_soup(self, url: str) -> BeautifulSoup:
        """Download one URL and parse it. Raises requests.RequestException on failure."""
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        response.encoding = "utf-8"  # keeps the £ sign correct
        soup = BeautifulSoup(response.text, "lxml")
        if self.delay:
            time.sleep(self.delay)
        return soup

    # ---- hooks for subclasses ---------------------------------------
    def parse_page(self, soup, page_url):
        raise NotImplementedError

    def enrich(self, records):
        """Optional second pass (e.g. visiting detail pages). Default: no-op."""
        return records

    # ---- pagination -------------------------------------------------
    def _next_url(self, soup, page_url):
        link = soup.select_one(self.next_selector)
        href = link.get("href") if link else None
        return urljoin(page_url, href) if href else None

    def scrape(self):
        records, visited = [], set()
        url, page = self.start_url, 0
        while url:
            if self.max_pages and page >= self.max_pages:
                logger.info("[%s] reached --max-pages=%d, stopping", self.source_name, self.max_pages)
                break
            if url in visited:
                logger.warning("[%s] pagination loop detected at %s, stopping", self.source_name, url)
                break
            visited.add(url)
            page += 1
            logger.info("[%s] page %d: %s", self.source_name, page, url)

            try:
                soup = self.fetch_soup(url)
            except requests.RequestException as exc:
                self.pages_failed += 1
                logger.error("[%s] failed to fetch %s: %s", self.source_name, url, exc)
                break  # without this page we cannot find the next link
            self.pages_fetched += 1

            try:
                page_records = self.parse_page(soup, url)
            except Exception:
                logger.exception("[%s] could not parse %s; moving on", self.source_name, url)
                page_records = []
            logger.info("[%s] page %d -> %d records", self.source_name, page, len(page_records))
            records.extend(page_records)
            url = self._next_url(soup, url)

        return self.enrich(records)
