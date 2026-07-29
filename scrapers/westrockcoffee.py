"""Westrock Coffee job listings via ADP's myjobs Recruiting Cloud public API."""

from .adp_myjobs import ADPMyJobsScraper


class WestrockCoffeeScraper(ADPMyJobsScraper):
    domain = "westrockcoffeeexternaljobs"
    company = "Westrock Coffee"
    target_locations = {("concord", "nc")}

    @property
    def slug(self) -> str:
        return "westrock"
