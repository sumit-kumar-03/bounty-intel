#!/usr/bin/env python3
import sys

sys.path.insert(0, "/usr/src/app")

from bounty_intel.core.logger import logger
from bounty_intel.support.mongo_client import DB_NAME, get_client
from bounty_intel.support.mongo_reader import load_engagement_records
from bounty_intel.support.mongo_writer import reconcile_parent_domains


def main() -> int:
    client = get_client()
    try:
        db = client[DB_NAME]
        records = load_engagement_records(db)
        logger.info("Loaded %d engagement records from Mongo", len(records))
        n_kept, n_dropped = reconcile_parent_domains(db, records)
        logger.info(
            "Reconciled parent_domains: %d kept (eligible_for_bounty-backed), "
            "%d dropped (no bounty-eligible source)",
            n_kept,
            n_dropped,
        )
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
