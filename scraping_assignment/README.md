# Multi-Source Web Scraping & Data Consolidation

A Python ETL pipeline that scrapes two public practice sites, converts their different structures into one common schema, cleans and validates every record, removes duplicates, and writes one consolidated CSV plus a JSON summary and a log file.

```
Books to Scrape  ─┐
                  ├─> Scrape -> Clean -> Validate -> Deduplicate -> Consolidate -> final_dataset.csv
Quotes to Scrape ─┘                                                              summary_report.json
```

## Python version
Python 3.10 – 3.12 (developed and unit-tested on Python 3.12.3).

## Setup
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Dependencies
| Library | Purpose |
| --- | --- |
| `requests` | HTTP requests (session, timeouts, retries) |
| `beautifulsoup4` + `lxml` | HTML parsing |
| `pytest` | Unit tests (optional) |

Everything else (`csv`, `json`, `logging`, `re`, `hashlib`, `urllib.parse`, `argparse`…) is the standard library. `requirements.txt` pins the exact versions used. No API keys or accounts are needed.

## How to run
```bash
python main.py                      # full run: both sources, incl. book detail pages
python main.py --skip-details       # faster: skip per-book detail pages (category/description stay empty)
python main.py --max-pages 2        # quick smoke test: 2 listing pages per source
python main.py --sources quotes     # only one source
python main.py --delay 1.0          # slower / more polite
python main.py --help
pytest                              # unit tests (offline, no internet needed)
```
A full default run visits ~50 + 10 listing pages and ~1,000 book detail pages with a 0.5 s pause after every request, so expect roughly 10–15 minutes. `--skip-details` takes about a minute. Exit code is `0` if at least one record was written, `1` otherwise.

Outputs: `output/final_dataset.csv`, `output/summary_report.json`, `logs/scraper.log`.

## Source exploration (Step 1)
| Item | Books to Scrape | Quotes to Scrape |
| --- | --- | --- |
| One record | `article.product_pod` | `div.quote` |
| Main text | `h3 > a` – the **full** title is in the `title` attribute (visible text is truncated with `...`) | `span.text` (wrapped in curly quotes) |
| Price | `p.price_color` (`£51.77`) | – |
| Rating | class on `p.star-rating` (`Three`) – a word, not a number | – |
| Author / tags | – | `small.author`, `div.tags a.tag` (0 or more) |
| Link | `h3 > a[href]` – relative, and relative to the *current* page | none per quote |
| Category / description | **Only** on the book detail page (breadcrumb, `#product_description + p`) | – |
| Pagination | `li.next > a` (relative href; ~50 pages) | `li.next > a` (`/page/N/`; 10 pages) |

Both sites are server-rendered HTML, so Requests + BeautifulSoup is enough; Selenium/Playwright would only add overhead.

## How pagination works
`BaseScraper.scrape()` starts at the source's start URL, parses the page, then looks for `li.next > a`, joins its (relative) `href` to the current URL with `urljoin`, and repeats until there is no next link. Page numbers are never hard-coded, so it adapts if a site gains or loses pages. Safety nets: a `visited` set stops infinite loops, and `--max-pages` caps the run for testing.

## Data model
One schema for both sources (columns in this order):

| Column | Books | Quotes |
| --- | --- | --- |
| `source` | `Books to Scrape` | `Quotes to Scrape` |
| `source_url` | Book detail page URL | URL of the listing page the quote appeared on (quotes have no page of their own) |
| `name_or_title` | Book title | Quote text (wrapping curly quotes removed) |
| `category` | From detail page | empty |
| `price` | Float, e.g. `51.77` (pound sign dropped; currency is GBP) | empty |
| `rating` | Integer 1–5 | empty |
| `author` | empty | Author name |
| `tags` | empty | Lower-case, sorted, `;`-joined |
| `description` | From detail page | empty |
| `scraped_at` | UTC ISO timestamp | UTC ISO timestamp |

Fields that do not apply are left **empty (None → empty CSV cell)**. Nothing is invented (e.g. quotes do not get a price of 0).

## Cleaning approach (`processing/cleaning.py`)
Pure functions with no network or file access, so they are tested with plain strings.
- `clean_text`: Unicode NFKC normalisation, collapses all whitespace including `\xa0`, empty → `None`.
- `strip_quotes`: removes exactly one wrapping pair of curly/straight double quotes.
- `clean_price`: `£1,234.50` → `1234.5`; unparseable → `None`.
- `clean_rating`: `star-rating Three` → `3`.
- `clean_tags`: trim, lower-case, de-duplicate, sort.
- `normalize_url`: makes URLs absolute, lower-cases scheme/host, drops fragments, returns `None` unless http(s).
- `response.encoding = "utf-8"` is set before parsing so `£` is not read as `Â£`.

