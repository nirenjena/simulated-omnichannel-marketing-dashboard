"""Refresh materialized weekly KPI output; supports one-shot or daily schedule."""
import argparse, sqlite3, time
from datetime import datetime, timedelta
from pathlib import Path

DB = Path(__file__).resolve().parent / "marketing.db"

def refresh():
    with sqlite3.connect(DB) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS kpi_weekly (
          week_start TEXT NOT NULL, channel_name TEXT NOT NULL,
          impressions INTEGER, clicks INTEGER, visits INTEGER, signups INTEGER,
          conversions INTEGER, sessions INTEGER, users INTEGER,
          click_through_rate REAL, conversion_rate REAL,
          refreshed_at TEXT NOT NULL, PRIMARY KEY(week_start,channel_name))""")
        con.execute("DELETE FROM kpi_weekly")
        con.execute("""INSERT INTO kpi_weekly
          SELECT week_start,channel_name,impressions,clicks,visits,signups,conversions,
                 sessions,users,click_through_rate,conversion_rate,?
          FROM vw_weekly_kpi_summary""", (datetime.now().astimezone().isoformat(timespec="seconds"),))
    print("Weekly KPI table refreshed")

def sleep_to_next_run(hour: int):
    now=datetime.now().astimezone(); target=now.replace(hour=hour,minute=0,second=0,microsecond=0)
    if target<=now: target+=timedelta(days=1)
    time.sleep((target-now).total_seconds())

if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("--schedule",action="store_true",help="run every day")
    p.add_argument("--hour",type=int,default=6,help="local hour 0-23")
    a=p.parse_args(); refresh()
    while a.schedule:
        sleep_to_next_run(a.hour); refresh()
