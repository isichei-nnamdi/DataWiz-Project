# Data Source Scraper Ban Check

**Checked by:** Success Akinnusi (Collection / NLP Engineer)
**Date:** 19 July 2026
**Scope:** robots.txt and Terms of Use/Conditions review for assigned outlets, to confirm whether scraping is explicitly prohibited before building scrapers.

## Results

| S/N | Name | Link | File | Result |
|---|---|---|---|---|
| 1 | Premium Times | [premiumtimesng.com](https://www.premiumtimesng.com) | [robots.txt](https://www.premiumtimesng.com/robots.txt) / [Terms and Conditions](https://www.premiumtimesng.com/terms-and-conditions) | No explicitly stated ban on use of scrapers |
| 2 | Nigerian Tribune | [tribuneonlineng.com](https://tribuneonlineng.com) | [robots.txt](https://tribuneonlineng.com/robots.txt) / [Terms and Conditions](https://tribuneonlineng.com/terms-and-conditions/) | Explicit ban on named scraper/AI-crawler bots (robots.txt) |
| 3 | PRNigeria | [prnigeria.com](https://prnigeria.com) | [robots.txt](https://prnigeria.com/robots.txt) | No explicitly stated ban on use of scrapers |
| 4 | HumAngle | [humanglemedia.com](https://humanglemedia.com) | [robots.txt](https://humanglemedia.com/robots.txt) | No explicitly stated ban on use of scrapers |
| 5 | NTA | [nta.ng](https://nta.ng) | [robots.txt](https://nta.ng/robots.txt) | No explicitly stated ban on use of scrapers |

## Conclusion

Of the five assigned outlets, only **Nigerian Tribune** carries an explicit ban on scraper/automated-crawler use, naming specific bots (ClaudeBot, GPTBot, Amazonbot, and others) as disallowed in its robots.txt, alongside an `ai-train=no` content signal. The remaining four outlets — Premium Times, PRNigeria, HumAngle, and NTA — do not explicitly prohibit scraping in the files checked. Scraper development can proceed for these four; Nigerian Tribune should be flagged to the team for a compliance decision before building a scraper against it.
