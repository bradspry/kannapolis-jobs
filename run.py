#!/usr/bin/env python3
"""
Kannapolis Job Pipeline
Runs all configured job scrapers and produces a unified report.

Usage:
    python run.py                            # all jobs, all modules
    python run.py warehouse                  # keyword search (modules that support it)
    python run.py --modules dhl              # run a specific module
    python run.py warehouse --modules indeed dhl kcs

Licensed under the GNU General Public License v3.0 — see LICENSE.
"""

import argparse
import re
import sys
from datetime import datetime

from scrapers.indeed import IndeedScraper
from scrapers.indeedremote import IndeedRemoteScraper
from scrapers.dhl import DHLScraper
from scrapers.kcs import KCSScraper
from scrapers.city import CityOfKannapolisScraper
from scrapers.cfasupply import CFASupplyScraper
from scrapers.momentec import MomentecScraper
from scrapers.gfs import GFSScraper
from scrapers.shoeshow import ShoeShowScraper
from scrapers.uncc import UNCCScraper
from scrapers.rccc import RCCCScraper
from scrapers.unc import UNCScraper
from scrapers.ncstate import NCStateScraper
from scrapers.appstate import AppStateScraper
from scrapers.uncg import UNCGScraper
from scrapers.standardprocess import StandardProcessScraper
from scrapers.lilly import LillyScraper
from scrapers.cabarrus import CabarrusCountyScraper
from scrapers.rowancounty import RowanCountyGovernmentScraper
from scrapers.speedwaymotorsports import SpeedwayMotorsportsScraper
from scrapers.cabarrushealthalliance import CabarrusHealthAllianceScraper
from scrapers.monarch import MonarchScraper
from scrapers.rebel import RebelScraper
from scrapers.corning import CorningScraper
from scrapers.chewy import ChewyScraper
from scrapers.sysco import SyscoScraper
from scrapers.macys import MacysScraper
from scrapers.westrockcoffee import WestrockCoffeeScraper
from scrapers.base import Job

ALL_SCRAPERS = [IndeedScraper(), IndeedRemoteScraper(), DHLScraper(), KCSScraper(), CityOfKannapolisScraper(), CFASupplyScraper(), MomentecScraper(), GFSScraper(), ShoeShowScraper(), UNCCScraper(), RCCCScraper(), UNCScraper(), NCStateScraper(), AppStateScraper(), UNCGScraper(), StandardProcessScraper(), LillyScraper(), CabarrusCountyScraper(), RowanCountyGovernmentScraper(), SpeedwayMotorsportsScraper(), CabarrusHealthAllianceScraper(), MonarchScraper(), RebelScraper(), CorningScraper(), ChewyScraper(), SyscoScraper(), MacysScraper(), WestrockCoffeeScraper()]

MAX_LINES = 99
SEP  = "=" * 10
DASH = "-" * 10


def build_posts(jobs: list[Job], label: str = "KANNAPOLIS") -> list[list[str]]:
    """Format jobs into Facebook-post-sized text chunks, splitting when a chunk would exceed MAX_LINES."""
    date_str = datetime.now().strftime("%m-%d-%y")
    header = [SEP, f"{label} JOB LISTINGS: {date_str}", SEP]

    posts: list[list[str]] = []
    chunk: list[str] = list(header)
    jobs_in_chunk = 0

    for job in jobs:
        jl = [
            f"Job Title : {job.title    or 'N/A'}",
            f"Company   : {job.company  or 'N/A'}",
            f"Location  : {job.location or 'N/A'}",
            f"Link      : {job.url      or 'N/A'}",
        ]
        candidate = ([DASH] if jobs_in_chunk > 0 else []) + jl

        if len(chunk) + len(candidate) > MAX_LINES:
            posts.append(chunk)
            chunk = list(jl)
            jobs_in_chunk = 1
        else:
            chunk.extend(candidate)
            jobs_in_chunk += 1

    if chunk:
        posts.append(chunk)

    return posts


def write_posts(posts: list[list[str]], filename_prefix: str) -> None:
    """Write each post chunk to its own numbered .txt file and print a summary."""
    for i, lines in enumerate(posts, 1):
        filename = f"{filename_prefix}_part{i}.txt"
        text = "\n".join(lines)
        with open(filename, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(text)
        print()
    print("=" * 40)
    for i, lines in enumerate(posts, 1):
        filename = f"{filename_prefix}_part{i}.txt"
        print(f"  Saved: {filename}  ({len(lines)} lines)")
    print("=" * 40)


def main() -> None:
    """Parse CLI args, run the selected scrapers, dedupe results, and write the output post(s)."""
    parser = argparse.ArgumentParser(description="Kannapolis job pipeline")
    parser.add_argument(
        "keyword", nargs="?", default="",
        help="Search keyword passed to modules that support it (default: all jobs)",
    )
    parser.add_argument(
        "--modules", nargs="+", metavar="MODULE",
        help=f"Run only these module(s). Available: {[s.slug for s in ALL_SCRAPERS]}",
    )
    parser.add_argument(
        "--split", action="store_true",
        help="Write a separate file set per source instead of one combined output",
    )
    args = parser.parse_args()

    scrapers = ALL_SCRAPERS
    if args.modules:
        names = {m.lower() for m in args.modules}
        scrapers = [s for s in ALL_SCRAPERS if s.slug in names]
        if not scrapers:
            sys.exit(
                f"No modules matched: {args.modules}\n"
                f"Available: {[s.slug for s in ALL_SCRAPERS]}"
            )

    all_jobs: list[Job] = []
    seen_urls: set[str] = set()
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_kw = re.sub(r"[^\w]+", "_", args.keyword).strip("_") if args.keyword else "all"

    for scraper in scrapers:
        print(f"\n{'=' * 40}")
        print(f"  {scraper.name}")
        print(f"{'=' * 40}")
        try:
            jobs = scraper.fetch(keyword=args.keyword)
            new_jobs = [j for j in jobs if j.url not in seen_urls]
            seen_urls.update(j.url for j in new_jobs)
            print(f"  {len(new_jobs)} unique job(s) added.")

            if args.split and new_jobs:
                new_jobs.sort(key=lambda j: j.title.lower())
                label  = scraper.name.upper()
                posts  = build_posts(new_jobs, label=label)
                prefix = f"{scraper.slug}-jobs_{safe_kw}_{ts}"
                write_posts(posts, prefix)
            else:
                all_jobs.extend(new_jobs)
        except Exception as e:
            print(f"  ERROR in {scraper.name}: {e}")

    if args.split:
        return

    print(f"\n{'=' * 40}")
    print(f"  Total: {len(all_jobs)} unique job(s) across all modules")
    print(f"{'=' * 40}\n")

    if not all_jobs:
        print("Nothing to write.")
        return

    all_jobs.sort(key=lambda j: (j.company.lower(), j.title.lower()))
    mod_tag = "_".join(m.lower() for m in args.modules) if args.modules else ""
    suffix  = f"_{mod_tag}" if mod_tag else ""
    label   = scrapers[0].name.upper() if len(scrapers) == 1 else "KANNAPOLIS"
    posts   = build_posts(all_jobs, label=label)
    write_posts(posts, f"jobs_{safe_kw}_{ts}{suffix}")


if __name__ == "__main__":
    main()
