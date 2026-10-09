# DataWiz Data Dictionary

**Status:** v1 draft, 9 October 2026. Maintained by Success Akinnusi.
**Supersedes:** nothing. This is the first data dictionary kept in the repository. The Drive copy referenced in the README (Ojo Ilesanmi's Sprint 1 deliverable) was not available when this was written. If it turns up, reconcile the two and record which one wins.

## How to read this document

This dictionary has two layers:

| Layer | What it describes | Status |
|---|---|---|
| **Part A: Collection records** | What the collector writes today (`scrapers/` + `pipeline/`), schema `v0-provisional`. | **Implemented.** Every claim here is checked against the code. |
| **Part B: Database tables** | The PostgreSQL/Supabase tables the README's core data model calls for. | **Proposed.** Nothing is migrated yet. |

Conventions:
- **OPEN** marks a decision nobody has made. The dictionary states a recommended default and does not treat it as settled. All open items are collected in [Part D](#part-d-open-decisions).
- **Known issue** marks a defect in the current implementation that affects what a field means. These are real behaviours of the code today, not future work.
- In Part A, **Type and expected shape** gives the JSON type first, then the form a valid value takes (a pattern, a literal, an allowed set, or an array's contents). "Always set in a written record" means the collector guarantees it for records in the candidate file, even where the field is nullable in general.
- Enumerations are defined once, in [Part C](#part-c-enumerations), and referenced by name.
- The Verification Standards in the README (numbered 1–7) are cited as **Std 1** to **Std 7**.

---

## Part A: Collection records (implemented, `v0-provisional`)

Source of truth in code: `pipeline/schema.py` (record shape), `pipeline/relevance.py`, `pipeline/extract.py`, `pipeline/dedup.py`, `scrapers/run.py`, `scrapers/config.py`.

The only place field names are defined is `pipeline/schema.py::build_record`. Any rename happens there (and in `to_ojo_format`, currently an identity stub).

### A1. Candidate record

Written to `datasets/<outlet_key>/<YYYY-MM-DD>_<batch>.json` as a JSON array. One element per article that passed relevance and the geography gate.

| Field | Type and expected shape | Null? | Meaning | Produced by |
|---|---|---|---|---|
| `schema_version` | `string`, the literal `v0-provisional` | no | Always `"v0-provisional"`. Bump on any change to this table. | `schema.py` |
| `article_id` | `string`, 40 lowercase hex chars: `^[0-9a-f]{40}$` | no | `sha1(source_url.strip())`. Dedup key and primary identifier of a collected article. | `schema.article_id` |
| `source` | `string`, snake_case outlet key: `^[a-z_]+$` (see C1) | no | Outlet key. One of the values in [Part C: source keys](#c1-source-keys). | `config.py` |
| `source_url` | `string`, absolute `http(s)://` URL | no | The article URL exactly as the feed gave it. **Known issue:** not canonicalised, so `?utm_*`, trailing slashes and `http`/`https` variants hash to different ids. |  `collector.fetch_feed` |
| `fetched_at` | `string`, `YYYY-MM-DDTHH:MM:SS[.ffffff]+00:00` (UTC) | no | When the record was built, e.g. `2026-10-09T08:14:02.118000+00:00`. | `schema.build_record` |
| `published_at` | `string` or `null`; usually RFC-822, `Ddd, DD Mon YYYY HH:MM:SS +0000`; not validated | **yes** | The outlet's own timestamp, passed through **unparsed** (typically RFC-822, e.g. `Mon, 20 Jul 2026 17:46:54 +0000`). Null if the feed gave none. **Known issue:** not normalised. Parse before storing as a timestamp. | `collector.fetch_feed` |
| `title` | `string`, trimmed; non-empty in practice, not enforced | no | Feed title, whitespace-trimmed. | `collector.fetch_feed` |
| `raw_text` | `string`, plain text with no HTML, paragraphs separated by a newline character (`\n`), non-empty | no, non-empty | Cleaned article body: paragraphs joined with `\n`, boilerplate lines removed. A record with empty text is routed to the low-confidence file instead, never written here. **Internal only.** Never publish it (outlet copyright). | `collector.fetch_article_text` |
| `collection_mode` | `string`, one of `rss` / `html_fallback` | no | `"rss"` today. `"html_fallback"` is reserved for outlets without a feed (NTA) and is not implemented. | `run.py` |
| `relevance` | `object` with exactly the keys `is_candidate`, `matched_keywords`, `corroborating` | no | See [A1.1](#a11-relevance-object). | `relevance.score` |
| `extraction` | `object` with exactly the keys `event_type`, `event_types_all`, `date`, `location`, `locations_all`, `actors`, `impact` | no | See [A1.2](#a12-extraction-object). | `extract.extract` |
| `extraction_confidence` | `string`, one of `low` / `medium` / `high` | no | Always `"low"` today (hardcoded in `run.py`). Allowed values: `low`, `medium`, `high`. **Known issue:** carries no information until a real extractor sets it. | `run.py` |
| `review_status` | `string`, `pending` at creation | no | Always `"pending"` at creation. | `schema.build_record` |

#### A1.1 `relevance` object

| Field | Type and expected shape | Meaning |
|---|---|---|
| `is_candidate` | `boolean`, always `true` in a written record | Always `true` in a written record (non-candidates go to the low-confidence file). True when at least one event keyword matched and the article was not suppressed. **Known issue:** a single keyword match is enough, so precision is low (for example "cult" matches *culture* and *cultivate*, "attack" matches *heart attack*). |
| `matched_keywords` | `array<string>`, 1 or more lowercase roots; a root may contain a space (`boko haram`) | Event keyword **roots** that matched (for example `kidnap`, `gunmen`, `attack`). Roots match with `\b<root>\w*\b`; multi-word roots match literally. |
| `corroborating` | `array<string>`, 0 or more lowercase roots | Supporting terms that matched (`troops`, `police`, `casualt`, and so on). Informational only: **not used in the candidate decision.** |

#### A1.2 `extraction` object

| Field | Type and expected shape | Null? | Meaning |
|---|---|---|---|
| `event_type` | `string` or `null`; a key from C2; always set in a written record | yes | First matching category key in the order of `EVENT_KEYWORDS` (not the most prominent one). One of the 11 values in [C2](#c2-scraper-event-type-keys-provisional). |
| `event_types_all` | `array<string>`, 1 or more unique keys from C2 | no | Every category key that matched, in `EVENT_KEYWORDS` order, de-duplicated. |
| `date` | `string` or `null`, same shape as `published_at` | yes | Currently a copy of `published_at`. **It is the publish date, not the date of the incident.** |
| `location` | `string` or `null`; one gazetteer name (a state, `Abuja`, `FCT`, or a listed town); always set in a written record | yes | First gazetteer entry (state or listed town) found **anywhere in the text**, in gazetteer order, not text order. **Known issue:** may not be the incident site, and `Niger` also matches "Niger Republic". |
| `locations_all` | `array<string>`, 1 or more gazetteer names; may repeat | no | Every gazetteer entry found. **Known issue:** may contain duplicates (for example `Sokoto` twice), because the gazetteer lists it twice. Never empty in a written record, since the geography gate rejects empties. |
| `actors` | `array<string>`, 0 or more names from the fixed actor list (`bandits`, `Boko Haram`, ...) | no | Matches from a fixed list (`bandits`, `gunmen`, `Boko Haram`, `police`, `troops`, ...). **Known issue:** includes responders (`police`, `troops`, `soldiers`, `vigilantes`) as well as perpetrators, so this is not a perpetrator list (Std 7). |
| `impact` | `string` or `null`: `<count> <outcome>`. `count` is 1 to 4 digits, or `several` / `many`. `outcome` is one of `killed`, `dead`, `abducted`, `kidnapped`, `injured`, `wounded`, `missing`, `beheaded`, `shot` | yes | Casualty phrase as `"<count> <outcome>"`, for example `"12 killed"`, `"30 abducted"`. Victim type is dropped. Only the **first** matching phrase in the text is kept, so a story with several casualty types reports just one (for example "abducted 12 ... two women were killed" yields `2 killed`). Outcome words: killed, dead, abducted, kidnapped, injured, wounded, missing, beheaded, shot. **Known issues:** vague words become invented numbers (`dozens` → 24, `scores` → 20); "no one was killed" yields `"1 killed"`. Do not treat as a figure (Std 4). |

### A2. Low-confidence record

Written to `datasets/_low_confidence/<outlet_key>_<YYYY-MM-DD>_<batch>.json`. Articles that were seen but not emitted as candidates. They are never silently dropped.

| Field | Type and expected shape | Meaning |
|---|---|---|
| `title` | `string`, the feed title | Feed title. |
| `url` | `string`, absolute `http(s)://` URL | Article URL. (Note: the candidate record calls this `source_url`.) |
| `published` | `string` or `null`, raw outlet timestamp (same shape as `published_at`) | Raw outlet timestamp. (The candidate record calls this `published_at`.) |
| `reason` | `string`: one of the seven prefixes below, optionally followed by `: <detail>` | Why it was filed here. One of the patterns below. |

`reason` values (exact prefixes, produced in `run.py`):

| Reason (prefix) | Stage | Meaning |
|---|---|---|
| `no keyword match in title+summary` | cheap pass | No event keyword in the feed title or excerpt. Not re-examined later. |
| `suppressed (drug/regulatory context, no strong incident term): <roots>` | cheap pass | Only broad keywords matched, alongside drug/regulatory terms. |
| `fetch_error: <message>` | full-text fetch | The page request failed. **Known issue:** the URL is still marked seen, so it is never retried. |
| `empty_body: content selector matched nothing` | full-text fetch | No article body could be extracted. |
| `suppressed on full text (drug/regulatory context): <roots>` | full-text re-score | As above, on the full body. |
| `no keyword match on full text (feed excerpt matched)` | full-text re-score | The excerpt matched but the body did not. |
| `no Nigerian location detected (likely out-of-scope: sports/international)` | geography gate | No gazetteer entry anywhere in the text. |

### A3. Seen-URL store

`datasets/_seen_urls.csv`. Header row, then one row per article ever processed (kept, filed low-confidence, or failed).

| Column | Type and expected shape | Meaning |
|---|---|---|
| `article_id` | `string`, 40 lowercase hex chars: `^[0-9a-f]{40}$` | As in A1. |
| `source_url` | `string`, absolute URL (CSV-quoted if it contains a comma) | The URL that was hashed. |
| `first_seen` | `string`, `YYYY-MM-DDTHH:MM:SS[.ffffff]+00:00` (UTC) | When it was first recorded. |

Interim only. Part B replaces this with a unique constraint on `raw_reports.article_id`.

### A4. Outlet configuration (`OutletConfig`)

| Field | Type and expected shape | Meaning |
|---|---|---|
| `key` | `string`, unique snake_case: `^[a-z_]+$` | Stable outlet id, used in filenames and records. |
| `name` | `string` | Display name. |
| `base_url` | `string`, absolute `https://` URL with no trailing slash | Site root. Also determines the host used for crawl-delay throttling. |
| `feeds` | `array<string>` of absolute feed URLs; an empty array means no feed | RSS/Atom feed URLs. Merged and de-duplicated by link within a run. Empty means no feed (NTA). |
| `robots_status` | `string`, free text | Free-text summary of the robots.txt finding. Not machine-read. |
| `crawl_delay` | `integer`, seconds, 0 or more (configured values: 5 or 10) | Minimum gap between article-page requests to the host. **Not applied to feed requests.** |
| `category_paths` | `array<string>`, each starting with `/`; may be empty | Section paths reserved for an HTML fallback. Unused today. |
| `enabled` | `boolean` | If false, `run.py` refuses to run the outlet. |

---

## Part B: Database tables (proposed)

Target: PostgreSQL (Supabase). These are the entities named in the README's *Core Data Model*, plus `collection_runs`, reference tables, `user_roles` and `corrections`. Column types use Postgres names. `uuid` primary keys use `gen_random_uuid()`. All timestamps are `timestamptz` (UTC). Every table has `created_at timestamptz not null default now()` unless stated.

Pipeline position: `sources` → `collection_runs` → `raw_reports` → `candidate_incidents` → (review) → `incidents` + `incident_sources` + `locations` → `reviews` / `edits`.

### B1. `sources`: approved outlets and statements

Seeded from `config.py`. The README rule "no outlet is scraped before its robots.txt and terms are checked and recorded" is enforced by a constraint.

| Column | Type | Null? | Meaning |
|---|---|---|---|
| `source_key` | text, **PK** | no | Same value as `OutletConfig.key`. |
| `name` | text | no | Display name, used for attribution. |
| `source_type` | enum `source_type` | no | `news_outlet` or `official_statement`. |
| `base_url` | text | no | Site root. |
| `feeds` | text[] | no, default `{}` | Feed URLs. |
| `crawl_delay_seconds` | int | no | From robots.txt `Crawl-delay`, or the team default. |
| `robots_checked_at` | timestamptz | yes | When robots.txt was last read and recorded. |
| `robots_summary` | text | yes | What it says about bots in general and named bots. |
| `tos_url` | text | yes | The terms-of-use page that was read. |
| `tos_checked_at` | timestamptz | yes | When the terms were read. |
| `tos_result` | enum `tos_result` | no, default `unchecked` | `unchecked`, `no_explicit_ban`, `explicit_ban`. |
| `enabled` | boolean | no, default false | Whether the scheduler may collect from it. |
| `reliability_rating` | smallint | yes | Post-MVP (README: automated reliability scoring is out of scope). Leave null. |
| `notes` | text | yes | Free text, such as the compliance decision for Nigerian Tribune. |

Constraint: `CHECK (NOT enabled OR (tos_result = 'no_explicit_ban' AND tos_checked_at IS NOT NULL AND robots_checked_at IS NOT NULL))`.

### B2. `collection_runs`: one row per outlet per run

| Column | Type | Null? | Meaning |
|---|---|---|---|
| `run_id` | uuid, **PK** | no | |
| `source_key` | text, FK → `sources` | no | |
| `batch_label` | text | no | Free-form label (`0700`, `am`, ...). Replaces the filename suffix. |
| `trigger` | enum `run_trigger` | no | `schedule` or `manual`. |
| `started_at` | timestamptz | no | |
| `finished_at` | timestamptz | yes | Null while running or if the process died. |
| `status` | enum `run_status` | no | `running`, `success`, `partial`, `failed`. |
| `feed_items` | int | no, default 0 | Items fetched from feeds after merge. |
| `skipped_seen` | int | no, default 0 | Skipped because `article_id` already existed. |
| `candidates` | int | no, default 0 | |
| `low_confidence` | int | no, default 0 | |
| `fetch_errors` | int | no, default 0 | |
| `error_message` | text | yes | First fatal error, if any. |

A run with `feed_items = 0` is suspicious and should alert (blocked feed, changed URL).

### B3. `raw_reports`: original collected content

One row per article ever processed. Replaces both `datasets/**` JSON files and `_seen_urls.csv`.

| Column | Type | Null? | Meaning |
|---|---|---|---|
| `article_id` | text, **PK** | no | A1 `article_id`. Uniqueness here is the dedup. |
| `source_key` | text, FK → `sources` | no | |
| `run_id` | uuid, FK → `collection_runs` | no | Run that first saw it. |
| `source_url` | text, **unique** | no | |
| `title` | text | no | |
| `published_at` | timestamptz | yes | Parsed from the outlet's string. |
| `published_at_raw` | text | yes | The unparsed original, kept for audit. |
| `fetched_at` | timestamptz | no | |
| `raw_text` | text | yes | Internal only. Nullable so it can be purged on a retention schedule. **OPEN-8.** |
| `raw_text_purged_at` | timestamptz | yes | Set when `raw_text` is deleted. |
| `collection_mode` | enum `collection_mode` | no | `rss` or `html_fallback`. |
| `disposition` | enum `disposition` | no | `candidate`, `low_confidence`, `suppressed`, `failed`. |
| `disposition_reason` | text | yes | The A2 reason string. Null for candidates. |
| `is_candidate` | boolean | no | A1.1 `relevance.is_candidate`. |
| `matched_keywords` | text[] | no, default `{}` | |
| `corroborating` | text[] | no, default `{}` | |
| `schema_version` | text | no | Collector schema that produced it. |

Access: **never exposed publicly.** Row-level security allows reviewers and admins only.

### B4. `candidate_incidents`: extracted, awaiting review

One row per candidate `raw_reports` row, created by the extractor. Clustering of the same event across outlets happens at review time by attaching candidates to one incident.

| Column | Type | Null? | Meaning |
|---|---|---|---|
| `candidate_id` | uuid, **PK** | no | |
| `article_id` | text, FK → `raw_reports`, **unique** | no | |
| `extractor_version` | text | no | Which extractor produced the row, so output is reproducible. |
| `event_type_raw` | text | yes | A1.2 `event_type` (scraper key). |
| `event_types_all` | text[] | no, default `{}` | |
| `suggested_category_id` | int, FK → `categories` | yes | Mapped from the scraper key. **OPEN-1.** |
| `event_date` | date | yes | Extracted incident date; null until a real extractor sets it. |
| `event_date_source` | enum `date_source` | no, default `published` | `published`, `extracted`, `reviewer`. |
| `location_text` | text | yes | A1.2 `location`. |
| `locations_all` | text[] | no, default `{}` | De-duplicated. |
| `suggested_state_code` | text, FK → `ref_states` | yes | |
| `suggested_lga_id` | int, FK → `ref_lgas` | yes | |
| `actors_raw` | text[] | no, default `{}` | A1.2 `actors`. Private. Not shown publicly. |
| `impact_text` | text | yes | A1.2 `impact`. |
| `casualty_count_hint` | int | yes | Number parsed from `impact_text` **only when stated as a digit or number word**; never derived from "dozens"/"scores". |
| `extraction_confidence` | enum `confidence_level` | no, default `low` | |
| `status` | enum `candidate_status` | no, default `new` | `new`, `in_review`, `approved`, `rejected`, `merged`. |
| `incident_id` | uuid, FK → `incidents` | yes | Set when approved or merged into an incident. |

### B5. `categories`: reference list of incident categories

Public-facing category vocabulary. **OPEN-1.** Seed values are the 11 scraper keys (provisional) until the team agrees a final list.

| Column | Type | Null? | Meaning |
|---|---|---|---|
| `category_id` | int, **PK** | no | |
| `code` | text, unique | no | snake_case key. |
| `label` | text | no | Public wording. |
| `description` | text | yes | Inclusion rules, so reviewers classify consistently. |
| `active` | boolean | no, default true | |

### B6. Reference geography

Needed for extraction, the reviewer's location picker, and zone filtering. None of this exists in the repo yet.

**`ref_states`**

| Column | Type | Meaning |
|---|---|---|
| `state_code` | text, **PK** | Short code (for example `KD`). FCT included. |
| `name` | text | |
| `geopolitical_zone` | enum `zone` | One of the six zones in C5. |
| `centroid_lat`, `centroid_lng` | numeric(9,6) | |

**`ref_lgas`**: `lga_id` int PK, `state_code` FK, `name`, `centroid_lat`, `centroid_lng`.

**`ref_places`**: `place_id` int PK, `lga_id` FK, `name`, `place_kind` (`town`, `landmark`, `road`), `lat`, `lng`, `aliases text[]`.

### B7. `locations`: one resolved, confirmed location

Created or confirmed by a reviewer (the "Geocode" stage). Referenced by `incidents`.

| Column | Type | Null? | Meaning |
|---|---|---|---|
| `location_id` | uuid, **PK** | no | |
| `state_code` | text, FK → `ref_states` | no | |
| `lga_id` | int, FK → `ref_lgas` | yes | |
| `place_id` | int, FK → `ref_places` | yes | |
| `place_text` | text | yes | Free text where the gazetteer has no match. |
| `latitude`, `longitude` | numeric(9,6) | yes | Internal best coordinates. **Never published when `is_generalised`.** |
| `precision` | enum `location_precision` | no | `exact`, `landmark`, `town`, `lga`, `state` (Std 3). The finest level the evidence supports. |
| `is_generalised` | boolean | no, default false | True when a sensitive location is shown less precisely than known (Std 5). |
| `public_latitude`, `public_longitude` | numeric(9,6) | yes | What the public map may show. Equal to the internal coordinates only when not generalised; otherwise the centroid of the generalised area. |
| `public_precision` | enum `location_precision` | no | Precision of the public coordinates. Differs from `precision` when generalised. |
| `confirmed_by` | text | no | Reviewer `user_id`. |

### B8. `incidents`: verified or reviewed incidents

Only rows with `visibility = 'public'` and `verification_status = 'verified'` appear on the public map.

| Column | Type | Null? | Meaning |
|---|---|---|---|
| `incident_id` | uuid, **PK** | no | |
| `public_ref` | text, unique | no | Human-readable reference for incident pages. Format **OPEN-10**. |
| `title` | text | no | Neutral wording (Std 7). |
| `summary` | text | no | Written in the reviewer's own words. **Never copied from the outlet.** |
| `category_id` | int, FK → `categories` | no | |
| `event_date` | date | no | Date of the incident, not of the article. |
| `severity` | enum `severity_level` | yes | **OPEN-2.** Null until defined. |
| `location_id` | uuid, FK → `locations` | no | |
| `casualty_status` | enum `casualty_status` | no, default `unknown` | `reported`, `confirmed`, `unknown` (Std 4). Required on every incident. |
| `casualty_summary` | text | yes | Public wording, for example "At least 12 reported killed". Must match `casualty_status`. |
| `killed`, `injured`, `abducted_or_missing` | int | yes | Optional breakdown. Leave null unless a source states the number. **OPEN-6.** |
| `public_actor_label` | text | yes | Filled only where the source clearly reports the actor (Std 7). Otherwise null. |
| `verification_status` | enum `verification_status` | no, default `pending` | `pending`, `verified`, `rejected`. Whether "verified" needs two independent sources is **OPEN-3**. |
| `visibility` | enum `visibility` | no, default `draft` | `draft`, `public`, `restricted` (temporarily withheld, Std 5), `withdrawn` (taken down after a correction). |
| `confidence` | enum `confidence_level` | no, default `low` | `low`, `medium`, `high`. Rule **OPEN-4**. |
| `version` | int | no, default 1 | Incremented on each edit. |
| `published_at` | timestamptz | yes | |
| `published_by` | text | yes | Editor `user_id`. |
| `updated_at` | timestamptz | no | |

Derived (view, not stored): `source_count` = count of `incident_sources`; `second_source` = `source_count >= 2` from distinct outlets.

### B9. `incident_sources`: incidents ↔ collected articles

| Column | Type | Null? | Meaning |
|---|---|---|---|
| `incident_id` | uuid, FK → `incidents` | no | |
| `article_id` | text, FK → `raw_reports` | no | |
| `role` | enum `source_role` | no | `primary` or `corroborating`. |
| `added_by` | text | no | Reviewer `user_id`. |
| `added_at` | timestamptz | no | |

Primary key `(incident_id, article_id)`. Every published incident needs at least one row (Std 1). Public output shows the outlet name, the article title and a link, never `raw_text`.

### B10. `reviews`: human decisions

| Column | Type | Null? | Meaning |
|---|---|---|---|
| `review_id` | uuid, **PK** | no | |
| `subject_type` | enum `review_subject` | no | `candidate` or `incident`. |
| `subject_id` | uuid | no | `candidate_id` or `incident_id`. |
| `reviewer_id` | text | no | `user_id` from `user_roles`. |
| `decision` | enum `review_decision` | no | `approve`, `reject`, `merge`, `request_second_source`, `restrict`, `unpublish`, `publish`. |
| `reason` | text | **required** for `reject`, `merge`, `restrict`, `unpublish` | |
| `notes` | text | yes | |

### B11. `edits`: change history (Std 6)

Every change to an incident after creation writes one row per changed field.

| Column | Type | Null? | Meaning |
|---|---|---|---|
| `edit_id` | uuid, **PK** | no | |
| `incident_id` | uuid, FK → `incidents` | no | |
| `field_name` | text | no | Column that changed. |
| `old_value`, `new_value` | jsonb | yes | |
| `editor_id` | text | no | |
| `reason` | text | **no, required** | Std 6 requires reviewer, timestamp **and reason**. |

Implement with a database trigger or a single write function so edits cannot bypass the log.

### B12. `user_roles`: staff accounts

Authentication is handled by the identity provider (Firebase or Supabase Auth; undecided). This table holds authorisation only.

| Column | Type | Null? | Meaning |
|---|---|---|---|
| `user_id` | text, **PK** | no | The provider's user id. |
| `role` | enum `staff_role` | no | `reviewer`, `editor`, `admin`. |
| `display_name` | text | no | |
| `active` | boolean | no, default true | |

Per D-018, accounts at launch are **staff only**. There are no public accounts.

### B13. `corrections`: public correction flag

The MVP includes a correction flag. By design it collects **no personal data**.

| Column | Type | Null? | Meaning |
|---|---|---|---|
| `correction_id` | uuid, **PK** | no | |
| `incident_id` | uuid, FK → `incidents` | no | |
| `message` | text | no | What the sender believes is wrong. Length-limited. |
| `status` | enum `correction_status` | no, default `open` | `open`, `accepted`, `dismissed`. |
| `handled_by` | text | yes | |
| `handled_at` | timestamptz | yes | |

No name, email or IP address is stored. Rate-limit at the edge instead.

---

## Part C: Enumerations

### C1. Source keys

| Key | Outlet | State |
|---|---|---|
| `premium_times` | Premium Times | Enabled. 4 feeds. |
| `prnigeria` | PRNigeria | Enabled. 1 feed. |
| `humangle` | HumAngle | Enabled. 1 feed. |
| `nta` | NTA | Configured, no feed (HTML fallback not built). |
| `nigerian_tribune` | Nigerian Tribune | **Disabled.** robots.txt bans named bots. |

The other eleven approved outlets (Vanguard, Punch, NAN, Channels TV, Daily Sun, Guardian, ThisDay, Daily Trust, TVC News, AIT, ICIR) have no config entry or recorded ToS check yet.

### C2. Scraper event-type keys (provisional)

The 11 values `EVENT_KEYWORDS` can produce. Not a ratified vocabulary (**OPEN-1**).

`kidnapping`, `banditry`, `terrorism`, `armed_attack`, `violence_fatal`, `communal_clash`, `robbery`, `cult_violence`, `explosion`, `militancy`, `arson`.

Overlaps to resolve: `terrorism` vs `militancy`; `armed_attack` vs `violence_fatal`. Not producible today: civil unrest, piracy, protest-related events.

### C3. Database enumerations

| Enum | Values | Source |
|---|---|---|
| `location_precision` | `exact`, `landmark`, `town`, `lga`, `state` | Std 3 (README) |
| `casualty_status` | `reported`, `confirmed`, `unknown` | Std 4 (README) |
| `verification_status` | `pending`, `verified`, `rejected` | Proposed; rule **OPEN-3** |
| `visibility` | `draft`, `public`, `restricted`, `withdrawn` | Proposed (`restricted` per Std 5) |
| `candidate_status` | `new`, `in_review`, `approved`, `rejected`, `merged` | Proposed |
| `confidence_level` | `low`, `medium`, `high` | Matches v0 `extraction_confidence`; rule **OPEN-4** |
| `severity_level` | not defined | **OPEN-2** |
| `disposition` | `candidate`, `low_confidence`, `suppressed`, `failed` | Derived from A2 reasons |
| `collection_mode` | `rss`, `html_fallback` | A1 |
| `source_type` | `news_outlet`, `official_statement` | MVP scope |
| `tos_result` | `unchecked`, `no_explicit_ban`, `explicit_ban` | Ban-check document |
| `run_status` | `running`, `success`, `partial`, `failed` | Proposed |
| `run_trigger` | `schedule`, `manual` | Proposed |
| `date_source` | `published`, `extracted`, `reviewer` | Proposed |
| `source_role` | `primary`, `corroborating` | Proposed |
| `review_subject` | `candidate`, `incident` | Proposed |
| `review_decision` | `approve`, `reject`, `merge`, `request_second_source`, `restrict`, `unpublish`, `publish` | Proposed |
| `staff_role` | `reviewer`, `editor`, `admin` | README review workflow |
| `correction_status` | `open`, `accepted`, `dismissed` | Proposed |

### C4. Candidate disposition mapping (A2 reason → `disposition`)

| A2 reason prefix | `disposition` |
|---|---|
| (candidate written) | `candidate` |
| `no keyword match…`, `no Nigerian location detected…` | `low_confidence` |
| `suppressed…` | `suppressed` |
| `fetch_error…`, `empty_body…` | `failed` |

### C5. Geopolitical zones

`North Central`, `North East`, `North West`, `South East`, `South South`, `South West`. The README requires coverage of all six. FCT sits in North Central.

---

## Part D: Open decisions

Nothing in this part is decided. Each item says who it blocks and a recommended default. Record the outcome in the Decision Log.

| ID | Decision | Blocks | Recommended default |
|---|---|---|---|
| **OPEN-1** | Final **category vocabulary**, and the map from the 11 scraper keys. | `categories`, filters, extraction | Merge `terrorism`/`militancy`; split `armed_attack` from `violence_fatal` (a fatal outcome is an attribute, not a category); add `civil_unrest`, `piracy`. Ratify before seeding. |
| **OPEN-2** | **Severity** definition. | `incidents.severity`, public filters | Base on a stated rule (for example outcome and scale of harm) so two reviewers rate the same way. Leave null until defined. |
| **OPEN-3** | Does `verified` require **two independent sources** for news-only incidents? The README applies the second-source rule to social claims only. | `verification_status`, `confidence` | One reputable outlet is enough to *publish* as `verified` with `medium` confidence; two or more outlets raise it to `high`. Decide explicitly. |
| **OPEN-4** | **Confidence** rule. | `incidents.confidence` | Derive from source count, source type (official statement vs. single outlet) and which fields a reviewer confirmed. Keep it a 3-level enum, not a percentage. |
| **OPEN-5** | Definition of a **sensitive incident** and the generalisation rule (Std 5). | `locations.is_generalised`, publication | Written list of incident types and locations (for example schools, places of worship, ongoing hostage situations) that always publish at LGA level. |
| **OPEN-6** | Structure of casualty data: status only, or numeric breakdown too. | `incidents.killed/injured/…` | Always store `casualty_status`; store numbers only when a source states them; never compute from vague words. |
| **OPEN-7** | Event-date semantics when the article gives only a relative date ("on Sunday"). | `event_date` | Resolve against `published_at`; flag `event_date_source` as `extracted`; reviewer confirms. |
| **OPEN-8** | **Retention** of `raw_text`. | `raw_reports.raw_text` | Keep for candidates under review; purge for rejected and low-confidence items after a fixed period; never publish. Must be reflected in the DPIA. |
| **OPEN-9** | Geocoding source for `ref_places`. | `locations`, location picker | Build state and LGA reference first (finite, sourceable); add towns and landmarks as reviewers resolve them. |
| **OPEN-10** | `public_ref` format for incident pages. | `incidents.public_ref` | Opaque short id; avoid sequential numbers that reveal volume. |

---

## Part E: Mapping the collector output into the tables

| v0 field | Destination | Transformation |
|---|---|---|
| `article_id` | `raw_reports.article_id` | None. Insert-or-ignore; uniqueness is the dedup. |
| `source` | `raw_reports.source_key` | None. |
| `source_url` | `raw_reports.source_url` | Canonicalise before hashing in a future schema version. |
| `fetched_at` | `raw_reports.fetched_at` | Parse ISO-8601. |
| `published_at` | `raw_reports.published_at` and `published_at_raw` | Parse the RFC-822 string; keep the original. |
| `title`, `raw_text`, `collection_mode`, `schema_version` | same-named columns | None. |
| `relevance.is_candidate`, `matched_keywords`, `corroborating` | `raw_reports.*` | None. |
| `extraction.event_type`, `event_types_all` | `candidate_incidents.event_type_raw`, `event_types_all` | Map to `suggested_category_id` once OPEN-1 is decided. |
| `extraction.date` | `candidate_incidents.event_date` | **Do not copy.** Leave null; `event_date_source = 'published'` records that only the publish date is known. |
| `extraction.location`, `locations_all` | `candidate_incidents.location_text`, `locations_all` | De-duplicate; resolve to `ref_states` for `suggested_state_code`. |
| `extraction.actors` | `candidate_incidents.actors_raw` | Private. Not shown publicly. |
| `extraction.impact` | `candidate_incidents.impact_text` | `casualty_count_hint` only from a stated digit or number word. |
| `extraction_confidence` | `candidate_incidents.extraction_confidence` | None. |
| `review_status` | `candidate_incidents.status` | `pending` → `new`. |
| low-confidence `title`, `url`, `published`, `reason` | `raw_reports` rows with `disposition` ≠ `candidate` | `url` → `source_url`; `published` → `published_at`; reason → `disposition` via C4. |
| run summary (`feed_items`, `skipped_seen`, `candidates_written`, `low_confidence`) | `collection_runs.*` | `candidates_written` → `candidates`. |

---

## Part F: Verification Standards coverage

Which standard each part of the model supports.

| Std | Requirement | Where it is enforced |
|---|---|---|
| 1 | Source traceability | `incident_sources` (at least one row to publish); outlet name and link shown publicly |
| 2 | Second-source rule (social claims) | `second_source` view; policy **OPEN-3**; social ingestion is post-MVP |
| 3 | Location precision stated | `locations.precision` is `NOT NULL`; `public_precision` for what is shown |
| 4 | Casualty status marked | `incidents.casualty_status` is `NOT NULL`; numbers optional and never derived from vague words |
| 5 | Sensitive locations generalised | `locations.is_generalised`, `public_*` columns, `visibility = 'restricted'`; definition **OPEN-5** |
| 6 | Edit history | `edits` with a required `reason`; written by trigger or a single write function |
| 7 | Neutral wording | `public_actor_label` null unless the source clearly reports the actor; private `actors_raw` |

---

## Change log

| Date | Version | Change |
|---|---|---|
| 2026-10-09 | v1 draft | First version. Part A checked against the code on `main` at `f22a953`. Part B and the open decisions are proposals. |
| 2026-10-09 | v1.1 | Part A: the `Type` column is now `Type and expected shape` (JSON type plus the form a valid value takes). Shapes were checked against real output from `relevance`, `extract`, `build_record` and `SeenStore`. Part B is unchanged. `impact` now notes that only the first matching phrase is kept. |
