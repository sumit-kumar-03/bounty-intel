from abc import ABC, abstractmethod

from bounty_intel.core.schema import EngagementRecord


class BaseScraper(ABC):
    platform: str

    @abstractmethod
    def fetch(self) -> list[EngagementRecord]:
        """Return the full list of engagement records for this platform."""
