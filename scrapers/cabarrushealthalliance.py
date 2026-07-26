"""Cabarrus Health Alliance job listings via the ADP WorkforceNow public staffing API."""

from .adp_workforcenow import ADPWorkforceNowScraper


class CabarrusHealthAllianceScraper(ADPWorkforceNowScraper):
    cid  = "c25f2dd9-f40c-43eb-98d8-7e82e7033050"
    ccid = "19000101_000001"
    company = "Cabarrus Health Alliance"
    default_location = "Concord, NC"

    @property
    def slug(self) -> str:
        return "cha"
