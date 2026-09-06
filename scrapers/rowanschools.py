"""Rowan-Salisbury Schools job listings via the SchoolSpring public jobs API."""

from .schoolspring import SchoolSpringScraper


class RowanCountySchoolsScraper(SchoolSpringScraper):
    domain = "rssk12.schoolspring.com"
    company = "Rowan-Salisbury Schools"

    @property
    def slug(self) -> str:
        return "rss"
