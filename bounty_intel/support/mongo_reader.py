from bounty_intel.core.schema import EngagementRecord
from bounty_intel.support.mongo_writer import ENGAGEMENTS_COLLECTION


def load_engagement_records(db) -> list[EngagementRecord]:
    records = []
    for doc in db[ENGAGEMENTS_COLLECTION].find({}):
        doc["id"] = doc.pop("_id")
        records.append(EngagementRecord(**doc))
    return records
