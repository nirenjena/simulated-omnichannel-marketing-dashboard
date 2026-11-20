"""Generate six months of deterministic, simulated omnichannel data."""
from __future__ import annotations
import argparse, math, random, sqlite3
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
try:
    from faker import Faker
except ImportError:  # deterministic fallback for offline generation
    Faker = None

BASE = Path(__file__).resolve().parent
DB = BASE / "marketing.db"
CSV = BASE / "daily_performance.csv"
SCHEMA = BASE / "schema.sql"
SEED = 20261120


def generate(end_date: date | None = None) -> pd.DataFrame:
    end_date = end_date or date.today()
    start = end_date - timedelta(days=182)  # 183 days, approximately six months
    rng = random.Random(SEED)
    if Faker is not None:
        fake = Faker(); Faker.seed(SEED)
        campaign_names = [fake.catch_phrase() for _ in range(3)]
    else:
        campaign_names = ["Spring Launch", "Member Appreciation", "Summer Preview"]
    campaign_days = {start + timedelta(days=31): campaign_names[0],
                     start + timedelta(days=87): campaign_names[1],
                     start + timedelta(days=146): campaign_names[2]}
    records = []
    for i in range(183):
        day = start + timedelta(days=i)
        weekday_factor = 0.70 if day.weekday() >= 5 else 1.0
        seasonal = 1 + 0.12 * math.sin(2 * math.pi * i / 183) + 0.0008 * i
        campaign = campaign_days.get(day, "Always-on")
        spike = 2.0 if day in campaign_days else 1.0
        for channel in ("website", "email", "social"):
            noise = rng.uniform(.88, 1.13)
            row = dict(date=day, channel=channel, campaign=campaign if day in campaign_days else "Always-on",
                       impressions=0, clicks=0, visits=0, signups=0, conversions=0,
                       sessions=0, users=0, bounce_rate=None, email_sent=0,
                       email_opened=0, email_clicked=0, social_followers=0)
            if channel == "website":
                sessions = int(1700 * weekday_factor * seasonal * (1.15 if day in campaign_days else 1) * noise)
                users = int(sessions * rng.uniform(.68, .82))
                signups = int(sessions * rng.uniform(.035, .055) * (1.25 if day in campaign_days else 1))
                row.update(impressions=sessions * 5, clicks=sessions, visits=sessions,
                           signups=signups, conversions=int(signups * rng.uniform(.12, .2)),
                           sessions=sessions, users=users,
                           bounce_rate=round(min(.78,max(.25,rng.gauss(.47,.06))),4))
            elif channel == "email":
                sent = int((7600 if day.weekday() in (1,3) else 900) * seasonal * noise * spike)
                opened = int(sent * rng.uniform(.22,.34)); clicked = int(opened * rng.uniform(.08,.16))
                visits = int(clicked * rng.uniform(.82,.98))
                row.update(impressions=sent, clicks=clicked, visits=visits,
                           signups=int(visits*rng.uniform(.025,.045)), conversions=int(visits*rng.uniform(.025,.05)),
                           email_sent=sent, email_opened=opened, email_clicked=clicked)
            else:
                impressions = int(12500 * weekday_factor * seasonal * spike * noise)
                clicks = int(impressions * rng.uniform(.012,.032))
                visits = int(clicks * rng.uniform(.55,.8))
                row.update(impressions=impressions, clicks=clicks, visits=visits,
                           signups=int(visits*rng.uniform(.02,.04)), conversions=int(visits*rng.uniform(.018,.038)),
                           social_followers=42000 + i*int(rng.uniform(16,35)))
            records.append(row)
    return pd.DataFrame(records)


def load(df: pd.DataFrame, db_path: Path = DB) -> None:
    with sqlite3.connect(db_path) as con:
        con.executescript(SCHEMA.read_text(encoding="utf-8-sig"))
        con.execute("DELETE FROM fact_performance"); con.execute("DELETE FROM dim_date"); con.execute("DELETE FROM dim_channel")
        dates = pd.DataFrame({"full_date": sorted(df.date.unique())})
        dates["date_key"] = dates.full_date.map(lambda d: int(d.strftime("%Y%m%d")))
        dates["year"] = dates.full_date.map(lambda d: d.year)
        dates["quarter"] = dates.full_date.map(lambda d: (d.month-1)//3+1)
        dates["month"] = dates.full_date.map(lambda d: d.month)
        dates["month_name"] = dates.full_date.map(lambda d: d.strftime("%B"))
        dates["week_start"] = dates.full_date.map(lambda d: (d-timedelta(days=d.weekday())).isoformat())
        dates["day_of_week"] = dates.full_date.map(lambda d: d.isoweekday())
        dates["day_name"] = dates.full_date.map(lambda d: d.strftime("%A"))
        dates["is_weekend"] = dates.full_date.map(lambda d: int(d.weekday()>=5))
        dates["full_date"] = dates.full_date.map(date.isoformat)
        dates.to_sql("dim_date", con, if_exists="append", index=False)
        pd.DataFrame([(1,"website","Owned"),(2,"email","Owned"),(3,"social","Paid & Organic")],
                     columns=["channel_key","channel_name","channel_group"]).to_sql("dim_channel",con,if_exists="append",index=False)
        channel_keys = {"website":1,"email":2,"social":3}
        fact = df.copy(); fact["date_key"] = fact.date.map(lambda d:int(d.strftime("%Y%m%d")))
        fact["channel_key"] = fact.channel.map(channel_keys)
        fact.drop(columns=["date","channel"],inplace=True)
        fact.to_sql("fact_performance",con,if_exists="append",index=False)
    df.assign(date=df.date.map(date.isoformat)).to_csv(CSV,index=False)

if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--end-date", help="ISO date for reproducible range")
    args=parser.parse_args(); end=date.fromisoformat(args.end_date) if args.end_date else None
    data=generate(end); load(data); print(f"Wrote {len(data)} daily channel rows to {DB} and {CSV}")
