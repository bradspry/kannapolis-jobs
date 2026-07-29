"""Shared client for ADP's "myjobs" Recruiting Cloud career-site platform.

Any employer whose "Careers" page is hosted at myjobs.adp.com/{domain}
exposes the same public JSON API — subclass ADPMyJobsScraper with that
employer's domain to add it as a source.

The site's public career-site config endpoint hands back a short-lived
anonymous `myJobsToken` (not a real login) that authorizes the job-search
API; we fetch that token fresh on every run rather than trying to cache it.
"""

import re

import requests

from .base import BaseScraper, Job

CONFIG_URL = "https://myjobs.adp.com/public/staffing/v1/career-site/{domain}"
SEARCH_URL = "https://my.adp.com/myadp_prefix/mycareer/public/staffing/v1/job-requisitions/apply-custom-filters"
DETAIL_URL = "https://myjobs.adp.com/{domain}/cx/job/{reqId}"
SELECT_FIELDS = "reqId,jobTitle,publishedJobTitle,requisitionLocations"
PAGE_SIZE = 50

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


def _primary_address(req: dict) -> dict:
    """The structured address of the primary posted location, if any."""
    locs = req.get("requisitionLocations") or []
    return (locs[0].get("address") or {}) if locs else {}


def _location(req: dict) -> str:
    """City/state from the primary posted location."""
    addr = _primary_address(req)
    city, state = addr.get("cityName"), (addr.get("countrySubdivisionLevel1") or {}).get("codeValue")
    if city and state:
        return f"{city}, {state}"
    return city or state or ""


class ADPMyJobsScraper(BaseScraper):
    """Base class for an ADP myjobs career site. Subclass and set domain/company."""

    domain: str
    company: str
    target_locations: set[tuple[str, str]] | None = None  # lowercased (city, state) pairs; None keeps everything

    @property
    def name(self) -> str:
        return self.company

    def fetch(self, keyword: str = "") -> list[Job]:
        """Page through the ADP myjobs search API with $skip until every requisition has been seen."""
        results: list[Job] = []

        print(f"  Fetching {self.company} job listings...")
        cfg_resp = requests.get(CONFIG_URL.format(domain=self.domain), headers=HEADERS, timeout=15)
        if cfg_resp.status_code != 200:
            print(f"  Career-site config request failed: HTTP {cfg_resp.status_code}")
            return results

        token = cfg_resp.json().get("myJobsToken")
        if not token:
            print("  No myJobsToken found in career-site config.")
            return results

        search_headers = {**HEADERS, "myJobsToken": token, "rolecode": "manager"}

        skip = 0
        total = None
        while total is None or skip < total:
            params = {
                "$select": SELECT_FIELDS,
                "$top": PAGE_SIZE,
                "$skip": skip,
                "$filter": "",
                "tz": "America/New_York",
            }
            resp = requests.get(SEARCH_URL, params=params, headers=search_headers, timeout=15)
            if resp.status_code != 200:
                break

            data = resp.json()
            total = data.get("count", 0)
            reqs = data.get("jobRequisitions") or []
            if not reqs:
                break

            for req in reqs:
                title = _clean(req.get("publishedJobTitle") or req.get("jobTitle") or "")
                req_id = req.get("reqId") or ""
                if not title or not req_id:
                    continue

                addr = _primary_address(req)
                city = (addr.get("cityName") or "").strip().lower()
                state = ((addr.get("countrySubdivisionLevel1") or {}).get("codeValue") or "").strip().lower()
                if self.target_locations is not None and (city, state) not in self.target_locations:
                    continue

                location = _location(req)
                url = DETAIL_URL.format(domain=self.domain, reqId=req_id)
                print(f"  {title}  |  {location or '(no location)'}")
                results.append(Job(
                    title=title,
                    company=self.company,
                    location=location,
                    url=url,
                    source=self.company,
                ))

            skip += len(reqs)

        print(f"  Found {len(results)} job(s).")
        return results
