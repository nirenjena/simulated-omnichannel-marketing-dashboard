-- Star schema for simulated omnichannel marketing performance.
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS dim_date (
  date_key INTEGER PRIMARY KEY, -- YYYYMMDD
  full_date TEXT NOT NULL UNIQUE,
  year INTEGER NOT NULL,
  quarter INTEGER NOT NULL,
  month INTEGER NOT NULL,
  month_name TEXT NOT NULL,
  week_start TEXT NOT NULL,
  day_of_week INTEGER NOT NULL,
  day_name TEXT NOT NULL,
  is_weekend INTEGER NOT NULL CHECK (is_weekend IN (0,1))
);
CREATE TABLE IF NOT EXISTS dim_channel (
  channel_key INTEGER PRIMARY KEY,
  channel_name TEXT NOT NULL UNIQUE,
  channel_group TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fact_performance (
  date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
  channel_key INTEGER NOT NULL REFERENCES dim_channel(channel_key),
  campaign TEXT NOT NULL DEFAULT 'Always-on',
  impressions INTEGER NOT NULL DEFAULT 0,
  clicks INTEGER NOT NULL DEFAULT 0,
  visits INTEGER NOT NULL DEFAULT 0,
  signups INTEGER NOT NULL DEFAULT 0,
  conversions INTEGER NOT NULL DEFAULT 0,
  sessions INTEGER NOT NULL DEFAULT 0,
  users INTEGER NOT NULL DEFAULT 0,
  bounce_rate REAL,
  email_sent INTEGER NOT NULL DEFAULT 0,
  email_opened INTEGER NOT NULL DEFAULT 0,
  email_clicked INTEGER NOT NULL DEFAULT 0,
  social_followers INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (date_key, channel_key)
);
CREATE INDEX IF NOT EXISTS idx_fact_channel_date ON fact_performance(channel_key, date_key);
CREATE INDEX IF NOT EXISTS idx_date_week_start ON dim_date(week_start);

DROP VIEW IF EXISTS vw_conversion_funnel;
CREATE VIEW vw_conversion_funnel AS
SELECT d.full_date, d.week_start, c.channel_name, f.campaign,
       f.impressions, f.clicks, f.visits, f.signups,
       f.conversions
FROM fact_performance f JOIN dim_date d USING(date_key)
JOIN dim_channel c USING(channel_key);

DROP VIEW IF EXISTS vw_channel_comparison;
CREATE VIEW vw_channel_comparison AS
SELECT c.channel_name, SUM(f.impressions) impressions, SUM(f.clicks) clicks,
       SUM(f.visits) visits, SUM(f.signups) signups, SUM(f.conversions) conversions,
       SUM(f.sessions) sessions, SUM(f.users) users,
       CASE WHEN SUM(f.impressions)=0 THEN 0.0 ELSE 1.0*SUM(f.clicks)/SUM(f.impressions) END click_through_rate,
       CASE WHEN SUM(f.visits)=0 THEN 0.0 ELSE 1.0*SUM(f.conversions)/SUM(f.visits) END conversion_rate
FROM fact_performance f JOIN dim_channel c USING(channel_key)
GROUP BY c.channel_key, c.channel_name;

DROP VIEW IF EXISTS vw_weekly_kpi_summary;
CREATE VIEW vw_weekly_kpi_summary AS
SELECT d.week_start, c.channel_name,
       SUM(f.impressions) impressions, SUM(f.clicks) clicks, SUM(f.visits) visits,
       SUM(f.signups) signups, SUM(f.conversions) conversions,
       SUM(f.sessions) sessions, SUM(f.users) users,
       ROUND(1.0*SUM(f.clicks)/NULLIF(SUM(f.impressions),0),4) click_through_rate,
       ROUND(1.0*SUM(f.conversions)/NULLIF(SUM(f.visits),0),4) conversion_rate
FROM fact_performance f JOIN dim_date d USING(date_key)
JOIN dim_channel c USING(channel_key)
GROUP BY d.week_start, c.channel_name;

DROP VIEW IF EXISTS vw_week_over_week;
CREATE VIEW vw_week_over_week AS
WITH weekly AS (SELECT * FROM vw_weekly_kpi_summary)
SELECT week_start, channel_name, impressions, clicks, visits, signups, conversions,
       LAG(conversions) OVER (PARTITION BY channel_name ORDER BY week_start) previous_week_conversions,
       conversions - LAG(conversions) OVER (PARTITION BY channel_name ORDER BY week_start) wow_conversion_change,
       ROUND(100.0*(conversions-LAG(conversions) OVER (PARTITION BY channel_name ORDER BY week_start)) /
          NULLIF(LAG(conversions) OVER (PARTITION BY channel_name ORDER BY week_start),0),2) wow_conversion_pct
FROM weekly;
