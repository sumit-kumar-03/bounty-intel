import json
import os
from html.parser import HTMLParser

from bounty_intel.core.logger import logger
from bounty_intel.core.schema import EngagementRecord, RewardInfo, ScopeTarget
from bounty_intel.scrapers.base import BaseScraper
from bounty_intel.support.http import build_session, get_json

BASE_URL = "https://bugcrowd.com"
LISTING_URL = f"{BASE_URL}/engagements.json"
PAGE_SIZE = 24


class _ReactRootFinder(HTMLParser):
    """Finds <div data-react-class="ResearcherEngagementBrief" data-api-endpoints="...">
    server-rendered by Bugcrowd's react-rails integration. A plain regex breaks on the
    nested quotes inside the large HTML-escaped JSON attribute values; HTMLParser handles
    attribute parsing correctly."""

    def __init__(self, target_class: str):
        super().__init__()
        self.target_class = target_class
        self.match: dict | None = None

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if d.get("data-react-class") == self.target_class and self.match is None:
            self.match = d


class BugcrowdScraper(BaseScraper):
    platform = "bugcrowd"

    def __init__(self, category: str = "bug_bounty", fetch_scope: bool = True):
        self.category = category
        self.fetch_scope = fetch_scope
        self.session = build_session()
        self.session_cookie = os.environ.get("BUGCROWD_SESSION_COOKIE", "").strip()

    def fetch(self) -> list[EngagementRecord]:
        engagements = self._fetch_listing()
        records = [self._to_record(e) for e in engagements]

        if self.fetch_scope:
            if not self.session_cookie:
                logger.info(
                    "BUGCROWD_SESSION_COOKIE not set; fetching scope anonymously "
                    "(works for public programs, private/gated ones will fail soft)"
                )
            for record in records:
                record.scope = self._fetch_scope(record.handle)

        return records

    def _fetch_listing(self) -> list[dict]:
        page = 1
        engagements: list[dict] = []
        total_count = None

        while total_count is None or len(engagements) < total_count:
            data = get_json(
                self.session,
                LISTING_URL,
                params={
                    "category": self.category,
                    "sort_by": "promoted",
                    "sort_direction": "desc",
                    "page": page,
                },
            )
            batch = data.get("engagements", [])
            if not batch:
                break
            engagements.extend(batch)
            total_count = data.get("paginationMeta", {}).get("totalCount", len(engagements))
            page += 1

        logger.info(
            "Bugcrowd listing: fetched %d/%s engagements across %d page(s)",
            len(engagements),
            total_count,
            page - 1,
        )
        return engagements

    def _to_record(self, engagement: dict) -> EngagementRecord:
        brief_url = engagement.get("briefUrl") or ""
        handle = brief_url.rstrip("/").rsplit("/", 1)[-1]
        reward_summary = engagement.get("rewardSummary") or {}
        engagement_type = (engagement.get("productEngagementType") or {}).get("label")

        return EngagementRecord(
            id=f"bugcrowd:{handle}",
            platform="bugcrowd",
            handle=handle,
            name=engagement.get("name", ""),
            url=f"{BASE_URL}{brief_url}" if brief_url else BASE_URL,
            tagline=engagement.get("tagline"),
            engagement_type=engagement_type,
            access_status=engagement.get("accessStatus"),
            is_private=bool(engagement.get("isPrivate", False)),
            reward=RewardInfo(
                type="points" if "Points" in (reward_summary.get("minReward") or "") else "paid",
                min_amount=reward_summary.get("minReward"),
                max_amount=reward_summary.get("maxReward"),
                currency=None,
                summary=reward_summary.get("summary"),
            ),
            industry=engagement.get("industryName"),
            starts_at=None,
            ends_at=engagement.get("endsAt"),
            scope=[],
            platform_data=engagement,
        )

    def _fetch_scope(self, handle: str) -> list[ScopeTarget]:
        # The Targets/Scope tab has no dedicated REST endpoint and isn't in the
        # server-rendered HTML or any structured JSON prop -- confirmed via live
        # browser network capture (every XHR the page fires) and by parsing every
        # react-rails root's data-props on the page. It's actually the SAME data
        # the "changelog" (brief version document) endpoint returns, under
        # data.scope -- that endpoint's URL is per-engagement and only exists in
        # the api-endpoints manifest embedded on the engagement's own brief page,
        # so this is a two-step fetch: get the brief page, extract the versioned
        # document URL, then fetch that document's `scope` array.
        engagement_url = f"{BASE_URL}/engagements/{handle}"
        headers = {
            "Accept": "*/*",
            "Referer": engagement_url,
            "Cookie": self.session_cookie,
        }

        try:
            brief_html = self.session.get(
                engagement_url, headers={**headers, "Accept": "text/html"}
            ).text
            finder = _ReactRootFinder("ResearcherEngagementBrief")
            finder.feed(brief_html)
            if finder.match is None:
                raise ValueError("ResearcherEngagementBrief root not found on brief page")

            endpoints = json.loads(finder.match["data-api-endpoints"])
            brief_doc_path = endpoints["engagementBriefApi"]["getBriefVersionDocument"]

            doc = get_json(self.session, f"{BASE_URL}{brief_doc_path}.json", headers=headers)
        except Exception as exc:
            logger.warning("Bugcrowd scope fetch failed for %s: %s", handle, exc)
            return []

        targets = []
        for group in doc.get("data", {}).get("scope", []):
            in_scope = group.get("inScope")
            for target in group.get("targets", []):
                targets.append(
                    ScopeTarget(
                        identifier=target.get("uri") or target.get("name", ""),
                        asset_type=target.get("category"),
                        eligible_for_bounty=in_scope,
                        eligible_for_submission=in_scope,
                        max_severity=None,
                    )
                )
        return targets
