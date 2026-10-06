"""Pure cleaning functions: no network, no files."""
import re
import unicodedata
from urllib.parse import urljoin, urlparse, urlunparse

import config

RATING_MAP = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
_QUOTE_PAIRS = (("\u201c", "\u201d"), ('"', '"'))


def clean_text(value):
    """Unicode-normalise, collapse all whitespace (incl. \\xa0). Empty -> None."""
    if value is None:
        return None
    text = unicodedata.normalize("NFKC", str(value))
    text = " ".join(text.split())
    return text or None


def strip_quotes(value):
    """Remove ONE pair of wrapping quotation marks (curly or straight)."""
    if not value:
        return value
    for left, right in _QUOTE_PAIRS:
        if len(value) >= 2 and value.startswith(left) and value.endswith(right):
            return value[1:-1].strip() or None
    return value


def clean_price(raw):
    """'£51.77' -> 51.77; '£1,234.50' -> 1234.5; unparseable -> None."""
    if raw is None:
        return None
    match = re.search(r"\d+(?:\.\d+)?", str(raw).replace(",", ""))
    return float(match.group()) if match else None


def clean_rating(raw):
    """'star-rating Three' / 'Three' / '3' -> 3; unparseable -> None."""
    for word in str(raw or "").lower().split():
        if word in RATING_MAP:
            return RATING_MAP[word]
        if word.isdigit():
            return int(word)
    return None


def clean_tags(tags):
    """Lowercase, trim, de-duplicate, sort, join with ';'. No tags -> None."""
    cleaned = {clean_text(t).lower() for t in (tags or []) if clean_text(t)}
    return ";".join(sorted(cleaned)) or None


def normalize_url(url, base=None):
    """Return an absolute http(s) URL (no fragment) or None if it is not valid."""
    text = clean_text(url)
    if not text:
        return None
    if base:
        text = urljoin(base, text)
    parts = urlparse(text)
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
        return None
    return urlunparse((parts.scheme.lower(), parts.netloc.lower(), parts.path,
                       parts.params, parts.query, ""))


def _blank_record(source):
    record = {column: None for column in config.OUTPUT_COLUMNS}
    record["source"] = source
    return record


def clean_book_record(raw):
    record = _blank_record(config.SOURCE_BOOKS)
    record.update(
        source_url=normalize_url(raw.get("source_url")),
        name_or_title=clean_text(raw.get("title")),
        category=clean_text(raw.get("category_raw")),
        price=clean_price(raw.get("price_raw")),
        rating=clean_rating(raw.get("rating_raw")),
        description=clean_text(raw.get("description_raw")),
        scraped_at=raw.get("scraped_at"),
    )
    return record


def clean_quote_record(raw):
    record = _blank_record(config.SOURCE_QUOTES)
    record.update(
        source_url=normalize_url(raw.get("source_url")),
        name_or_title=strip_quotes(clean_text(raw.get("text_raw"))),
        author=clean_text(raw.get("author_raw")),
        tags=clean_tags(raw.get("tags_raw")),
        scraped_at=raw.get("scraped_at"),
    )
    return record


CLEANERS = {
    config.SOURCE_BOOKS: clean_book_record,
    config.SOURCE_QUOTES: clean_quote_record,
}
