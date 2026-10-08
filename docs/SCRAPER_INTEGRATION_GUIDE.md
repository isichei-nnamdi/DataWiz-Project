# DataWiz Scraper Integration Guide

**For:** Ojo (Data Engineering Lead), Aduragbemi (Collection Engineer), and anyone
building an outlet scraper.
**From:** Success Akinnusi (Collection / NLP Engineer)
**Status:** Reference implementation working on 3 outlets (Premium Times, PRNigeria,
HumAngle). The output format below is **proposed** — it stands in for the "standard
scraper output format" pending Ojo's ratification. Adopt or amend at the next meeting.

---

## 1. Why this exists

We agreed every owner's scraper must produce **the same output shape** so datasets merge
cleanly and the verification/mapping stages downstream don't care which outlet a record
came from. This guide defines that shape and the collection behaviour around it, and gives
you a working package (`datawiz_scraper/`) to build on rather than starting from scratch.

**The golden rule:** don't invent your own output structure. Either (a) add your outlet to
the shared package's `config.py` and reuse the whole pipeline, or (b) if you must write
standalone code, emit records that validate against the schema in Section 3.

---

## 2. Pipeline stages (what every scraper must do, in order)

```
feeds ─▶ merge+dedup ─▶ SEEN check ─▶ relevance (title+summary)
      ─▶ full-text fetch (candidates only, throttled)
      ─▶ relevance re-score (full text)  ─▶ geography gate
      ─▶ extract fields ─▶ write record + mark SEEN
```

1. **Collect from RSS first.** Pull one or more feeds. Prefer category feeds — each has its
   own ~15-item window, so several together widen coverage. Merge and dedup by canonical URL.
2. **Dedup against the SEEN store** before doing any work, so re-runs are idempotent.
3. **Relevance filter (cheap pass)** on title + feed summary. Non-matches → low-confidence
   bucket (not discarded).
4. **Fetch full article text** only for candidates. Respect the per-host crawl-delay.
5. **Re-score relevance on full text** — the full-text verdict is authoritative (feed
   excerpts are short and cause both false positives and negatives).
6. **Geography gate** — this is a *Nigeria* map. No detectable Nigerian location →
   low-confidence bucket.
7. **Extract** event_type, date, location, actors, impact.
8. **Write one record per article** in the schema below; mark the URL SEEN.

Anything filtered out at steps 3/5/6 goes to `datasets/_low_confidence/` **with a reason**,
never silently dropped — that bucket is how we grow the keyword library.

---

## 3. Output schema (v0 — the contract)

One JSON array per outlet per run: `datasets/<outlet_key>/<YYYY-MM-DD>_<batch>.json`.
Each element:

```json
{
  "schema_version": "v0-provisional",
  "article_id": "sha1 of canonical source_url",
  "source": "premium_times",
  "source_url": "https://.../896847-....html",
  "fetched_at": "2026-07-20T22:37:47Z",
  "published_at": "Mon, 20 Jul 2026 17:46:54 +0000",
  "title": "Protest over killing of two women in Plateau",
  "raw_text": "full cleaned article body, boilerplate stripped",
  "collection_mode": "rss",
  "relevance": {
    "is_candidate": true,
    "matched_keywords": ["gunmen", "attack", "kill"],
    "corroborating": ["police", "security"]
  },
  "extraction": {
    "event_type": "armed_attack",
    "event_types_all": ["armed_attack", "violence_fatal"],
    "date": "Mon, 20 Jul 2026 17:46:54 +0000",
    "location": "Plateau",
    "locations_all": ["Plateau", "Jos"],
    "actors": ["gunmen", "police"],
    "impact": "2 killed"
  },
  "extraction_confidence": "low",
  "review_status": "pending"
}
```

**Field rules**
- `article_id` — `sha1(source_url)`. This is also the dedup key. Same everywhere.
- `source` — your outlet's stable key (snake_case), matching `config.py`.
- `raw_text` — **required, non-empty.** Reviewers read this; a record with empty text is a
  bug, not a candidate (see Section 6).
- `collection_mode` — `"rss"` or `"html_fallback"`.
- `extraction_confidence` — `"low"` for the rule-based stub; the real NLP model (Sprint 2)
  sets medium/high.
- `review_status` — always starts `"pending"`.
- Do **not** rename fields. If Ojo ratifies different names, we change them in ONE place
  (`schema.py::to_ojo_format`) and everyone inherits it.

---

## 4. Adding your outlet to the shared package (recommended path)

Add an entry to `datawiz_scraper/config.py`:

