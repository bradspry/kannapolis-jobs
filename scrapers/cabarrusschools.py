"""Cabarrus County Schools job listings via the SchoolSpring public jobs API."""

from .schoolspring import SchoolSpringScraper


class CabarrusCountySchoolsScraper(SchoolSpringScraper):
    domain = "cabarrus.schoolspring.com"
    company = "Cabarrus County Schools"

    @property
    def slug(self) -> str:
        return "ccs"
