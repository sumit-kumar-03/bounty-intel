import os

import pymongo

from bounty_intel.core.logger import logger

DB_NAME = "bug_bounty"


def get_client() -> pymongo.MongoClient:
    host = os.environ["MONGO_HOST"]
    port = os.environ.get("MONGO_PORT", "27017")
    user = os.environ["MONGO_INITDB_ROOT_USERNAME"]
    password = os.environ["MONGO_INITDB_ROOT_PASSWORD"]

    uri = f"mongodb://{user}:{password}@{host}:{port}/"
    client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    logger.info("Connected to MongoDB at %s:%s", host, port)
    return client
