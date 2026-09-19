#!/bin/sh
set -e

echo "=================================================="
echo "bounty-intel starting..."
echo "=================================================="

echo "Running initial scrape..."
python3 /usr/src/app/scripts/run_daily_scrape.py || true

echo "Installing cron schedule..."
crontab /usr/src/app/scripts/crontab
crontab -l

echo "Starting cron daemon in foreground..."
exec crond -f -l 2
