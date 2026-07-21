"""Shared data model and interface that every scraper module implements."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Job:
    """A single normalized job listing produced by any scraper."""
    title: str
    company: str
    location: str
    url: str
    source: str


class BaseScraper(ABC):
    """Common interface for a job source. Subclass and implement `name` and `fetch`."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable source name, used in console output and report headers."""
        ...

    @property
    def slug(self) -> str:
        """Short lowercase CLI identifier used with --modules. Defaults to name.lower()."""
        return self.name.lower()

    @abstractmethod
    def fetch(self, keyword: str = "") -> list[Job]:
        """Fetch current listings, optionally filtered by keyword, as a list of Job."""
        ...
