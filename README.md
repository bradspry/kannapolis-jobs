# kannapolis-jobs

*by Brad Spry, Kannapolitan*

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
python run.py --part-time                # only jobs whose title mentions "part time"
python run.py --title-match "mechanic|automotive|diesel"   # filter titles by regex
```

Results are deduplicated by URL, sorted by company then title, and written to
the current directory. Each file holds at most 99 lines to fit within
Facebook's length limits, so a run splits across as many `_part{N}` files as
it needs.

Filenames record what produced them, so runs stay distinguishable:

```
jobs_{keyword}_{timestamp}[_{modules}][_{filters}]_part{N}.txt   # combined (default)
{slug}-jobs_{keyword}_{timestamp}[_{filters}]_part{N}.txt        # one set per source (--split)
```

`{keyword}` is `all` when no keyword is given, and the optional segments appear
only when the matching flag is used:

```
jobs_all_20260821_100948_speedway_parttime_technician_part1.txt
```

`--part-time` filters by job title (matching "part time", "part-time", or
"parttime" in any casing/spacing) after fetching, so it applies uniformly
across every module regardless of whether that module supports a keyword
filter.

`--title-match TERMS` works the same way but takes your own terms, which is
useful for trades that span many job titles:

```bash
python run.py --title-match "mechanic|automotive|auto tech|diesel|collision|tire|service advisor"
```

Plain words separated by `|` are matched as **whole words**, plus an optional
plural `s`. This matters more than it sounds: a bare substring search for `car`
also hits "Carolina", "Homecare", "Urgent Care", and "Carousel", which buries
the real listings. Whole-word matching removes that noise without you having to
write out the boundaries:

| Term | Matches | Does not match |
|---|---|---|
| `car` | Car Wash Attendant, Used Cars Salesperson | Carolina, Homecare, Urgent Care, Carousel |
| `mechanic` | Maintenance Mechanic II, Mechanics | Mechanical Designer |

If the value contains regex syntax — `\`, `(`, `.`, `*`, `^`, `[` and so on — it
is compiled as a regex verbatim and no boundaries are added, so full regexes
still work:

```bash
python run.py --title-match "^(Senior )?Mechanic"     # anchored regex, used as-is
python run.py --title-match "(?:car)"                 # force plain substring matching
```

Both flags can be combined, in which case a title must match all of them.

## Modules

| Source | `--modules` slug | Mechanism | Keyword filter |
|---|---|---|---|
| AppState | `appstate` | Atom feed, filtered to Kannapolis-area postings | Yes |
| Cabarrus County Government | `cabarrus` | Playwright (GovernmentJobs/NEOGOV, paginated) | No |
| Cabarrus Health Alliance | `cha` | ADP WorkforceNow public API | No |
| Chewy | `chewy` | Phenom People career site, embedded JSON (Salisbury, NC only) | No |
| Chick-fil-A Supply | `cfasupply` | Playwright (iCIMS, route interception) | No |
| City of Kannapolis | `city` | Playwright (GovernmentJobs/NEOGOV) | No |
| Corning | `corning` | SAP SuccessFactors career site, filtered to Concord, NC | Yes |
| DHL Careers | `dhl` | Playwright (search + per-job address check) | No |
| Gordon Food Service | `gfs` | Playwright (Workday) | No |
| Indeed | `indeed` | [jobspy](https://github.com/speedyapply/JobSpy) | Yes |
| Indeed (Remote/Hybrid) | `indeedremote` | jobspy, filtered to remote/hybrid postings | Yes |
| Kannapolis City Schools | `kcs` | Playwright (AppliTrack/Frontline) | No |
| Lilly | `lilly` | jobsyn.org search API | No |
| Macy's | `macys` | Oracle Recruiting Cloud public API (radius search, filtered to China Grove) | Yes |
| Momentec | `momentec` | Playwright (Paycom) | No |
| Monarch | `monarch` | Workday CXS public API, filtered to Concord/Kannapolis | Yes |
| NC State | `ncstate` | Atom feed, filtered to Kannapolis-area postings | Yes |
| RCCC | `rccc` | Atom feed | Yes |
| REBEL | `rebel` | BambooHR public careers API, filtered to Kannapolis (incl. remote) | No |
| Rowan County Government | `rowancounty` | Tyler Portico public API | Yes |
| Shoe Show | `shoeshow` | Playwright (zip-radius search, paginated) | No |
| Speedway Motorsports | `speedway` | ADP WorkforceNow public API, filtered to Concord/Harrisburg | No |
| Standard Process | `standardprocess` | UltiPro job board API | Yes |
| Sysco | `sysco` | TalentBrew career site (radius search, filtered to Concord) | No |
| UNC | `unc` | Atom feed, filtered to Kannapolis-area postings | Yes |
| UNC Charlotte | `uncc` | Atom feed | Yes |
| UNC Greensboro | `uncg` | Atom feed, filtered to Kannapolis-area postings | Yes |
| Westrock Coffee | `westrock` | ADP myjobs (Recruiting Cloud) public API, filtered to Concord | No |

Modules that don't support a keyword filter always return their full current
listing set (they already scope to a specific employer/location).

## Adding a new module

1. Create `scrapers/yourmodule.py`, subclassing `BaseScraper` (see
   `scrapers/base.py`) and implementing `name` and `fetch(keyword) -> list[Job]`.
2. Import it and add an instance to `ALL_SCRAPERS` in `run.py`.

## License

Licensed under the GNU General Public License v3.0 — see [LICENSE](LICENSE).
