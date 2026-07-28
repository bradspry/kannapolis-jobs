"""Monarch (NC) job listings via the Workday CXS public career-site API."""

from .workday import WorkdayScraper


class MonarchScraper(WorkdayScraper):
    host = "monarch.wd5.myworkdayjobs.com"
    tenant = "monarch"
    site = "Monarch"
    company = "Monarch"
    location_ids = [
        "182af004158901c74f1fc8a7e8178803",
        "8e87b040b5ea012a1daffb06f70184b6",
    ]
    target_city_names = {"concord, nc", "kannapolis, nc"}

    @property
    def slug(self) -> str:
        return "monarch"
