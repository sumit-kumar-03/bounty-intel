# bounty-intel

Daily scraper for Bugcrowd and HackerOne bug-bounty engagements. Runs in a
Docker container on a daily cron, upserting current engagement data into
MongoDB. No code is baked into the image — this repo directory is
bind-mounted into the container.

## Setup

1. Copy `.env.example` to `.env` and fill in:
   - `HACKERONE_API_USERNAME` / `HACKERONE_API_TOKEN` — from your HackerOne
     account's API token settings. Required; without it the HackerOne
     scraper is skipped (logged as an error) and only Bugcrowd data is
     written.
   - `BUGCROWD_SESSION_COOKIE` — optional. Public programs' listing, brief
     page, and scope are all served with no auth at all (verified), so scope
     fetching works out of the box with this left blank. Only needed for
     private/invite-only programs your account has access to — the full
     `Cookie:` header value from a logged-in bugcrowd.com session (devtools
     -> Network -> any request -> copy the `cookie` request header). Expires
     periodically and must be refreshed manually. If it contains literal `$`
     characters (Google Analytics cookies commonly do), escape each one as
     `$$` — Docker Compose interpolates `$VAR` syntax in `env_file` values
     and will otherwise silently blank them out.
   - `MONGO_HOST` / `MONGO_PORT` / `MONGO_INITDB_ROOT_USERNAME` /
     `MONGO_INITDB_ROOT_PASSWORD` — the shared MongoDB instance managed by
     the sibling [`infra-hub`](../infra-hub) repo. Defaults point at
     `infra-mongodb`; only the credentials normally need filling in.
2. Make sure `infra-hub`'s stack is up (`docker compose up -d` in
   `../infra-hub`) so the `infra-net` network and `infra-mongodb` exist.
3. `docker compose up -d --build`

The container runs one scrape immediately on startup, then again daily at
`02:00 UTC` via cron (`scripts/crontab`).

## Storage

Each run upserts into the shared `infra-mongodb` instance, database
`bug_bounty`:

- **`engagements`** — one document per engagement, `_id` is the same
  `"<platform>:<handle>"` value previously used as `EngagementRecord.id`.
  Each run does a merge-update (`$set` of every scraped field, not a full
  document replace), so the collection always reflects the latest scrape
  for its scraper-owned fields while any other data added to a document
  survives. There is no per-day history inside Mongo — re-running the
  scrape does not create new entries, matching the schema in
  `bounty_intel/core/schema.py` (`EngagementRecord`).
- **`parent_domains`** — minimal `{_id: "<domain>"}` documents, one per
  unique registrable domain extracted from every engagement's
  `scope[].identifier`, via `bounty_intel/support/domain_extractor.py`
  (`tldextract`, running fully offline against its bundled public-suffix
  snapshot). Non-domain scope entries (IPs, CIDRs, mobile app/store IDs,
  source-code links, free text) are safely skipped.

Historical JSON snapshots (`output/engagements_<date>.json`) from before
this migration remain on disk for reference; nothing new is written there.

## How Bugcrowd scope is fetched

Bugcrowd has no official public API for hackers, and the "Targets" section
on an engagement page isn't a separate route or a plain REST endpoint — it's
populated client-side from the same JSON document that backs the brief's
version history. `bounty_intel/scrapers/bugcrowd.py::_fetch_scope` does this
in two requests per engagement (no auth required for public programs; the
session cookie, when set, is attached to both so private programs work too):

1. `GET /engagements/<handle>` (HTML) — parses the `data-api-endpoints`
   attribute on the server-rendered `ResearcherEngagementBrief` root to find
   `engagementBriefApi.getBriefVersionDocument`, a per-engagement URL.
2. `GET <that URL>.json` — the response's `data.scope` array holds each
   target group (in-scope / out-of-scope, reward range) and its individual
   targets (uri, category, tags).

A small number of engagements use a different brief layout with no
`ResearcherEngagementBrief` root; those fail soft (logged warning, empty
`scope`) rather than aborting the run.

## Manual run

```
docker compose exec bounty-intel python scripts/run_daily_scrape.py
```

Re-running is idempotent — it upserts rather than creating a new dated
file.
