"""Dedup store — idempotent re-runs.

Flat CSV of seen article ids (interim, per current Drive-storage decision).
Swap for a Postgres table once Ojo's pipeline lands.
"""

import csv
import os
from datetime import datetime, timezone


class SeenStore:
    def __init__(self, path: str):
        self.path = path
        self._seen: set[str] = set()
        if os.path.exists(path):
            with open(path, newline="", encoding="utf-8") as f:
                for row in csv.reader(f):
                    if row:
                        self._seen.add(row[0])

    def is_seen(self, article_id: str) -> bool:
        return article_id in self._seen

    def add(self, article_id: str, source_url: str) -> None:
        if article_id in self._seen:
            return
        self._seen.add(article_id)
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        write_header = not os.path.exists(self.path)
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(["article_id", "source_url", "first_seen"])
            w.writerow([article_id, source_url, datetime.now(timezone.utc).isoformat()])
