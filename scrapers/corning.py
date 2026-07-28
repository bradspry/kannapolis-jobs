"""Corning job listings via their SAP SuccessFactors career site, filtered to Concord, NC.

The site's location facet filters by whether ANY of a job's posted locations
match (not just the one shown as primary), so a result may display a
different city as its "jobLocation" text even though Concord is also a valid
posting location for it — we override the display location to Concord since
that's the whole point of the facet filter.
"""

import re

import requests

from .base import BaseScraper, Job

BASE_URL = "https://corningjobs.corning.com"
SEARCH_URL = f"{BASE_URL}/search/"
LOCATION_FACET = "Concord, NC, US, 28026"
PAGE_SIZE = 25

ROW_RE = re.compile(r'<tr class="data-row">(.*?)</tr>', re.S)
TITLE_TAG_RE = re.compile(r'<a\s+([^>]*class="jobTitle-link"[^>]*)>([^<]+)</a>')
HREF_RE = re.compile(r'href="([^"]+)"')

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _clean(text: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", text or "").strip()


class CorningScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Corning"

    @property
    def slug(self) -> str:
        return "corning"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Page through the SuccessFactors career-site search with startrow, filtered to Concord."""
        results: list[Job] = []
        seen: set[str] = set()

        print("  Fetching Corning job listings...")
        startrow = 0
        while True:
            params = {
                "q": keyword or "",
                "optionsFacetsDD_city": "Concord",
                "optionsFacetsDD_location": LOCATION_FACET,
            }
            if startrow:
                params["startrow"] = startrow

            resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                break

            rows = ROW_RE.findall(resp.text)
            if not rows:
                break

            new_count = 0
            for row in rows:
                m = TITLE_TAG_RE.search(row)
                if not m:
                    continue
                href_m = HREF_RE.search(m.group(1))
                href = href_m.group(1) if href_m else ""
                title = _clean(m.group(2))
                if not href or not title or href in seen:
                    continue
                seen.add(href)
                new_count += 1

                url = BASE_URL + href if href.startswith("/") else href
                print(f"  {title}  |  {LOCATION_FACET}")
                results.append(Job(
                    title=title,
                    company="Corning",
                    location=LOCATION_FACET,
                    url=url,
                    source="Corning",
                ))

            startrow += len(rows)
            if new_count == 0 or len(rows) < PAGE_SIZE:
                break

        print(f"  Found {len(results)} job(s).")
        return results
