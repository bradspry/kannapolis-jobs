"""Sysco job listings via their TalentBrew career site, filtered to Concord, Cabarrus County, NC.

The search URL is a radius search (50 miles from Concord), so results also
include nearby cities like Charlotte — the job list itself is server-rendered
directly in the HTML, paginated with a `?p=N` query param, so we page through
it and keep only listings whose location text is exactly the target city.
"""

import re

import requests

from .base import BaseScraper, Job

BASE_URL = "https://careers.sysco.com"
SEARCH_URL = (
    f"{BASE_URL}/en/search-jobs/Concord%2C%20Cabarrus%20County%2C%20NC"
    "/1105/4/6252001-4482348-4458491-4461574/35x40888/-80x58158/50/2"
)
TARGET_LOCATION = "concord, cabarrus county, nc"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

TOTAL_RE = re.compile(r'<h1 id="search-results-headline-label">(\d+) Results found')
LIST_RE = re.compile(r'id="search-results-jobs".*?</ul>', re.S)
ITEM_RE = re.compile(
    r'<a href="([^"]+)" data-job-id="[^"]*">\s*<h2>([^<]+)</h2>\s*'
    r'(?:<span class="job-location">([^<]*)</span>)?'
)


def _clean(text: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", text or "").strip()


class SyscoScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Sysco"

    @property
    def slug(self) -> str:
        return "sysco"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Page through the TalentBrew search results, keeping only Concord, Cabarrus County postings."""
        results: list[Job] = []
        seen: set[str] = set()

        print("  Fetching Sysco job listings...")
        page = 1
        total = None
        while True:
            url = SEARCH_URL if page == 1 else f"{SEARCH_URL}?p={page}"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                break

            if total is None:
                m = TOTAL_RE.search(resp.text)
                total = int(m.group(1)) if m else 0

            list_m = LIST_RE.search(resp.text)
            if not list_m:
                break
            segment = list_m.group(0)

            items = ITEM_RE.findall(segment)
            if not items:
                break

            for href, title, location in items:
                if href in seen:
                    continue
                seen.add(href)

                title = _clean(title)
                location = _clean(location)
                if not title or location.lower() != TARGET_LOCATION:
                    continue

                url_abs = BASE_URL + href if href.startswith("/") else href
                print(f"  {title}  |  {location}")
                results.append(Job(
                    title=title,
                    company="Sysco",
                    location=location,
                    url=url_abs,
                    source="Sysco",
                ))

            if len(seen) >= total or not items:
                break
            page += 1

        print(f"  Found {len(results)} job(s).")
        return results
