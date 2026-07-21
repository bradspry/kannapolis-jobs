"""Gordon Food Service job listings via their Workday careers site, filtered to the target city."""

import re

from playwright.sync_api import sync_playwright

from .base import BaseScraper, Job

LISTING_URL = (
    "https://gfs.wd5.myworkdayjobs.com/en-US/usjobs-gen-gfs/jobs"
    "?locationCountry=bc33aa3152ec42d4995f4791a106ed09"
    "&locationRegionStateProvince=1486a0a4a8464c3b9ec482d4038deb99"
)
BASE_URL = "https://gfs.wd5.myworkdayjobs.com"
TARGET_CITY = "concord"


def _clean(text: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", text or "").strip()


class GFSScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Gordon Food Service"

    @property
    def slug(self) -> str:
        return "gfs"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Load the Workday job list and keep only listings whose location matches TARGET_CITY."""
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

            print("  Loading Gordon Food Service job listings...")
            page.goto(LISTING_URL, wait_until="networkidle", timeout=60000)

            try:
                page.wait_for_selector("a[data-automation-id='jobTitle']", timeout=20000)
            except Exception:
                print("  No job listings found.")
                browser.close()
                return []

            seen: set[str] = set()
            for link in page.query_selector_all("a[data-automation-id='jobTitle']"):
                href = link.get_attribute("href") or ""
                if not href or href in seen:
                    continue

                title = _clean(link.inner_text())
                if not title:
                    continue

                # Location is in the sibling dd inside [data-automation-id='locations']
                location = ""
                try:
                    card = link.evaluate_handle(
                        "el => el.closest('li') || el.closest('[class*=\"css\"]').parentElement"
                    )
                    if card:
                        loc_dd = card.query_selector("[data-automation-id='locations'] dd")
                        if loc_dd:
                            location = _clean(loc_dd.inner_text())
                except Exception:
                    pass

                if TARGET_CITY not in location.lower():
                    continue

                # Strip filter query params from the URL
                clean_href = href.split("?")[0]
                url = BASE_URL + clean_href if clean_href.startswith("/") else clean_href

                seen.add(href)
                print(f"  {title}  |  {location}")
                results.append(Job(
                    title=title,
                    company="Gordon Food Service",
                    location=location,
                    url=url,
                    source="Gordon Food Service",
                ))

            print(f"  Found {len(results)} job(s).")
            browser.close()

        return results
