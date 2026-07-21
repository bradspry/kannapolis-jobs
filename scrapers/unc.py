"""UNC Chapel Hill job postings via their public Atom feed, filtered to Kannapolis-area content."""

import html
import xml.etree.ElementTree as ET

import requests

from .base import BaseScraper, Job

FEED_URL = "https://unc.peopleadmin.com/postings/all_jobs.atom"
NS = {"atom": "http://www.w3.org/2005/Atom"}


class UNCScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "UNC"

    @property
    def slug(self) -> str:
        return "unc"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Parse the Atom feed, keep only entries mentioning Kannapolis, and apply the optional keyword filter."""
        print("  Fetching UNC Atom feed...")
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

            content_el = entry.find("atom:content", NS)
            content = html.unescape(content_el.text or "") if content_el is not None else ""

            if "kannapolis" not in content.lower():
                continue

            if kw and kw not in title.lower():
                continue

            link_el = entry.find("atom:link[@rel='alternate']", NS)
            url = link_el.attrib.get("href", "") if link_el is not None else ""

            print(f"  {title}")
            results.append(Job(
                title=title,
                company="UNC",
                location="Kannapolis, NC",
                url=url,
                source="UNC",
            ))

        print(f"  Found {len(results)} job(s).")
        return results
