"""City of Kannapolis government job listings via the NEOGOV/GovernmentJobs portal."""

import re
import time

from playwright.sync_api import sync_playwright

from .base import BaseScraper, Job

LISTING_URL = "https://www.governmentjobs.com/careers/kannapolis/"
BASE_URL    = "https://www.governmentjobs.com"


def _clean(text: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", text or "").strip()


def _abs(href: str) -> str:
    """Resolve a possibly-relative href against BASE_URL."""
    if not href:
        return ""
    if href.startswith("http"):
        return href
    return BASE_URL + href


class CityOfKannapolisScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "City of Kannapolis"

    @property
    def slug(self) -> str:
        return "city"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Load the city careers page and collect every listed job."""
        results: list[Job] = []

        with sync_playwright() as p:
            print("  Launching browser...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()

            print("  Loading City of Kannapolis job listings...")
            page.goto(LISTING_URL, wait_until="networkidle", timeout=60000)

            try:
                page.wait_for_selector("li.list-item[data-job-id]", timeout=20000)
            except Exception:
                print("  No job listings found — city may have no open positions.")
                browser.close()
                return []

            seen: set[str] = set()
            for item in page.query_selector_all("li.list-item[data-job-id]"):
                link = item.query_selector("a.item-details-link")
                if not link:
                    continue

                href  = _abs(link.get_attribute("href") or "")
                if not href or href in seen:
                    continue

                title      = _clean(link.inner_text())
                department = _clean(link.get_attribute("data-department-name") or "")
                location   = f"Kannapolis, NC — {department}" if department else "Kannapolis, NC"

                seen.add(href)
                print(f"  {title}  |  {location}")
                results.append(Job(
                    title=title,
                    company="City of Kannapolis",
                    location=location,
                    url=href,
                    source="City of Kannapolis",
                ))

            print(f"  Found {len(results)} job(s).")
            browser.close()

        return results
