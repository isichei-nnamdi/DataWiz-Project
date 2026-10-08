# Scraper Pipeline Plan — Collection / NLP

**Owner:** Success Akinnusi (Collection / NLP Engineer)
**Sprint:** Sprint 1 — Foundation (13–26 Jul 2026)
**Date drafted:** 19 July 2026

## Context

Ojo (Data Engineering Lead) was absent from Meeting 4, so the two items that
formally gate this work were not ratified:

1. **Standard scraper output format** — "unblocks all owners" (Meeting 4 Pack, Sprint 1 Checkpoint).
2. **Architecture, ETL & storage direction** — "Blocks scraping runs and schema work" (Meeting 4 Pack, Top risks).

Decision: forge ahead against a **provisional schema (v0)** isolated behind a single
mapping file, so adopting Ojo's ratified format later is a one-file change rather than a
rewrite. robots.txt / relevance / dedup work is explicitly cleared to proceed in parallel
(Meeting 3 minutes, closing note).

## Assigned outlets

| Outlet | Status |
|---|---|
| Premium Times | Build — open robots.txt (crawl-delay 10s) |
| PRNigeria | Build — open robots.txt |
| HumAngle | Build — open robots.txt |
| NTA | Build — open robots.txt (Next.js site) |
| Nigerian Tribune | **Held back** — explicit bot ban in robots.txt; awaiting team compliance decision |

## Provisional output schema (v0)

Kept in a single schema definition file. When Ojo's format is ratified, remap field
names in this one place only.

```json
{
  "article_id": "<hash of canonical URL>",
  "source": "premium_times | prnigeria | humangle | nta",
  "source_url": "...",
  "fetched_at": "ISO8601",
  "published_at": "ISO8601 | null",
  "title": "...",
  "raw_text": "...",
  "collection_mode": "rss | html_fallback",
  "relevance": { "is_candidate": true, "matched_keywords": [] },
  "extraction": {
    "event_type": "...", "date": "...", "location": "...",
    "actors": [], "impact": "..."
  },
  "extraction_confidence": "low | medium | high",
  "review_status": "pending"
}
```

## Architecture

- **Per-outlet config file** — base URL, RSS/sitemap feed URL, robots.txt status,
  crawl-delay, category paths for HTML fallback.
- **Scheduler** — twice daily (fixed morning & evening times), one job per outlet.
  Consistent with the daily-batch (not real-time) publishing decision (D-018); flag to
  Solomon that "daily" in the Decision Log should read "twice-daily" for review-queue
  capacity planning.
- **Collector** — RSS/sitemap-first; fall back to HTML category-page fetch when the feed
  is missing (404), stale (no update beyond the outlet's expected frequency), or thin
  (item count far below what the homepage shows).
- **Dedup check** — hash of canonical URL against a "seen" store (flat CSV in Drive to
  start; Postgres later) before any downstream work runs. Guarantees idempotent re-runs.
- **Relevance filter** — security-keyword library + normalization (lowercase, strip
  stopwords/punctuation, lemmatize). Zero-match articles go to a low-confidence bucket
  for periodic manual spot-check, NOT discarded — feeds keyword-library growth.
- **Extraction (NLP)** — runs only on relevance-passed candidates. Fields: event_type,
  date, location, actors, impact. Rule-based first pass in Sprint 1; real NLP model is a
  Sprint 2 deliverable per the roadmap.
- **Output** — raw text + extracted fields written together, one record per article, into
  the shared Drive dataset folder, one subfolder per outlet.

## Drive folder layout (interim storage, per current decision)

```
/datasets/
  /premium_times/2026-07-19_am.json
  /prnigeria/...
  /humangle/...
  /nta/...
  /_seen_urls.csv        (dedup store)
  /_low_confidence/      (zero-keyword-match articles for review)
```

## Build order (within Sprint 1)

1. Per-outlet config + RSS/sitemap collector (4 outlets; skip Tribune).
2. Dedup check against `_seen_urls.csv`.
3. Keyword library v1 + relevance filter.
4. HTML fallback logic — only for outlets where the feed proves thin/missing (verify per
   source first).
5. Provisional extraction schema wiring (rule-based stub for Sprint 1).
6. Sample dataset run → upload to Drive → Sprint 1 demo deliverable.

## Flagged dependencies (resolve, but not blockers to starting)

- Ojo's ratified output format — remap schema file when it lands.
- Ojo's ETL/architecture ratification — affects handoff/Postgres timing, not whether the
  scraper can be built.
- Nigerian Tribune scraping — team compliance decision required before building.
