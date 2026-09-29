"""Streamlit dashboard — Data Center Energy Stress Predictor.

Reads data/clean/*.csv only; makes no API calls at runtime.
"""

import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Energy Stress Predictor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
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
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0, font_size=11),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=BORDER)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=BORDER)
    return fig


# ── DATA ──────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    for name in ("master_timeseries.csv", "geo_summary.csv", "im3_clean.csv"):
        if not (CLEAN / name).exists():
            st.error(f"Missing `{CLEAN / name}`. Run the notebook first.")
            st.stop()
    master = pd.read_csv(CLEAN / "master_timeseries.csv")
    master["Timestamp"] = pd.to_datetime(master["Timestamp"], utc=True)
    im3 = pd.read_csv(CLEAN / "im3_clean.csv")
    # Full atlas (all 47 states) for the nationwide map layer
    im3_full_path = CLEAN / "im3_atlas_full.csv"
    im3_full = pd.read_csv(im3_full_path) if im3_full_path.exists() else im3
    return master, pd.read_csv(CLEAN / "geo_summary.csv"), im3, im3_full


master_all, geo_all, im3_all, im3_full_all = load_data()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")
    sel_regions = st.multiselect(
        "Region", sorted(master_all["Region"].unique()), default=sorted(master_all["Region"].unique()),
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

master = master_all[
    master_all["Region"].isin(sel_regions) & master_all["Season"].isin(sel_seasons)
].copy()
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

# ── KPI ROW ───────────────────────────────────────────────────────────────────
avg_demand = master["Demand_MW"].mean()
peak_demand = master["Demand_MW"].max()
peak_region = master.loc[master["Demand_MW"].idxmax(), "Region"]
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
    <div class="kpi-value">{avg_demand:,.0f} <span style="font-size:.85rem;font-weight:400;">MW</span></div>
    <div class="kpi-sub">filtered period</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Peak Demand</div>
    <div class="kpi-value">{peak_demand:,.0f} <span style="font-size:.85rem;font-weight:400;">MW</span></div>
    <div class="kpi-sub">{peak_region}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">High Stress Hours</div>
    <div class="kpi-value">{p95_pct:.1f}%</div>
    <div class="kpi-sub">above 95th percentile</div>
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
        ts = master[["Region", "Timestamp", "Demand_MW"]].rename(columns={"Timestamp": "Date"})
    else:
        ts = (
            master.groupby(["Region", master["Timestamp"].dt.date])["Demand_MW"]
            .mean().reset_index().rename(columns={"Timestamp": "Date"})
        )
        ts["Date"] = pd.to_datetime(ts["Date"])

    fig = px.line(ts, x="Date", y="Demand_MW", color="Region",
                  labels={"Demand_MW": "MW", "Date": ""}, color_discrete_map=REGION_COLOR)
    apply_theme(fig, 380)
    fig.update_layout(legend=dict(orientation="h", y=1.06, x=0.5, xanchor="center"))
    st.plotly_chart(fig, use_container_width=True)

    # Per-region cards
    st.markdown('<p class="sec">Region Snapshot</p>', unsafe_allow_html=True)
    cols = st.columns(len(sel_regions))
    for i, reg in enumerate(sel_regions):
        rm = master[master["Region"] == reg]
        rg = geo[geo["Region"] == reg]
        pk = rm["Demand_MW"].max()
        pk_ts = str(rm.loc[rm["Demand_MW"].idxmax(), "Timestamp_Local"])[:16]
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
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown('<p class="sec">Seasonal Demand</p>', unsafe_allow_html=True)
        seas = master.groupby(["Region", "Season"])["Demand_MW"].mean().reset_index()
        seas["Season"] = pd.Categorical(seas["Season"], SEASON_ORDER, ordered=True)
        fig = px.bar(seas.sort_values("Season"), x="Season", y="Demand_MW", color="Region",
                     barmode="group", labels={"Demand_MW": "Avg MW", "Season": ""},
                     color_discrete_map=REGION_COLOR)
        apply_theme(fig, 360)
        st.plotly_chart(fig, use_container_width=True)

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
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        st.markdown('<p class="sec">Demand Distribution</p>', unsafe_allow_html=True)
        fig = px.violin(master, x="Region", y="Demand_MW", color="Region", box=True,
                        labels={"Demand_MW": "MW"}, color_discrete_map=REGION_COLOR)
        apply_theme(fig, 340)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<p class="sec">Monthly Trend</p>', unsafe_allow_html=True)
    mo = master.groupby(["Region", "Year", "Month"])["Demand_MW"].mean().reset_index()
    mo["Period"] = pd.to_datetime(
        mo["Year"].astype(str) + "-" + mo["Month"].astype(str).str.zfill(2) + "-01"
    )
    fig = px.line(mo, x="Period", y="Demand_MW", color="Region", markers=True,
                  labels={"Demand_MW": "Avg MW", "Period": ""}, color_discrete_map=REGION_COLOR)
    apply_theme(fig, 320)
    fig.update_traces(marker_size=5)
    st.plotly_chart(fig, use_container_width=True)

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
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown('<p class="sec">Stress by Season</p>', unsafe_allow_html=True)
        ss = master.groupby(["Region", "Season"])["Stress_Index"].mean().reset_index()
        ss["Season"] = pd.Categorical(ss["Season"], SEASON_ORDER, ordered=True)
        fig = px.bar(ss.sort_values("Season"), x="Season", y="Stress_Index", color="Region",
                     barmode="group", labels={"Stress_Index": "Avg Stress", "Season": ""},
                     color_discrete_map=REGION_COLOR)
        apply_theme(fig, 370)
        st.plotly_chart(fig, use_container_width=True)

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
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<p class="sec">Top 20 Stress Events</p>', unsafe_allow_html=True)
    top = master.nlargest(20, "Stress_Index")[
        ["Region", "Timestamp_Local", "Demand_MW", "Temperature", "GHI", "Stress_Index"]
    ].copy()
    top.columns = ["Region", "Time (local)", "Demand MW", "Temp °C", "GHI W/m²", "Stress"]
    top["Demand MW"] = top["Demand MW"].map("{:,.0f}".format)
    top["Stress"] = top["Stress"].map("{:.1f}".format)
    top["Temp °C"] = top["Temp °C"].map("{:.1f}".format)
    top["GHI W/m²"] = top["GHI W/m²"].map("{:.0f}".format)
    st.dataframe(top, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
#  WEATHER & SOLAR
# ══════════════════════════════════════════════════════════════════════════════
with tab_wx:
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<p class="sec">Temperature vs Demand</p>', unsafe_allow_html=True)
        samp = master.iloc[::6].copy()
        fig = go.Figure()
        for reg in sel_regions:
            rd = samp[samp["Region"] == reg]
            fig.add_trace(go.Scatter(
                x=rd["Temperature"], y=rd["Demand_MW"], mode="markers", name=reg,
                marker=dict(size=3, color=REGION_COLOR[reg], opacity=0.35),
            ))
        apply_theme(fig, 390)
        fig.update_layout(xaxis_title="Temperature (°C)", yaxis_title="Demand (MW)")
        st.plotly_chart(fig, use_container_width=True)

        corrs = []
        for reg in sel_regions:
            rd = master[master["Region"] == reg]
            corrs.append({"Region": reg, "Pearson r": f"{rd['Temperature'].corr(rd['Demand_MW']):.3f}"})
        st.dataframe(pd.DataFrame(corrs), use_container_width=True, hide_index=True)

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
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Daytime only (GHI > 0). Solar availability does not directly reduce demand — "
                   "temperature-driven HVAC loads dominate the relationship.")

    c3, c4 = st.columns(2)

    with c3:
        st.markdown('<p class="sec">Solar Profile by Hour</p>', unsafe_allow_html=True)
        sp = master.groupby(["Region", "Hour"])["GHI"].mean().reset_index()
        fig = px.area(sp, x="Hour", y="GHI", color="Region",
                      labels={"GHI": "Avg GHI (W/m²)", "Hour": "Hour (UTC)"},
                      color_discrete_map=REGION_COLOR)
        apply_theme(fig, 330)
        fig.update_traces(line_width=1, opacity=0.6)
        fig.update_xaxes(dtick=3)
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        st.markdown('<p class="sec">Wind Speed by Hour</p>', unsafe_allow_html=True)
        wp = master.groupby(["Region", "Hour"])["Wind Speed"].mean().reset_index()
        fig = px.line(wp, x="Hour", y="Wind Speed", color="Region", markers=True,
                      labels={"Wind Speed": "m/s", "Hour": "Hour (UTC)"},
                      color_discrete_map=REGION_COLOR)
        apply_theme(fig, 330)
        fig.update_traces(marker_size=4)
        fig.update_xaxes(dtick=3)
        st.plotly_chart(fig, use_container_width=True)

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
    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
#  GEOSPATIAL
# ══════════════════════════════════════════════════════════════════════════════
with tab_geo:
    st.markdown('<p class="sec">Data Center Locations</p>', unsafe_allow_html=True)

    # Use full nationwide atlas for the map; color focus regions, gray for others
    OTHER_RGB = [85, 91, 102]  # neutral gray for non-focus states
    rgb_with_other = {**REGION_RGB, "Other": OTHER_RGB}

    mdf = im3_full_all.dropna(subset=["lat", "lon"]).copy()
    mdf["sqft_fill"] = mdf["sqft"].fillna(50_000)
    mdf["radius"] = np.clip(np.sqrt(mdf["sqft_fill"]) * 2.5, 400, 10_000).astype(float)
    mdf["cr"] = mdf["Region"].map({r: c[0] for r, c in rgb_with_other.items()}).astype(int)
    mdf["cg"] = mdf["Region"].map({r: c[1] for r, c in rgb_with_other.items()}).astype(int)
    mdf["cb"] = mdf["Region"].map({r: c[2] for r, c in rgb_with_other.items()}).astype(int)
    mdf["tip"] = (
        mdf["name"].fillna("Unnamed") + " | " + mdf["type"] + " | "
        + mdf["sqft"].apply(lambda x: f"{x:,.0f} sqft" if pd.notnull(x) else "N/A")
        + " | " + mdf["state"].fillna("")
    )

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=mdf[["lon", "lat", "radius", "cr", "cg", "cb", "tip"]],
        get_position="[lon, lat]",
        get_radius="radius",
        get_fill_color="[cr, cg, cb, 180]",
        pickable=True,
        auto_highlight=True,
        highlight_color=[255, 255, 255, 60],
    )

    view = pdk.ViewState(
        latitude=38.0,
        longitude=-96.0,
        zoom=3.5,
        pitch=0,
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view,
            tooltip={"text": "{tip}"},
            map_style=MAP_STYLE,
        ),
        height=480,
    )
    st.caption(
        f"Showing all {im3_full_all['id'].nunique():,} data centers from the IM3 atlas "
        f"across {im3_full_all['state'].nunique()} states. "
        "Colored dots = demand analysis regions; gray = other states."
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
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown('<p class="sec">DC Concentration vs Peak Demand</p>', unsafe_allow_html=True)
        fig = go.Figure()
        for _, row in geo.iterrows():
            reg = row["Region"]
            fig.add_trace(go.Scatter(
                x=[row["unique_DCs"]], y=[row["peak_demand_MW"]],
                mode="markers+text", text=[reg], textposition="top center", name=reg,
                marker=dict(
                    size=max(14, row["avg_demand_MW"] / 1000),
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
        st.plotly_chart(fig, use_container_width=True)

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
    st.dataframe(tbl, use_container_width=True, hide_index=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "**Stress Index** is a relative, percentile-based measure (0–100) within each region. "
    "Cross-region comparisons are not meaningful. "
    "Sources: PJM Kaggle (2015–2017) · EIA-930 (2019–2021) · NSRDB · IM3 Atlas v2026.02.09 (ODbL)."
)
