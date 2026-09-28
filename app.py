"""Streamlit dashboard — Data Center Energy Stress Predictor.

Reads data/clean/*.csv only; makes no API calls at runtime.
"""

import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Data Center Energy Stress Predictor",
    page_icon="⚡",
    layout="wide",
)

CLEAN = Path("data/clean")

REGION_COLORS = {
    "Virginia": "#2196F3",
    "Ohio":     "#FF9800",
    "Texas":    "#4CAF50",
    "Georgia":  "#E91E63",
}

SEASON_ORDER = ["Winter", "Spring", "Summer", "Fall"]

# ── DATA LOADING ──────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    master = pd.read_csv(CLEAN / "master_timeseries.csv")
    master["Timestamp"] = pd.to_datetime(master["Timestamp"], utc=True)
    geo    = pd.read_csv(CLEAN / "geo_summary.csv")
    im3    = pd.read_csv(CLEAN / "im3_clean.csv")
    return master, geo, im3


master_all, geo_all, im3_all = load_data()
ALL_REGIONS  = sorted(master_all["Region"].unique().tolist())
ALL_SEASONS  = SEASON_ORDER

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
st.sidebar.header("Filters")

sel_regions = st.sidebar.multiselect(
    "Regions", ALL_REGIONS, default=ALL_REGIONS
)
sel_seasons = st.sidebar.multiselect(
    "Seasons", ALL_SEASONS, default=ALL_SEASONS
)
resolution = st.sidebar.radio(
    "Time resolution",
    ["Daily (default)", "Hourly"],
    index=0,
    help="Hourly plots 100k+ points and may be slow.",
)
hourly_mode = resolution == "Hourly"

if not sel_regions:
    st.warning("Select at least one region to display data.")
    st.stop()
if not sel_seasons:
    st.warning("Select at least one season to display data.")
    st.stop()

# ── FILTER DATA ───────────────────────────────────────────────────────────────
master = master_all[
    master_all["Region"].isin(sel_regions) &
    master_all["Season"].isin(sel_seasons)
].copy()

geo = geo_all[geo_all["Region"].isin(sel_regions)].copy()
im3 = im3_all[im3_all["Region"].isin(sel_regions)].copy()

if master.empty:
    st.warning("No data for the selected filters.")
    st.stop()

# ── KPI ROW ───────────────────────────────────────────────────────────────────
st.title("Data Center Energy Stress Predictor")
st.caption("Analytics & Visualization — Virginia, Ohio, Texas, Georgia")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Regions shown",          len(sel_regions))
k2.metric("Unique data centers",    f"{im3['id'].nunique():,}")
k3.metric("Avg demand (filtered)",  f"{master['Demand_MW'].mean():,.0f} MW")
k4.metric("Peak stress index",      f"{master['Stress_Index'].max():.1f}")

st.divider()

# ── DEMAND TIME SERIES ────────────────────────────────────────────────────────
st.subheader("Demand Time Series")

if hourly_mode:
    ts_df = master[["Region","Timestamp","Demand_MW"]].copy()
    ts_df["Date"] = ts_df["Timestamp"]
else:
    ts_df = (
        master.groupby(["Region", master["Timestamp"].dt.date])
        ["Demand_MW"].mean().reset_index()
        .rename(columns={"Timestamp": "Date"})
    )
    ts_df["Date"] = pd.to_datetime(ts_df["Date"])

fig_ts = px.line(
    ts_df, x="Date", y="Demand_MW", color="Region",
    facet_col="Region", facet_col_wrap=2, height=420,
    labels={"Demand_MW": "Demand (MW)", "Date": "Date"},
    color_discrete_map=REGION_COLORS,
    title="",
)
fig_ts.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
fig_ts.update_layout(showlegend=False, margin=dict(t=20))
st.plotly_chart(fig_ts, use_container_width=True)

# ── HOURLY PROFILE ────────────────────────────────────────────────────────────
st.subheader("Hourly Demand Profile")
col_l, col_r = st.columns(2)

profile = (
    master.groupby(["Region","Hour","Is_Weekend"])["Demand_MW"]
    .mean().reset_index()
)
profile["Day Type"] = profile["Is_Weekend"].map({0: "Weekday", 1: "Weekend"})

with col_l:
    fig_prof = px.line(
        profile, x="Hour", y="Demand_MW", color="Region",
        line_dash="Day Type", height=350,
        labels={"Demand_MW": "Avg Demand (MW)", "Hour": "Hour of Day (local)"},
        color_discrete_map=REGION_COLORS,
        title="Weekday vs Weekend Profile",
    )
    fig_prof.update_xaxes(dtick=3)
    fig_prof.update_layout(margin=dict(t=40))
    st.plotly_chart(fig_prof, use_container_width=True)

# ── STRESS BOX PLOT ───────────────────────────────────────────────────────────
with col_r:
    fig_box = px.box(
        master, x="Region", y="Stress_Index", color="Region",
        height=350,
        labels={"Stress_Index": "Stress Index (percentile rank)"},
        color_discrete_map=REGION_COLORS,
        title="Stress Index Distribution",
    )
    fig_box.update_layout(showlegend=False, margin=dict(t=40))
    st.plotly_chart(fig_box, use_container_width=True)

