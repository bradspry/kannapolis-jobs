"""Kannapolis City Schools scraper for the AppliTrack/Frontline listing page."""

import re
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from playwright.sync_api import sync_playwright, Frame

from .base import BaseScraper, Job

LISTING_URL = "https://www.applitrack.com/kannapolis/onlineapp/default.aspx?all=1"
DETAIL_BASE = "https://www.applitrack.com/kannapolis/onlineapp/default.aspx"

# The listing page can still show jobs whose detail page was already closed;
# AppliTrack renders this text instead of the posting when that happens.
UNAVAILABLE_MARKER = "this vacancy is not available"


def _is_live(url: str) -> bool:
    """Check a detail page still has a posting behind it."""
    try:
        resp = requests.get(url, timeout=15)
        return UNAVAILABLE_MARKER not in resp.text.lower()
    except requests.RequestException:
        return True  # fail open — don't drop a job over a network hiccup


def _clean(text: str) -> str:
    """Collapse whitespace and trim."""
    return re.sub(r"\s+", " ", text or "").strip()


def _find_job_frame(page) -> Frame | None:
    """Poll all frames until one contains AppliTrackJobId links (up to 20 s)."""
    deadline = time.time() + 20
    while time.time() < deadline:
        for frame in page.frames:
            try:
                if frame.query_selector("a[href*='AppliTrackJobId']"):
                    return frame
            except Exception:
                pass
        time.sleep(0.5)
    return None


def _parse_listing(frame: Frame) -> list[dict]:
    """
    All jobs are on the single listing page.  Each job has two links:
      • 'Email To A Friend'  — href embeds "The position is {Title}."
      • 'Print Version'      — href embeds ApplitrackHardcodedURL?...&AppliTrackJobId=N&...

    Group both by job ID, extract title from the email link and the
    deep-link URL from the print link.
    """
    jobs: dict[str, dict] = {}

    for link in frame.query_selector_all("a[href*='AppliTrackJobId']"):
        href  = link.get_attribute("href") or ""
        id_m  = re.search(r"AppliTrackJobId=(\d+)", href)
        if not id_m:
            continue
        job_id = id_m.group(1)
        jobs.setdefault(job_id, {"title": "", "url": "", "location": ""})

        text = _clean(link.inner_text())

        if text == "Print Version":
            q_m = re.search(r"ApplitrackHardcodedURL(\?[^'\"]+)", href)
            if q_m:
                jobs[job_id]["url"] = DETAIL_BASE + q_m.group(1)
                # Try to find location text in the DOM near this link
                if not jobs[job_id]["location"]:
                    jobs[job_id]["location"] = _nearby_location(link)

        elif text == "Email To A Friend":
            t_m = re.search(r"The position is ([^.]+)\.", href)
            if t_m:
                jobs[job_id]["title"] = t_m.group(1).strip()

    return [j for j in jobs.values() if j["title"] and j["url"]]


def _nearby_location(link) -> str:
    """
    Walk up the DOM from the Print Version link looking for a
    'Location' label or school-name text.
    """
    js = r"""
    el => {
        for (let block = el.parentElement, depth = 0; block && depth < 8; block = block.parentElement, depth++) {
            let t = block.innerText || '';
            // AppliTrack often shows "Location: School Name"
            let m = t.match(/Location[:\s]+([^\n\r]+)/i);
            if (m) return m[1].trim();
        }
        return '';
    }
    """
    try:
        result = link.evaluate(js)
        return _clean(result or "")
    except Exception:
        return ""


class KCSScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "KCS"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Load the single AppliTrack listing page and parse every job link found in its frames."""
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

            print("  Loading KCS job listings...")
            page.goto(LISTING_URL, wait_until="networkidle", timeout=60000)

            frame = _find_job_frame(page)
            if frame is None:
                print("  No job links found in any frame.")
                print(f"  Frames loaded ({len(page.frames)}):")
                for f in page.frames:
                    print(f"    {f.url}")
                browser.close()
                return []

            candidates = _parse_listing(frame)
            print(f"  Found {len(candidates)} job(s). Verifying postings are still live...")

            # Detail pages checked concurrently — sequential requests here noticeably slow the scrape.
            with ThreadPoolExecutor(max_workers=10) as executor:
                live_flags = list(executor.map(lambda j: _is_live(j["url"]), candidates))

            dropped = [j for j, live in zip(candidates, live_flags) if not live]
            candidates = [j for j, live in zip(candidates, live_flags) if live]

            if dropped:
                print(f"  Dropped {len(dropped)} closed/unavailable listing(s):")
                for job in dropped:
                    print(f"    (removed) {job['title']}")

            for job in candidates:
                print(f"  {job['title']}  |  {job['location'] or '(no location)'}")
                results.append(Job(
                    title=job["title"],
                    company="Kannapolis City Schools",
                    location=job["location"] or "Kannapolis, NC",
                    url=job["url"],
                    source="KCS",
                ))

            browser.close()

        return results
