"""Shoe Show job listings via their careers site's zip-code radius search, paginated."""

import re
import time

from playwright.sync_api import sync_playwright

from .base import BaseScraper, Job

LISTING_URL = "https://careers.shoeshow.com/careers"
BASE_URL    = "https://careers.shoeshow.com"
ZIP_CODE    = "28083"
DISTANCE    = "10 Miles"


def _clean(text: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", text or "").strip()


class ShoeShowScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Shoe Show"

    @property
    def slug(self) -> str:
        return "shoeshow"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Run the site's zip-code radius search, then page through and collect NC results."""
        results: list[Job] = []

        with sync_playwright() as p:
            print("  Launching browser...")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )

            print("  Loading Shoe Show careers page...")
            page.goto(LISTING_URL, wait_until="networkidle", timeout=60000)
            time.sleep(1)

            page.fill("#filters_ZipCode", ZIP_CODE)
            page.select_option("#filters_Distance", label=DISTANCE)
            page.click("#searchBtn")
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            try:
                page.wait_for_selector(".job_Listing", timeout=15000)
            except Exception:
                print("  No job listings found.")
                browser.close()
                return []

            seen: set[str] = set()
            page_num = 1

            while True:
                print(f"  Scanning page {page_num}...")
                for card in page.query_selector_all(".job_Listing"):
                    job_id = card.get_attribute("data-id") or ""
                    if not job_id or job_id in seen:
                        continue

                    title_el = card.query_selector("h2")
                    title = _clean(title_el.inner_text()) if title_el else ""
                    if not title:
                        continue

                    loc_el = card.query_selector("p.bold")
                    location = _clean(loc_el.inner_text()) if loc_el else "Kannapolis, NC"

                    if ", NC" not in location.upper():
                        continue

                    url = f"{BASE_URL}/job/{job_id}"

                    seen.add(job_id)
                    print(f"  {title}  |  {location}")
                    results.append(Job(
                        title=title,
                        company="Shoe Show",
                        location=location,
                        url=url,
                        source="Shoe Show",
                    ))

                # Check if Next page is available (hidden when on last page)
                next_span = page.query_selector("#PageNext")
                if not next_span:
                    break
                next_class = next_span.get_attribute("class") or ""
                if "displayHidden" in next_class:
                    break

                next_link = next_span.query_selector("a")
                if not next_link:
                    break

                page_num += 1
                next_link.click()
                page.wait_for_load_state("networkidle")
                time.sleep(1)

            print(f"  Found {len(results)} job(s).")
            browser.close()

        return results