# ── HOUR × MONTH STRESS HEATMAP ───────────────────────────────────────────────
st.subheader("Hour × Month Stress Heatmap")
hm_region = st.selectbox("Select region for heatmap", sel_regions, index=0)

hm_df = master[master["Region"] == hm_region]
heat = hm_df.groupby(["Month","Hour"])["Stress_Index"].mean().reset_index()
heat_pivot = heat.pivot(index="Hour", columns="Month", values="Stress_Index")
month_labels = ["Jan","Feb","Mar","Apr","May","Jun",
                "Jul","Aug","Sep","Oct","Nov","Dec"]
present_months = sorted(heat_pivot.columns.tolist())

fig_hm = px.imshow(
    heat_pivot,
    aspect="auto",
    color_continuous_scale="RdYlGn_r",
    labels={"x": "Month", "y": "Hour of Day (local)", "color": "Avg Stress Index"},
    x=[month_labels[m-1] for m in present_months],
    title=f"{hm_region}: Mean Stress Index — Hour × Month",
    height=380,
)
fig_hm.update_layout(margin=dict(t=50))
st.plotly_chart(fig_hm, use_container_width=True)

# ── TEMPERATURE VS DEMAND ─────────────────────────────────────────────────────
st.subheader("Temperature vs Demand (sample)")
sample = master.iloc[::8].copy()    # thin for speed

fig_temp = px.scatter(
    sample, x="Temperature", y="Demand_MW", color="Region",
    opacity=0.35, height=380,
    labels={"Temperature": "Temperature (°C)", "Demand_MW": "Demand (MW)"},
    color_discrete_map=REGION_COLORS,
    title="Temperature vs Demand",
)
fig_temp.update_traces(marker=dict(size=3))
fig_temp.update_layout(margin=dict(t=50))
st.plotly_chart(fig_temp, use_container_width=True)

# ── PYDECK DATA-CENTER MAP ────────────────────────────────────────────────────
st.subheader("Data Center Locations")

map_df = im3.copy()
map_df["sqft_plot"] = map_df["sqft"].fillna(50_000)
map_df["radius"] = np.clip(np.sqrt(map_df["sqft_plot"]) * 3, 500, 12000)
map_df["color_r"] = map_df["Region"].map(
    {"Virginia":33,"Ohio":255,"Texas":76,"Georgia":233})
map_df["color_g"] = map_df["Region"].map(
    {"Virginia":150,"Ohio":152,"Texas":175,"Georgia":30})
map_df["color_b"] = map_df["Region"].map(
    {"Virginia":243,"Ohio":0,"Texas":80,"Georgia":99})
map_df["tooltip_text"] = (
    map_df["name"].fillna("unnamed") + " | " +
    map_df["type"] + " | " +
    map_df["sqft"].apply(lambda x: f"{x:,.0f} sqft" if pd.notnull(x) else "sqft N/A")
)

layer = pdk.Layer(
    "ScatterplotLayer",
    data=map_df,
    get_position="[lon, lat]",
    get_radius="radius",
    get_fill_color="[color_r, color_g, color_b, 160]",
    pickable=True,
)

mid_lat = map_df["lat"].mean()
mid_lon = map_df["lon"].mean()
view = pdk.ViewState(latitude=mid_lat, longitude=mid_lon, zoom=4, pitch=0)

deck = pdk.Deck(
    layers=[layer],
    initial_view_state=view,
    tooltip={"text": "{tooltip_text}"},
    map_style="mapbox://styles/mapbox/light-v9",
)
st.pydeck_chart(deck, height=450)

# ── REGION SUMMARY TABLE ──────────────────────────────────────────────────────
st.subheader("Region Summary")

demand_stats = (
    master.groupby("Region")["Demand_MW"]
    .agg(avg_demand="mean", peak_demand="max", std_demand="std")
    .round(1)
    .reset_index()
)
stress_stats = (
    master.groupby("Region")["Stress_Index"]
    .agg(stress_p95=lambda x: x.quantile(0.95))
    .round(1)
    .reset_index()
)
dc_counts = (
    im3.groupby("Region")["id"].nunique().reset_index()
    .rename(columns={"id": "unique_DCs"})
)
summary = (
    demand_stats
    .merge(stress_stats, on="Region")
    .merge(dc_counts, on="Region", how="left")
)
summary.columns = [
    "Region", "Avg Demand (MW)", "Peak Demand (MW)",
    "Std Demand (MW)", "Stress P95", "Unique DCs",
]
st.dataframe(summary.set_index("Region"), use_container_width=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "**Stress Index** is a relative, percentile-based measure (0–100) computed "
    "within each region's own demand history. A value of 95 means that hour's demand "
    "is in the top 5 % of that region's observed data. "
    "Cross-region comparisons of Stress Index are not meaningful. "
    "Data sources: PJM Kaggle CSVs (2015–2017), EIA-930 API (2019–2021), "
    "NREL NSRDB (weather/solar), IM3 Data Center Atlas v2026.02.09 (ODbL)."
)
