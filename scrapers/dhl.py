"""DHL Careers scraper: crawls search-result pages, then visits each job's detail
page to confirm its address falls within the target Kannapolis-area cities."""

import re
import time

from playwright.sync_api import sync_playwright

from .base import BaseScraper, Job

URL = (
    "https://careers.dhl.com/global/en/search-results"
    "?keywords=&p=ChIJPW97u5QIVIgRHdxKah_1bak&location=Kannapolis,%20NC,%20USA"
)

TARGET_CITIES = {"kannapolis", "landis", "china grove"}

SITE_NICKNAMES = {
    "1894 old beatty ford rd": "85 Overlook",
    "1400 armstrong street":   "Landis Ridge",
}


def _location_matches(text: str) -> bool:
    """True if the text mentions one of the target Kannapolis-area cities."""
    if not text:
        return False
    t = text.lower()
    return any(city in t for city in TARGET_CITIES)


def _format_address(full_address: str) -> str:
    """Shorten a full address to "street, city" and prefix a known site nickname if any."""
    parts = [p.strip() for p in full_address.split(",")]
    short = f"{parts[0]}, {parts[1]}" if len(parts) >= 2 else full_address
    nickname = SITE_NICKNAMES.get(parts[0].lower(), "")
    return f"({nickname}) {short}" if nickname else short


def _extract_jobs_from_page(page) -> list[dict]:
    """Collect title/url/list-page-location for every job link on the current search-results page."""
    jobs = []
    seen = set()
    for link in page.query_selector_all("a[href*='/job/']"):
        href = link.get_attribute("href") or ""
        if not href or href in seen:
            continue
        if not href.startswith("http"):
            href = "https://careers.dhl.com" + href

        title = (link.inner_text() or "").strip()
        if not title:
            try:
                el = link.query_selector("h3, h2, [class*='title']")
                title = el.inner_text().strip() if el else ""
            except Exception:
                title = ""
        title = re.sub(r"\s+", " ", title).strip()
        if not title:
            continue

        list_location = ""
        try:
            card = link.evaluate_handle(
                "el => el.closest('li, article, [class*=\"job-item\"], [class*=\"job-card\"]')"
            )
            if card:
                loc_el = card.query_selector("span.job-location")
                if loc_el:
                    list_location = re.sub(r"\s+", " ", loc_el.inner_text() or "").strip()
                    list_location = re.sub(r"^Location\s*", "", list_location, flags=re.IGNORECASE).strip()
        except Exception:
            pass

        seen.add(href)
        jobs.append({"title": title, "url": href, "list_location": list_location})
    return jobs


def _fetch_job_address(page, url: str) -> str:
    """Visit a job's detail page and read its full posted address."""
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_selector("span.locationDisplay", timeout=15000)
        el = page.query_selector("span.locationDisplay")
        if el:
            return re.sub(r"\s+", " ", el.inner_text() or "").strip()
    except Exception:
        pass
    return ""


class DHLScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "DHL"

    @property
    def slug(self) -> str:
        return "dhl"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Crawl all search-result pages for candidates, then confirm each one's address via its detail page."""
        candidate_jobs = []

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

            print("  Loading DHL search results...")
            page.goto(URL, wait_until="networkidle", timeout=60000)
            try:
                page.wait_for_selector("a[href*='/job/']", timeout=20000)
            except Exception:
                print("  Job selector timed out — page may be slow or structure changed.")

            page_urls = [URL]
            try:
                for link in page.query_selector_all("a[data-ph-at-id='pagination-page-number-link']"):
                    href = link.get_attribute("href") or ""
                    if href and href not in page_urls:
                        if not href.startswith("http"):
                            href = "https://careers.dhl.com" + href
                        page_urls.append(href)
            except Exception as e:
                print(f"  Could not read pagination: {e}")

            print(f"  Found {len(page_urls)} search page(s).")

            all_seen: set[str] = set()
            for page_num, page_url in enumerate(page_urls, 1):
                if page_num > 1:
                    print(f"  Loading search page {page_num}...")
                    page.goto(page_url, wait_until="networkidle", timeout=60000)
                    try:
                        page.wait_for_selector("a[href*='/job/']", timeout=15000)
                    except Exception:
                        print(f"    No jobs on page {page_num}, skipping.")
                        continue

                print(f"  Scanning page {page_num}...")
                jobs = _extract_jobs_from_page(page)
                new_jobs = [j for j in jobs if j["url"] not in all_seen]
                all_seen.update(j["url"] for j in new_jobs)
                candidate_jobs.extend(new_jobs)
                print(f"    {len(new_jobs)} new job(s).")

                located = [j for j in new_jobs if j["list_location"]]
                if located and not any(_location_matches(j["list_location"]) for j in located):
                    print(f"    No target-city jobs on page {page_num} — stopping.")
                    break

            print(f"\n  Fetching full address for {len(candidate_jobs)} job(s)...")
            matched_raw = []
            consecutive_misses = 0
            MISS_LIMIT = 3

            for i, job in enumerate(candidate_jobs, 1):
                print(f"  [{i}/{len(candidate_jobs)}] {job['title']}")
                address = _fetch_job_address(page, job["url"])
                print(f"    Address: {address or '(not found)'}")
                if _location_matches(address):
                    job["address"] = address
                    matched_raw.append(job)
                    consecutive_misses = 0
                else:
                    consecutive_misses += 1
                    if consecutive_misses >= MISS_LIMIT:
                        print(f"    {MISS_LIMIT} consecutive misses — stopping.")
                        break
                time.sleep(0.5)

            browser.close()

        return [
            Job(
                title=job["title"],
                company="DHL",
                location=_format_address(job["address"]),
                url=job["url"],
                source="DHL Careers",
            )
            for job in matched_raw
        ]
