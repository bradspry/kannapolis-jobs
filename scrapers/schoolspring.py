"""Shared client for the SchoolSpring (PowerSchool) school-district job board.

A district's board at {district}.schoolspring.com is a React app with no
server-rendered listings, but the bundle it loads calls a public JSON API that
needs no authentication — subclass SchoolSpringScraper with the district's
domain to add it as a source.

The API takes the board's own hostname as `domainName`, which is what scopes
results to that district, and it honours a keyword, so these modules support
the CLI keyword argument.
"""

import re
from urllib.parse import urlencode

import requests

from .base import BaseScraper, Job

API_URL   = "https://api.schoolspring.com/api/Jobs/GetPagedJobsWithSearch"
JOB_URL   = "https://{domain}/jobdetail?jobId={job_id}"
PAGE_SIZE = 100

STATE_ABBREV = {"north carolina": "NC", "south carolina": "SC", "virginia": "VA"}


def _short_location(location: str) -> str:
    """Turn "Concord, North Carolina" into "Concord, NC"; leave anything else alone."""
    city, _, state = (location or "").partition(",")
    abbrev = STATE_ABBREV.get(state.strip().lower())
    return f"{city.strip()}, {abbrev}" if abbrev else re.sub(r"\s+", " ", location or "").strip()


class SchoolSpringScraper(BaseScraper):
    """Base class for a SchoolSpring job board. Subclass and set domain/company."""

    domain: str
    company: str

    @property
    def name(self) -> str:
        return self.company

    def fetch(self, keyword: str = "") -> list[Job]:
        """Page through the district's job board and collect every posting."""
        print(f"  Fetching {self.company} job listings...")

        results: list[Job] = []
        seen: set[int] = set()
        page = 1

        while True:
            params = {
                "domainName": self.domain,
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
                headers={"Accept": "application/json", "Referer": f"https://{self.domain}/"},
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
                title  = re.sub(r"\s+", " ", job.get("title") or "").strip()
                if not job_id or not title or job_id in seen:
                    continue
                seen.add(job_id)

                school   = (job.get("employer") or "").strip()
                city     = _short_location(job.get("location") or "")
                location = f"{city} — {school}" if city and school else (city or school)

                print(f"  {title}  |  {location}")
                results.append(Job(
                    title=title,
                    company=self.company,
                    location=location,
                    url=JOB_URL.format(domain=self.domain, job_id=job_id),
                    source=self.company,
                ))

            if len(jobs) < PAGE_SIZE:
                break
            page += 1

        print(f"  Found {len(results)} job(s).")
        return results
