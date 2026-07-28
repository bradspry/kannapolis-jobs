"""Chewy job listings, scraped from a Phenom People career-site landing page.

The landing page for a given location (e.g. the Salisbury, NC fulfillment
center) embeds its job search results directly in the initial HTML as a
`phApp.ddo = {...}` JSON blob — no JS execution or session/token dance
needed, just a plain GET and a balanced-brace JSON extraction.

The embedded result set is capped at the page's configured page size (5 at
last check); if a location ever posts more openings than that, we print a
notice rather than silently truncating, since paginating further requires
replicating a token-gated search flow that isn't practical from a plain
HTTP client.
"""

import json
import re

import requests

from .base import BaseScraper, Job

LANDING_URL = "https://careers.chewy.com/us/en/salisbury-nc-warehouse-and-fulfillment-center-jobs"

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


class ChewyScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Chewy"

    @property
    def slug(self) -> str:
        return "chewy"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Parse the phApp.ddo JSON embedded in the landing page's server-rendered HTML."""
        results: list[Job] = []

        print("  Fetching Chewy job listings...")
        resp = requests.get(LANDING_URL, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"  Request failed: HTTP {resp.status_code}")
            return results

        marker = "phApp.ddo = "
        idx = resp.text.find(marker)
        if idx == -1:
            print("  Could not find embedded job data on the page.")
            return results

        try:
            ddo, _ = json.JSONDecoder().raw_decode(resp.text, idx + len(marker))
        except json.JSONDecodeError as e:
            print(f"  Failed to parse embedded job data: {e}")
            return results

        search = (ddo.get("eagerLoadRefineSearch") or {}).get("data") or {}
        jobs = search.get("jobs") or []
        total_hits = (ddo.get("eagerLoadRefineSearch") or {}).get("totalHits", len(jobs))
        if total_hits > len(jobs):
            print(f"  Note: {total_hits} total job(s) reported but only {len(jobs)} embedded on the page.")

        for job in jobs:
            title = _clean(job.get("title") or "")
            location = _clean(job.get("location") or job.get("cityStateCountry") or "")
            url = job.get("applyUrl") or ""
            if not title or not url:
                continue

            print(f"  {title}  |  {location or '(no location)'}")
            results.append(Job(
                title=title,
                company="Chewy",
                location=location,
                url=url,
                source="Chewy",
            ))

        print(f"  Found {len(results)} job(s).")
        return results
