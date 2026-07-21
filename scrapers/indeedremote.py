"""Indeed job search restricted to remote/hybrid listings, via the jobspy library."""

import re
import sys

try:
    from jobspy import scrape_jobs
except ImportError:
    sys.exit("jobspy not found — run: pip install python-jobspy")

import pandas as pd

from .base import BaseScraper, Job

SITES     = ["indeed"]
LOCATIONS = ["Kannapolis, NC", "28083"]
RADIUS    = 25
RESULTS   = 100
HOURS_OLD = 168

_REMOTE = re.compile(r"\b(remote|work[\s\-]+from[\s\-]+home|wfh|telecommute)\b", re.IGNORECASE)
_HYBRID = re.compile(r"\bhybrid\b", re.IGNORECASE)
_EXCLUDE = re.compile(
    r"\b(not\s+remote|no\s+remote|on[\s\-]?site\s+only|in[\s\-]?person\s+only|hybrid\s+cloud|hybrid\s+infrastructure)\b",
    re.IGNORECASE,
)


def _label(row: dict) -> str | None:
    """Classify a listing as Remote/Hybrid/both from its title+description text, or None to drop it."""
    text = " ".join([
        str(row.get("title") or ""),
        str(row.get("description") or ""),
    ])
    if _EXCLUDE.search(text):
        return None
    is_remote = bool(_REMOTE.search(text))
    is_hybrid = bool(_HYBRID.search(text))
    if is_remote and is_hybrid:
        return "(Remote/Hybrid)"
    if is_remote:
        return "(Remote)"
    if is_hybrid:
        return "(Hybrid)"
    return None


def _scrape(keyword: str, location: str) -> pd.DataFrame:
    """Run one jobspy Indeed search, returning an empty DataFrame on failure."""
    try:
        return scrape_jobs(
            site_name=SITES,
            search_term=keyword,
            location=location,
            distance=RADIUS,
            results_wanted=RESULTS,
            hours_old=HOURS_OLD,
            country_indeed="USA",
            verbose=0,
        )
    except Exception as e:
        print(f"  error: {e}")
        return pd.DataFrame()


def _dedup_jk(df: pd.DataFrame) -> pd.DataFrame:
    """Drop duplicate rows sharing the same Indeed job key."""
    def extract_jk(url: str) -> str:
        m = re.search(r"[?&]jk=([^&]+)", str(url))
        return m.group(1) if m else str(url)

    df = df.copy()
    df["_jk"] = df["job_url"].apply(extract_jk)
    return df.drop_duplicates(subset="_jk").drop(columns="_jk")


class IndeedRemoteScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Indeed (Remote/Hybrid)"

    @property
    def slug(self) -> str:
        return "indeedremote"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Search each configured location, keep only remote/hybrid results, dedupe, and sort by company."""
        frames: list[pd.DataFrame] = []

        for loc in LOCATIONS:
            print(f"  Searching Indeed near {loc} ...", end="", flush=True)
            df = _scrape(keyword, loc)
            if df.empty:
                print("  0 listing(s)")
                continue
            print(f"  {len(df)} listing(s)", end="")

            records = df.to_dict(orient="records")
            labels = [_label(r) for r in records]
            df = df.copy()
            df["_label"] = labels
            kept = df[df["_label"].notna()]
            print(f"  → {len(kept)} remote/hybrid kept")
            frames.append(kept)

        if not frames:
            return []

        combined = pd.concat(frames, ignore_index=True)
        combined = _dedup_jk(combined)
        combined = combined[
            combined["company"].notna()
            & (combined["company"].astype(str).str.strip() != "")
            & (combined["company"].astype(str).str.lower() != "nan")
        ]
        combined = combined.sort_values(
            "company", ascending=True, na_position="last",
            key=lambda s: s.str.lower(),
        )

        return [
            Job(
                title=f"{row.get('title') or ''} {row['_label']}".strip(),
                company=str(row.get("company") or ""),
                location=str(row.get("location") or ""),
                url=str(row.get("job_url") or ""),
                source="Indeed (Remote/Hybrid)",
            )
            for row in combined.to_dict(orient="records")
        ]
