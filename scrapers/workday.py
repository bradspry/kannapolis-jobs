"""Shared client for Workday's public CXS career-site API.

Any employer whose "Careers" page is hosted at {tenant}.wd{n}.myworkdayjobs.com
exposes the same public JSON API at /wday/cxs/{tenant}/{site}/jobs — subclass
WorkdayScraper with that employer's host/tenant/site to add it as a source.
"""

import re

import requests

from .base import BaseScraper, Job


def _clean(text: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", text or "").strip()


class WorkdayScraper(BaseScraper):
    """Base class for a Workday career site. Subclass and set host/tenant/site/company."""

    host: str  # e.g. "monarch.wd5.myworkdayjobs.com"
    tenant: str  # e.g. "monarch"
    site: str  # e.g. "Monarch" (case-sensitive path segment)
    company: str
    location_ids: list[str] | None = None  # Workday location facet UUIDs to filter to; None keeps everything
    target_city_names: set[str] | None = None  # lowercased "City, ST" names used to resolve "N Locations" text
    page_size = 20

    @property
    def name(self) -> str:
        return self.company

    def _resolve_location(self, api_base: str, path: str, locations_text: str) -> str:
        """Turn vague "N Locations" text into actual city names via the job detail endpoint."""
        if not re.match(r"^\d+\s+Locations?$", locations_text, re.IGNORECASE):
            return locations_text

        try:
            resp = requests.get(api_base + path, timeout=15)
            resp.raise_for_status()
            info = resp.json().get("jobPostingInfo") or {}
        except Exception:
            return locations_text

        cities = [info.get("location")] + list(info.get("additionalLocations") or [])
        cities = [c for c in cities if c]
        if self.target_city_names is not None:
            cities = [c for c in cities if c.lower() in self.target_city_names]
        return "; ".join(cities) if cities else locations_text

    def fetch(self, keyword: str = "") -> list[Job]:
        """Page through the Workday CXS jobs API with offset until every posting has been seen."""
        results: list[Job] = []
        seen: set[str] = set()

        api_base = f"https://{self.host}/wday/cxs/{self.tenant}/{self.site}"
        api_url = f"{api_base}/jobs"
        detail_base = f"https://{self.host}/en-US/{self.site}"

        print(f"  Fetching {self.company} job listings...")
        offset = 0
        while True:
            body = {
                "appliedFacets": {},
                "limit": self.page_size,
                "offset": offset,
                "searchText": keyword or "",
            }
            if self.location_ids:
                body["appliedFacets"]["locations"] = self.location_ids

            resp = requests.post(api_url, json=body, timeout=15)
            if resp.status_code != 200:
                break

            data = resp.json()
            postings = data.get("jobPostings") or []
            if not postings:
                break

            new_count = 0
            for posting in postings:
                path = posting.get("externalPath") or ""
                if not path or path in seen:
                    continue
                seen.add(path)
                new_count += 1

                title = _clean(posting.get("title") or "")
                location = _clean(posting.get("locationsText") or "")
                if not title:
                    continue
                location = self._resolve_location(api_base, path, location)

                url = detail_base + path
                print(f"  {title}  |  {location or '(no location)'}")
                results.append(Job(
                    title=title,
                    company=self.company,
                    location=location,
                    url=url,
                    source=self.company,
                ))

            # Workday's "total" field is unreliable (has been observed to report 0
            # mid-pagination, and offsets past the real end wrap back to page 1),
            # so rely on page size and new-item count instead of trusting it.
            offset += len(postings)
            if new_count == 0 or len(postings) < self.page_size:
                break

        print(f"  Found {len(results)} job(s).")
        return results
