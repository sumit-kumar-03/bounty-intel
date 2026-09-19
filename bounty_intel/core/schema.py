from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


class RewardInfo(BaseModel):
    type: str = "unknown"  # paid | points | swag | vdp | unknown
    min_amount: Optional[str] = None
    max_amount: Optional[str] = None
    currency: Optional[str] = None
    summary: Optional[str] = None


class ScopeTarget(BaseModel):
    identifier: str
    asset_type: Optional[str] = None
    eligible_for_bounty: Optional[bool] = None
    eligible_for_submission: Optional[bool] = None
    max_severity: Optional[str] = None


class EngagementRecord(BaseModel):
    id: str
    platform: Literal["bugcrowd", "hackerone"]
    handle: str
    name: str
    url: str
    tagline: Optional[str] = None
    engagement_type: Optional[str] = None
    access_status: Optional[str] = None
    is_private: bool = False
    reward: RewardInfo = Field(default_factory=RewardInfo)
    industry: Optional[str] = None
    starts_at: Optional[str] = None
    ends_at: Optional[str] = None
    scope: list[ScopeTarget] = Field(default_factory=list)
    scraped_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    platform_data: dict = Field(default_factory=dict)
