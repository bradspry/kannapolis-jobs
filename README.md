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
python run.py --evening                  # only evening/PM or second-shift jobs
python run.py --part-time --evening      # part-time evening work only
python run.py --school-bus               # school bus jobs across the three districts
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

`--evening` filters the same way, for work that starts late in the day. It
matches the forms employers actually use in a title:

| Matches | Example title |
|---|---|
| evening, night(s), overnight, twilight | Part-Time Evening Custodian |
| 2nd/second/3rd/third shift, swing shift, closing shift | Custodian 2nd Shift Hours |
| after school | After School Program Aide |
| a bare "PM" | Team Member (PM Shift) |
| a clock time | Sales Associate 5:00pm-10:00pm |

That last row is the reason `--evening` exists instead of just
`--title-match "evening|pm|night"`. Whole-word matching cannot see the `PM` in
`4PM-9PM`, because a digit is a word character and so no word boundary exists
between `4` and `PM` — and a shift written as a clock range is one of the most
common ways an evening job is advertised. `--evening` special-cases it.

Deliberately excluded: bare "closing" and "closer", which match real-estate and
sales titles ("Closing Coordinator", "Sales Closer") far more often than they
match evening shifts. Only the unambiguous "closing shift" counts.

Combine it with `--part-time` for part-time evening work specifically:

```bash
python run.py --part-time --evening
```

`--school-bus` finds school bus work — drivers, monitors, mechanics, and the
transportation assistants who ride along. Unlike the other filters it also
narrows the module set, to the three school districts:

| District | Slug |
|---|---|
| Cabarrus County Schools | `ccs` |
| Kannapolis City Schools | `kcs` |
| Rowan-Salisbury Schools | `rss` |

That narrowing is what lets the pattern be broad. A bare "bus" is unambiguous
inside a school district, so the filter catches "BUS MONITOR" and "BUS MECHANIC"
without anyone having to think of those titles in advance — whereas board-wide
it would pull in restaurant "Bus Person" postings. The districts each write the
job differently, and all of these are matched:

```
System-Wide Bus Driver                        (Kannapolis)
Field Trip Bus Driver                         (Kannapolis, Cabarrus)
Part-Time Transportation Assistant (AM)       (Kannapolis)
Bus Driver Cox Mill High School               (Cabarrus)
EC Lead Bus Driver                            (Cabarrus)
EC Transportation Safety Assistant            (Cabarrus)
Substitute Van Driver                         (Cabarrus)
TEACHER ASSISTANT/BUS DRIVER                  (Rowan-Salisbury)
BUS MONITOR, BUS MECHANIC, VAN DRIVER         (Rowan-Salisbury)
```

A `--school-bus` run ends with a per-employer tally, so you can see at a glance
which district is hiring without counting entries in the output files:

```
========================================
  SCHOOL BUS JOBS BY EMPLOYER
========================================
  Cabarrus County Schools  26
  Rowan-Salisbury Schools  15
  Kannapolis City Schools  7
  -----------------------  --
  TOTAL                    48
========================================
```

The tally is printed for `--split` runs too, and reads "None found." when
nothing matched. It counts by the employer name that appears in the output
files, which is not always the module name — the `kcs` module posts its jobs
as "Kannapolis City Schools".

Monitor and mechanic roles are excluded — "BUS MONITOR" rides along rather than
drives, and "BUS MECHANIC" is garage work. The ride-along *Transportation
Assistant* roles are kept, since those are the ones districts hire for
alongside routes. "Business" and "Drivers Ed Teacher" are also left out. Passing `--modules`
explicitly overrides the narrowing, so `--school-bus --modules rss` searches
only Rowan-Salisbury, and it composes with the other filters as usual:

```bash
python run.py --school-bus --part-time   # part-time bus routes only
```

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

All four title filters can be combined, in which case a title must match
every one of them.

## Modules

| Source | `--modules` slug | Mechanism | Keyword filter |
|---|---|---|---|
| AppState | `appstate` | Atom feed, filtered to Kannapolis-area postings | Yes |
| Cabarrus County Government | `cabarrus` | Playwright (GovernmentJobs/NEOGOV, paginated) | No |
| Cabarrus County Schools | `ccs` | SchoolSpring public jobs API, paginated | Yes |
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
| Rowan-Salisbury Schools | `rss` | SchoolSpring public jobs API, paginated | Yes |
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
