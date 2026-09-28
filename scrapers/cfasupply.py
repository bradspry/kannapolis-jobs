"""Chick-fil-A Supply job listings from the Chick-fil-A careers site.

The careers site (careers.chick-fil-a.com) is a Jibe portal whose search page
is backed by a plain JSON endpoint, so a location-radius query against
`/api/jobs` returns the same results as the site's Supply search page. The
endpoint covers all Chick-fil-A brands, so results are narrowed to those
tagged "CFA Supply".
"""

import re

import requests

from .base import BaseScraper, Job

API_URL = "https://careers.chick-fil-a.com/api/jobs"
JOB_URL = "https://careers.chick-fil-a.com/supply/jobs/{slug}?lang=en-us"

SEARCH_PARAMS = {
    "location": "Kannapolis, NC",
    "woe": "7",
    "regionCode": "US",
    "stretchUnit": "MILES",
    "stretch": "10",
    "limit": "100",
}

SUPPLY_TAG = "CFA Supply"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def _clean(text: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", text or "").strip()


class CFASupplyScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Chick-fil-A Supply"

    @property
    def slug(self) -> str:
        return "cfasupply"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Page through the Jibe jobs API for the Kannapolis radius search, keeping CFA Supply jobs."""
        results: list[Job] = []
        seen: set[str] = set()

        print("  Fetching Chick-fil-A Supply job listings...")
        page = 1
        fetched = 0
        while True:
            try:
                resp = requests.get(
                    API_URL, params={**SEARCH_PARAMS, "page": page},
                    headers=HEADERS, timeout=20,
                )
                resp.raise_for_status()
                data = resp.json()
            except (requests.RequestException, ValueError) as e:
                print(f"  Request failed: {e}")
                break

            jobs = data.get("jobs") or []
            fetched += len(jobs)
            for entry in jobs:
                job = entry.get("data") or {}
                if SUPPLY_TAG not in (job.get("tags1") or []):
                    continue
                slug = str(job.get("slug") or job.get("req_id") or "")
                title = _clean(job.get("title") or "")
                if not slug or not title or slug in seen:
                    continue
                seen.add(slug)

                location = _clean(job.get("full_location") or "") or "Kannapolis, NC"
                print(f"  {title}  |  {location}")
                results.append(Job(
                    title=title,
                    company="Chick-fil-A Supply",
                    location=location,
                    url=JOB_URL.format(slug=slug),
                    source="Chick-fil-A Supply",
                ))

            total = data.get("totalCount") or 0
            if not jobs or fetched >= total:
                break
            page += 1

        print(f"  Found {len(results)} job(s).")
        return results