## Validation approach (`processing/validation.py`)
`validate_record()` returns a **list of reason codes** (empty = valid), so the report can explain every rejection:
`unknown_source`, `missing_name`, `invalid_url`, `invalid_price` (negative/NaN/non-numeric), `invalid_rating` (not 1–5), and source-specific required fields: `missing_price`, `missing_rating` (books) and `missing_author` (quotes). Quotes with no tags are valid (tags are optional). Rejected records are logged as warnings and counted in the summary; a record with several problems is counted once in `rejected` but under each reason in `rejected_by_reason`.

## Deduplication approach (`processing/deduplication.py`)
Each record gets a SHA-256 **fingerprint** of normalised identifying fields. Normalisation = NFKC, case-fold, strip punctuation, collapse whitespace.
- **Books:** source + normalised title + price (2 decimals).
- **Quotes:** source + normalised author + first 50 characters of the normalised quote text.

So `"Example Book Title"`, `" Example Book Title "` and `"EXAMPLE BOOK TITLE"` are one record. Books also include price so two different books that merely share a title are not merged; including `source` means the same text in two different sources is never treated as a duplicate. The **first occurrence is kept** and later ones are **removed** (not flagged) because the deliverable is a clean consolidated dataset; every removed duplicate is logged at INFO level and counted in the summary. The practice sites are expected to contain few or no duplicates, so the logic is proven by unit tests with deliberately duplicated data (`tests/test_deduplication.py`, `tests/test_pipeline.py`).

## Error-handling approach
- `requests.Session` with a timeout (10 s) and `urllib3` retries with exponential backoff (1 s, 2 s, 4 s) for 429/500/502/503/504 and connection errors.
- A failed listing page is logged as an ERROR and ends that source only (without the page we cannot find the next link); records already collected are kept and the other source still runs.
- A failed book detail page is a WARNING; the book is kept with empty category/description and counted as `detail_pages_failed`.
- Every record is parsed in its own `try/except`; missing HTML elements give `None`, never an exception.
- Cleaning errors become rejections (`cleaning_error`); a scraper that crashes unexpectedly is contained in `run_pipeline`.
- The `logs/scraper.log` file records every page, rejection, duplicate and error with timestamps.

## Output description
- `output/final_dataset.csv` – UTF-8, fixed column order, one row per valid unique record.
- `output/summary_report.json` – per source: pages fetched/failed, detail pages failed, collected, cleaned, rejected (+ reasons), duplicates, final; plus totals, run start/end/duration, and a reconciliation block (`collected = rejected + duplicates + final` per source, and final count = CSV rows).
- `logs/scraper.log` – overwritten on every run.

## Project structure
```
scraping_assignment/
├── scrapers/        base_scraper.py (session, retries, pagination), books_scraper.py, quotes_scraper.py
├── processing/      cleaning.py, validation.py, deduplication.py
├── tests/           offline unit tests + fake HTTP session/HTML fixtures
├── output/          final_dataset.csv, summary_report.json
├── logs/            scraper.log
├── config.py        URLs, schema column order, timeouts, retry settings
├── pipeline.py      connects the stages and writes the outputs
├── main.py          CLI entry point + logging setup
├── requirements.txt, README.md, AI_USAGE.md
```
Rule of thumb: anything touching the internet is in `scrapers/`, anything that only transforms data is in `processing/`, `pipeline.py`/`main.py` connect them.

## Assumptions
- Prices are GBP and are stored as plain numbers (no currency column).
- A quote's `source_url` is the listing page it appeared on.
- Books require a price and rating; quotes require an author.
- Tag order is irrelevant, so tags are sorted for consistency.

## Known limitations
- If a listing page fails after all retries, the rest of that source is not scraped (the next link is unknown); this is logged and reflected in `pages_failed`.
- Scraping is sequential (one request at a time, on purpose, to respect the server).
- Category/description require ~1,000 extra requests; use `--skip-details` to avoid them.
- Selectors are specific to the current page layout of the practice sites.
- No persistence beyond CSV/JSON, no checkpoint/resume, and no incremental scraping.

## AI usage summary
Claude (Anthropic) was used to draft the code, tests and documentation; see `AI_USAGE.md` for details, what was verified and how.
