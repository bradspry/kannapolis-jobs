"""Rowan County Government job listings via the Tyler Portico public positions API."""

from urllib.parse import quote

import requests

from .base import BaseScraper, Job

API_URL  = "https://rowancountync.tylerportico.com/tess/citizen/api/Positions"
BASE_URL = "https://rowancountync.tylerportico.com/tess/citizen/jobs/job-list"


class RowanCountyGovernmentScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Rowan County Government"

    @property
    def slug(self) -> str:
        return "rowancounty"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Call the positions API and return entries matching the optional keyword filter."""
        print("  Fetching Rowan County Government job listings...")
        resp = requests.get(API_URL, headers={"Accept": "application/json"}, timeout=30)
        resp.raise_for_status()

        positions = resp.json()
        kw = keyword.lower()
        results: list[Job] = []

        for pos in positions:
            title = (pos.get("title") or "").strip()
            if not title:
                continue
            if kw and kw not in title.lower():
                continue

            job_id     = pos.get("id") or pos.get("code") or ""
            url        = f"{BASE_URL}/{quote(job_id, safe='')}" if job_id else BASE_URL
            department = (pos.get("locationDescription") or "").strip()
            location   = f"Rowan County, NC — {department}" if department else "Rowan County, NC"

            print(f"  {title}  |  {location}")
            results.append(Job(
                title=title,
                company="Rowan County Government",
                location=location,
                url=url,
                source="Rowan County Government",
            ))

        print(f"  Found {len(results)} job(s).")
        return results
