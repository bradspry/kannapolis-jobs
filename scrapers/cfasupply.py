"""Chick-fil-A Supply job listings from their iCIMS career portal.

The portal's init script redirects both plain requests and normal headless
navigation before the job HTML is reachable, so this module intercepts the
search response in-flight and parses the raw HTML instead of the rendered DOM.
"""

import re

from playwright.sync_api import sync_playwright

from .base import BaseScraper, Job

LISTING_URL = "https://careers-cfasupply.icims.com/jobs/search?ss=1&searchKeyword=kannapolis&in_iframe=1"


def _clean(text: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", text or "").strip()


def _strip_tags(html: str) -> str:
    """Remove HTML tags, leaving plain text."""
    return re.sub(r"<[^>]+>", "", html)


def _parse_jobs(html: str) -> list[dict]:
    """
    Split on each card opening tag instead of trying to match a closing </li>,
    which would stop at the first nested </li> inside the card.
    """
    jobs = []
    seen: set[str] = set()

    segments = html.split('<li class="iCIMS_JobCardItem">')
    for segment in segments[1:]:   # first segment is content before the first card
        url_m = re.search(
            r'href="(https://careers-cfasupply\.icims\.com/jobs/\d+/[^"/?]+/job)',
            segment
        )
        if not url_m or url_m.group(1) in seen:
            continue
        url = url_m.group(1)

        title_m = re.search(r"<h3[^>]*>(.*?)</h3>", segment, re.DOTALL)
        title = _clean(_strip_tags(title_m.group(1))) if title_m else ""
        if not title:
            continue

        location = "Kannapolis, NC"
        loc_m = re.search(
            r"Work Location.*?<dd[^>]*>.*?<span[^>]*>(.*?)</span>",
            segment, re.DOTALL
        )
        if loc_m:
            location = _clean(_strip_tags(loc_m.group(1)))

        seen.add(url)
        jobs.append({"title": title, "url": url, "location": location})

    return jobs


class CFASupplyScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Chick-fil-A Supply"

    @property
    def slug(self) -> str:
        return "cfasupply"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Capture the search response's raw HTML via route interception and parse job cards from it."""
        captured: dict[str, str | None] = {"html": None}

        def intercept(route, request):
            """Fetch the response ourselves, capture its body, then serve it to the page."""
            try:
                response = route.fetch()
                html = response.body().decode("utf-8", errors="replace")
                if "iCIMS_JobCardItem" in html and captured["html"] is None:
                    captured["html"] = html
                route.fulfill(response=response)
            except Exception:
                route.continue_()

        print("  Fetching Chick-fil-A Supply job listings...")
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            page = context.new_page()

            # Intercept only the iCIMS job-search URL to capture raw HTML
            page.route("**/jobs/search*in_iframe*", intercept)

            try:
                page.goto(LISTING_URL, wait_until="commit", timeout=60000)
            except Exception:
                pass  # Redirect/abort is expected after HTML is served

            browser.close()

        if not captured["html"]:
            print("  Could not capture job listing HTML.")
            return []

        jobs = _parse_jobs(captured["html"])
        results = []
        for job in jobs:
            print(f"  {job['title']}  |  {job['location']}")
            results.append(Job(
                title=job["title"],
                company="Chick-fil-A Supply",
                location=job["location"],
                url=job["url"],
                source="Chick-fil-A Supply",
            ))

        print(f"  Found {len(results)} job(s).")
        return results
