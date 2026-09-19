import os

from bounty_intel.core.logger import logger
from bounty_intel.core.schema import EngagementRecord, RewardInfo, ScopeTarget
from bounty_intel.scrapers.base import BaseScraper
from bounty_intel.support.http import build_session, get_json

API_BASE = "https://api.hackerone.com/v1/hackers"
WEB_BASE = "https://hackerone.com"
PAGE_SIZE = 100


class HackerOneScraper(BaseScraper):
    platform = "hackerone"

    def __init__(self, fetch_scope: bool = True):
        self.fetch_scope = fetch_scope
        self.session = build_session()

        username = os.environ.get("HACKERONE_API_USERNAME", "").strip()
        token = os.environ.get("HACKERONE_API_TOKEN", "").strip()
        if not username or not token:
            raise RuntimeError(
                "HACKERONE_API_USERNAME and HACKERONE_API_TOKEN must be set"
            )
        self.session.auth = (username, token)

    def fetch(self) -> list[EngagementRecord]:
        programs = self._fetch_programs()
        records = [self._to_record(p) for p in programs]

        if self.fetch_scope:
            for record in records:
                record.scope = self._fetch_structured_scopes(record.handle)

        return records

    def _fetch_programs(self) -> list[dict]:
        page = 1
        programs: list[dict] = []

        while True:
            data = get_json(
                self.session,
                f"{API_BASE}/programs",
                params={"page[number]": page, "page[size]": PAGE_SIZE},
            )
            batch = data.get("data", [])
            if not batch:
                break
            programs.extend(batch)

            # The API's `links` only ever has self/next/prev, never `last` --
            # relying on `last` here previously stopped pagination after the
            # first page even when `next` (and more data) existed.
            if len(batch) < PAGE_SIZE:
                break
            page += 1

        logger.info("HackerOne listing: fetched %d programs", len(programs))
        return programs

    def _to_record(self, program: dict) -> EngagementRecord:
        attrs = program.get("attributes", {})
        handle = attrs.get("handle", program.get("id", ""))
        submission_state = attrs.get("submission_state")

        return EngagementRecord(
            id=f"hackerone:{handle}",
            platform="hackerone",
            handle=handle,
            name=attrs.get("name", handle),
            url=f"{WEB_BASE}/{handle}",
            tagline=None,
            engagement_type="bug_bounty" if attrs.get("offers_bounties") else "vdp",
            access_status=submission_state,
            is_private=submission_state == "paused" if submission_state else False,
            reward=RewardInfo(
                type="paid" if attrs.get("offers_bounties") else "vdp",
                min_amount=None,
                max_amount=None,
                currency=attrs.get("currency"),
                summary=None,
            ),
            industry=None,
            starts_at=None,
            ends_at=None,
            scope=[],
            platform_data=program,
        )

    def _fetch_structured_scopes(self, handle: str) -> list[ScopeTarget]:
        page = 1
        scopes: list[ScopeTarget] = []

        try:
            while True:
                data = get_json(
                    self.session,
                    f"{API_BASE}/programs/{handle}/structured_scopes",
                    params={"page[number]": page, "page[size]": PAGE_SIZE},
                )
                batch = data.get("data", [])
                if not batch:
                    break

                for item in batch:
                    attrs = item.get("attributes", {})
                    scopes.append(
                        ScopeTarget(
                            identifier=attrs.get("asset_identifier", ""),
                            asset_type=attrs.get("asset_type"),
                            eligible_for_bounty=attrs.get("eligible_for_bounty"),
                            eligible_for_submission=attrs.get("eligible_for_submission"),
                            max_severity=attrs.get("max_severity"),
                        )
                    )

                if len(batch) < PAGE_SIZE:
                    break
                page += 1
        except Exception as exc:
            logger.warning("HackerOne structured_scopes fetch failed for %s: %s", handle, exc)
            return []

        return scopes
