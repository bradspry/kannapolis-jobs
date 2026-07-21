"""Indeed job search via the jobspy library, queried across nearby zip codes/locations."""

import re
import sys

try:
    from jobspy import scrape_jobs
except ImportError:
    sys.exit("jobspy not found — run: pip install python-jobspy")

from .base import BaseScraper, Job

LOCATIONS = ["Kannapolis, NC", "28081", "28083"]
SITES     = ["indeed"]
RADIUS    = 10
RESULTS   = 50
HOURS_OLD = 168


class IndeedScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "Indeed"

    def fetch(self, keyword: str = "") -> list[Job]:
        """Query Indeed for each configured location, merge, dedupe by job key, and sort by company."""
        all_rows = []
        for loc in LOCATIONS:
            print(f"  Searching Indeed near {loc} ...", end="", flush=True)
            try:
                df = scrape_jobs(
                    site_name=SITES,
                    search_term=keyword,
                    location=loc,
                    distance=RADIUS,
                    results_wanted=RESULTS,
                    hours_old=HOURS_OLD,
                    country_indeed="USA",
                    verbose=0,
                )
                print(f"  {len(df)} listing(s)")
                all_rows.append(df)
            except Exception as e:
                print(f"  error: {e}")

        if not all_rows:
            return []

        import pandas as pd
        combined = pd.concat(all_rows, ignore_index=True)

        if combined.empty or "job_url" not in combined.columns:
            return []

        def extract_jk(url: str) -> str:
            """Pull Indeed's job-key query param so duplicate listings can be deduped."""
            m = re.search(r"[?&]jk=([^&]+)", str(url))
            return m.group(1) if m else str(url)

        combined["_jk"] = combined["job_url"].apply(extract_jk)
        combined = combined.drop_duplicates(subset="_jk").drop(columns="_jk")
        combined = combined[
            combined["company"].notna()
            & (combined["company"].astype(str).str.strip() != "")
            & (combined["company"].astype(str).str.lower() != "nan")
        ]
        combined = combined.sort_values(
            "company", ascending=True, na_position="last",
            key=lambda s: s.str.lower()
        )

        return [
            Job(
                title=str(row.get("title") or ""),
                company=str(row.get("company") or ""),
                location=str(row.get("location") or ""),
                url=str(row.get("job_url") or ""),
                source="Indeed",
            )
            for row in combined.to_dict(orient="records")
        ]