```python
"the_guardian": OutletConfig(
    key="the_guardian",
    name="The Guardian",
    base_url="https://guardian.ng",
    feeds=[
        "https://guardian.ng/category/nigeria/feed",
        "https://guardian.ng/category/news/feed",
    ],
    robots_status="<what you found in robots.txt>",
    crawl_delay=<seconds>,
    category_paths=["/category/nigeria"],  # for HTML fallback later
),
```

Then run:

```bash
python -m datawiz_scraper.run the_guardian --batch 0700
```

That reuses collection, dedup, relevance, geography gate, extraction, and output — you only
supply the feeds and crawl-delay. **Probe the feed URLs first** (a quick `feedparser.parse`)
to confirm they return entries before committing them.

---

## 5. Collection cadence (A+B decision)

- **Multiple feeds per outlet** (B): use category feeds, not just `/feed`. Each carries its
  own recent-item window; together they defeat the ~15-item depth limit.
- **Run more often than twice daily** (A): the `--batch` label is free-form
  (`0700`, `1100`, `1500`, `1900`), so schedule several collection runs per day.

> **Important distinction for the team:** collection frequency ≠ publishing frequency.
> Collecting every few hours does **not** change our agreed daily human-review/publish
> cadence (Meeting 3). It just avoids missing articles that roll off feeds between runs.

---

## 6. Content extraction — the gotcha that will bite you

`soup.find("article")` is **not reliable.** Many Nigerian news themes (JNews, etc.) wrap
related-post *teaser cards* in `<article>` tags with no body text, so the first `<article>`
is empty and you silently get `raw_text == ""`.

Do this instead (already implemented in `collector.py`):
1. Try named content containers first: `div.entry-content`, `div.content-inner`,
   `div.post-content`, `div.td-post-content`, `main`.
2. Fall back to the container with the **most `<p>` descendants**.
3. Strip boilerplate lines ("Follow us on Google News…", "( NAN )", "Read also…").
4. **If `raw_text` comes back empty, route to low-confidence with reason `empty_body`** —
   never emit a textless candidate.

Verified working across three different themes (Premium Times, PRNigeria, HumAngle). If your
outlet's body sits in a different container, add its selector to the list in `collector.py`.

---

## 7. Relevance, suppression, geography (shared, don't fork these)

- **Keyword library** lives in `relevance.py` (`EVENT_KEYWORDS`). Roots match morphological
  variants (`kidnap` → kidnap/kidnapped/kidnapping/kidnappers) via `\b<root>\w*\b`.
- **Suppression:** drug/regulatory-enforcement stories (NDLEA, NAFDAC, cannabis…) that only
  trip a broad keyword like "raid" and carry **no strong incident term** are downgraded.
  Keeps NDLEA drug-bust noise out of the review queue.
- **Geography gate:** no Nigerian location detected → downgraded (likely sports/international).
- All three are shared logic. If you find a false positive/negative, **fix it in the shared
  module** so every outlet benefits — don't special-case it in your scraper.

---

## 8. Respect / compliance (non-negotiable)

- Honour each outlet's `crawl_delay`; the collector throttles per host automatically.
- **Nigerian Tribune stays disabled** (`enabled=False`) — its robots.txt explicitly bans
  scraper/AI bots. Do not scrape it until the team makes a compliance decision.
- Send our identifying User-Agent (`DataWizBot/0.1`). Don't spoof browsers.
- MVP is **secondary published data only** (D-018) — article text, not personal data.

---

## 9. Known limitations (honest list, for Sprint 2)

- **Extraction is a rule-based stub.** For long-form articles covering several incidents it
  picks one primary `event_type` (first match). Real NLP replaces this in Sprint 2.
- **`impact`** catches digit and small spelled-out counts ("2 killed", "twelve dead") but not
  every phrasing.
- **NTA has no RSS feed** (Next.js site). It needs the HTML-fallback collector, which is
  scaffolded in config (`category_paths`) but not yet built.
- **Location gazetteer** is states + FCT + major hotspot towns; smaller LGAs/villages may not
  resolve, which can trip the geography gate. Extend `extract.py::LOCATIONS` as needed.

---

## 10. Open items for Ojo / the meeting

1. **Ratify or amend the output schema** in Section 3 (it's currently `v0-provisional`).
2. Confirm the **Drive → Postgres** handoff: these JSON records map to which tables/columns?
3. Confirm **interim storage layout** in Drive matches `datasets/<outlet>/<date>_<batch>.json`.
4. Decide **collection cadence** (how many runs/day) and confirm it's decoupled from the
   daily publish/review batch.
5. Nigerian Tribune scraping — compliance go/no-go.
