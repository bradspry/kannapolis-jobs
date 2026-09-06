"""Cabarrus County Schools job listings via the SchoolSpring public jobs API."""

import re
from urllib.parse import urlencode

import requests

from .base import BaseScraper, Job

API_URL     = "https://api.schoolspring.com/api/Jobs/GetPagedJobsWithSearch"
JOB_URL     = "https://cabarrus.schoolspring.com/jobdetail?jobId={}"
DOMAIN_NAME = "cabarrus.schoolspring.com"
PAGE_SIZE   = 100

STATE_ABBREV = {"north carolina": "NC", "south carolina": "SC", "virginia": "VA"}


def _short_location(location: str) -> str:
    """Turn "Concord, North Carolina" into "Concord, NC"; leave anything else alone."""
    city, _, state = (location or "").partition(",")
    abbrev = STATE_ABBREV.get(state.strip().lower())
    return f"{city.strip()}, {abbrev}" if abbrev else re.sub(r"\s+", " ", location or "").strip()


class CabarrusCountySchoolsScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Cabarrus County Schools"

    @property
    def slug(self) -> str:
        return "ccs"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Page through the district's SchoolSpring job board and collect every posting."""
        print("  Fetching Cabarrus County Schools job listings...")

        results: list[Job] = []
        seen: set[int] = set()
        page = 1

        while True:
            params = {
                "domainName": DOMAIN_NAME,
                "keyword": keyword,
                "location": "",
                "category": "",
                "gradelevel": "",
                "jobtype": "",
                "organization": "",
                "swLat": "", "swLon": "", "neLat": "", "neLon": "",
                "page": page,
                "size": PAGE_SIZE,
                "sortDateAscending": "false",
            }
            resp = requests.get(
                f"{API_URL}?{urlencode(params)}",
                headers={"Accept": "application/json", "Referer": f"https://{DOMAIN_NAME}/"},
                timeout=30,
            )
            resp.raise_for_status()
            payload = resp.json()

            if not payload.get("success"):
                print(f"  API error: {payload.get('message') or 'unknown'}")
                break

            jobs = (payload.get("value") or {}).get("jobsList") or []
            if not jobs:
                break

            for job in jobs:
                job_id = job.get("jobId")
                title  = (job.get("title") or "").strip()
                if not job_id or not title or job_id in seen:
                    continue
                seen.add(job_id)

                school   = (job.get("employer") or "").strip()
                city     = _short_location(job.get("location") or "")
                location = f"{city} — {school}" if city and school else (city or school)

                print(f"  {title}  |  {location}")
                results.append(Job(
                    title=title,
                    company="Cabarrus County Schools",
                    location=location,
                    url=JOB_URL.format(job_id),
                    source="Cabarrus County Schools",
                ))

            if len(jobs) < PAGE_SIZE:
                break
            page += 1

        print(f"  Found {len(results)} job(s).")
        return results
