"""Speedway Motorsports job listings via the ADP WorkforceNow public staffing API."""

from .adp_workforcenow import ADPWorkforceNowScraper


class SpeedwayMotorsportsScraper(ADPWorkforceNowScraper):
    cid  = "d180c324-e784-463d-a355-61b3275338b9"
    ccid = "19000101_000001"
    company = "Speedway Motorsports"
    default_location = "Concord, NC"
    target_cities = {"concord", "harrisburg"}

    @property
    def slug(self) -> str:
        return "speedway"
