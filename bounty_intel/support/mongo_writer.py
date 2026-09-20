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
    domains: set[str] = set()
    for record in records:
        for target in record.scope:
            domain = extract_registrable_domain(
                target.identifier, target.asset_type, record.platform
            )
            if domain:
                domains.add(domain)

    ops = [
        UpdateOne({"_id": domain}, {"$setOnInsert": {"_id": domain}}, upsert=True)
        for domain in domains
    ]
    if ops:
        db[PARENT_DOMAINS_COLLECTION].bulk_write(ops, ordered=False)
    return len(domains)
