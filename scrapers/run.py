"""Orchestrator — run one outlet end to end.

Flow: feed -> dedup -> relevance (on title+summary) -> full-text fetch (candidates
only) -> re-check relevance on full text -> extract -> write record. Zero-match
articles are routed to a low-confidence bucket, not discarded.

Run from the repo root:
    python -m scrapers.run premium_times --batch 0700
"""

import argparse
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

from scrapers.config import OUTLETS
from scrapers.collector import fetch_feeds, fetch_article_text
from pipeline import relevance, extract as extractor
from pipeline.dedup import SeenStore
from pipeline.schema import build_record, article_id

DATASETS_ROOT = os.path.join(os.path.dirname(__file__), "..", "datasets")


def run_outlet(outlet_key: str, batch: str, limit: int) -> dict:
    cfg = OUTLETS[outlet_key]
    if not cfg.enabled:
        raise SystemExit(f"{cfg.name} is disabled (see config: {cfg.robots_status}).")
    if not cfg.feeds:
        raise SystemExit(f"{cfg.name} has no confirmed feeds; HTML fallback not built yet.")

    host = urlparse(cfg.base_url).netloc
    out_dir = os.path.abspath(os.path.join(DATASETS_ROOT, cfg.key))
    low_conf_dir = os.path.abspath(os.path.join(DATASETS_ROOT, "_low_confidence"))
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(low_conf_dir, exist_ok=True)
    seen = SeenStore(os.path.abspath(os.path.join(DATASETS_ROOT, "_seen_urls.csv")))

    items = fetch_feeds(cfg.feeds)[:limit]
    candidates, low_conf, skipped_seen = [], [], 0

    for it in items:
        url = it["link"]
        if not url:
            continue
        aid = article_id(url)
        if seen.is_seen(aid):
            skipped_seen += 1
            continue

        # Cheap first pass on title + feed summary.
        prelim = relevance.score(f"{it['title']} {it['summary']}")
        if not prelim["is_candidate"]:
            reason = ("suppressed (drug/regulatory context, no strong incident term): "
                      + ",".join(prelim["suppressors"])) if prelim["suppressed"] \
                     else "no keyword match in title+summary"
            low_conf.append({"title": it["title"], "url": url, "published": it["published"],
                             "reason": reason})
            seen.add(aid, url)
            continue

        # Candidate -> fetch full text and re-score.
        try:
            body = fetch_article_text(url, host, cfg.crawl_delay)
        except Exception as e:  # noqa: BLE001 - log and move on
            low_conf.append({"title": it["title"], "url": url, "published": it["published"],
                             "reason": f"fetch_error: {e}"})
            seen.add(aid, url)
            continue

        # Guard: empty body means content extraction failed — don't silently
        # emit a textless "candidate". Route it for manual review instead.
        if not body:
            low_conf.append({"title": it["title"], "url": url, "published": it["published"],
                             "reason": "empty_body: content selector matched nothing"})
            seen.add(aid, url)
            continue

        # Re-score on full text; the full-text verdict is authoritative.
        rel = relevance.score(f"{it['title']} {body}")
        if not rel["is_candidate"]:
            reason = ("suppressed on full text (drug/regulatory context): "
                      + ",".join(rel["suppressors"])) if rel["suppressed"] \
                     else "no keyword match on full text (feed excerpt matched)"
            low_conf.append({"title": it["title"], "url": url, "published": it["published"],
                             "reason": reason})
            seen.add(aid, url)
            continue

        ext = extractor.extract(it["title"], body, it["published"])

        # Geography gate: this is a Nigeria security map. An article with no
        # detectable Nigerian location is almost always out of scope (sports,
        # international news). Downgrade to low-confidence, don't discard — a
        # reviewer can still rescue a genuine incident the gazetteer missed.
        if not ext["locations_all"]:
            low_conf.append({"title": it["title"], "url": url, "published": it["published"],
                             "reason": "no Nigerian location detected (likely out-of-scope: "
                                       "sports/international)"})
            seen.add(aid, url)
            continue

        rec = build_record(
            source=cfg.key, source_url=url, title=it["title"], raw_text=body,
            published_at=it["published"], collection_mode="rss",
            relevance={"is_candidate": rel["is_candidate"],
                       "matched_keywords": rel["matched_keywords"],
                       "corroborating": rel["corroborating"]},
            extraction=ext, extraction_confidence="low",
        )
        candidates.append(rec)
        seen.add(aid, url)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = os.path.join(out_dir, f"{stamp}_{batch}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)
    if low_conf:
        lc_path = os.path.join(low_conf_dir, f"{cfg.key}_{stamp}_{batch}.json")
        with open(lc_path, "w", encoding="utf-8") as f:
            json.dump(low_conf, f, ensure_ascii=False, indent=2)

    return {
        "outlet": cfg.name,
        "feed_items": len(items),
        "skipped_seen": skipped_seen,
        "candidates_written": len(candidates),
        "low_confidence": len(low_conf),
        "output": out_path,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outlet", choices=list(OUTLETS.keys()))
    # Free-form run label (e.g. am, pm, 0700, 1100) so collection can run at any
    # cadence. Collection frequency is independent of the daily publish/review batch.
    ap.add_argument("--batch", default="am")
    ap.add_argument("--limit", type=int, default=60)
    args = ap.parse_args()
    summary = run_outlet(args.outlet, args.batch, args.limit)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
