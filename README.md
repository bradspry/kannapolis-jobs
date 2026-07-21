# Kannapolis Job Pipeline

A command-line tool that scrapes job listings from employers, schools, and
government sites in and around Kannapolis, NC, and formats them into
ready-to-post text files sized for a Facebook post/comment (99 lines each).

Built to support a local community Facebook group that shares job leads.

## Requirements

- Python 3.10+
- Google Chrome/Chromium (installed automatically by Playwright, see below)

## Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
python run.py                            # all jobs, all modules
python run.py warehouse                  # keyword search (modules that support it)
python run.py --modules dhl              # run a specific module
python run.py warehouse --modules indeed dhl kcs
python run.py --split                    # write a separate file set per source
```

Results are deduplicated by URL, sorted by company then title, and written to
`jobs_{keyword}_{timestamp}_part{N}.txt` in the current directory. Each file
holds at most 99 lines to fit within Facebook's length limits.

## Modules

| Source | `--modules` slug | Mechanism | Keyword filter |
|---|---|---|---|
| Indeed | `indeed` | [jobspy](https://github.com/speedyapply/JobSpy) | Yes |
| Indeed (Remote/Hybrid) | `indeedremote` | jobspy, filtered to remote/hybrid postings | Yes |
| DHL Careers | `dhl` | Playwright (search + per-job address check) | No |
| Kannapolis City Schools | `kcs` | Playwright (AppliTrack/Frontline) | No |
| City of Kannapolis | `city` | Playwright (GovernmentJobs/NEOGOV) | No |
| Cabarrus County Government | `cabarrus` | Playwright (GovernmentJobs/NEOGOV, paginated) | No |
| Rowan County Government | `rowancounty` | Tyler Portico public API | Yes |
| Chick-fil-A Supply | `cfasupply` | Playwright (iCIMS, route interception) | No |
| Momentec | `momentec` | Playwright (Paycom) | No |
| Gordon Food Service | `gfs` | Playwright (Workday) | No |
| Shoe Show | `shoeshow` | Playwright (zip-radius search, paginated) | No |
| Standard Process | `standardprocess` | UltiPro job board API | Yes |
| Lilly | `lilly` | jobsyn.org search API | No |
| UNC Charlotte | `uncc` | Atom feed | Yes |
| RCCC | `rccc` | Atom feed | Yes |
| UNC | `unc` | Atom feed, filtered to Kannapolis-area postings | Yes |
| NC State | `ncstate` | Atom feed, filtered to Kannapolis-area postings | Yes |
| AppState | `appstate` | Atom feed, filtered to Kannapolis-area postings | Yes |
| UNC Greensboro | `uncg` | Atom feed, filtered to Kannapolis-area postings | Yes |

Modules that don't support a keyword filter always return their full current
listing set (they already scope to a specific employer/location).

## Adding a new module

1. Create `scrapers/yourmodule.py`, subclassing `BaseScraper` (see
   `scrapers/base.py`) and implementing `name` and `fetch(keyword) -> list[Job]`.
2. Import it and add an instance to `ALL_SCRAPERS` in `run.py`.

## License

Licensed under the GNU General Public License v3.0 — see [LICENSE](LICENSE).
