"""Validation returns a LIST OF REASONS so the summary can explain every rejection."""
import math
from urllib.parse import urlparse

import config


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and not math.isnan(value)


def validate_record(record):
    """Return [] if the record is valid, otherwise a list of reason codes."""
    problems = []
    source = record.get("source")

    if source not in config.VALID_SOURCES:
        problems.append("unknown_source")
    if not record.get("name_or_title"):
        problems.append("missing_name")

    parts = urlparse(str(record.get("source_url") or ""))
    if parts.scheme not in ("http", "https") or not parts.netloc:
        problems.append("invalid_url")

    price = record.get("price")
    if price is not None and (not _is_number(price) or price < 0):
        problems.append("invalid_price")
    rating = record.get("rating")
    if rating is not None and rating not in (1, 2, 3, 4, 5):
        problems.append("invalid_rating")

    # Source-specific required fields
    if source == config.SOURCE_BOOKS:
        if price is None:
            problems.append("missing_price")
        if rating is None:
            problems.append("missing_rating")
    elif source == config.SOURCE_QUOTES:
        if not record.get("author"):
            problems.append("missing_author")
    return problems
