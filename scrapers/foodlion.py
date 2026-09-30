"""Food Lion job listings via the careers site's public Job Query API, filtered to Kannapolis, NC.

The careers site (foodlion.careerswithus.com) documents a JSON endpoint in its
llms.txt, `/api/mcp/jobs?tool=search_jobs`. Its `location` parameter is
ignored — every value returns the full chain-wide list — but its `search`
keyword covers job descriptions, which open with the store address
("Address: USA-NC-Kannapolis-2825 B N Cannon Blvd Store Code: ..."). So we
search for "Kannapolis" and then keep only postings whose location city is
Kannapolis itself, which drops any posting that merely mentions the city.

Because the search keyword is spent on the location, this module ignores
the CLI keyword and always returns every current Kannapolis posting.
"""

import re
from urllib.parse import quote

import requests

from .base import BaseScraper, Job

API_URL = "https://foodlion.careerswithus.com/api/mcp/jobs"
JOB_URL = "https://foodlion.careerswithus.com/job/{job_id}"
TARGET_CITY = "kannapolis"
PAGE_SIZE = 100
MAX_PAGES = 10

HEADERS = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def _clean(text: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", text or "").strip()


def _street(description: str) -> str:
    """Pull the store's street address out of "Address: USA-NC-Kannapolis-<street> Store Code: ..."."""
    m = re.search(r"Address:\s*[A-Z]{3}-[A-Z]{2}-[^-]+-(.+?)\s+Store Code:", description or "")
    return _clean(m.group(1)) if m else ""


class FoodLionScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Food Lion"

    @property
    def slug(self) -> str:
        return "foodlion"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Search the Job Query API for Kannapolis and keep postings located there."""
        results: list[Job] = []
        seen: set[str] = set()

        print("  Fetching Food Lion job listings...")
        for page in range(1, MAX_PAGES + 1):
            params = {
                "tool": "search_jobs",
                "search": "Kannapolis",
                "page": page,
                "pageSize": PAGE_SIZE,
            }
            try:
                resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except (requests.RequestException, ValueError) as e:
                print(f"  Request failed on page {page}: {e}")
                break

            jobs = data.get("results") or []
            if not jobs:
                break

            for job in jobs:
                job_id = _clean(job.get("requisitionId") or "")
                title = _clean(job.get("title") or "")
                if not job_id or not title or job_id in seen:
                    continue

                # "Kannapolis, NC, USA" -> city "Kannapolis", state "NC"
                parts = [p.strip() for p in (job.get("location") or "").split(",")]
                if not parts or parts[0].lower() != TARGET_CITY:
                    continue
                seen.add(job_id)

                location = ", ".join(p for p in parts[:2] if p)
                street = _street(job.get("description") or "")
                if street:
                    location = f"{location} — {street}"

                print(f"  {title}  |  {location}")
                results.append(Job(
                    title=title,
                    company="Food Lion",
                    location=location,
                    url=JOB_URL.format(job_id=quote(job_id)),
                    source="Food Lion",
                ))

            if page * PAGE_SIZE >= (data.get("totalCount") or 0):
                break

        print(f"  Found {len(results)} job(s).")
        return results
