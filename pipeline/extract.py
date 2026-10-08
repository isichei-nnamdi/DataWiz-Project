"""Rule-based extraction stub (Sprint 1).

Deliberately simple: real NLP extraction is a Sprint 2 deliverable per the
roadmap. This produces low-confidence structured fields so the end-to-end
pipeline and review queue can be exercised now.
"""

import re
from .relevance import EVENT_KEYWORDS, _compile

# Small Nigerian gazetteer — states + notable security-hotspot towns.
# Extend in Sprint 2; this is enough to exercise location extraction now.
LOCATIONS = [
    "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa", "Benue",
    "Borno", "Cross River", "Delta", "Ebonyi", "Edo", "Ekiti", "Enugu", "Gombe",
    "Imo", "Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi", "Kogi", "Kwara",
    "Lagos", "Nasarawa", "Niger", "Ogun", "Ondo", "Osun", "Oyo", "Plateau",
    "Rivers", "Sokoto", "Taraba", "Yobe", "Zamfara", "Abuja", "FCT",
    "Maiduguri", "Sokoto", "Jos", "Mubi", "Monguno", "Chibok", "Zaria",
]
_LOC_PATTERNS = [(loc, re.compile(r"\b" + re.escape(loc) + r"\b")) for loc in LOCATIONS]

ACTORS = [
    "bandits", "gunmen", "Boko Haram", "ISWAP", "kidnappers", "insurgents",
    "herdsmen", "militants", "cultists", "troops", "soldiers", "police",
    "vigilantes", "ESN", "IPOB", "unknown gunmen",
]
_ACTOR_PATTERNS = [(a, _compile(a)) for a in ACTORS]

# Spelled-out counts common in Nigerian crime reporting ("killed two women").
_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "scores": 20, "dozens": 24,
    "several": None, "many": None,  # qualitative — captured but no number
}
_COUNT = r"(\d{1,4}|" + "|".join(_WORD_NUMBERS) + r")"
_VICTIM = (r"(?:persons?|people|students?|residents?|villagers?|soldiers?|women|"
           r"men|children|worshippers?|passengers?|travellers?|farmers?|pupils?|"
           r"teachers?|victims?)?")
_OUTCOME = r"(killed|dead|abducted|kidnapped|injured|wounded|missing|beheaded|shot)"

# Order-flexible: "12 killed", "killed two women", "abducted 30 students".
_CASUALTY_A = re.compile(rf"{_COUNT}\s+{_VICTIM}\s*(?:were\s+|was\s+)?{_OUTCOME}", re.IGNORECASE)
_CASUALTY_B = re.compile(rf"{_OUTCOME}\s+{_COUNT}\s+{_VICTIM}", re.IGNORECASE)


def _normalise_count(raw: str) -> str:
    key = raw.lower()
    if key in _WORD_NUMBERS:
        n = _WORD_NUMBERS[key]
        return str(n) if n is not None else key
    return key


def extract(title: str, body: str, published_at: str | None) -> dict:
    text = f"{title}\n{body}"

    event_types: list[str] = []
    for root, pat in ((r, _compile(r)) for r in EVENT_KEYWORDS):
        if pat.search(text):
            et = EVENT_KEYWORDS[root]
            if et not in event_types:
                event_types.append(et)

    locations = [loc for loc, pat in _LOC_PATTERNS if pat.search(text)]
    actors = [a for a, pat in _ACTOR_PATTERNS if pat.search(text)]

    impact = None
    m = _CASUALTY_A.search(text)
    if m:
        impact = f"{_normalise_count(m.group(1))} {m.group(2).lower()}"
    else:
        m = _CASUALTY_B.search(text)
        if m:
            impact = f"{_normalise_count(m.group(2))} {m.group(1).lower()}"

    return {
        "event_type": event_types[0] if event_types else None,
        "event_types_all": event_types,
        "date": published_at,
        "location": locations[0] if locations else None,
        "locations_all": locations,
        "actors": actors,
        "impact": impact,
    }
