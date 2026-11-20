"""Interactive Streamlit dashboard for the simulated marketing warehouse."""
from pathlib import Path
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE = Path(__file__).resolve().parent
DB = BASE / "marketing.db"
COLORS = {"website": "#31C6B3", "email": "#9B8AFB", "social": "#F4A261"}

st.set_page_config(page_title="Northstar | Growth Intelligence", page_icon="✦", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root { --ink:#e7edf5; --muted:#91a0b5; --panel:#111b2b; --line:#223149; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp { background: radial-gradient(ellipse at 82% 0%, #19334a 0%, #0a1220 40%, #080e18 100%); color:var(--ink); }
.block-container { max-width:1500px; padding-top:2rem; padding-bottom:3rem; }
[data-testid="stSidebar"] { background:#0b1422; border-right:1px solid #1c2a3f; }
h1,h2,h3 { font-family:'Manrope',sans-serif!important; letter-spacing:-.035em; color:#f3f6fb!important; }
.hero { padding:8px 0 25px; }
.eyebrow { color:#63d9c4; text-transform:uppercase; letter-spacing:.18em; font-size:11px; font-weight:700; }
.hero-title { font-family:Manrope,sans-serif; font-size:34px; line-height:1.18; font-weight:800; margin:8px 0 6px; }
.hero-sub { color:#9baac0; font-size:14px; }
.kpi { background:linear-gradient(145deg,rgba(21,34,53,.95),rgba(14,24,39,.94)); border:1px solid #24344b; border-radius:14px; padding:17px 18px 16px; min-height:112px; box-shadow:0 10px 28px #00000020; }
.kpi-label { color:#9baac0; font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:.09em; }
.kpi-value { color:#f4f7fb; font-family:Manrope,sans-serif; font-size:27px; font-weight:800; padding-top:7px; }
.kpi-note { color:#70d8c2; font-size:11px; padding-top:2px; }
.section-label { font-size:12px; color:#70d8c2; text-transform:uppercase; letter-spacing:.15em; font-weight:700; margin:15px 0 8px; }
.note { color:#91a0b5; font-size:12px; }
div[data-testid="stPlotlyChart"] { border:1px solid #203047; border-radius:14px; padding:10px; background:rgba(15,25,40,.82); }
[data-testid="stMetric"] { background:transparent; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=30)
def load_data():
    if not DB.exists():
        return pd.DataFrame()
    with sqlite3.connect(DB) as con:
        return pd.read_sql_query("""SELECT d.full_date, d.week_start, c.channel_name channel,
          f.campaign,f.impressions,f.clicks,f.visits,f.signups,f.conversions,f.sessions,
          f.users,f.bounce_rate,f.email_sent,f.email_opened,f.email_clicked,f.social_followers
          FROM fact_performance f JOIN dim_date d USING(date_key)
          JOIN dim_channel c USING(channel_key) ORDER BY d.full_date""", con, parse_dates=["full_date","week_start"])

df=load_data()
if df.empty:
    st.error("No database found. Run `python generate_data.py` from the outputs folder first.")
    st.stop()

st.sidebar.markdown("<div class='eyebrow'>Growth intelligence</div>",unsafe_allow_html=True)
st.sidebar.title("Report controls")
min_date,max_date=df.full_date.min().date(),df.full_date.max().date()
selected=st.sidebar.date_input("Date range",value=(min_date,max_date),min_value=min_date,max_value=max_date)
channels=st.sidebar.multiselect("Channels",options=sorted(df.channel.unique()),default=sorted(df.channel.unique()))
if isinstance(selected,tuple):
    start,end=selected if len(selected)==2 else (selected[0],selected[0])
else: start=end=selected
filtered=df[(df.full_date.dt.date>=start)&(df.full_date.dt.date<=end)&df.channel.isin(channels)]
if filtered.empty: st.warning("Choose a date range and at least one channel to display results."); st.stop()

st.markdown("<div class='hero'><div class='eyebrow'>Simulated omnichannel performance · 6 month view</div><div class='hero-title'>Campaigns, connected.</div><div class='hero-sub'>A unified view of reach, engagement and conversion across every channel.</div></div>",unsafe_allow_html=True)

# KPI totals honor current date and channel selections.
imp=int(filtered.impressions.sum()); clicks=int(filtered.clicks.sum()); visits=int(filtered.visits.sum()); signs=int(filtered.signups.sum()); conv=int(filtered.conversions.sum())
ctr=clicks/imp if imp else 0; cvr=conv/visits if visits else 0
cards=[("Impressions",f"{imp:,}","Total audience reach"),("Visits",f"{visits:,}","Qualified site traffic"),("Signups",f"{signs:,}","New leads captured"),("Conversions",f"{conv:,}","Attributed outcomes"),("Visit → conversion",f"{cvr:.1%}",f"{ctr:.1%} click-through rate")]
cols=st.columns(5)
for col,(label,value,note) in zip(cols,cards):
    col.markdown(f"<div class='kpi'><div class='kpi-label'>{label}</div><div class='kpi-value'>{value}</div><div class='kpi-note'>{note}</div></div>",unsafe_allow_html=True)

st.markdown("<div class='section-label'>Conversion journey</div>",unsafe_allow_html=True)
left,right=st.columns([1.02,1.55],gap="large")
with left:
    stages=["Impressions","Clicks","Visits","Signups"]
    values=[imp,clicks,visits,signs]
    fig=go.Figure(go.Funnel(y=stages,x=values,textinfo="value+percent initial",marker={"color":["#31c6b3","#62b7cd","#8e9bed","#b196ef"]},connector={"line":{"color":"#34445b","width":1}}))
    fig.update_layout(title="From awareness to intent",height=355,margin=dict(l=10,r=15,t=55,b=15),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#dce6f2",title_font_size=16)
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
with right:
    comparison=filtered.groupby("channel",as_index=False)[["impressions","clicks","visits","signups","conversions"]].sum()
    melt=comparison.melt(id_vars="channel",var_name="Metric",value_name="Volume")
    fig=px.bar(melt,x="channel",y="Volume",color="Metric",barmode="group",color_discrete_sequence=["#31c6b3","#70b7cc","#9b8afb","#f4a261","#e879a9"],title="Channel contribution by stage")
    fig.update_layout(height=355,margin=dict(l=10,r=15,t=55,b=15),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#dce6f2",title_font_size=16,legend_title_text="",xaxis_title="",yaxis_title="Events",yaxis=dict(gridcolor="#24344b",zeroline=False),xaxis=dict(categoryorder="array",categoryarray=["website","email","social"]))
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

st.markdown("<div class='section-label'>Performance over time</div>",unsafe_allow_html=True)
weekly=filtered.groupby(["week_start","channel"],as_index=False)[["visits","conversions","impressions"]].sum().sort_values("week_start")
metric=st.selectbox("Trend metric",["conversions","visits","impressions"],index=0,label_visibility="collapsed")
fig=px.line(weekly,x="week_start",y=metric,color="channel",markers=True,color_discrete_map=COLORS,title=f"Weekly {metric.replace('_',' ')}")
fig.update_traces(line_width=2.5,marker_size=5)
fig.update_layout(height=370,margin=dict(l=10,r=15,t=55,b=20),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#dce6f2",title_font_size=16,legend_title_text="",xaxis_title="",yaxis_title=metric.title(),yaxis=dict(gridcolor="#24344b",zeroline=False),xaxis=dict(gridcolor="#172438"))
st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

with st.expander("Explore channel detail"):
    details=filtered.groupby("channel",as_index=False).agg(Impressions=("impressions","sum"),Clicks=("clicks","sum"),Visits=("visits","sum"),Signups=("signups","sum"),Conversions=("conversions","sum"),Sessions=("sessions","sum"),Users=("users","sum"),Average_bounce_rate=("bounce_rate","mean"))
    details["Click_through_rate"]=details.Clicks/details.Impressions
    details["Visit_conversion_rate"]=details.Conversions/details.Visits
    st.dataframe(details.style.format({"Average_bounce_rate":"{:.1%}","Click_through_rate":"{:.2%}","Visit_conversion_rate":"{:.2%}"}),use_container_width=True,hide_index=True)
    st.download_button("Download filtered data",filtered.to_csv(index=False).encode("utf-8"),"marketing_filtered.csv","text/csv")
st.caption("All metrics are generated synthetic data for portfolio demonstration. Follower counts are daily snapshots; do not aggregate them across days.")
