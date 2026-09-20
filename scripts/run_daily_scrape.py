#!/usr/bin/env python3
import sys
import traceback

sys.path.insert(0, "/usr/src/app")

from bounty_intel.core.logger import logger
from bounty_intel.scrapers.bugcrowd import BugcrowdScraper
from bounty_intel.scrapers.hackerone import HackerOneScraper
from bounty_intel.support.mongo_client import DB_NAME, get_client
from bounty_intel.support.mongo_writer import write_engagements, write_parent_domains


def main() -> int:
    logger.info("Starting daily bounty-intel scrape...")
    records = []

    for scraper_cls in (BugcrowdScraper, HackerOneScraper):
        name = scraper_cls.platform
        try:
            scraper = scraper_cls()
            platform_records = scraper.fetch()
            logger.info("%s: %d records", name, len(platform_records))
            records.extend(platform_records)
        except Exception:
            logger.error("%s scraper failed:\n%s", name, traceback.format_exc())

    if not records:
        logger.error("No records collected from any platform; aborting write")
        return 1

    client = get_client()
    try:
        db = client[DB_NAME]
        n_engagements = write_engagements(db, records)
        n_domains = write_parent_domains(db, records)
        logger.info(
            "Upserted %d engagements, %d unique parent domains into %s",
            n_engagements,
            n_domains,
            DB_NAME,
        )
    finally:
        client.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
