"""Streamlit dashboard — Data Center Energy Stress Predictor.

Reads data/clean/*.csv only; makes no API calls at runtime.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import plotly.colors as pc
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Energy Stress Predictor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="auto",   # expanded on desktop, collapsed on phones
)

CLEAN = Path("data/clean")

# ── PALETTE — single source of truth ─────────────────────────────────────────
REGION_COLOR = {
    "Virginia": "#4A90D9",   # steel blue
    "Ohio":     "#E89B3E",   # amber
    "Texas":    "#3AAFA9",   # teal
    "Georgia":  "#D9534F",   # coral red
}
REGION_RGB = {
    "Virginia": [74, 144, 217],
    "Ohio":     [232, 155, 62],
    "Texas":    [58, 175, 169],
    "Georgia":  [217, 83, 79],
}
SEASON_ORDER = ["Winter", "Spring", "Summer", "Fall"]

# Page colors
PAGE_BG   = "#0F1419"
CARD_BG   = "#1A2233"
BORDER    = "#2A3444"
GRID      = "rgba(255,255,255,0.04)"
TEXT_MAIN  = "#C9D1D9"
TEXT_MUTED = "#8B949E"

# Free basemap — no Mapbox token required (pydeck 0.9+ needs this)
MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
  .main .block-container {{ padding-top: 1rem; max-width: 1400px; }}
  #MainMenu, footer, header {{ visibility: hidden; }}

  /* sidebar */
  section[data-testid="stSidebar"] {{ background: {PAGE_BG}; }}

  /* tabs */
  .stTabs [data-baseweb="tab-list"] {{
      background: {PAGE_BG}; border-radius: 6px; padding: 2px; gap: 0;
      border: 1px solid {BORDER};
  }}
  .stTabs [data-baseweb="tab"] {{
      border-radius: 4px; color: {TEXT_MUTED}; font-weight: 500; font-size: 0.85rem;
  }}
  .stTabs [aria-selected="true"] {{
      background: {CARD_BG} !important; color: {TEXT_MAIN} !important;
  }}

  /* KPI row */
  .kpi-row {{ display: flex; gap: 12px; margin-bottom: 16px; }}
  .kpi-card {{
      flex: 1; background: {CARD_BG}; border: 1px solid {BORDER};
      border-radius: 8px; padding: 16px 18px 12px;
  }}
  .kpi-label {{
      font-size: 0.7rem; color: {TEXT_MUTED}; text-transform: uppercase;
      letter-spacing: 0.06em; margin-bottom: 2px;
  }}
  .kpi-value {{ font-size: 1.55rem; font-weight: 700; color: {TEXT_MAIN}; line-height: 1.2; }}
  .kpi-sub   {{ font-size: 0.75rem; color: {TEXT_MUTED}; margin-top: 2px; }}
  @media (max-width: 768px) {{
      .kpi-row {{ flex-wrap: wrap; }}
      .kpi-card {{ flex: 1 1 140px; }}
  }}

  /* section labels */
  .sec {{
      font-size: 0.78rem; font-weight: 600; color: {TEXT_MUTED};
      text-transform: uppercase; letter-spacing: 0.06em; margin: 20px 0 8px;
  }}

  /* hide default metric cards — we use custom HTML ones */
  div[data-testid="stMetric"] {{ display: none; }}
</style>
""", unsafe_allow_html=True)


