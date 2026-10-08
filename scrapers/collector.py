"""Collection layer — RSS-first, respects per-host crawl-delay.

Two-stage by design: the RSS feed gives title + link + excerpt cheaply; full
article text is fetched ONLY for relevance-passed candidates (saves requests and
respects the outlet). Full-text fetch is a separate call the orchestrator makes.
"""

import re
import time
import feedparser
import requests
from bs4 import BeautifulSoup

USER_AGENT = "DataWizBot/0.1 (+security-incident research; contact: datawiz team)"
_last_hit: dict[str, float] = {}

# Newsletter/CTA/wire-attribution lines to drop from extracted article text.
_BOILERPLATE = [
    re.compile(r"follow us on google news.*", re.IGNORECASE),
    re.compile(r"never miss breaking stories.*", re.IGNORECASE),
    re.compile(r"^\(\s*[A-Z]{2,5}\s*\)$"),           # "( NAN )", "(NAN)"
    re.compile(r"^(share this|read also|read more)[:\s].*", re.IGNORECASE),
    re.compile(r"sign up for our newsletter.*", re.IGNORECASE),
    re.compile(r"click here to (join|follow).*", re.IGNORECASE),
]


def _strip_boilerplate(paras: list[str]) -> list[str]:
    cleaned = []
    for p in paras:
        if any(pat.search(p) for pat in _BOILERPLATE):
            continue
        cleaned.append(p)
    return cleaned


def _throttle(host: str, delay: int) -> None:
    now = time.monotonic()
    last = _last_hit.get(host, 0.0)
    wait = delay - (now - last)
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.monotonic()


def fetch_feed(feed_url: str) -> list[dict]:
    """Return list of {title, link, published, summary} from an RSS/Atom feed."""
    parsed = feedparser.parse(feed_url)
    items = []
    for e in parsed.entries:
        items.append({
            "title": e.get("title", "").strip(),
            "link": e.get("link", "").strip(),
            "published": e.get("published", None) or e.get("updated", None),
            "summary": BeautifulSoup(e.get("summary", ""), "html.parser").get_text(" ", strip=True),
        })
    return items


def fetch_feeds(feed_urls: list[str]) -> list[dict]:
    """Fetch several feeds and merge, deduping by canonical link within the run.

    Category feeds overlap (a headline appears in both /headlines and /top-news),
    so first-seen-wins dedup keeps one copy and preserves ordering.
    """
    merged: dict[str, dict] = {}
    for url in feed_urls:
        for item in fetch_feed(url):
            link = item["link"]
            if link and link not in merged:
                merged[link] = item
    return list(merged.values())


def fetch_article_text(url: str, host: str, crawl_delay: int) -> str:
    """Fetch and extract main article text. Respects crawl-delay for the host."""
    _throttle(host, crawl_delay)
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    # Strip non-content nodes.
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    # Prefer specific content containers first. NOTE: a bare <article> is NOT
    # reliable — themes (e.g. JNews) wrap related-post teaser cards in <article>
    # tags with no body text, so a generic soup.find("article") grabs an empty
    # teaser. Named content selectors come first; densest-paragraph node last.
    node = None
    for sel in [
        "div.entry-content", "div.content-inner", "div.post-content",
        "div.td-post-content", "article.jeg_single_tpl_content", "main",
    ]:
        node = soup.select_one(sel)
        if node and node.find_all("p"):
            break
        node = None

    if node is None:
        # Fallback: pick the container with the most <p> descendants.
        best, best_count = None, 0
        for d in soup.find_all(["div", "section", "article"]):
            c = len(d.find_all("p"))
            if c > best_count:
                best, best_count = d, c
        node = best or soup

    paras = [p.get_text(" ", strip=True) for p in node.find_all("p")]
    paras = _strip_boilerplate([p for p in paras if p])
    text = "\n".join(paras)
    return text.strip()
