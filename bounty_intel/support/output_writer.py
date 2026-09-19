import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

from bounty_intel.core.schema import EngagementRecord

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "output"


def write_snapshot(records: list[EngagementRecord], run_date: date | None = None) -> Path:
    run_date = run_date or datetime.now(timezone.utc).date()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"engagements_{run_date.isoformat()}.json"
    payload = [record.model_dump() for record in records]
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    _chown_to_host_user(out_path)
    return out_path


def _chown_to_host_user(path: Path) -> None:
    # The container runs as root (crond needs it), but the output dir is bind-mounted
    # from the host -- without this, every snapshot is root-owned and the host user
    # can't edit/delete it. HOST_UID/HOST_GID are set in docker-compose.yml.
    if os.name != "posix" or os.geteuid() != 0:
        return
    uid, gid = os.environ.get("HOST_UID"), os.environ.get("HOST_GID")
    if not uid or not gid:
        return
    try:
        os.chown(path, int(uid), int(gid))
    except (OSError, ValueError):
        pass
