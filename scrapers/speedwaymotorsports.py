"""Speedway Motorsports job listings via the ADP WorkforceNow public staffing API."""

import re

import requests

from .base import BaseScraper, Job

CID  = "d180c324-e784-463d-a355-61b3275338b9"
CCID = "19000101_000001"

API_URL    = "https://workforcenow.adp.com/mascsr/default/careercenter/public/events/staffing/v1/job-requisitions"
DETAIL_URL = (
    "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html"
    f"?cid={CID}&ccId={CCID}&lang=en_US&source=EN&jobId={{job_id}}"
)
PAGE_SIZE = 20
TARGET_CITIES = {"concord", "harrisburg"}


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


class SpeedwayMotorsportsScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Speedway Motorsports"

    @property
    def slug(self) -> str:
        return "speedway"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Page through the ADP staffing API with $skip until every requisition has been seen."""
        results: list[Job] = []
        seen: set[str] = set()

        print("  Fetching Speedway Motorsports job listings...")
        skip = 0
        while True:
            params = {
                "cid": CID, "ccId": CCID, "lang": "en_US", "fcid": CID,
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

                city = (_address(req).get("cityName") or "").strip().lower()
                if city not in TARGET_CITIES:
                    continue

                title    = _clean(req.get("requisitionTitle") or "")
                location = _location(req)
                job_id   = _external_job_id(req)
                if not title or not job_id:
                    continue

                url = DETAIL_URL.format(job_id=job_id)
                print(f"  {title}  |  {location or '(no location)'}")
                results.append(Job(
                    title=title,
                    company="Speedway Motorsports",
                    location=location or "Concord, NC",
                    url=url,
                    source="Speedway Motorsports",
                ))

            total = (data.get("meta") or {}).get("totalNumber", 0)
            skip += len(reqs)
            if new_count == 0 or skip >= total:
                break

        print(f"  Found {len(results)} job(s).")
        return results
