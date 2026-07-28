"""Macy's job listings via the Oracle Recruiting Cloud public REST API, filtered to China Grove, NC.

The given URL is a 25-mile radius search around Landis, NC, so raw results
also include Charlotte-area postings — keep only requisitions whose
PrimaryLocation is exactly China Grove, NC.
"""

import re

import requests

from .base import BaseScraper, Job

BASE_URL = "https://ebwh.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001"
API_URL = "https://ebwh.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
LOCATION_ID = "300000002935637"
TARGET_LOCATION = "china grove, nc, united states"
PAGE_SIZE = 25

HEADERS = {"Accept": "application/json"}


def _clean(text: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", text or "").strip()


class MacysScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Macy's"

    @property
    def slug(self) -> str:
        return "macys"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Page through the Oracle recruitingCEJobRequisitions API, keeping only China Grove postings."""
        results: list[Job] = []
        seen: set[str] = set()

        print("  Fetching Macy's job listings...")
        offset = 0
        total = None
        while total is None or offset < total:
            finder = (
                f"findReqs;siteNumber=CX_1001,limit={PAGE_SIZE},offset={offset},"
                f"locationId={LOCATION_ID},radius=25,radiusUnit=MI,sortBy=POSTING_DATES_DESC"
            )
            if keyword:
                finder += f",keyword={keyword}"

            resp = requests.get(
                API_URL,
                params={"onlyData": "true", "expand": "requisitionList", "finder": finder},
                headers=HEADERS,
                timeout=15,
            )
            if resp.status_code != 200:
                break

            item = (resp.json().get("items") or [None])[0]
            if not item:
                break

            total = item.get("TotalJobsCount", 0)
            reqs = item.get("requisitionList") or []
            if not reqs:
                break

            for req in reqs:
                req_id = req.get("Id") or ""
                if not req_id or req_id in seen:
                    continue
                seen.add(req_id)

                title = _clean(req.get("Title") or "")
                location = _clean(req.get("PrimaryLocation") or "")
                if not title or location.lower() != TARGET_LOCATION:
                    continue

                url = f"{BASE_URL}/job/{req_id}"
                print(f"  {title}  |  {location}")
                results.append(Job(
                    title=title,
                    company="Macy's",
                    location=location,
                    url=url,
                    source="Macy's",
                ))

            offset += len(reqs)

        print(f"  Found {len(results)} job(s).")
        return results