# ── CHART HELPER ──────────────────────────────────────────────────────────────
def apply_theme(fig, h=370):
    """One shared dark template for every Plotly chart."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=h,
        font=dict(family="Inter, sans-serif", size=12, color=TEXT_MUTED),
        title_font=dict(size=13, color=TEXT_MAIN),
        margin=dict(l=48, r=16, t=40, b=36),
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0, font_size=11,
                    itemsizing="constant"),   # legible legend symbols for tiny scatter markers
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=BORDER)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=BORDER)
    return fig


# ── DATA ──────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    for name in ("master_timeseries.csv", "geo_summary.csv", "im3_atlas_full.csv"):
        if not (CLEAN / name).exists():
            st.error(f"Missing `{CLEAN / name}`. Run the notebook first.")
            st.stop()
    master = pd.read_csv(CLEAN / "master_timeseries.csv")
    master["Timestamp"] = pd.to_datetime(master["Timestamp"], utc=True)
    master["Date_Local"] = pd.to_datetime(master["Timestamp_Local"].str[:10])
    if "data_type" not in master.columns:          # files written before synthetic rows existed
        master["data_type"] = "real"
    # Full atlas (all states, written by the notebook); focus regions are a subset of it
    im3_full = pd.read_csv(CLEAN / "im3_atlas_full.csv")
    im3 = im3_full[im3_full["Region"] != "Other"]
    return master, pd.read_csv(CLEAN / "geo_summary.csv"), im3, im3_full


master_all, geo_all, im3_all, im3_full_all = load_data()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")
    data_mode = st.radio(
        "Data mode", ["Real data", "Real + synthetic (demo)"], index=0,
        help="Real data = measured observations only (default). The demo mode adds generated "
             "synthetic hours (data_type = 'synthetic') for demonstration; they are not measurements.",
    )
    demo = data_mode != "Real data"
    # Every chart, KPI and table below is computed from `base`, so no view mixes populations silently
    base = master_all if demo else master_all[master_all["data_type"] == "real"]
    sel_regions = st.multiselect(
        "Region", sorted(base["Region"].unique()), default=sorted(base["Region"].unique()),
    )
    sel_seasons = st.multiselect("Season", SEASON_ORDER, default=SEASON_ORDER)
    resolution = st.radio("Resolution", ["Daily", "Hourly"], index=0,
                          help="Hourly renders ~100 k points — may be slow.")
    hourly = resolution == "Hourly"

    with st.expander("About this project"):
        st.markdown(
            "Multi-source geospatial analytics platform showing when and where "
            "the electric grid is stressed in four U.S. data-center hub regions.\n\n"
            "**Sources:** PJM Kaggle CSVs (2015–2017), EIA-930 API (2019–2021), "
            "NREL NSRDB weather/solar, IM3 Data Center Atlas v2026.02.09 (ODbL).\n\n"
            "**Stress Index** is a percentile rank (0–100) of demand within each "
            "region — not an engineering threshold. Cross-region comparison is not meaningful."
        )

if not sel_regions or not sel_seasons:
    st.warning("Select at least one region and season.")
    st.stop()

master = base[
    base["Region"].isin(sel_regions) & base["Season"].isin(sel_seasons)
].copy()
SYN_TAG = " (synthetic)"
syn_tag = lambda row: SYN_TAG if row["data_type"] == "synthetic" else ""
geo = geo_all[geo_all["Region"].isin(sel_regions)].copy()
im3 = im3_all[im3_all["Region"].isin(sel_regions)].copy()

if master.empty:
    st.warning("No data for the selected filters.")
    st.stop()

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown(
    f"<h2 style='margin:0 0 2px; color:{TEXT_MAIN};'>Data Center Energy Stress Predictor</h2>"
    f"<p style='color:{TEXT_MUTED}; margin:0 0 14px; font-size:0.85rem;'>"
    "Virginia · Ohio · Texas · Georgia</p>",
    unsafe_allow_html=True,
)

# ── DEMONSTRATION MODE NOTICE ─────────────────────────────────────────────────
if demo:
    n_syn = int((master["data_type"] == "synthetic").sum())
    st.warning(
        f"**Demonstration mode.** {n_syn:,} of the {len(master):,} hours shown are **synthetic** — generated "
        "from real-day templates for demonstration, **not measured demand or weather**. Synthetic periods: "
        "Virginia/Ohio Jan–Jul 2018 and Texas/Georgia Jan–Jul 2022 (labels only; they do not describe those dates). "
        "Data-center facilities are always real. Switch Data mode to 'Real data' for the analytical results."
    )
    with st.expander("Compare real-only vs real + synthetic (current filters)"):
        def summ(d):
            return d.groupby("Region")["Demand_MW"].agg(hours="size", avg="mean", peak="max")
        r_only, both = summ(master[master["data_type"] == "real"]), summ(master)
        cmp_tbl = pd.DataFrame({
            "Real hours": r_only["hours"], "Synthetic hours": both["hours"] - r_only["hours"],
            "Avg MW — real only": r_only["avg"].round(0), "Avg MW — real + synthetic": both["avg"].round(0),
            "Peak MW — real only": r_only["peak"], "Peak MW — real + synthetic": both["peak"],
        }).reindex(sel_regions).reset_index().rename(columns={"index": "Region"})
        st.dataframe(cmp_tbl, hide_index=True)
        st.caption("Synthetic rows cover January–July only, so pooled averages shift toward winter/spring. "
                   "Synthetic Stress_Index values are placed on each region's real percentile scale.")

# ── KPI ROW ───────────────────────────────────────────────────────────────────
# Regions differ in grid area and years, so demand is reported per region, never pooled
reg_avg = master.groupby("Region")["Demand_MW"].mean().reindex(sel_regions)
reg_years = master.groupby("Region")["Year"].agg(lambda y: f"{y.min()}–{y.max()}").reindex(sel_regions)
if len(sel_regions) == 1:
    avg_html = f'{reg_avg.iloc[0]:,.0f} <span style="font-size:.85rem;font-weight:400;">MW</span>'
    avg_sub = f"{sel_regions[0]}, {reg_years.iloc[0]}"
else:
    avg_html = "".join(
        f'<div style="font-size:.85rem;font-weight:500;line-height:1.5;">'
        f'<span style="color:{REGION_COLOR[r]};">{r}</span> {v:,.0f} MW</div>'
        for r, v in reg_avg.items()
    )
    avg_sub = "per region; not pooled"
if demo:
    avg_sub += " · incl. synthetic"
peak_row = master.loc[master["Demand_MW"].idxmax()]
peak_demand = peak_row["Demand_MW"]
peak_region = peak_row["Region"]
peak_when = str(peak_row["Timestamp_Local"])[:10] + syn_tag(peak_row)
total_dcs = im3["id"].nunique()
total_dcs_nationwide = im3_full_all["id"].nunique()
p95_pct = (master["Stress_Index"] >= 95).mean() * 100

st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card">
    <div class="kpi-label">Regions</div>
    <div class="kpi-value">{len(sel_regions)}</div>
    <div class="kpi-sub">of 4 selected</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Data Centers</div>
    <div class="kpi-value">{total_dcs:,}</div>
    <div class="kpi-sub">of {total_dcs_nationwide:,} nationwide</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Avg Demand</div>
    <div class="kpi-value">{avg_html}</div>
    <div class="kpi-sub">{avg_sub}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Highest Regional Peak</div>
    <div class="kpi-value">{peak_demand:,.0f} <span style="font-size:.85rem;font-weight:400;">MW</span></div>
    <div class="kpi-sub">{peak_region}, {peak_when}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">High Stress Hours</div>
    <div class="kpi-value">{p95_pct:.1f}%</div>
    <div class="kpi-sub">hours ≥ each region's own 95th pct{" · incl. synthetic" if demo else ""}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────────────────────────────────────
tab_ov, tab_demand, tab_stress, tab_wx, tab_geo = st.tabs([
    "Overview", "Demand", "Stress Analysis", "Weather & Solar", "Geospatial",
])

# ══════════════════════════════════════════════════════════════════════════════
#  OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab_ov:
    st.markdown('<p class="sec">Demand Time Series</p>', unsafe_allow_html=True)
    if hourly:
        ts = master[["Region", "data_type", "Timestamp", "Demand_MW"]].rename(columns={"Timestamp": "Date"})
    else:
        ts = (
            master.groupby(["Region", "data_type", "Date_Local"])["Demand_MW"]
            .mean().reset_index().rename(columns={"Date_Local": "Date"})
        )
    if not demo:
        ts = ts.drop(columns="data_type", errors="ignore")
    # Demo mode: synthetic periods drawn dotted and named in the legend
    dash = dict(line_dash="data_type", line_dash_map={"real": "solid", "synthetic": "dot"}) if demo else {}

    fig = px.line(ts, x="Date", y="Demand_MW", color="Region",
                  labels={"Demand_MW": "MW", "Date": "", "data_type": "Data"},
                  color_discrete_map=REGION_COLOR, **dash)
    apply_theme(fig, 380)
    fig.update_layout(legend=dict(orientation="h", y=1.06, x=0.5, xanchor="center"))
    st.plotly_chart(fig)

    # Per-region cards
    st.markdown('<p class="sec">Region Snapshot</p>', unsafe_allow_html=True)
    cols = st.columns(len(sel_regions))
    for i, reg in enumerate(sel_regions):
        rm = master[master["Region"] == reg]
        rg = geo[geo["Region"] == reg]
        pk = rm["Demand_MW"].max()
        pk_row = rm.loc[rm["Demand_MW"].idxmax()]
        pk_ts = str(pk_row["Timestamp_Local"])[:16] + syn_tag(pk_row)
        dc = int(rg["unique_DCs"].values[0]) if len(rg) else 0
        c = REGION_COLOR[reg]
        with cols[i]:
            st.markdown(
                f"<div style='background:{CARD_BG}; border:1px solid {BORDER}; "
                f"border-left:3px solid {c}; border-radius:6px; padding:14px;'>"
                f"<div style='font-weight:600; color:{TEXT_MAIN}; margin-bottom:6px;'>{reg}</div>"
                f"<div style='font-size:.8rem; color:{TEXT_MUTED}; line-height:1.8;'>"
                f"Peak: <b style='color:{TEXT_MAIN};'>{pk:,.0f} MW</b><br>"
                f"When: {pk_ts}<br>"
                f"Avg temp: <b style='color:{TEXT_MAIN};'>{rm['Temperature'].mean():.1f} °C</b><br>"
                f"Avg GHI: <b style='color:{TEXT_MAIN};'>{rm['GHI'].mean():.0f} W/m²</b><br>"
                f"Data centers: <b style='color:{TEXT_MAIN};'>{dc}</b>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

# ══════════════════════════════════════════════════════════════════════════════
#  DEMAND
# ══════════════════════════════════════════════════════════════════════════════
with tab_demand:
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<p class="sec">Hourly Profile — Weekday vs Weekend</p>', unsafe_allow_html=True)
        prof = master.groupby(["Region", "Hour", "Is_Weekend"])["Demand_MW"].mean().reset_index()
        prof["Type"] = prof["Is_Weekend"].map({0: "Weekday", 1: "Weekend"})
        fig = px.line(prof, x="Hour", y="Demand_MW", color="Region", line_dash="Type",
                      labels={"Demand_MW": "Avg MW", "Hour": "Hour (local)"},
                      color_discrete_map=REGION_COLOR)
        apply_theme(fig, 360)
        fig.update_xaxes(dtick=3)
        st.plotly_chart(fig)

    with c2:
        st.markdown('<p class="sec">Seasonal Demand</p>', unsafe_allow_html=True)
        seas = master.groupby(["Region", "Season"])["Demand_MW"].mean().reset_index()
        seas["Season"] = pd.Categorical(seas["Season"], SEASON_ORDER, ordered=True)
        fig = px.bar(seas.sort_values("Season"), x="Season", y="Demand_MW", color="Region",
                     barmode="group", labels={"Demand_MW": "Avg MW", "Season": ""},
                     color_discrete_map=REGION_COLOR)
        apply_theme(fig, 360)
        st.plotly_chart(fig)

    c3, c4 = st.columns(2)

    with c3:
        st.markdown('<p class="sec">Day of Week</p>', unsafe_allow_html=True)
        dow = master.groupby(["Region", "DayOfWeek"])["Demand_MW"].mean().reset_index()
        dow_names = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
        dow["Day"] = dow["DayOfWeek"].map(dow_names)
        dow["Day"] = pd.Categorical(dow["Day"], list(dow_names.values()), ordered=True)
        fig = px.bar(dow.sort_values("Day"), x="Day", y="Demand_MW", color="Region",
                     barmode="group", labels={"Demand_MW": "Avg MW", "Day": ""},
                     color_discrete_map=REGION_COLOR)
        apply_theme(fig, 340)
        st.plotly_chart(fig)

    with c4:
        st.markdown('<p class="sec">Demand Distribution</p>', unsafe_allow_html=True)
        fig = px.violin(master, x="Region", y="Demand_MW", color="Region", box=True,
                        labels={"Demand_MW": "MW"}, color_discrete_map=REGION_COLOR)
        apply_theme(fig, 340)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig)

    st.markdown('<p class="sec">Monthly Trend</p>', unsafe_allow_html=True)
    mo = master.groupby(["Region", "data_type", "Year", "Month"])["Demand_MW"].mean().reset_index()
    if not demo:
        mo = mo.drop(columns="data_type")
    mo["Period"] = pd.to_datetime(
        mo["Year"].astype(str) + "-" + mo["Month"].astype(str).str.zfill(2) + "-01"
    )
    fig = px.line(mo, x="Period", y="Demand_MW", color="Region", markers=True,
                  labels={"Demand_MW": "Avg MW", "Period": "", "data_type": "Data"},
                  color_discrete_map=REGION_COLOR, **dash)
    apply_theme(fig, 320)
    fig.update_traces(marker_size=5)
    st.plotly_chart(fig)

# ══════════════════════════════════════════════════════════════════════════════
#  STRESS
# ══════════════════════════════════════════════════════════════════════════════
with tab_stress:
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<p class="sec">Stress Index Distribution</p>', unsafe_allow_html=True)
        fig = px.box(master, x="Region", y="Stress_Index", color="Region",
                     labels={"Stress_Index": "Stress Index"}, color_discrete_map=REGION_COLOR)
        apply_theme(fig, 370)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig)

    with c2:
        st.markdown('<p class="sec">Stress by Season</p>', unsafe_allow_html=True)
        ss = master.groupby(["Region", "Season"])["Stress_Index"].mean().reset_index()
        ss["Season"] = pd.Categorical(ss["Season"], SEASON_ORDER, ordered=True)
        fig = px.bar(ss.sort_values("Season"), x="Season", y="Stress_Index", color="Region",
                     barmode="group", labels={"Stress_Index": "Avg Stress", "Season": ""},
                     color_discrete_map=REGION_COLOR)
        apply_theme(fig, 370)
        st.plotly_chart(fig)

    st.markdown('<p class="sec">Hour × Month Heatmap</p>', unsafe_allow_html=True)
    hm_reg = st.selectbox("Region", sel_regions, key="hm")
    hm = (
        master[master["Region"] == hm_reg]
        .groupby(["Month", "Hour"])["Stress_Index"].mean().reset_index()
    )
    hm_piv = hm.pivot(index="Hour", columns="Month", values="Stress_Index")
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    present = sorted(hm_piv.columns)
    fig = px.imshow(hm_piv, aspect="auto", color_continuous_scale="Inferno",
                    labels={"x": "Month", "y": "Hour", "color": "Stress"},
                    x=[month_labels[m - 1] for m in present])
    apply_theme(fig, 400)
    fig.update_layout(title=dict(text=f"{hm_reg} — Stress by Hour & Month"))
    # Same Inferno stops written as rgb() strings: in the browser, Streamlit recolored the
    # near-black hex stop (#000004) at the low end of the scale
    fig.update_coloraxes(colorscale=[
        [s, "rgb({},{},{})".format(*pc.hex_to_rgb(c))]
        for s, c in pc.make_colorscale(pc.sequential.Inferno)
    ])
    st.plotly_chart(fig)

    # Stress is a within-region percentile, so rank events inside each region (20 rows split evenly)
    n_per = max(1, 20 // len(sel_regions))
    st.markdown(f'<p class="sec">Top Stress Events — top {n_per} per region</p>', unsafe_allow_html=True)
    n_hours = base.groupby("Region").size()
    top = (master.sort_values("Stress_Index", ascending=False, kind="stable")
           .groupby("Region", sort=False).head(n_per).copy())
    top["Rank in region"] = top.groupby("Region")["Stress_Index"].rank(ascending=False, method="min").astype(int)
    top = top.sort_values(["Region", "Rank in region"])
    top["Of hours"] = top["Region"].map(n_hours).map("{:,}".format)
    top = top[["Region", "Rank in region", "Of hours", "Timestamp_Local", "Demand_MW",
               "Temperature", "GHI", "Stress_Index"]]
    top.columns = ["Region", "Rank in region", "Of hours", "Time (local)", "Demand MW",
                   "Temp °C", "GHI W/m²", "Stress"]
    top["Time (local)"] = top["Time (local)"].str[:16]
    top["Demand MW"] = top["Demand MW"].map("{:,.0f}".format)
    top["Stress"] = top["Stress"].map("{:.3f}".format)
    top["Temp °C"] = top["Temp °C"].map("{:.1f}".format)
    top["GHI W/m²"] = top["GHI W/m²"].map("{:.0f}".format)
    if demo:   # label every event with its population
        top.insert(1, "Data", master.loc[top.index, "data_type"])
    st.dataframe(top, hide_index=True)
    st.caption(
        "Rank is among the hours in the current season filter (tied hours share a rank); "
        "Stress is the percentile of that hour's "
        "demand within its region's full record (all seasons). Because each region is ranked against "
        "itself, a Stress of 100 in Texas and in Ohio means 'that region's highest hour', not equal "
        "grid stress — compare MW within a region, not Stress across regions."
    )

# ══════════════════════════════════════════════════════════════════════════════
#  WEATHER & SOLAR
# ══════════════════════════════════════════════════════════════════════════════
with tab_wx:
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<p class="sec">Temperature vs Demand</p>', unsafe_allow_html=True)
        # Random 1/6 sample per region (fixed seed) keeps every hour of day represented
        samp = master.groupby("Region").sample(frac=1 / 6, random_state=42)
        fig = go.Figure()
        for reg in sel_regions:
            rd = samp[samp["Region"] == reg]
            fig.add_trace(go.Scatter(
                x=rd["Temperature"], y=rd["Demand_MW"], mode="markers", name=reg,
                marker=dict(size=3, color=REGION_COLOR[reg], opacity=0.35),
            ))
        apply_theme(fig, 390)
        fig.update_layout(xaxis_title="Temperature (°C)", yaxis_title="Demand (MW)")
        st.plotly_chart(fig)

        corrs = []
        for reg in sel_regions:
            rd = master[master["Region"] == reg]
            corrs.append({"Region": reg, "Pearson r": f"{rd['Temperature'].corr(rd['Demand_MW']):.3f}"})
        st.dataframe(pd.DataFrame(corrs), hide_index=True)
        st.caption("Scatter shows a random 1/6 sample per region; Pearson r uses all filtered hours.")

    with c2:
        st.markdown('<p class="sec">Solar Irradiance vs Demand</p>', unsafe_allow_html=True)
        day = samp[samp["GHI"] > 0]
        fig = go.Figure()
        for reg in sel_regions:
            rd = day[day["Region"] == reg]
            fig.add_trace(go.Scatter(
                x=rd["GHI"], y=rd["Demand_MW"], mode="markers", name=reg,
                marker=dict(size=3, color=REGION_COLOR[reg], opacity=0.35),
            ))
        apply_theme(fig, 390)
        fig.update_layout(xaxis_title="GHI (W/m²)", yaxis_title="Demand (MW)")
        st.plotly_chart(fig)
        ghi_r = ", ".join(
            f"{reg} {master[(master['Region'] == reg) & (master['GHI'] > 0)][['GHI', 'Demand_MW']].corr().iloc[0, 1]:+.2f}"
            for reg in sel_regions
        )
        st.caption(f"Daytime hours only (GHI > 0), same random sample. "
                   f"Pearson r over all filtered daytime hours: {ghi_r}.")

    c3, c4 = st.columns(2)

    with c3:
        st.markdown('<p class="sec">Solar Profile by Hour</p>', unsafe_allow_html=True)
        sp = master.groupby(["Region", "Hour"])["GHI"].mean().reset_index()
        fig = px.area(sp, x="Hour", y="GHI", color="Region",
                      labels={"GHI": "Avg GHI (W/m²)", "Hour": "Hour (local)"},
                      color_discrete_map=REGION_COLOR)
        apply_theme(fig, 330)
        # Overlapping (not stacked) areas: each curve is one region's own mean GHI
        fig.update_traces(line_width=1, opacity=0.6, stackgroup=None, fill="tozeroy")
        fig.update_xaxes(dtick=3)
        st.plotly_chart(fig)

    with c4:
        st.markdown('<p class="sec">Wind Speed by Hour</p>', unsafe_allow_html=True)
        wp = master.groupby(["Region", "Hour"])["Wind Speed"].mean().reset_index()
        fig = px.line(wp, x="Hour", y="Wind Speed", color="Region", markers=True,
                      labels={"Wind Speed": "m/s", "Hour": "Hour (local)"},
                      color_discrete_map=REGION_COLOR)
        apply_theme(fig, 330)
        fig.update_traces(marker_size=4)
        fig.update_xaxes(dtick=3)
        st.plotly_chart(fig)

    st.markdown('<p class="sec">Monthly Solar Components</p>', unsafe_allow_html=True)
    sol_reg = st.selectbox("Region", sel_regions, key="sol_r")
    sm = master[master["Region"] == sol_reg].groupby("Month")[["GHI", "DNI", "DHI"]].mean().reset_index()
    smm = sm.melt(id_vars="Month", var_name="Component", value_name="W/m²")
    fig = px.bar(smm, x="Month", y="W/m²", color="Component", barmode="group",
                 color_discrete_map={"GHI": "#E89B3E", "DNI": "#D9534F", "DHI": "#4A90D9"})
    apply_theme(fig, 320)
    fig.update_xaxes(
        tickvals=list(range(1, 13)),
        ticktext=["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    )
    st.plotly_chart(fig)

# ══════════════════════════════════════════════════════════════════════════════
#  GEOSPATIAL
# ══════════════════════════════════════════════════════════════════════════════
with tab_geo:
    st.markdown('<p class="sec">Data Center Locations</p>', unsafe_allow_html=True)

    # Selected focus regions in color; other states stay as gray national context
    OTHER_RGB = [85, 91, 102]  # neutral gray for non-focus states
    rgb_with_other = {**REGION_RGB, "Other": OTHER_RGB}

    mdf = im3_full_all[im3_full_all["Region"].isin(sel_regions + ["Other"])].copy()
    mdf["cr"] = mdf["Region"].map({r: c[0] for r, c in rgb_with_other.items()}).astype(int)
    mdf["cg"] = mdf["Region"].map({r: c[1] for r, c in rgb_with_other.items()}).astype(int)
    mdf["cb"] = mdf["Region"].map({r: c[2] for r, c in rgb_with_other.items()}).astype(int)
    mdf["tip"] = (
        mdf["name"].fillna("Unnamed") + " | " + mdf["type"] + " | "
        + mdf["sqft"].apply(lambda x: f"{x:,.0f} sqft" if pd.notnull(x) else "floor area not available")
        + " | " + mdf["state"].fillna("")
    )
    has_area = mdf["sqft"].notna()
    area_df = mdf[has_area].copy()
    # Radius (m) ∝ sqrt(floor area), so marker AREA ∝ sq ft. Largest facility ≈ 150 km (~14 px at the
    # initial zoom); on-screen size is kept between 2 and 30 px so small sites stay visible.
    area_df["radius"] = (150_000 * np.sqrt(area_df["sqft"] / im3_full_all["sqft"].max())).astype(float)
    cols = ["lon", "lat", "cr", "cg", "cb", "tip"]

    area_layer = pdk.Layer(
        "ScatterplotLayer",
        data=area_df[cols + ["radius"]],
        get_position="[lon, lat]",
        get_radius="radius",
        radius_min_pixels=2,
        radius_max_pixels=30,
        get_fill_color="[cr, cg, cb, 180]",
        pickable=True,
        auto_highlight=True,
        highlight_color=[255, 255, 255, 60],
    )
    # Point records have no floor area: hollow rings at a fixed size, not a guessed area
    point_layer = pdk.Layer(
        "ScatterplotLayer",
        data=mdf[~has_area][cols],
        get_position="[lon, lat]",
        get_radius=1,
        radius_min_pixels=3,     # fixed 3 px ring: a marker, not a size
        filled=False,
        stroked=True,
        line_width_min_pixels=1.5,
        get_line_color="[cr, cg, cb, 230]",
        pickable=True,
    )

    view = pdk.ViewState(
        latitude=38.0,
        longitude=-96.0,
        zoom=3.5,
        pitch=0,
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[area_layer, point_layer],
            initial_view_state=view,
            tooltip={"text": "{tip}"},
            map_style=MAP_STYLE,
        ),
        height=480,
    )
    st.caption(
        f"Showing {mdf['id'].nunique():,} of {im3_full_all['id'].nunique():,} IM3 data centers "
        f"({im3_full_all['state'].nunique()} states). Colored = selected regions; gray = non-focus states. "
        f"Filled dots: area ∝ floor area (sq ft), shown between 2 and 30 px; hollow rings are {(~has_area).sum()} point records "
        "with no floor area in the source. IM3 is a Feb 2026 snapshot."
    )

    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<p class="sec">DC Type Breakdown</p>', unsafe_allow_html=True)
        dt = im3.groupby(["Region", "type"])["id"].nunique().reset_index()
        dt.columns = ["Region", "Type", "Count"]
        fig = px.bar(dt, x="Region", y="Count", color="Type", barmode="stack",
                     color_discrete_map={
                         "building": "#4A90D9", "campus": "#3AAFA9", "point": "#E89B3E",
                     })
        apply_theme(fig, 350)
        st.plotly_chart(fig)

    with c2:
        st.markdown('<p class="sec">DC Concentration vs Peak Demand</p>', unsafe_allow_html=True)
        # Demand stats follow the region AND season filters
        bub = master.groupby("Region")["Demand_MW"].agg(avg="mean", peak="max")
        bub["dcs"] = im3.groupby("Region")["id"].nunique()
        sizeref = 2 * bub["avg"].max() / 45 ** 2   # largest bubble ≈ 45 px across
        fig = go.Figure()
        for reg, row in bub.iterrows():
            fig.add_trace(go.Scatter(
                x=[row["dcs"]], y=[row["peak"]],
                mode="markers+text", text=[f"{reg}<br>avg {row['avg']:,.0f} MW"],
                textposition="top center", name=reg, cliponaxis=False,
                marker=dict(
                    size=[row["avg"]], sizemode="area", sizeref=sizeref, sizemin=6,
                    color=REGION_COLOR[reg], opacity=0.85,
                    line=dict(width=1, color=BORDER),
                ),
                textfont=dict(size=11, color=TEXT_MUTED),
            ))
        apply_theme(fig, 350)
        fig.update_layout(
            xaxis_title="Unique Data Centers", yaxis_title="Peak Demand (MW)",
            showlegend=False,
        )
        # Headroom so bubble labels are not clipped at the plot edges
        fig.update_xaxes(range=[0, bub["dcs"].max() * 1.2])
        fig.update_yaxes(range=[0, bub["peak"].max() * 1.3])
        st.plotly_chart(fig)
        st.caption("Bubble area ∝ average demand (MW) for the selected seasons; "
                   "each bubble is labeled with its value. Four points cannot establish a relationship.")

    st.markdown('<p class="sec">Region Summary</p>', unsafe_allow_html=True)
    ds = master.groupby("Region")["Demand_MW"].agg(["mean", "max", "min", "std"]).round(1).reset_index()
    ss = master.groupby("Region")["Stress_Index"].agg(
        mean="mean", p95=lambda x: x.quantile(0.95)
    ).round(1).reset_index()
    ts = master.groupby("Region")["Temperature"].agg(avg_t="mean", max_t="max").round(1).reset_index()
    dc = im3.groupby("Region")["id"].nunique().reset_index().rename(columns={"id": "DCs"})
    tbl = ds.merge(ss, on="Region").merge(ts, on="Region").merge(dc, on="Region", how="left")
    tbl.columns = ["Region", "Avg MW", "Peak MW", "Min MW", "Std MW",
                    "Avg Stress", "Stress P95", "Avg °C", "Max °C", "DCs"]
    st.dataframe(tbl, hide_index=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "**Stress Index** is a relative, percentile-based measure (0–100) within each region. "
    "Cross-region comparisons are not meaningful. It is not a grid-capacity measure, and no "
    "prediction is performed: all figures describe historical data. Hours are local interval starts. "
    "Sources: PJM Kaggle (2015–2017) · EIA-930 (2019–2021) · NSRDB · IM3 Atlas v2026.02.09 (ODbL)."
)
