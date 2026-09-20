#!/usr/bin/env python3
import sys

sys.path.insert(0, "/usr/src/app")

from bounty_intel.core.logger import logger
from bounty_intel.core.schema import EngagementRecord
from bounty_intel.support.mongo_client import DB_NAME, get_client
from bounty_intel.support.mongo_writer import ENGAGEMENTS_COLLECTION, write_parent_domains


def load_engagement_records(db) -> list[EngagementRecord]:
    records = []
    for doc in db[ENGAGEMENTS_COLLECTION].find({}):
        doc["id"] = doc.pop("_id")
        records.append(EngagementRecord(**doc))
    return records


def main() -> int:
    client = get_client()
    try:
        db = client[DB_NAME]
        records = load_engagement_records(db)
        logger.info("Loaded %d engagement records from Mongo", len(records))
        n_domains = write_parent_domains(db, records)
        logger.info("Backfilled engagement_ids on %d parent domains", n_domains)
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
