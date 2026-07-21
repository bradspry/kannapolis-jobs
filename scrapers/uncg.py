"""UNC Greensboro job postings via their public Atom feed, filtered to Kannapolis-area content."""

import html
import xml.etree.ElementTree as ET

import requests

from .base import BaseScraper, Job

FEED_URL = "https://spartantalent.uncg.edu/postings/all_jobs.atom"
NS = {"atom": "http://www.w3.org/2005/Atom"}


class UNCGScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "UNC Greensboro"

    @property
    def slug(self) -> str:
        return "uncg"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Parse the Atom feed, keep only entries mentioning Kannapolis, and apply the optional keyword filter."""
        print("  Fetching UNC Greensboro Atom feed...")
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

            author_el = entry.find("atom:author/atom:name", NS)
            author = (author_el.text or "").strip() if author_el is not None else ""

            if not any("kannapolis" in s.lower() for s in (title, content, author)):
                continue

            if kw and kw not in title.lower():
                continue

            link_el = entry.find("atom:link[@rel='alternate']", NS)
            url = link_el.attrib.get("href", "") if link_el is not None else ""

            print(f"  {title}")
            results.append(Job(
                title=title,
                company="UNC Greensboro",
                location="Kannapolis, NC",
                url=url,
                source="UNC Greensboro",
            ))

        print(f"  Found {len(results)} job(s).")
        return results
