# Simulated omnichannel marketing dataset

> **All data in this project is simulated.** It is synthetic and must not be treated as actual business or customer performance.

This package contains six months (183 days) of daily website, email, and social channel performance, generated with pandas and Faker where Faker is installed. A fixed random seed makes the metrics repeatable. Weekday effects, a gentle seasonal trend, metric-specific noise, and three campaign bursts are included. The default range ends on the day the generator runs; use `--end-date YYYY-MM-DD` to pin the range.

## Files

- `generate_data.py` generates and loads the dataset.
- `daily_performance.csv` is the flat daily extract for quick inspection.
- `marketing.db` is a ready-to-use SQLite database.
- `app.py` is an interactive Streamlit dashboard with date/channel filters, KPI cards, a funnel, channel comparison, weekly trend, detail table, and CSV download.
- `schema.sql` defines `dim_date`, `dim_channel`, `fact_performance`, indexes, and analytical views.
- `refresh_kpis.py` refreshes the materialized `kpi_weekly` table.
- `requirements.txt` lists Python dependencies.

## Generate or refresh the data

```powershell
cd outputs
python -m pip install -r requirements.txt
python generate_data.py
python refresh_kpis.py
streamlit run app.py
```

The script needs pandas and Faker. If Faker cannot be imported (for example, in an offline environment), it uses fixed campaign names so generation remains deterministic. To reproduce the delivered date window, pass the date shown in the first/last rows of `daily_performance.csv` as `--end-date`.

The SQLite schema uses one fact row per date and channel. Channel-specific measures are retained alongside common funnel fields: `impressions`, `clicks`, `visits`, `signups`, and `conversions`. Website sessions and users, email sent/opened/clicked, social followers, and website bounce rate are also available. `social_followers` is a daily snapshot; do not sum it across dates.

## Interactive dashboard

Run `streamlit run app.py` from this folder to open the portfolio dashboard in your browser. The dark, responsive layout includes KPI cards, an impressions-to-signups funnel, a channel contribution chart, a selectable weekly trend, date and channel filters, and a downloadable filtered extract. Install dependencies from `requirements.txt` first.

## SQL views

- `vw_conversion_funnel`: daily funnel measures by channel and campaign.
- `vw_channel_comparison`: all-period channel totals and rates.
- `vw_week_over_week`: weekly conversion totals, prior week, absolute change, and percentage change, calculated with `LAG()`.
- `vw_weekly_kpi_summary`: weekly totals and rates by channel.

Rates are ratios of totals (not averages of daily rates). `kpi_weekly` is the refreshable physical table populated from the weekly view.

## Automated KPI refresh

One-time refresh:

```powershell
python refresh_kpis.py
```

Keep the process running to refresh daily at 06:00 local time:

```powershell
python refresh_kpis.py --schedule --hour 6
```

For production scheduling, create a Windows Task Scheduler task that runs `python <path>\refresh_kpis.py` daily at 06:00, with the working directory set to this `outputs` folder. The scheduled task only refreshes KPIs; run `generate_data.py` when you want to regenerate the simulated source data.

## Power BI page layout

Use **Get Data → SQLite database** (or a SQLite ODBC connector) and select `dim_date`, `dim_channel`, `fact_performance`, and the views. Create relationships:

- `dim_date[date_key]` 1 → * `fact_performance[date_key]`
- `dim_channel[channel_key]` 1 → * `fact_performance[channel_key]`

Mark `dim_date` as the date table using `full_date`. Suggested single-page canvas, 16:9:

1. **Top row:** KPI cards for impressions, clicks, visits, signups, conversions, and conversion rate.
2. **Left column:** funnel visual with stages `impressions → clicks → visits → signups`, using `vw_conversion_funnel` and a stage-order field in Power Query or a small stage table.
3. **Center:** clustered bar chart comparing impressions, clicks, visits, and conversions by channel; use channel as legend or small multiples to avoid mixing scales.
4. **Bottom:** line chart of weekly conversions or visits by `week_start`, colored by channel.
5. **Filter rail:** date range slicer from `dim_date[full_date]` and channel slicer from `dim_channel[channel_name]`.

Use `vw_week_over_week` for a companion weekly change card/table if desired. For stable funnel visuals, use one selected metric per funnel or a normalized stage table; the funnel steps count different events and should not be added together.
