"""Atrium Health job listings via the Symphony Talent jobs API, filtered to Kannapolis, NC.

The careers site (careers.advocatehealth.org) is a WordPress front end whose
job search widget loads results client-side, as JSONP, from Symphony Talent's
jobs API (`jobsapi-internal.m-cloud.io/api/job`) for Advocate Health's
organization id. The site's human-verification check sits in front of the
browsable pages, not this endpoint, so a plain GET returns the same results.

The search is a radius search around Kannapolis, matching the site's own
location search, so results cover much of the Charlotte metro — keep only
postings whose primary or additional location city is Kannapolis itself. The
radius stays wide because the city filter is what makes the result exact.
"""

import re

import requests

from .base import BaseScraper, Job

API_URL = "https://jobsapi-internal.m-cloud.io/api/job"
ORG_ID = "2297"
LATITUDE = "35.4873613"
LONGITUDE = "-80.6217341"
RADIUS = "25"
TARGET_CITY = "kannapolis"
OLD_HOST = "://careers.aah.org/"
NEW_HOST = "://careers.advocatehealth.org/"
PAGE_SIZE = 200
MAX_PAGES = 25

HEADERS = {
    "Accept": "application/json",
    "Referer": "https://careers.advocatehealth.org/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def _clean(text: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", text or "").strip()


def _kannapolis_location(job: dict) -> str:
    """Return "City, ST ZIP" for the job's Kannapolis location, or "" if it has none."""
    candidates = [(job.get("primary_city"), job.get("primary_state"), job.get("primary_zip"))]
    for loc in job.get("addtnl_locations") or []:
        candidates.append((loc.get("addtnl_city"), loc.get("addtnl_state"), loc.get("addtnl_zip")))

    for city, state, zip_code in candidates:
        city = _clean(city)
        if city.lower() != TARGET_CITY:
            continue
        location = ", ".join(p for p in (city, _clean(state)) if p)
        return f"{location} {_clean(zip_code)}".strip()
    return ""


class AtriumScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Atrium Health"

    @property
    def slug(self) -> str:
        return "atrium"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Page through the Symphony Talent jobs API, keeping only Kannapolis postings."""
        results: list[Job] = []
        seen: set[str] = set()

        print("  Fetching Atrium Health job listings...")
        for page in range(MAX_PAGES):
            params = {
                "Organization": ORG_ID,
                "Latitude": LATITUDE,
                "Longitude": LONGITUDE,
                "LocationRadius": RADIUS,
                "Limit": PAGE_SIZE,
                "offset": page * PAGE_SIZE + 1,
                "sortfield": "open_date",
                "sortorder": "descending",
            }
            try:
                resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except (requests.RequestException, ValueError) as e:
                print(f"  Request failed on page {page + 1}: {e}")
                break

            jobs = data.get("queryResult") or []
            if not jobs:
                break

            for job in jobs:
                job_id = str(job.get("id") or "")
                title = _clean(job.get("title") or "")
                # The API still hands out links on the old careers.aah.org domain, which redirects
                url = _clean(job.get("url") or "").replace(OLD_HOST, NEW_HOST)
                if not job_id or not title or not url or job_id in seen:
                    continue

                location = _kannapolis_location(job)
                if not location:
                    continue

                seen.add(job_id)
                print(f"  {title}  |  {location}")
                results.append(Job(
                    title=title,
                    company="Atrium Health",
                    location=location,
                    url=url,
                    source="Atrium Health",
                ))

            if (page + 1) * PAGE_SIZE >= (data.get("totalHits") or 0):
                break

        print(f"  Found {len(results)} job(s).")
        return results
