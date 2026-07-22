"""Security-relevance filter (keyword library v1).

Design notes (addresses the brainstorm points):
- Keywords are stored as ROOTS. Matching uses `\\b<root>\\w*\\b`, so a single
  root ("kidnap") matches kidnap, kidnapped, kidnapping, kidnappers. This is a
  lightweight substitute for lemmatization and keeps the library small.
- Multi-word phrases ("armed robbery", "unknown gunmen") are matched literally.
- Zero-match articles are NOT discarded by this module — the caller routes them
  to a low-confidence bucket for manual spot-check and keyword-library growth.
"""

import re

# Incident-type roots -> canonical event category (also reused by extraction).
EVENT_KEYWORDS: dict[str, str] = {
    "kidnap": "kidnapping",
    "abduct": "kidnapping",
    "hostage": "kidnapping",
    "ransom": "kidnapping",
    "bandit": "banditry",
    "terror": "terrorism",
    "insurgen": "terrorism",
    "boko haram": "terrorism",
    "iswap": "terrorism",
    "ambush": "armed_attack",
    "gunmen": "armed_attack",
    "gunman": "armed_attack",
    "shoot": "armed_attack",
    "shot": "armed_attack",
    "attack": "armed_attack",
    "raid": "armed_attack",
    "kill": "violence_fatal",
    "massacre": "violence_fatal",
    "murder": "violence_fatal",
    "clash": "communal_clash",
    "herdsm": "communal_clash",
    "robber": "robbery",
    "cult": "cult_violence",
    "explos": "explosion",
    "bomb": "explosion",
    "blast": "explosion",
    "ied": "explosion",
    "militant": "militancy",
    "arson": "arson",
}

# Extra corroborating terms that raise confidence but don't set an event type.
CORROBORATING = [
    "troops", "military", "police", "operatives", "vigilante", "casualt",
    "fatalit", "wounded", "injured", "arrested", "arms", "ammunition",
    "curfew", "displac", "idp", "security",
]

# STRONG roots = unambiguous public-safety incidents. If any of these match,
# the article is a candidate regardless of suppression context.
STRONG_ROOTS = {
    "kidnap", "abduct", "hostage", "ransom", "bandit", "terror", "insurgen",
    "boko haram", "iswap", "ambush", "gunmen", "gunman", "massacre", "militant",
    "bomb", "blast", "ied", "explos", "herdsm", "arson",
}

# Suppression context = drug/regulatory enforcement stories. These trip broad
# keywords like "raid"/"attack" but are NOT the safety-map incident type. An
# article matching suppression with NO strong keyword is downgraded to
# low-confidence before it ever reaches a human reviewer (keeps review load low).
SUPPRESS_ROOTS = [
    "ndlea", "nafdac", "efcc", "cannabis", "narcotic", "tramadol", "codeine",
    "skunk", "contraband", "smuggl", "illicit drug", "drug trafficking",
    "seized", "seizure", "counterfeit", "adulterat",
]


def _compile(root: str) -> re.Pattern:
    if " " in root:  # multi-word phrase — match literally
        return re.compile(r"\b" + re.escape(root) + r"\b", re.IGNORECASE)
    return re.compile(r"\b" + re.escape(root) + r"\w*\b", re.IGNORECASE)


_EVENT_PATTERNS = {root: _compile(root) for root in EVENT_KEYWORDS}
_CORROB_PATTERNS = {root: _compile(root) for root in CORROBORATING}
_SUPPRESS_PATTERNS = {root: _compile(root) for root in SUPPRESS_ROOTS}


def score(text: str) -> dict:
    """Return relevance verdict for an article's text (title + body)."""
    matched: list[str] = []
    event_types: set[str] = set()
    for root, pat in _EVENT_PATTERNS.items():
        if pat.search(text):
            matched.append(root)
            event_types.add(EVENT_KEYWORDS[root])
    corroborating = [root for root, pat in _CORROB_PATTERNS.items() if pat.search(text)]
    suppressors = [root for root, pat in _SUPPRESS_PATTERNS.items() if pat.search(text)]
    has_strong = any(m in STRONG_ROOTS for m in matched)

    # Downgrade drug/regulatory-enforcement stories that only tripped a broad
    # keyword (e.g. "raid") and carry no strong incident term.
    suppressed = bool(matched) and bool(suppressors) and not has_strong
    is_candidate = bool(matched) and not suppressed

    return {
        "is_candidate": is_candidate,
        "matched_keywords": matched,
        "corroborating": corroborating,
        "event_types": sorted(event_types),
        "suppressed": suppressed,
        "suppressors": suppressors,
    }
