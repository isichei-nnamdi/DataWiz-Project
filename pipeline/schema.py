"""Provisional output schema (v0).

This is the ONLY place field names/shape are defined. When Ojo's ratified
scraper output format lands, remap here (see `to_ojo_format`) — no other
module should need to change.
"""

import hashlib
from datetime import datetime, timezone


SCHEMA_VERSION = "v0-provisional"


def article_id(source_url: str) -> str:
    """Stable id = sha1 of the canonical URL (used for dedup + record id)."""
    return hashlib.sha1(source_url.strip().encode("utf-8")).hexdigest()


def build_record(
    *,
    source: str,
    source_url: str,
    title: str,
    raw_text: str,
    published_at: str | None,
    collection_mode: str,
    relevance: dict,
    extraction: dict,
    extraction_confidence: str,
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "article_id": article_id(source_url),
        "source": source,
        "source_url": source_url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "published_at": published_at,
        "title": title,
        "raw_text": raw_text,
        "collection_mode": collection_mode,
        "relevance": relevance,          # {"is_candidate": bool, "matched_keywords": [...]}
        "extraction": extraction,        # {event_type, date, location, actors, impact}
        "extraction_confidence": extraction_confidence,  # low|medium|high
        "review_status": "pending",
    }


def to_ojo_format(record: dict) -> dict:
    """STUB: remap v0 -> Ojo's ratified format once it exists.

    Kept deliberately identity for now so the pipeline is wired end-to-end.
    Replace the mapping below when the standard output format is ratified.
    """
    return record
