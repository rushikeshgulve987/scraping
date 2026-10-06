"""Central settings for the scraping pipeline (no secrets live here)."""

SOURCE_BOOKS = "Books to Scrape"
SOURCE_QUOTES = "Quotes to Scrape"
VALID_SOURCES = {SOURCE_BOOKS, SOURCE_QUOTES}

BOOKS_START_URL = "https://books.toscrape.com/"
QUOTES_START_URL = "https://quotes.toscrape.com/"

# Fixed column order of final_dataset.csv
OUTPUT_COLUMNS = [
    "source",
    "source_url",
    "name_or_title",
    "category",
    "price",
    "rating",
    "author",
    "tags",
    "description",
    "scraped_at",
]

# HTTP behaviour
USER_AGENT = "ScrapingAssignment/1.0 (learning project)"
REQUEST_TIMEOUT = 10        # seconds
REQUEST_DELAY = 0.5         # polite pause after every successful request
MAX_RETRIES = 3
RETRY_BACKOFF = 1.0         # 1s, 2s, 4s between retries
RETRY_STATUSES = [429, 500, 502, 503, 504]

# Output locations (overridable from the CLI)
OUTPUT_DIR = "output"
LOG_DIR = "logs"
