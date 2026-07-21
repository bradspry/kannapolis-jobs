"""Eli Lilly job listings near Concord, NC via the jobsyn.org Solr search API."""

import re

import requests

from .base import BaseScraper, Job

API_URL  = "https://prod-search-api.jobsyn.org/api/v1/solr/search?location=concord-nc&page={page}"
BASE_URL = "https://jobsearch.lilly.com"
HEADERS  = {
    "referer": "https://jobsearch.lilly.com/",
    "x-origin": "jobsearch.lilly.com",
    "accept": "application/json",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}


def _clean(text: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", text or "").strip()


def _job_url(job: dict) -> str:
    """Build the public job-detail URL from its location, title slug, and guid."""
    loc   = (job.get("location_exact") or "").replace(", ", "-").lower()
    slug  = job.get("title_slug") or ""
    guid  = job.get("guid") or ""
    return f"{BASE_URL}/{loc}/{slug}/{guid}/job/"


class LillyScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Lilly"

    @property
    def slug(self) -> str:
        return "lilly"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Page through the search API until a page comes back empty, deduping by URL."""
        results: list[Job] = []
        seen: set[str] = set()

        print("  Fetching Lilly job listings...")
        for page in range(1, 20):
            resp = requests.get(API_URL.format(page=page), headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                break
            jobs = resp.json().get("jobs") or []
            if not jobs:
                break
            for job in jobs:
                title    = _clean(job.get("title_exact") or "")
                location = _clean(job.get("location_exact") or "")
                url      = _job_url(job)
                if not title or url in seen:
                    continue
                seen.add(url)
                print(f"  {title}  |  {location}")
                results.append(Job(
                    title=title,
                    company="Lilly",
                    location=location,
                    url=url,
                    source="Lilly",
                ))

        print(f"  Found {len(results)} job(s).")
        return results
