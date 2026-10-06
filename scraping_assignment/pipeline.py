"""Connects the stages: scrape -> clean -> validate -> deduplicate -> consolidate -> write."""
import csv
import json
import logging
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import config
from processing.cleaning import CLEANERS
from processing.deduplication import find_duplicates
from processing.validation import validate_record

logger = logging.getLogger(__name__)


def _new_stats():
    return {
        "scrape_crashed": False,
        "pages_fetched": 0,
        "pages_failed": 0,
        "detail_pages_failed": 0,
        "collected": 0,
        "cleaned": 0,
        "rejected": 0,
        "rejected_by_reason": {},
        "duplicates": 0,
        "final": 0,
    }


def write_csv(records, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=config.OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)  # None is written as an empty cell


def write_summary(summary: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=4, ensure_ascii=False)


def run_pipeline(scrapers, output_dir=config.OUTPUT_DIR):
    output_dir = Path(output_dir)
    started = datetime.now(timezone.utc)
    timer = time.perf_counter()

    stats_by_source = {}
    valid_records = []

    for scraper in scrapers:
        name = scraper.source_name
        stats = stats_by_source[name] = _new_stats()
        reasons = Counter()
        logger.info("=== Source: %s ===", name)

        # 1) scrape - one source crashing must not stop the other
        try:
            raw_records = scraper.scrape()
        except Exception:
            logger.exception("[%s] scraper crashed; continuing with next source", name)
            raw_records = []
            stats["scrape_crashed"] = True
        stats["pages_fetched"] = scraper.pages_fetched
        stats["pages_failed"] = scraper.pages_failed
        stats["detail_pages_failed"] = scraper.detail_failures
        stats["collected"] = len(raw_records)

        # 2) clean + 3) validate
        for raw in raw_records:
            try:
                record = CLEANERS[name](raw)
            except Exception as exc:
                reasons["cleaning_error"] += 1
                stats["rejected"] += 1
                logger.warning("[%s] REJECTED (cleaning_error): %s | %r", name, exc, raw)
                continue
            stats["cleaned"] += 1
            problems = validate_record(record)
            if problems:
                stats["rejected"] += 1
                reasons.update(problems)  # a record with 2 problems counts under both reasons
                logger.warning("[%s] REJECTED (%s): %r", name, ",".join(problems),
                               record.get("name_or_title") or record.get("source_url"))
            else:
                valid_records.append(record)
        stats["rejected_by_reason"] = dict(sorted(reasons.items()))

    # 4) deduplicate across everything that survived validation
    unique, duplicates = find_duplicates(valid_records)
    for dup in duplicates:
        stats_by_source[dup["source"]]["duplicates"] += 1
        logger.info("DUPLICATE removed (%s): %s", dup["source"], dup["name_or_title"])
    for record in unique:
        stats_by_source[record["source"]]["final"] += 1

    # 5) consolidate + write
    csv_path = output_dir / "final_dataset.csv"
    summary_path = output_dir / "summary_report.json"
    write_csv(unique, csv_path)

    totals = {key: sum(s[key] for s in stats_by_source.values())
              for key in ("collected", "cleaned", "rejected", "duplicates", "final")}
    reconciles = {
        name: s["collected"] == s["rejected"] + s["duplicates"] + s["final"]
        for name, s in stats_by_source.items()
    }
    if not all(reconciles.values()):
        logger.warning("Counts do not reconcile: %s", reconciles)

    finished = datetime.now(timezone.utc)
    summary = {
        "run": {
            "started_at": started.isoformat(timespec="seconds"),
            "finished_at": finished.isoformat(timespec="seconds"),
            "duration_seconds": round(time.perf_counter() - timer, 2),
        },
        "sources": stats_by_source,
        "totals": totals,
        "reconciliation": {
            "rule": "collected = rejected + duplicates + final (per source)",
            "per_source": reconciles,
            "final_matches_csv_rows": totals["final"] == len(unique),
        },
        "output_files": {"dataset": str(csv_path), "summary": str(summary_path)},
    }
    write_summary(summary, summary_path)
    logger.info("Finished: %d collected, %d rejected, %d duplicates, %d final (%.1fs)",
                totals["collected"], totals["rejected"], totals["duplicates"],
                totals["final"], summary["run"]["duration_seconds"])
    return summary
