"""Rowan-Cabarrus Community College job postings via their public Atom feed."""

import xml.etree.ElementTree as ET

import requests

from .base import BaseScraper, Job

FEED_URL = "https://rcccjobs.com/postings/all_jobs.atom"
NS = {"atom": "http://www.w3.org/2005/Atom"}


class RCCCScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "RCCC"

    @property
    def slug(self) -> str:
        return "rccc"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Parse the Atom feed and return entries matching the optional keyword filter."""
        print("  Fetching RCCC Atom feed...")
        resp = requests.get(FEED_URL, timeout=30)
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        kw = keyword.lower()
        results: list[Job] = []

        for entry in root.findall("atom:entry", NS):
            title_el = entry.find("atom:title", NS)
            title = (title_el.text or "").strip() if title_el is not None else ""
            if not title:
                continue

            if kw and kw not in title.lower():
                continue

            link_el = entry.find("atom:link[@rel='alternate']", NS)
            url = link_el.attrib.get("href", "") if link_el is not None else ""

            print(f"  {title}")
            results.append(Job(
                title=title,
                company="RCCC",
                location="Salisbury, NC",
                url=url,
                source="RCCC",
            ))

        print(f"  Found {len(results)} job(s).")
        return results
