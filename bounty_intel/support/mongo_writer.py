from collections import defaultdict

from pymongo import UpdateOne

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


def write_parent_domains(db, records: list[EngagementRecord]) -> int:
    domain_to_engagement_ids: dict[str, set[str]] = defaultdict(set)

    for record in records:
        for target in record.scope:
            if target.eligible_for_submission is not True:
                continue  # skip out-of-scope / unknown-scope targets
            domain = extract_registrable_domain(
                target.identifier, target.asset_type, record.platform
            )
            if domain:
                domain_to_engagement_ids[domain].add(record.id)

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
