"""Momentec job listings via their Paycom careers page, filtered to Kannapolis."""

import re

from playwright.sync_api import sync_playwright

from .base import BaseScraper, Job

LISTING_URL = (
    "https://www.paycomonline.net/v4/ats/web.php/portal/"
    "666553572663EC7F7F3472C2CF94B117/career-page"
)
BASE_URL = "https://www.paycomonline.net"


def _clean(text: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", text or "").strip()


class MomentecScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Momentec"

    @property
    def slug(self) -> str:
        return "momentec"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Load the careers page and keep only listings whose location mentions Kannapolis."""
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

            print("  Loading Momentec job listings...")
            page.goto(LISTING_URL, wait_until="networkidle", timeout=60000)

            try:
                page.wait_for_selector("a[href*='/jobs/']", timeout=20000)
            except Exception:
                print("  No job listings found — Momentec may have no open positions.")
                browser.close()
                return []

            seen: set[str] = set()
            for card in page.query_selector_all("a[href*='/jobs/']"):
                href = card.get_attribute("href") or ""
                if not href or href in seen:
                    continue
                url = BASE_URL + href if href.startswith("/") else href

                title_el = card.query_selector("h2[data-testid='typography']")
                if not title_el:
                    continue
                title = _clean(title_el.inner_text())
                if not title:
                    continue

                # Location p has font-weight:600; job-type badges use font-weight:normal/inherit
                location = ""
                for loc_el in card.query_selector_all("p[data-testid='typography']"):
                    style = loc_el.get_attribute("style") or ""
                    if "font-weight: 600" in style or "font-weight:600" in style:
                        location = _clean(loc_el.inner_text())
                        break

                if "kannapolis" not in location.lower():
                    continue

                seen.add(href)
                print(f"  {title}  |  {location}")
                results.append(Job(
                    title=title,
                    company="Momentec",
                    location=location,
                    url=url,
                    source="Momentec",
                ))

            print(f"  Found {len(results)} job(s).")
            browser.close()

        return results
