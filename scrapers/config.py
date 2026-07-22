"""Per-outlet configuration.

One entry per assigned outlet. Nigerian Tribune is intentionally disabled
(explicit bot ban in robots.txt) pending a team compliance decision.
"""

from dataclasses import dataclass, field


@dataclass
class OutletConfig:
    key: str                 # stable id used in filenames/records
    name: str                # human-readable name
    base_url: str
    feeds: list[str]         # one or more RSS/Atom feeds (site-wide + category)
    robots_status: str       # short note on robots.txt findings
    crawl_delay: int         # seconds between requests to this host
    category_paths: list[str] = field(default_factory=list)  # HTML fallback sections
    enabled: bool = True


OUTLETS: dict[str, OutletConfig] = {
    "premium_times": OutletConfig(
        key="premium_times",
        name="Premium Times",
        base_url="https://www.premiumtimesng.com",
        # Multiple category feeds — each has its own ~15-item window, so together
        # they widen coverage and skew toward security-relevant sections.
        feeds=[
            "https://www.premiumtimesng.com/news/headlines/feed",
            "https://www.premiumtimesng.com/news/more-news/feed",
            "https://www.premiumtimesng.com/news/top-news/feed",
            "https://www.premiumtimesng.com/category/regional/feed",
        ],
        robots_status="open (Disallow empty; crawl-delay 10)",
        crawl_delay=10,
        category_paths=["/category/news/more-news", "/category/regional"],
    ),
    "prnigeria": OutletConfig(
        key="prnigeria",
        name="PRNigeria",
        base_url="https://prnigeria.com",
        feeds=["https://prnigeria.com/feed"],  # category feeds probed at roll-out
        robots_status="open (Disallow empty)",
        crawl_delay=5,
        category_paths=["/category/national"],
    ),
    "humangle": OutletConfig(
        key="humangle",
        name="HumAngle",
        base_url="https://humanglemedia.com",
        feeds=["https://humanglemedia.com/feed"],  # category feeds probed at roll-out
        robots_status="open (Disallow empty)",
        crawl_delay=5,
        category_paths=["/news"],
    ),
    "nta": OutletConfig(
        key="nta",
        name="NTA",
        base_url="https://www.nta.ng",
        feeds=[],  # Next.js site; no confirmed feed — HTML fallback needed
        robots_status="open (/api,/test,/_next,/static disallowed)",
        crawl_delay=5,
        category_paths=["/category/news", "/category/security"],
    ),
    "nigerian_tribune": OutletConfig(
        key="nigerian_tribune",
        name="Nigerian Tribune",
        base_url="https://tribuneonlineng.com",
        feeds=["https://tribuneonlineng.com/feed"],
        robots_status="BOT BAN — ClaudeBot/GPTBot/Amazonbot disallowed; ai-train=no",
        crawl_delay=10,
        enabled=False,  # held back pending compliance decision
    ),
}
