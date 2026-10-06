# AI_USAGE.md

## AI tools used
| Tool | Used for |
| --- | --- |
| Claude (Anthropic, via claude.ai chat) | Reading the assignment brief, proposing the project structure and data model, generating the initial code for all modules, the unit tests, and drafting README.md / AI_USAGE.md |

## Representative prompts
1. *(with the assignment brief and reference guide attached)* "Give me the final project for the submission."
2. *(AUTHOR: add 2–3 real follow-up prompts you used, e.g. debugging a selector or changing a rule.)*

## Which parts were AI-assisted
Essentially all of the first draft: `scrapers/*`, `processing/*`, `pipeline.py`, `main.py`, `config.py`, `tests/*`, README.md and this file. The overall design (scrape → clean → validate → deduplicate → consolidate) follows the stage layout in the assignment brief.

## Design decisions to review and be able to explain
- Books are de-duplicated on **title + price** (not title alone) so different books sharing a title are not merged.
- Duplicates are **removed** (logged and counted), not flagged.
- Quote `source_url` = the listing page the quote appeared on.
- A failed listing page ends that source only, because the next link is unknown without it.
- Books require price + rating; quotes require an author.

## Important changes made after reviewing AI output
- *(AUTHOR: fill in what you changed after reading/running the code, or write "none".)*

## Incorrect or incomplete AI suggestions discovered
- During generation, the first attempt to create the folder skeleton used a shell brace pattern that the shell did not expand, so the sub-folders were not created and the files had to be re-written; this was caught from the error output.
- *(AUTHOR: add anything you find on the live run, e.g. a selector that needed adjusting, or write "none found".)*

## How the final solution was tested and verified
**Offline unit tests (run in a fresh virtual environment with `pip install` of the pinned libraries):** 41 tests pass (`pytest`). They cover the cleaning functions, validation reason codes, duplicate detection (case/space/punctuation variants, same title different price, different sources), pagination (follows `next` links, stops at the last page, `--max-pages`, loop detection), missing HTML elements, failed pages and failed detail pages, and an end-to-end pipeline run against fake HTML that checks the CSV columns/values and that the summary counts reconcile.

**Failure path:** `python main.py` was run with the target sites unreachable; it logged the errors, still wrote an (empty) CSV and summary, and exited with code 1 without crashing.

**Live run (AUTHOR: complete after running `python main.py` on your machine):**
- Date/time of run: ____
- Pages fetched – Books: ____ (expected ~50), Quotes: ____ (expected 10)
- Records collected – Books: ____ (expected ~1000), Quotes: ____ (expected 100)
- Rejected: ____   Duplicates: ____   Final rows in CSV: ____
- Manual spot-check: opened the CSV and compared ____ random rows with the website.
- Confirmed `summary_report.json` final count equals the number of CSV rows: yes / no
