"""REBEL job listings via the BambooHR public careers-page API, filtered to Kannapolis."""

from .bamboohr import BambooHRScraper


class RebelScraper(BambooHRScraper):
    subdomain = "rebel"
    company = "REBEL"
    target_cities = {"kannapolis"}
    include_remote = True

    @property
    def slug(self) -> str:
        return "rebel"
