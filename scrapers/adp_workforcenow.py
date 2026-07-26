"""Shared client for ADP WorkforceNow's public career-site staffing API.

Any employer whose "Careers" page links to workforcenow.adp.com/mascsr/.../recruitment.html
exposes the same public JSON API — subclass ADPWorkforceNowScraper with that
employer's cid/ccId to add it as a source.
"""

import re

import requests

from .base import BaseScraper, Job

API_URL = "https://workforcenow.adp.com/mascsr/default/careercenter/public/events/staffing/v1/job-requisitions"
DETAIL_URL = (
    "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html"
    "?cid={cid}&ccId={ccid}&lang=en_US&source=EN&jobId={job_id}"
)


def _clean(text: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", text or "").strip()


def _address(req: dict) -> dict:
    """The structured address of the first requisition location, if any."""
    locs = req.get("requisitionLocations") or []
    return (locs[0].get("address") or {}) if locs else {}


def _location(req: dict) -> str:
    """Prefer the structured city/state address; fall back to the free-text location name."""
    addr  = _address(req)
    city  = addr.get("cityName")
    state = (addr.get("countrySubdivisionLevel1") or {}).get("codeValue")
    if city and state:
        return f"{city}, {state}"
    locs = req.get("requisitionLocations") or []
    return _clean((locs[0].get("nameCode") or {}).get("shortName") or "") if locs else ""


def _external_job_id(req: dict) -> str:
    """The public jobId query param — stored among the custom string fields, not the top-level itemID."""
    fields = (req.get("customFieldGroup") or {}).get("stringFields") or []
    for field in fields:
        if (field.get("nameCode") or {}).get("codeValue") == "ExternalJobID":
            return field.get("stringValue") or ""
    return ""


class ADPWorkforceNowScraper(BaseScraper):
    """Base class for an ADP WorkforceNow career site. Subclass and set cid/ccid/company."""

    cid: str
    ccid: str
    company: str
    default_location: str = ""
    target_cities: set[str] | None = None  # lowercased city names to keep; None keeps everything

    @property
    def name(self) -> str:
        return self.company

    def fetch(self, keyword: str = "") -> list[Job]:
        """Page through the ADP staffing API with $skip until every requisition has been seen."""
        results: list[Job] = []
        seen: set[str] = set()

        print(f"  Fetching {self.company} job listings...")
        skip = 0
        while True:
            params = {
                "cid": self.cid, "ccId": self.ccid, "lang": "en_US", "fcid": self.cid,
                "$skip": skip,
            }
            resp = requests.get(API_URL, params=params, timeout=15)
            if resp.status_code != 200:
                break

            data = resp.json()
            reqs = data.get("jobRequisitions") or []
            if not reqs:
                break

            new_count = 0
            for req in reqs:
                item_id = req.get("itemID") or ""
                if not item_id or item_id in seen:
                    continue
                seen.add(item_id)
                new_count += 1

                if self.target_cities is not None:
                    city = (_address(req).get("cityName") or "").strip().lower()
                    if city not in self.target_cities:
                        continue

                title    = _clean(req.get("requisitionTitle") or "")
                location = _location(req)
                job_id   = _external_job_id(req)
                if not title or not job_id:
                    continue

                url = DETAIL_URL.format(cid=self.cid, ccid=self.ccid, job_id=job_id)
                print(f"  {title}  |  {location or '(no location)'}")
                results.append(Job(
                    title=title,
                    company=self.company,
                    location=location or self.default_location,
                    url=url,
                    source=self.company,
                ))

            total = (data.get("meta") or {}).get("totalNumber", 0)
            skip += len(reqs)
            if new_count == 0 or skip >= total:
                break

        print(f"  Found {len(results)} job(s).")
        return results
