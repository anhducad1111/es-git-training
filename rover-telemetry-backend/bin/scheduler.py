#!/usr/bin/env python3
"""Runs aggregate.php every minute and retention.php once a day.

Stand-in for a real cron/Task Scheduler entry (see docs/api-contract.md:
"Schedule bin/aggregate.php (every minute) and bin/retention.php (nightly)
via cron"). Windows has no cron, so this loops in the foreground instead -
keep the terminal window open, or launch it as a background process
yourself (e.g. via `pythonw` or NSSM) if you want it to survive logout.

Usage: python bin/scheduler.py
"""
import datetime
import shutil
import subprocess
import sys
import time
from pathlib import Path

BIN_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BIN_DIR.parent / "storage"

FALLBACK_PHP_PATHS = [r"C:\xampp\php\php.exe"]


def resolve_php() -> str:
    found = shutil.which("php")
    if found:
        return found
    for candidate in FALLBACK_PHP_PATHS:
        if Path(candidate).exists():
            return candidate
    sys.exit(
        "Could not find a php executable on PATH or in the known XAMPP location "
        f"({FALLBACK_PHP_PATHS[0]}). Add php to your Windows PATH and try again."
    )


PHP = resolve_php()

AGGREGATE_INTERVAL_SECONDS = 60
RETENTION_CHECK_INTERVAL_SECONDS = 60


def log(message: str) -> None:
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{timestamp}] {message}", flush=True)


def run_php(script_name: str) -> None:
    script_path = BIN_DIR / script_name
    result = subprocess.run(
        [PHP, str(script_path)],
        capture_output=True,
        text=True,
        cwd=str(BIN_DIR),
    )
    if result.stdout.strip():
        log(f"{script_name}: {result.stdout.strip()}")
    if result.returncode != 0:
        log(f"{script_name} FAILED (exit {result.returncode}): {result.stderr.strip()}")


def last_run_date(marker_name: str) -> datetime.date | None:
    marker_path = STORAGE_DIR / marker_name
    if not marker_path.exists():
        return None
    try:
        text = marker_path.read_text().strip()
        return datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").date()
    except (ValueError, OSError):
        return None


def main() -> None:
    log("Scheduler started: aggregate.php every 60s, retention.php once/day")
    next_aggregate_at = time.monotonic()
    retention_done_date = last_run_date("retention.lastrun")

    while True:
        now = time.monotonic()
        if now >= next_aggregate_at:
            run_php("aggregate.php")
            next_aggregate_at = now + AGGREGATE_INTERVAL_SECONDS

        today = datetime.datetime.now(datetime.timezone.utc).date()
        if retention_done_date != today:
            run_php("retention.php")
            retention_done_date = today

        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
