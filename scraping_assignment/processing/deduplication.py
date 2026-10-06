"""Duplicate detection using a normalised fingerprint."""
import hashlib
import re
import unicodedata

import config

QUOTE_PREFIX_LENGTH = 50


def normalize_for_key(value):
    """Case-fold, strip punctuation, collapse whitespace."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())


def make_fingerprint(record):
    source = record.get("source")
    title = normalize_for_key(record.get("name_or_title"))
    if source == config.SOURCE_BOOKS:
        price = record.get("price")
        parts = [source, title, f"{price:.2f}" if price is not None else ""]
    elif source == config.SOURCE_QUOTES:
        parts = [source, normalize_for_key(record.get("author")), title[:QUOTE_PREFIX_LENGTH]]
    else:
        parts = [str(source), title]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def find_duplicates(records):
    """Return (unique, duplicates). The FIRST occurrence is kept."""
    seen, unique, duplicates = set(), [], []
    for record in records:
        fingerprint = make_fingerprint(record)
        if fingerprint in seen:
            duplicates.append(record)
        else:
            seen.add(fingerprint)
            unique.append(record)
    return unique, duplicates
