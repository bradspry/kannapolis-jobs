"""Standard Process job listings via their UltiPro job board search API, geo-filtered to the Kannapolis area."""

import requests

from .base import BaseScraper, Job

BASE_URL = "https://recruiting.ultipro.com/STA1020/JobBoard/1df7fbd1-d8cf-85ff-efe2-77bf30267012"
SEARCH_URL = f"{BASE_URL}/JobBoardView/LoadSearchResults"

# Bounding box centered on Kannapolis, NC (~12-mile radius)
PAYLOAD = {
    "opportunitySearch": {
        "Top": 50, "Skip": 0, "QueryString": "",
        "OrderBy": [{"Value": "distance", "PropertyName": "Distance", "Ascending": True}],
        "Filters": [
            {"t": "TermsSearchFilterDto", "fieldName": 4, "extra": None, "values": []},
            {"t": "TermsSearchFilterDto", "fieldName": 5, "extra": None, "values": []},
            {"t": "TermsSearchFilterDto", "fieldName": 6, "extra": None, "values": []},
            {"t": "TermsSearchFilterDto", "fieldName": 37, "extra": None, "values": []},
        ],
        "Coordinates": {"Longitude": -80.609746, "Latitude": 35.474701},
        "Extent": {
            "Min": {"Longitude": -80.805746, "Latitude": 35.670701},
            "Max": {"Longitude": -80.413746, "Latitude": 35.278701},
        },
        "ProximitySearchType": 2,
    },
    "matchCriteria": {
        "PreferredJobs": [], "Educations": [], "LicenseAndCertifications": [],
        "Skills": [], "hasNoLicenses": False, "SkippedSkills": [],
    },
}


class StandardProcessScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Standard Process"

    @property
    def slug(self) -> str:
        return "standardprocess"

    def fetch(self, keyword: str = "") -> list[Job]:
        """POST the proximity search payload and return opportunities matching the optional keyword filter."""
        print("  Fetching Standard Process jobs (Kannapolis area)...")
        resp = requests.post(SEARCH_URL, json=PAYLOAD, timeout=30)
        resp.raise_for_status()

        opportunities = resp.json().get("opportunities", [])
        kw = keyword.lower()
        results: list[Job] = []

        for opp in opportunities:
            title = (opp.get("Title") or "").strip()
            if not title:
                continue

            if kw and kw not in title.lower():
                continue

            opp_id = opp.get("Id", "")
            url = f"{BASE_URL}/OpportunityDetail?opportunityId={opp_id}"

            locations = opp.get("Locations") or []
            if locations:
                addr = locations[0].get("Address", {})
                city = addr.get("City", "")
                state = (addr.get("State") or {}).get("Code", "")
                location = f"{city}, {state}" if city and state else "Kannapolis, NC"
            else:
                location = "Kannapolis, NC"

            print(f"  {title}")
            results.append(Job(
                title=title,
                company="Standard Process",
                location=location,
                url=url,
                source="Standard Process",
            ))

        print(f"  Found {len(results)} job(s).")
        return results
