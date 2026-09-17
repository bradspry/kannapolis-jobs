"""Lowes Foods job listings via the Appcast landing-page API, filtered to Kannapolis, NC.

The careers site (apply.appcast.io/l/lowes-foods-careers) is an Angular app
whose job list is backed by a plain JSON endpoint,
`/api/tools/landing_page/{slug}/jobs`. Server-rendered HTML only ever carries
the first page, so we call that endpoint directly and page through it.

The search is a radius search around Kannapolis, so results also cover the
Charlotte metro and even across the SC line — keep only postings whose
location city is Kannapolis itself. The wide RADIUS is deliberate: filtering
on the city is what makes the result exact, and a generous radius means a
Kannapolis store sitting off Appcast's geocoded centroid is still seen.

The endpoint takes a `keyword`, but it only re-ranks the full result set
rather than narrowing it, so this module ignores keywords and always returns
every current Kannapolis posting.
"""

import re

import requests

from .base import BaseScraper, Job

SLUG = "lowes-foods-careers"
API_URL = f"https://apply.appcast.io/api/tools/landing_page/{SLUG}/jobs"
JOB_URL = f"https://apply.appcast.io/l/{SLUG}/job/{{job_id}}"
LOCATION = "Kannapolis, NC, USA"
RADIUS = "40miles"
TARGET_CITY = "kannapolis"
PAGE_SIZE = 12
MAX_PAGES = 25

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


def _strip_location_suffix(title: str, city: str, state: str) -> str:
    """Drop a trailing "<City> <ST>" from a job title.

    Lowes Foods tacks the store's city and state onto most titles ("Deli Clerk
    PT Kannapolis NC"), but not all of them ("Lead Grocery Stocker FT"). The
    Location line already says where the job is, so removing the suffix keeps
    titles consistent with each other and with the site's own job pages, which
    show the bare title.
    """
    if not city or not state:
        return title
    stripped = re.sub(
        rf"[\s,/-]*{re.escape(city)}[\s,]*{re.escape(state)}\s*$",
        "", title, flags=re.IGNORECASE,
    ).strip()
    return stripped or title


class LowesFoodsScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Lowes Foods"

    @property
    def slug(self) -> str:
        return "lowesfoods"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Page through the Appcast jobs API, keeping only Kannapolis postings."""
        results: list[Job] = []
        seen: set[str] = set()

        print("  Fetching Lowes Foods job listings...")
        for page in range(MAX_PAGES):
            params = {
                "page": page,
                "jobs_per_page": PAGE_SIZE,
                "radius": RADIUS,
                "plain_text_body": "false",
                "location": LOCATION,
                "keyword": "",
                "is_user_input_location": "false",
                "country_code": "",
                "usps_code": "",
            }
            resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                print(f"  Request failed on page {page + 1}: HTTP {resp.status_code}")
                break

            data = resp.json()
            jobs = data.get("jobs") or []
            if not jobs:
                break

            for job in jobs:
                job_id = str(job.get("id") or "")
                if not job_id or job_id in seen:
                    continue

                loc = job.get("location") or {}
                city = _clean(loc.get("city") or "")
                if city.lower() != TARGET_CITY:
                    continue

                state = _clean(loc.get("state") or "")
                zip_code = _clean(loc.get("zip") or "")
                title = _strip_location_suffix(_clean(job.get("title") or ""), city, state)
                if not title:
                    continue

                location = ", ".join(p for p in (city, state) if p)
                if zip_code:
                    location = f"{location} {zip_code}".strip()

                seen.add(job_id)
                print(f"  {title}  |  {location}")
                results.append(Job(
                    title=title,
                    company="Lowes Foods",
                    location=location,
                    url=JOB_URL.format(job_id=job_id),
                    source="Lowes Foods",
                ))

            if page + 1 >= (data.get("pages_total") or 0):
                break

        print(f"  Found {len(results)} job(s).")
        return results
