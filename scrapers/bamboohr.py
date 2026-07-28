"""Shared client for BambooHR's public careers-page JSON API.

Any employer whose "Careers" page is hosted at {company}.bamboohr.com/careers
exposes the same public JSON API at /careers/list — subclass BambooHRScraper
with that employer's subdomain to add it as a source.
"""

import re

import requests

from .base import BaseScraper, Job

API_URL = "https://{subdomain}.bamboohr.com/careers/list"
DETAIL_URL = "https://{subdomain}.bamboohr.com/careers/{job_id}"


def _clean(text: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", text or "").strip()


def _is_remote(posting: dict) -> bool:
    """No city/state set, but an ATS country is — BambooHR's shape for a remote/general opening."""
    loc = posting.get("location") or {}
    country = (posting.get("atsLocation") or {}).get("country")
    return not loc.get("city") and not loc.get("state") and bool(country)


def _location(posting: dict) -> str:
    """City/state from the primary location; falls back to "{Country} (Remote)" when unset."""
    loc = posting.get("location") or {}
    city, state = loc.get("city"), loc.get("state")
    if city and state:
        return f"{city}, {state}"
    if city or state:
        return city or state
    if _is_remote(posting):
        return f"{(posting.get('atsLocation') or {}).get('country')} (Remote)"
    return ""


class BambooHRScraper(BaseScraper):
    """Base class for a BambooHR careers page. Subclass and set subdomain/company."""

    subdomain: str
    company: str
    target_cities: set[str] | None = None  # lowercased city names to keep; None keeps everything
    include_remote: bool = False  # also keep listings with no city/state (e.g. "United States (Remote)")

    @property
    def name(self) -> str:
        return self.company

    def fetch(self, keyword: str = "") -> list[Job]:
        """Fetch the full BambooHR careers listing (a single unpaginated JSON response)."""
        results: list[Job] = []

        print(f"  Fetching {self.company} job listings...")
        url = API_URL.format(subdomain=self.subdomain)
        resp = requests.get(url, headers={"Accept": "application/json"}, timeout=15)
        if resp.status_code != 200:
            print(f"  Request failed: HTTP {resp.status_code}")
            return results

        postings = resp.json().get("result") or []
        for posting in postings:
            job_id = posting.get("id")
            title = _clean(posting.get("jobOpeningName") or "")
            location = _location(posting)
            if not job_id or not title:
                continue

            if self.target_cities is not None:
                loc_obj = posting.get("location") or {}
                city = (loc_obj.get("city") or "").strip().lower()
                matches_city = city in self.target_cities
                matches_remote = self.include_remote and _is_remote(posting)
                if not (matches_city or matches_remote):
                    continue

            url = DETAIL_URL.format(subdomain=self.subdomain, job_id=job_id)
            print(f"  {title}  |  {location or '(no location)'}")
            results.append(Job(
                title=title,
                company=self.company,
                location=location,
                url=url,
                source=self.company,
            ))

        print(f"  Found {len(results)} job(s).")
        return results
