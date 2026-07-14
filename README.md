# DataWiz: Nigeria Security Incident Intelligence Platform

> **"Google Maps for security incidents."** A Nigeria-wide platform that collects publicly reported security incidents, verifies them through a human-in-the-loop workflow, and publishes them on a searchable public map.

**Status:** Pre-MVP · Sprint 1 (Foundation) · 13 Jul to 26 Jul 2026
**Target MVP launch review:** 6 September 2026

---

## Table of Contents

- [Overview](#overview)
- [Why It Matters](#why-it-matters)
- [How It Works](#how-it-works)
- [MVP Scope](#mvp-scope)
- [Architecture](#architecture)
- [Core Data Model](#core-data-model)
- [Data Sources](#data-sources)
- [Verification Standards](#verification-standards)
- [Legal, Ethical & Compliance Commitments](#legal-ethical--compliance-commitments)
- [Roadmap](#roadmap)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
- [Contributing (Team Workflow)](#contributing-team-workflow)
- [Team](#team)
- [Project Management](#project-management)
- [Disclaimer](#disclaimer)

---

## Overview

DataWiz makes verified security incidents across Nigeria easier to find, understand, and use for decision-making. The platform:

1. **Collects** publicly available reports from approved Nigerian news outlets (RSS/websites) and official public statements.
2. **Extracts** key details (event type, date, location, actors, impact) using NLP.
3. **Verifies** every incident through human review before publication, with a mandatory second independent source for any social-media or Telegram-based claim.
4. **Geocodes** confirmed incidents with explicit location-precision levels (exact → landmark → town → LGA → state).
5. **Publishes** verified incidents on a public, searchable map of Nigeria with filters for location, date, category, and severity.

The first version prioritises **trust, accuracy, and usability** over prediction. Once a clean historical dataset exists, the same data can power alerts, risk reports, APIs, enterprise dashboards, and machine-learning models (hotspot detection, forecasting).

## Why It Matters

No existing platform combines **free public access** with **continuously updated, automated collection** and a **rigorous human verification layer**. Verification rigour and data quality are our core differentiators: automation moves fast, humans keep it honest. The system is deliberately designed so it cannot drift into becoming a misinformation platform.

## How It Works

Every report passes through the same pipeline:

```
 Collect → Classify → Extract → Deduplicate → Verify → Geocode → Publish
 (system)  (system)   (NLP)     (system +     (human    (human    (editor/
                                 reviewer)     review)   review)   reviewer lead)
```

| Stage | What happens | Owner |
|---|---|---|
| **Collect** | Raw article/statement saved with full metadata and original link | System |
| **Classify** | Is this security-related and worth processing? | System |
| **Extract** | NLP pulls candidate event type, date, location, actors, impact, summary | System |
| **Deduplicate** | Same incident already reported elsewhere? Attach source, don't duplicate | System + reviewer |
| **Verify** | Reviewer checks the original source, confirms facts, category, location | Human reviewer |
| **Geocode** | Coordinates confirmed; location precision explicitly set | Human reviewer |
| **Publish** | Only verified, appropriately generalised incidents go public | Editor / reviewer lead |

## MVP Scope

**MVP statement:** A user can search any Nigerian location and see verified security incidents around it with date, category, source references, location precision, and confidence. Target: **500 to 1,000 verified incidents across all six geopolitical zones**, on a map that works on mobile and desktop.

|  In scope (MVP) | Out of scope (post-MVP) |
|---|---|
| News RSS/site collection from approved outlets; official public statements | Telegram/social ingestion at scale; drone, image, geospatial feeds |
| NLP extraction of event type, date, location, actors, impact | Automated source-reliability scoring; reviewer reputation models |
| Human verification before publication; second-source rule for social claims | Fully automated publication |
| PostgreSQL incident database | Kafka/Spark streaming pipeline (design only, build later) |
| Public searchable map with filters; incident pages; correction flag | Personal alert subscriptions, trend pages, risk scores, paid APIs |
| Admin/reviewer queue (approve, reject, merge, geocode, publish) | ML forecasting and hotspot prediction models |

## Architecture

The architecture keeps **collection, extraction, verification, storage, and public access as separate concerns**, so each layer can improve without disrupting the public product.

> **Status (Jul 2026):** Final architecture/ETL direction is being ratified. Interim positions in force:
> - **PostgreSQL**: target structured store (incidents, sources, reviews, locations)
> - **Google Drive**: interim storage for sample datasets during Sprints 1 and 2, then migration to Postgres
> - **Cloudinary / S3-type storage**: under evaluation for media (pending pricing review)
> - **GitHub (this repo)**: all code, branch-based workflow

Publishing cadence for MVP is **daily batch review** (not real-time) to keep the human verification layer sustainable.

## Core Data Model

One incident can have **many sources**, **many review actions**, and **one confirmed location**.

| Entity | Purpose |
|---|---|
| `sources` | Approved sources and metadata (name, type, URL, reliability rating, active status) |
| `raw_reports` | Original collected content before extraction |
| `candidate_incidents` | NLP-extracted incidents awaiting human review |
| `incidents` | Verified/reviewed incident records (type, summary, date, severity, verification status, visibility) |
| `incident_sources` | Many-to-many link between incidents and reports |
| `locations` | Resolved Nigerian locations (state, LGA, town, landmark, lat/lng, precision) |
| `reviews` | Human verification decisions with notes and reasons |
| `edits` | Full change history for accountability |

The full Data Dictionary/Schema is maintained in the project's internal documentation and will be reflected in `db/` migrations as Sprint 1 progresses.

## Data Sources

Initial collection targets nine approved outlets, selected by media ranking, each with a single accountable owner. **No outlet is scraped before its robots.txt and terms of use are checked and recorded.**

| Owner | Outlets |
|---|---|
| Ojo Ilesanmi | Vanguard · The Punch · Business Day |
| Aduragbemi Kinoshi | The Guardian · This Day · Daily Trust |
| Favour Success | Premium Times · Nigerian Tribune · Nairametrics *(provisional, replacement under review)* |

Official public statements (police, government, emergency agencies) are treated as high-priority sources but still pass through review. Curated Telegram channels and social media come **after** the verification workflow is proven, because they are faster but noisier.

## Verification Standards

These rules are non-negotiable and are the platform's core differentiator:

1. **Source traceability**: every published incident links back to at least one traceable source.
2. **Second-source rule**: Telegram/social claims require at least one independent confirming source before confirmation.
3. **Location precision**: every incident states whether its location is exact, landmark-, town-, LGA-, or state-level. The map never pretends to be more accurate than the data.
4. **Casualty figures**: always marked *reported*, *confirmed*, or *unknown*. Early figures are never overstated.
5. **Sensitive incidents**: sensitive locations are generalised (to town/LGA level) or temporarily restricted from public display. Inform the public without increasing risk.
6. **Edit history**: every change to an incident is logged with reviewer, timestamp, and reason.
7. **Neutral wording**: actors are only named where the source clearly reports them.

## Legal, Ethical & Compliance Commitments

- **NDPR/NDPC compliance:** The project is registering with Nigeria's Data Protection Commission ([services.ndpc.gov.ng](https://services.ndpc.gov.ng)). Obligations tracked: published privacy policy, data minimization, technical & organizational safeguards, Data Protection Officer certification, and a Data Protection Impact Assessment (DPIA).
- **Secondary data only at launch:** The MVP collects only secondary (publicly published) data. User accounts and subscriptions are deferred until NDPC registration obligations are fully addressed.
- **Data minimization:** We collect only fields necessary for incident intelligence.
- **Respectful collection:** robots.txt, terms of use, and attribution requirements are checked per outlet **before** any scraping, and original source links are always preserved.
- **Harm avoidance:** We do not publish rumours, exact sensitive locations, or unsupported claims.

## Roadmap

| Phase | Focus | Timeline | Status |
|---|---|---|---|
| **Phase 1: Foundation** | Incident schema, source registry, raw report store, reviewer roles | Sprint 1 · 13 to 26 Jul | In progress |
| **Phase 2: Collection & extraction** | Scheduled collectors, relevance classifier, NLP extraction, candidate queue, dedup v1 | Sprint 2 · 27 Jul to 9 Aug | Planned |
| **Phase 3: Verification & mapping** | Reviewer workflow, second-source enforcement, geocoding, Drive to Postgres migration | Sprint 3 · 10 to 23 Aug | Planned |
| **Phase 4: Public MVP** | Public map, filters, incident pages, correction flow, 500+ verified incidents | Sprint 4 · 24 Aug to 6 Sep | Planned |
| **Phase 5: Commercial layer** | APIs, alerts, reports, partner dashboards | Post-MVP | Designed |
| **Phase 6: Intelligence layer** | Risk scoring, hotspot detection, trend analysis, forecasting | Post-MVP | Designed |

## Repository Structure

> Proposed layout, populated as Sprint 1 progresses.

```
DataWiz-Project/
├── README.md
├── docs/                      # Architecture notes, data dictionary, ADRs
├── scrapers/                  # One module per outlet
│   ├── vanguard/
│   ├── punch/
│   ├── businessday/
│   ├── guardian/
│   ├── thisday/
│   ├── dailytrust/
│   ├── premiumtimes/
│   ├── tribune/
│   └── nairametrics/
├── pipeline/                  # Classification, NLP extraction, deduplication
├── db/                        # PostgreSQL schema, migrations, seed data
├── review/                    # Admin/reviewer queue application
├── web/                       # Public map front-end
├── scripts/                   # One-off utilities
├── .env.example               # Environment variable template (never commit real .env)
└── requirements.txt           # Python dependencies
```

## Getting Started

> Full setup instructions will land with the first scraper merges. Interim quick start:

```bash
# 1. Clone the repository
git clone https://github.com/isichei-nnamdi/DataWiz-Project.git
cd DataWiz-Project

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env             # then fill in local values
```

**Requirements:** Python 3.10+, PostgreSQL 14+ (for schema work from Sprint 3), Git.

**Never commit** credentials, `.env` files, or scraped datasets to this repo. Sample datasets live in the team's shared Drive during Sprints 1 and 2.

## Contributing (Team Workflow)

This is a closed team project during the MVP phase. Team workflow:

1. **Branch-based development**: no direct commits to `main`.
   - Branch naming: `feature/<short-description>`, `fix/<short-description>`, e.g. `feature/vanguard-scraper`.
2. **Pull requests** for every merge into `main`; at least one review from another team member.
3. **One owner per outlet/workstream**: see [Team](#team). Owners keep their Trello card linked to their PR.
4. **Check before you scrape**: robots.txt/ToS verification results must be recorded in the Data Source Inventory before a scraper runs against a live site.
5. **Commit messages**: short imperative summary, e.g. `Add Punch RSS collector with retry logic`.
6. **Definition of done**: code merged, demoed at the Sunday sprint review, documentation updated, Trello card moved to Done with links attached.

External contributions, issues, and suggestions are welcome after the public MVP launch.

## Team

| Member | Role | Owns |
|---|---|---|
| [**Nnamdi Isichei**](https://www.linkedin.com/in/nnamdi-isichei/) | Project Lead / Compliance & Partnerships | Direction, NDPC/NDPR compliance, external relationships, repo administration, verification standards sign-off |
| [**Solomon Ayuba**](https://www.linkedin.com/in/solomonayuba/) | Product Manager | Backlog & Trello, documentation, minutes & Decision Log, sprint coordination, launch checklist |
| [**Ojo Ilesanmi**](https://www.linkedin.com/in/ojo-ilesanmi-a64a7a159/) | Data Engineering Lead | Storage architecture, ingestion/ETL design, schema & Data Dictionary, media storage evaluation |
| [**Aduragbemi Kinoshi**](https://www.linkedin.com/in/aduragbemi-kinoshi-760717395/) | Collection Engineer | Outlet scrapers, robots.txt/ToS audits, collector scheduling |
| **Favour Success** | Collection / NLP Engineer | Outlet scrapers, security-relevance classifier, NLP extraction pipeline |

## Project Management

- **Cadence:** Weekly sprint reviews (Sundays, 21:30 WAT) · async check-ins Wednesdays & Fridays
- **Task board:** Trello (Kanban), with cards mirroring sprint deliverables
- **Documentation:** Centralised in the team's shared Drive (meeting minutes, Decision Log, Data Source Inventory, Data Dictionary, Implementation Blueprint), access restricted to the team during the MVP phase
- **Decisions:** Recorded in an append-only Decision Log; reversals supersede rather than overwrite

## Disclaimer

DataWiz aggregates and verifies **publicly reported** information. It is an informational tool and not a substitute for official security advisories or emergency services. Incident data reflects what has been publicly reported and verified against our standards; absence of incidents on the map does not imply absence of risk. In an emergency, contact Nigeria's emergency services (**112**).

---

*DataWiz (working name) · Built by a volunteer team · 2026*
