from collections import defaultdict

from pymongo import UpdateOne

from bounty_intel.core.logger import logger
from bounty_intel.core.schema import EngagementRecord
from bounty_intel.support.domain_extractor import extract_registrable_domain

ENGAGEMENTS_COLLECTION = "engagements"
PARENT_DOMAINS_COLLECTION = "parent_domains"


def write_engagements(db, records: list[EngagementRecord]) -> int:
    ops = []
    for record in records:
        doc = record.model_dump()
        doc_id = doc.pop("id")
        ops.append(UpdateOne({"_id": doc_id}, {"$set": doc}, upsert=True))

    if ops:
        db[ENGAGEMENTS_COLLECTION].bulk_write(ops, ordered=False)
    return len(ops)


def _compute_domain_links(records: list[EngagementRecord]) -> dict[str, set[str]]:
    domain_to_engagement_ids: dict[str, set[str]] = defaultdict(set)
    for record in records:
        for target in record.scope:
            if target.eligible_for_bounty is not True:
                continue  # skip non-bounty-eligible / out-of-scope / unknown targets
            domain = extract_registrable_domain(
                target.identifier, target.asset_type, record.platform
            )
            if domain:
                domain_to_engagement_ids[domain].add(record.id)
    return domain_to_engagement_ids


def write_parent_domains(db, records: list[EngagementRecord]) -> int:
    """Additive-only: safe to call with a partial (e.g. single-platform)
    records list, since it never removes an existing link. Use this from
    the regular daily scrape path."""
    domain_to_engagement_ids = _compute_domain_links(records)

    ops = [
        UpdateOne(
            {"_id": domain},
            {"$addToSet": {"engagement_ids": {"$each": sorted(engagement_ids)}}},
            upsert=True,
        )
        for domain, engagement_ids in domain_to_engagement_ids.items()
    ]
    if ops:
        db[PARENT_DOMAINS_COLLECTION].bulk_write(ops, ordered=False)
    return len(domain_to_engagement_ids)


def reconcile_parent_domains(db, records: list[EngagementRecord]) -> tuple[int, int]:
    """Authoritative full recompute of parent_domains from a COMPLETE records
    snapshot (e.g. every engagement freshly loaded from Mongo -- never a
    partial/per-platform subset). Unlike write_parent_domains ($addToSet,
    safe for partial runs), this $set-replaces engagement_ids on every domain
    that still has >=1 bounty-eligible source (fixing any stale IDs left
    over from the old eligible_for_submission gate) and deletes every
    parent_domains document with zero bounty-eligible source. Returns
    (kept_count, dropped_count)."""
    domain_to_engagement_ids = _compute_domain_links(records)

    correct_domains = set(domain_to_engagement_ids)
    existing_domains = {
        doc["_id"] for doc in db[PARENT_DOMAINS_COLLECTION].find({}, {"_id": 1})
    }
    stale_domains = existing_domains - correct_domains

    ops = [
        UpdateOne(
            {"_id": domain},
            {"$set": {"engagement_ids": sorted(engagement_ids)}},
            upsert=True,
        )
        for domain, engagement_ids in domain_to_engagement_ids.items()
    ]
    if ops:
        db[PARENT_DOMAINS_COLLECTION].bulk_write(ops, ordered=False)

    if stale_domains:
        logger.info(
            "Dropping %d parent_domains with no eligible_for_bounty source: %s",
            len(stale_domains),
            sorted(stale_domains),
        )
        db[PARENT_DOMAINS_COLLECTION].delete_many({"_id": {"$in": sorted(stale_domains)}})

    return len(correct_domains), len(stale_domains)
