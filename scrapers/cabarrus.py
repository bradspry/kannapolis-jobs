"""Cabarrus County government job listings via the NEOGOV/GovernmentJobs portal, paginated."""

import re

from playwright.sync_api import sync_playwright

from .base import BaseScraper, Job

LISTING_URL = "https://www.governmentjobs.com/careers/Cabarruscounty"
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


class CabarrusCountyScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Cabarrus County Government"

    @property
    def slug(self) -> str:
        return "cabarrus"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Walk every result page of the county careers listing and collect all jobs."""
        results: list[Job] = []
        seen: set[str] = set()

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

            print("  Loading Cabarrus County Government job listings...")
            page.goto(LISTING_URL, wait_until="networkidle", timeout=60000)

            try:
                page.wait_for_selector("li.list-item[data-job-id]", timeout=20000)
            except Exception:
                print("  No job listings found — Cabarrus County Government may have no open positions.")
                browser.close()
                return []

            page_num = 1
            while True:
                print(f"  Scraping page {page_num}...")
                for item in page.query_selector_all("li.list-item[data-job-id]"):
                    link = item.query_selector("a.item-details-link")
                    if not link:
                        continue

                    href = _abs(link.get_attribute("href") or "")
                    if not href or href in seen:
                        continue

                    title      = _clean(link.inner_text())
                    department = _clean(link.get_attribute("data-department-name") or "")
                    location   = f"Cabarrus County Government, NC — {department}" if department else "Cabarrus County Government, NC"

                    seen.add(href)
                    print(f"  {title}  |  {location}")
                    results.append(Job(
                        title=title,
                        company="Cabarrus County Government",
                        location=location,
                        url=href,
                        source="Cabarrus County Government",
                    ))

                # li.PagedList-skipToNext is absent or disabled when on the last page
                next_li = page.query_selector("li.PagedList-skipToNext")
                if not next_li or "disabled" in (next_li.get_attribute("class") or ""):
                    break

                page_num += 1
                page.goto(f"{LISTING_URL}?page={page_num}", wait_until="networkidle", timeout=60000)
                page.wait_for_selector("li.list-item[data-job-id]", timeout=20000)

            print(f"  Found {len(results)} job(s).")
            browser.close()

        return results
