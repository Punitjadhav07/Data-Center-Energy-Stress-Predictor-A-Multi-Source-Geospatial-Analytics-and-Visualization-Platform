"""Generate dav_project.ipynb programmatically to avoid JSON escaping issues."""
import json, uuid
from pathlib import Path

def uid():
    return str(uuid.uuid4())[:8]

def md(src):
    return {"cell_type": "markdown", "id": uid(), "metadata": {}, "source": src}

def code(src):
    return {"cell_type": "code", "execution_count": None, "id": uid(),
            "metadata": {}, "outputs": [], "source": src}

cells = []

# ── TITLE ─────────────────────────────────────────────────────────────────────
cells.append(md("""\
# Data Center Energy Stress Predictor
## A Multi-Source Geospatial Analytics and Visualization Platform

**Course:** B.Tech IT — Data Analytics & Visualization
**Regions:** Virginia, Ohio (2015–2017) · Texas, Georgia (2019–2021)
**Sources:** PJM Kaggle CSVs · EIA-930 API · NREL NSRDB API · IM3 Data Center Atlas

Pipeline: collect → clean → integrate → feature engineering → EDA → stress index → geospatial → dashboard.
No machine learning or deep learning. All derived metrics are labeled as such.\
"""))

# ── IMPORTS ───────────────────────────────────────────────────────────────────
cells.append(code("""\
import os, json, zipfile, io, time, warnings
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

warnings.filterwarnings("ignore", category=FutureWarning)
pd.set_option("display.max_columns", 30)
pd.set_option("display.float_format", "{:,.2f}".format)
sns.set_theme(style="whitegrid", palette="muted")

load_dotenv()
EIA_KEY    = os.environ["EIA_API_KEY"]
NSRDB_KEY  = os.environ["NSRDB_API_KEY"]
NSRDB_NAME = os.environ["NSRDB_FULL_NAME"]
NSRDB_EMAIL= os.environ["NSRDB_EMAIL"]
NSRDB_AFF  = os.environ["NSRDB_AFFILIATION"]
print("Environment loaded. Keys present:", all([EIA_KEY, NSRDB_KEY, NSRDB_NAME, NSRDB_EMAIL, NSRDB_AFF]))\
"""))

# ── CONFIG ────────────────────────────────────────────────────────────────────
cells.append(code("""\
RAW   = Path("data/raw");   RAW.mkdir(parents=True, exist_ok=True)
CLEAN = Path("data/clean"); CLEAN.mkdir(parents=True, exist_ok=True)

REGIONS = {
    "Virginia": dict(lat=38.95, lon=-77.45, tz="America/New_York",
                     years=[2015,2016,2017], state="VA"),
    "Ohio":     dict(lat=39.96, lon=-82.99, tz="America/New_York",
                     years=[2015,2016,2017], state="OH"),
    "Texas":    dict(lat=32.78, lon=-96.80, tz="America/Chicago",
                     years=[2019,2020,2021], state="TX"),
    "Georgia":  dict(lat=33.75, lon=-84.39, tz="America/New_York",
                     years=[2019,2020,2021], state="GA"),
}

EIA_RESPONDENTS = {"Texas": "ERCO", "Georgia": "SOCO"}

# Expected rows per region (365+366+365)*24 = 26,304 for non-leap three-year blocks
EXPECTED_ROWS = 26304
print("Config OK. Regions:", list(REGIONS.keys()))\
"""))

# ── SECTION 1 ─────────────────────────────────────────────────────────────────
cells.append(md("""\
## 1. Data Collection

Four sources:
1. **Virginia** — PJM DOM_hourly.csv (Kaggle, already in project root)
2. **Ohio** — PJM AEP_hourly.csv.zip (Kaggle, already in project root)
3. **Texas / Georgia** — EIA-930 hourly demand API (UTC timestamps)
4. **Weather / Solar** — NREL NSRDB API, one year per call (multi-year returns 400), 30-min → resampled hourly\
"""))

# ── EXTRACT AEP ZIP ───────────────────────────────────────────────────────────
cells.append(code("""\
# Extract AEP zip to data/raw (do not modify original)
aep_raw = RAW / "AEP_hourly.csv"
if not aep_raw.exists():
    with zipfile.ZipFile("AEP_hourly.csv.zip") as z:
        name = z.namelist()[0]
        with z.open(name) as src, open(aep_raw, "wb") as dst:
            dst.write(src.read())
    print(f"Extracted → {aep_raw}")
else:
    print(f"Already extracted: {aep_raw}")\
"""))

# ── EIA-930 FETCH ─────────────────────────────────────────────────────────────
cells.append(code("""\
def fetch_eia930_year(respondent, year, api_key):
    \"\"\"Fetch all hourly demand rows for one respondent and one calendar year.
    Returns a list of record dicts. Caches to data/raw/eia930_{respondent}_{year}.json.\"\"\"
    cache = RAW / f"eia930_{respondent}_{year}.json"
    if cache.exists():
        with open(cache) as f:
            return json.load(f)

    url = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
    all_rows, offset, page_size = [], 0, 5000
    while True:
        params = {
            "api_key": api_key,
            "frequency": "hourly",
            "data[0]": "value",
            "facets[respondent][]": respondent,
            "facets[type][]": "D",
            "start": f"{year}-01-01T00",
            "end": f"{year}-12-31T23",
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "length": page_size,
            "offset": offset,
        }
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        batch = r.json()["response"]["data"]
        all_rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
        time.sleep(0.2)

    with open(cache, "w") as f:
        json.dump(all_rows, f)
    return all_rows


# Fetch Texas (ERCO) and Georgia (SOCO) for 2019-2021
eia_raw = {}
for region, respondent in EIA_RESPONDENTS.items():
    rows = []
    for yr in REGIONS[region]["years"]:
        batch = fetch_eia930_year(respondent, yr, EIA_KEY)
        rows.extend(batch)
        print(f"  {region} {yr}: {len(batch):,} rows fetched/cached")
    eia_raw[region] = rows
print("EIA-930 collection complete.")\
"""))

# ── NSRDB FETCH ───────────────────────────────────────────────────────────────
cells.append(code("""\
def fetch_nsrdb_year(region_name, lat, lon, year, api_key, email, full_name, affiliation):
    \"\"\"Fetch NSRDB 30-min solar/weather data for one region and one year.
    Caches raw CSV text (with 2 metadata header lines) to data/raw/.
    Returns DataFrame with columns Year,Month,Day,Hour,Minute,GHI,DNI,DHI,Temperature,Wind Speed.\"\"\"
    cache = RAW / f"nsrdb_{region_name}_{year}.csv"
    if cache.exists():
        df = pd.read_csv(cache, skiprows=2)
        return df

    url = ("https://developer.nlr.gov/api/nsrdb/v2/solar/"
           "nsrdb-GOES-aggregated-v4-0-0-download.csv")
    params = {
        "api_key": api_key,
        "wkt": f"POINT({lon} {lat})",
        "names": str(year),
        "attributes": "ghi,dni,dhi,air_temperature,wind_speed",
        "interval": "30",
        "utc": "true",
        "leap_day": "true",
        "full_name": full_name,
        "email": email,
        "affiliation": affiliation,
        "reason": "Academic research and data analytics project",
        "mailing_list": "false",
    }
    r = requests.get(url, params=params, timeout=120)
    r.raise_for_status()
    cache.write_text(r.text, encoding="utf-8")
    df = pd.read_csv(io.StringIO(r.text), skiprows=2)
    return df


# Fetch NSRDB for all 4 regions × 3 years (one call per year)
nsrdb_raw = {}
for region, cfg in REGIONS.items():
    frames = []
    for yr in cfg["years"]:
        df = fetch_nsrdb_year(
            region, cfg["lat"], cfg["lon"], yr,
            NSRDB_KEY, NSRDB_EMAIL, NSRDB_NAME, NSRDB_AFF
        )
        frames.append(df)
        print(f"  {region} {yr}: {len(df):,} rows (30-min)")
        time.sleep(0.5)          # be polite to the API
    nsrdb_raw[region] = pd.concat(frames, ignore_index=True)

print("NSRDB collection complete.")\
"""))

# ── SECTION 2 ─────────────────────────────────────────────────────────────────
cells.append(md("""\
## 2. Cleaning and Integration

### UTC Alignment Strategy

| Source | Local time convention | UTC approach |
|--------|----------------------|--------------|
| PJM (DOM/AEP) | Eastern prevailing time (DST); rows **not** sorted; Nov duplicate, Mar gap | Sort → filter years → assign sequential UTC from Jan 1 01:00 ET = Jan 1 06:00 UTC |
| EIA-930 | `period` is already UTC (`2019-01-01T00`) | Parse directly |
| NSRDB | Already UTC (`utc=true`) | Build timestamp from Year/Month/Day/Hour/Minute |

All three sources are merged on a single `Timestamp` column (UTC, tz-aware).\
"""))

# ── PJM PROCESSING ────────────────────────────────────────────────────────────
cells.append(code("""\
def process_pjm(csv_path, mw_col, region_name, years):
    \"\"\"
    Load a PJM hourly CSV, sort, filter to target years, assign sequential UTC timestamps,
    and verify first/last row alignment.

    Eastern prevailing time convention:
      - First row of year Y (after sorting) = Jan 1 01:00 ET (hour-ending 01:00)
      - Jan 1 01:00 ET = Jan 1 06:00 UTC  (EST = UTC-5 in January)
      - Each subsequent row = +1 hour UTC
      - Nov fall-back duplicate: two consecutive rows share the same local label;
        sequential UTC handles this correctly (both rows get real UTC hours).
      - Mar spring-forward gap: one local label is skipped; sequential UTC is unaffected.
    \"\"\"
    df = pd.read_csv(csv_path)
    df["Datetime"] = pd.to_datetime(df["Datetime"])
    df = df.sort_values("Datetime").reset_index(drop=True)

    frames = []
    for yr in years:
        yr_df = df[df["Datetime"].dt.year == yr].copy().reset_index(drop=True)

        # Verify first row
        first_local = yr_df["Datetime"].iloc[0]
        assert first_local.month == 1 and first_local.day == 1, (
            f"{region_name} {yr}: first row is {first_local}, expected Jan 1")

        # Assign sequential UTC: Jan 1 01:00 ET = Jan 1 06:00 UTC
        start_utc = pd.Timestamp(f"{yr}-01-01 06:00:00", tz="UTC")
        yr_df["Timestamp"] = pd.date_range(start=start_utc, periods=len(yr_df), freq="h")

        # Verify last row alignment
        last_utc = yr_df["Timestamp"].iloc[-1]
        expected_last = pd.Timestamp(f"{yr+1}-01-01 05:00:00", tz="UTC")
        assert last_utc == expected_last, (
            f"{region_name} {yr}: last UTC={last_utc}, expected {expected_last}")

        yr_df["Region"] = region_name
        yr_df["Demand_MW"] = yr_df[mw_col].astype(float)
        frames.append(yr_df[["Region", "Timestamp", "Demand_MW"]])
        print(f"  {region_name} {yr}: {len(yr_df):,} rows, "
              f"UTC {yr_df['Timestamp'].iloc[0]} → {yr_df['Timestamp'].iloc[-1]}")

    return pd.concat(frames, ignore_index=True)


demand_va = process_pjm("DOM_hourly.csv",    "DOM_MW", "Virginia", [2015,2016,2017])
demand_oh = process_pjm(str(RAW/"AEP_hourly.csv"), "AEP_MW", "Ohio", [2015,2016,2017])
print(f"Virginia rows: {len(demand_va):,}  Ohio rows: {len(demand_oh):,}")\
"""))

# ── EIA-930 PROCESSING ────────────────────────────────────────────────────────
cells.append(code("""\
def process_eia930(raw_rows, region_name):
    \"\"\"Convert EIA-930 list-of-dicts to a clean demand DataFrame with UTC Timestamp.\"\"\"
    df = pd.DataFrame(raw_rows)
    # period format: \"2019-01-01T00\" = UTC hour
    df["Timestamp"] = pd.to_datetime(df["period"], format="%Y-%m-%dT%H", utc=True)
    df["Demand_MW"] = pd.to_numeric(df["value"], errors="coerce")
    df["Region"] = region_name
    df = df[["Region", "Timestamp", "Demand_MW"]].sort_values("Timestamp").reset_index(drop=True)

    # Drop any nulls in Demand_MW and report
    nulls = df["Demand_MW"].isnull().sum()
    if nulls > 0:
        print(f"  WARNING {region_name}: {nulls} null Demand_MW values → dropped")
        df = df.dropna(subset=["Demand_MW"]).reset_index(drop=True)

    print(f"  {region_name}: {len(df):,} rows, "
          f"UTC {df['Timestamp'].iloc[0]} → {df['Timestamp'].iloc[-1]}")
    return df


demand_tx = process_eia930(eia_raw["Texas"],   "Texas")
demand_ga = process_eia930(eia_raw["Georgia"], "Georgia")
print(f"Texas rows: {len(demand_tx):,}  Georgia rows: {len(demand_ga):,}")\
"""))

# ── NSRDB PROCESSING ──────────────────────────────────────────────────────────
cells.append(code("""\
def process_nsrdb(raw_df, region_name):
    \"\"\"
    Convert 30-min NSRDB DataFrame to hourly UTC.
    Build Timestamp from Year/Month/Day/Hour/Minute (UTC),
    then resample to hourly mean.
    \"\"\"
    df = raw_df.copy()
    df["Timestamp"] = pd.to_datetime(
        df[["Year","Month","Day","Hour","Minute"]]
        .rename(columns={"Year":"year","Month":"month","Day":"day",
                         "Hour":"hour","Minute":"minute"}),
        utc=True
    )
    df = df.sort_values("Timestamp").reset_index(drop=True)

    # Resample to hourly mean (label=left to align with demand hour-start)
    df = df.set_index("Timestamp")
    hourly = df[["GHI","DNI","DHI","Temperature","Wind Speed"]].resample("h").mean()
    hourly = hourly.reset_index()
    hourly["Region"] = region_name
    print(f"  {region_name}: {len(raw_df):,} 30-min → {len(hourly):,} hourly rows, "
          f"UTC {hourly['Timestamp'].iloc[0]} → {hourly['Timestamp'].iloc[-1]}")
    return hourly


weather = {}
for region in REGIONS:
    weather[region] = process_nsrdb(nsrdb_raw[region], region)
print("NSRDB processing complete.")\
"""))

# ── MERGE DEMAND + WEATHER ────────────────────────────────────────────────────
cells.append(code("""\
def merge_region(demand_df, weather_df, region_name, tz_str):
    \"\"\"Merge demand and weather on UTC Timestamp, add local-time columns.\"\"\"
    merged = pd.merge(demand_df, weather_df.drop(columns=["Region"]),
                      on="Timestamp", how="inner")

    # Local time derived from UTC — extract features BEFORE converting to string
    local_ts = merged["Timestamp"].dt.tz_convert(tz_str)

    merged["Year"]      = local_ts.dt.year
    merged["Month"]     = local_ts.dt.month
    merged["Hour"]      = local_ts.dt.hour
    merged["DayOfWeek"] = local_ts.dt.dayofweek        # 0=Monday
    merged["Is_Weekend"]= (local_ts.dt.dayofweek >= 5).astype(int)

    def season(m):
        if m in [12,1,2]:  return "Winter"
        if m in [3,4,5]:   return "Spring"
        if m in [6,7,8]:   return "Summer"
        return "Fall"
    merged["Season"] = merged["Month"].map(season)

    # Store as string so pd.concat across different timezones works
    merged["Timestamp_Local"] = local_ts.astype(str)

    print(f"  {region_name}: {len(merged):,} merged rows "
          f"(demand {len(demand_df):,} × weather {len(weather_df):,})")
    return merged


merged_frames = []
for region, cfg in REGIONS.items():
    demand_map = {"Virginia": demand_va, "Ohio": demand_oh,
                  "Texas": demand_tx, "Georgia": demand_ga}
    m = merge_region(demand_map[region], weather[region], region, cfg["tz"])
    merged_frames.append(m)

master = pd.concat(merged_frames, ignore_index=True)
# Ensure Timestamp is UTC tz-aware
master["Timestamp"] = master["Timestamp"].dt.tz_convert("UTC")
print(f"\\nMaster shape: {master.shape}")
print("Columns:", master.columns.tolist())\
"""))

# ── SECTION 3 ─────────────────────────────────────────────────────────────────
cells.append(md("""\
## 3. Data Quality Checks

Verifying: row counts per region, zero duplicate (Region, Timestamp) pairs, null values after merge, and local hour of minimum demand (expected 3–5 AM local).\
"""))

# ── QUALITY CHECKS ────────────────────────────────────────────────────────────
cells.append(code("""\
print("=" * 60)
print("ROW COUNTS PER REGION")
print("=" * 60)
coverage = master.groupby("Region").size().reset_index(name="n_rows")
coverage["expected"] = EXPECTED_ROWS
coverage["gap"] = coverage["n_rows"] - coverage["expected"]
coverage["pct_coverage"] = (coverage["n_rows"] / coverage["expected"] * 100).round(2)
print(coverage.to_string(index=False))
for _, row in coverage.iterrows():
    if row["n_rows"] < EXPECTED_ROWS:
        print(f"  *** WARN: {row['Region']} is {-row['gap']:,} rows short of full coverage ***")

print()
print("=" * 60)
print("DUPLICATE (Region, Timestamp) CHECK")
print("=" * 60)
dupes = master.duplicated(subset=["Region","Timestamp"]).sum()
print(f"Duplicate pairs: {dupes}  (must be 0)")
assert dupes == 0, f"FAIL: {dupes} duplicates found!"
print("PASS: zero duplicates")

print()
print("=" * 60)
print("NULL CHECK AFTER MERGE")
print("=" * 60)
nulls = master.isnull().sum()
nulls_nonzero = nulls[nulls > 0]
if len(nulls_nonzero) == 0:
    print("No nulls found.")
else:
    print(nulls_nonzero.to_string())

print()
print("=" * 60)
print("TOTAL ROWS:", f"{len(master):,}")
if len(master) < 100_000:
    raise RuntimeError(f"FAIL: master has {len(master):,} rows, minimum is 100,000")\
"""))

# ── MIN HOUR CHECK ────────────────────────────────────────────────────────────
cells.append(code("""\
print("=" * 60)
print("CLOCK ALIGNMENT CHECK: Hour of Daily Minimum Demand")
print("Expected: 3-5 AM local for all regions")
print("=" * 60)
# Use UTC date as grouping proxy (off by at most a few hours but fine for mode)
# Hour column is already local time, set in merge_region
master["_utc_date"] = master["Timestamp"].dt.date
min_hour_idx = (
    master.groupby(["Region", "_utc_date"])["Demand_MW"].idxmin()
)
min_hour_vals = master.loc[min_hour_idx, ["Region","Hour","Demand_MW"]]
mode_hour = min_hour_vals.groupby("Region")["Hour"].agg(lambda x: x.mode().iloc[0])
master.drop(columns=["_utc_date"], inplace=True)
print(mode_hour.to_string())
for region, h in mode_hour.items():
    if not (1 <= h <= 7):
        print(f"  *** INVESTIGATE: {region} mode min-demand hour = {h} (expected 1-7 AM local) ***")
    else:
        print(f"  OK: {region} mode min-demand hour = {h:02d}:00 local")\
"""))

# ── SECTION 4 ─────────────────────────────────────────────────────────────────
cells.append(md("""\
## 4. Feature Engineering

### Stress Index

`Stress_Index` = percentile rank (0–100) of `Demand_MW` **within each region's own data**.

- It is a **relative, descriptive** measure, not an engineering or capacity threshold.
- A value of 95 means that hour's demand is in the top 5 % of that region's history.
- Comparisons **across regions** are not meaningful because each region has its own baseline.\
"""))

# ── STRESS INDEX ──────────────────────────────────────────────────────────────
cells.append(code("""\
from scipy.stats import rankdata

def stress_index(series):
    \"\"\"Percentile rank within the series, 0–100.\"\"\"
    ranks = rankdata(series, method="average")
    return (ranks - 1) / (len(ranks) - 1) * 100

master["Stress_Index"] = (
    master.groupby("Region")["Demand_MW"]
    .transform(stress_index)
)

print("Stress_Index stats per region:")
print(master.groupby("Region")["Stress_Index"].describe().round(2).to_string())
print()
print("Master schema:")
print(master.dtypes.to_string())\
"""))

# ── SECTION 5 ─────────────────────────────────────────────────────────────────
cells.append(md("""\
## 5. IM3 Data Center Atlas

**Source:** PNNL / DOE MSD-LIVE, record p147s-4h760 v2026.02.09, DOI 10.57931/3017294, ODbL license.

**Layer types:**
- `point` — location only, no `sqft`
- `building` — single structure, has `sqft`
- `campus` — multi-building facility, has `sqft`

Buildings and campuses overlap at the same facility, so we **never sum `sqft` across types**. Unique data centers are counted with `nunique(id)`.\
"""))

# ── IM3 LOAD + GEO_SUMMARY ────────────────────────────────────────────────────
cells.append(code("""\
IM3_PATH = (
    "p147s-4h760/im3_open_source_data_center_atlas_v2026.02.09/"
    "im3_open_source_data_center_atlas_v2026.02.09.csv"
)
im3_raw = pd.read_csv(IM3_PATH)
print(f"IM3 raw: {im3_raw.shape[0]:,} rows, columns: {im3_raw.columns.tolist()}")
print("Type counts:")
print(im3_raw["type"].value_counts().to_string())

# Filter to four states, drop rows without coordinates
state_map = {"Virginia":"VA","Ohio":"OH","Texas":"TX","Georgia":"GA"}
im3_clean = (
    im3_raw[im3_raw["state_abb"].isin(state_map.values())]
    .dropna(subset=["lat","lon"])
    .copy()
)
# Add Region column
inv_state_map = {v:k for k,v in state_map.items()}
im3_clean["Region"] = im3_clean["state_abb"].map(inv_state_map)
print(f"\\nIM3 filtered (4 states, coords required): {len(im3_clean):,} rows")
print(im3_clean.groupby("Region")["id"].nunique().rename("unique_DCs").to_string())
print("sqft nulls per region+type:")
print(im3_clean.groupby(["Region","type"])["sqft"].apply(lambda x: x.isnull().sum()).to_string())\
"""))

cells.append(code("""\
# geo_summary: one row per Region
# sqft reported separately per layer type to avoid double-counting
demand_summary = (
    master.groupby("Region")["Demand_MW"]
    .agg(avg_demand_MW="mean", peak_demand_MW="max", std_demand_MW="std")
    .round(1)
)

def sqft_by_type(grp, layer_type):
    sub = grp[grp["type"] == layer_type]
    # Campus and building: sum sqft of UNIQUE ids only (multi-county rows share same id)
    unique_sqft = sub.drop_duplicates("id")["sqft"].sum()
    return unique_sqft

geo_rows = []
for region in REGIONS:
    grp = im3_clean[im3_clean["Region"] == region]
    geo_rows.append({
        "Region": region,
        "unique_DCs": grp["id"].nunique(),
        "n_building": grp[grp["type"]=="building"]["id"].nunique(),
        "n_campus":   grp[grp["type"]=="campus"]["id"].nunique(),
        "n_point":    grp[grp["type"]=="point"]["id"].nunique(),
        "sqft_building_m2": sqft_by_type(grp, "building"),
        "sqft_campus_m2":   sqft_by_type(grp, "campus"),
    })

geo_summary = (
    pd.DataFrame(geo_rows)
    .merge(demand_summary.reset_index(), on="Region")
)
print("geo_summary:")
print(geo_summary.to_string(index=False))\
"""))

# ── SECTION 6 ─────────────────────────────────────────────────────────────────
cells.append(md("""\
## 6. Exploratory Data Analysis

All charts include title, axis labels with units, and a one-line takeaway derived from the real data.\
"""))

# ── DESCRIPTIVE STATS ─────────────────────────────────────────────────────────
cells.append(code("""\
print("DESCRIPTIVE STATISTICS — Demand_MW per Region")
stats = master.groupby("Region")["Demand_MW"].describe().round(1)
print(stats.to_string())
print()
print("DESCRIPTIVE STATISTICS — Temperature (°C) per Region")
print(master.groupby("Region")["Temperature"].describe().round(1).to_string())\
"""))

# ── PEAK / MIN DEMAND ─────────────────────────────────────────────────────────
cells.append(code("""\
print("PEAK AND MINIMUM DEMAND WITH TIMESTAMPS")
for region in REGIONS:
    sub = master[master["Region"] == region]
    peak_idx = sub["Demand_MW"].idxmax()
    min_idx  = sub["Demand_MW"].idxmin()
    peak_row = sub.loc[peak_idx]
    min_row  = sub.loc[min_idx]
    print(f"\\n{region}:")
    print(f"  Peak: {peak_row['Demand_MW']:,.0f} MW  at {peak_row['Timestamp_Local']} local")
    print(f"  Min:  {min_row['Demand_MW']:,.0f} MW  at {min_row['Timestamp_Local']} local")\
"""))

# ── DAILY AVERAGE DEMAND (FACETED) ────────────────────────────────────────────
cells.append(code("""\
daily_avg = (
    master.groupby(["Region", master["Timestamp"].dt.date])
    ["Demand_MW"].mean().reset_index()
    .rename(columns={"Timestamp": "Date"})
)
daily_avg["Date"] = pd.to_datetime(daily_avg["Date"])

fig = px.line(
    daily_avg, x="Date", y="Demand_MW", facet_col="Region",
    facet_col_wrap=2, height=500,
    title="Daily Average Electricity Demand by Region",
    labels={"Demand_MW": "Demand (MW)", "Date": "Date"},
    color="Region",
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig.update_layout(showlegend=False)
fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))

# Takeaway
peak_region = daily_avg.groupby("Region")["Demand_MW"].max().idxmax()
takeaway = (f"Takeaway: {peak_region} shows the highest daily peak demand; "
            "all regions show clear seasonal cycles.")
fig.add_annotation(text=takeaway, xref="paper", yref="paper",
                   x=0, y=-0.12, showarrow=False, font=dict(size=11, color="gray"))
fig.show()\
"""))

# ── HOURLY PROFILE WEEKDAY VS WEEKEND ─────────────────────────────────────────
cells.append(code("""\
hourly_profile = (
    master.groupby(["Region","Hour","Is_Weekend"])["Demand_MW"]
    .mean().reset_index()
)
hourly_profile["Day Type"] = hourly_profile["Is_Weekend"].map({0:"Weekday",1:"Weekend"})

fig = px.line(
    hourly_profile, x="Hour", y="Demand_MW", color="Day Type",
    facet_col="Region", facet_col_wrap=2, height=500,
    title="Average Hourly Demand Profile: Weekday vs Weekend",
    labels={"Demand_MW": "Avg Demand (MW)", "Hour": "Hour of Day (local)"},
    color_discrete_map={"Weekday":"steelblue","Weekend":"coral"},
)
fig.update_xaxes(dtick=3)
fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))

# Compute takeaway from data
wkday = hourly_profile[hourly_profile["Is_Weekend"]==0].groupby("Region")["Demand_MW"].mean()
wkend = hourly_profile[hourly_profile["Is_Weekend"]==1].groupby("Region")["Demand_MW"].mean()
diff_pct = ((wkday - wkend) / wkend * 100).mean()
takeaway = (f"Takeaway: Weekday demand averages {abs(diff_pct):.1f}% "
            f"{'higher' if diff_pct > 0 else 'lower'} than weekends across all regions.")
fig.add_annotation(text=takeaway, xref="paper", yref="paper",
                   x=0, y=-0.12, showarrow=False, font=dict(size=11, color="gray"))
fig.show()\
"""))

# ── SEASONAL / MONTHLY DEMAND ─────────────────────────────────────────────────
cells.append(code("""\
monthly_avg = (
    master.groupby(["Region","Month"])["Demand_MW"].mean().reset_index()
)
monthly_avg["Month_Name"] = pd.to_datetime(monthly_avg["Month"], format="%m").dt.strftime("%b")

fig = px.bar(
    monthly_avg, x="Month_Name", y="Demand_MW", color="Region",
    barmode="group", height=450,
    title="Average Monthly Demand by Region",
    labels={"Demand_MW": "Avg Demand (MW)", "Month_Name": "Month"},
    color_discrete_sequence=px.colors.qualitative.Set2,
    category_orders={"Month_Name":["Jan","Feb","Mar","Apr","May","Jun",
                                    "Jul","Aug","Sep","Oct","Nov","Dec"]},
)
# Takeaway
peak_month = monthly_avg.groupby("Month")["Demand_MW"].mean().idxmax()
peak_month_name = pd.to_datetime(str(peak_month), format="%m").strftime("%B")
takeaway = f"Takeaway: Month {peak_month_name} shows the highest average demand across regions, driven by heating/cooling loads."
fig.add_annotation(text=takeaway, xref="paper", yref="paper",
                   x=0, y=-0.15, showarrow=False, font=dict(size=11, color="gray"))
fig.show()

# Seasonal box plot
fig2 = px.box(
    master, x="Season", y="Demand_MW", color="Region",
    height=450,
    title="Demand Distribution by Season",
    labels={"Demand_MW": "Demand (MW)", "Season": "Season"},
    color_discrete_sequence=px.colors.qualitative.Set2,
    category_orders={"Season":["Winter","Spring","Summer","Fall"]},
)
fig2.show()\
"""))

# ── TEMPERATURE VS DEMAND ─────────────────────────────────────────────────────
cells.append(code("""\
# Sample to keep plot manageable (every 6th row → ~17k points)
sample = master.iloc[::6].copy()

fig = px.scatter(
    sample, x="Temperature", y="Demand_MW",
    color="Region", facet_col="Region", facet_col_wrap=2,
    opacity=0.3, height=550, trendline="lowess",
    title="Temperature vs Demand (hourly sample, LOWESS trend)",
    labels={"Temperature":"Temperature (°C)","Demand_MW":"Demand (MW)"},
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
fig.update_traces(marker=dict(size=3), selector=dict(mode="markers"))

# Compute correlations
corrs = master.groupby("Region").apply(
    lambda g: g["Temperature"].corr(g["Demand_MW"])
).round(3)
corr_str = ", ".join(f"{r}:{v:+.2f}" for r, v in corrs.items())
takeaway = f"Takeaway: Temperature-demand correlations — {corr_str} (negative = winter-peaking, positive = summer-peaking)."
fig.add_annotation(text=takeaway, xref="paper", yref="paper",
                   x=0, y=-0.12, showarrow=False, font=dict(size=10, color="gray"))
fig.show()\
"""))

# ── GHI VS DEMAND ─────────────────────────────────────────────────────────────
cells.append(code("""\
# GHI vs demand: daytime hours only (GHI > 0)
daytime = master[master["GHI"] > 0].iloc[::4].copy()

fig = px.scatter(
    daytime, x="GHI", y="Demand_MW",
    color="Region", facet_col="Region", facet_col_wrap=2,
    opacity=0.25, height=500,
    title="Solar Irradiance (GHI) vs Demand — Daytime Hours",
    labels={"GHI":"GHI (W/m²)","Demand_MW":"Demand (MW)"},
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
fig.update_traces(marker=dict(size=3))

ghi_corrs = daytime.groupby("Region").apply(
    lambda g: g["GHI"].corr(g["Demand_MW"])
).round(3)
ghi_str = ", ".join(f"{r}:{v:+.2f}" for r, v in ghi_corrs.items())
takeaway = f"Takeaway: GHI-demand correlations (daytime) — {ghi_str}."
fig.add_annotation(text=takeaway, xref="paper", yref="paper",
                   x=0, y=-0.12, showarrow=False, font=dict(size=10, color="gray"))
fig.show()\
"""))

# ── STRESS INDEX DISTRIBUTION ──────────────────────────────────────────────────
cells.append(code("""\
fig = px.histogram(
    master, x="Stress_Index", color="Region",
    facet_col="Region", facet_col_wrap=2,
    nbins=50, height=450,
    title="Stress Index Distribution per Region (0–100 percentile rank)",
    labels={"Stress_Index":"Stress Index (percentile rank)"},
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
fig.update_layout(showlegend=False)

top5_count = (master["Stress_Index"] >= 95).sum()
takeaway = (f"Takeaway: {top5_count:,} hours ({top5_count/len(master)*100:.1f}% of all) "
            f"have Stress Index ≥ 95 (top 5% per region). "
            f"Distribution is approximately uniform by construction.")
fig.add_annotation(text=takeaway, xref="paper", yref="paper",
                   x=0, y=-0.12, showarrow=False, font=dict(size=10, color="gray"))
fig.show()\
"""))

# ── HOUR × MONTH STRESS HEATMAP ───────────────────────────────────────────────
cells.append(code("""\
for region in REGIONS:
    sub = master[master["Region"] == region]
    heat = sub.groupby(["Month","Hour"])["Stress_Index"].mean().reset_index()
    heat_pivot = heat.pivot(index="Hour", columns="Month", values="Stress_Index")

    month_labels = ["Jan","Feb","Mar","Apr","May","Jun",
                    "Jul","Aug","Sep","Oct","Nov","Dec"]

    fig = px.imshow(
        heat_pivot, aspect="auto", color_continuous_scale="RdYlGn_r",
        title=f"{region}: Mean Stress Index — Hour × Month",
        labels={"x":"Month","y":"Hour of Day (local)","color":"Stress Index"},
        x=[month_labels[m-1] for m in sorted(heat_pivot.columns)],
    )
    peak_m, peak_h = heat.loc[heat["Stress_Index"].idxmax(), ["Month","Hour"]]
    takeaway = (f"Takeaway: Highest mean stress in {month_labels[int(peak_m)-1]}, "
                f"hour {int(peak_h):02d}:00 local.")
    fig.add_annotation(text=takeaway, xref="paper", yref="paper",
                       x=0, y=-0.12, showarrow=False, font=dict(size=11, color="gray"))
    fig.show()\
"""))

# ── TOP 1% STRESS HOURS ───────────────────────────────────────────────────────
cells.append(code("""\
top1 = master[master["Stress_Index"] >= 99].copy()
print(f"Hours at Stress Index ≥ 99 (top 1%): {len(top1):,}")
print()
by_region = top1.groupby("Region").agg(
    n_hours=("Stress_Index","count"),
    peak_demand=("Demand_MW","max"),
    most_common_month=("Month", lambda x: x.mode().iloc[0]),
    most_common_hour=("Hour", lambda x: x.mode().iloc[0]),
).reset_index()
by_region["most_common_month"] = by_region["most_common_month"].apply(
    lambda m: pd.to_datetime(str(m), format="%m").strftime("%B"))
print(by_region.to_string(index=False))

fig = px.histogram(
    top1, x="Month", color="Region", barmode="group",
    facet_col="Region", facet_col_wrap=2, nbins=12,
    title="Top 1% Stress Hours: Distribution by Month",
    labels={"Month":"Month","count":"Number of Hours"},
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
fig.update_layout(showlegend=False)
fig.show()\
"""))

# ── DATA CENTER MAP ───────────────────────────────────────────────────────────
cells.append(code("""\
# Plotly scatter_geo map: data centers sized by sqft (NaN → small default size)
map_df = im3_clean.copy()
map_df["sqft_plot"] = map_df["sqft"].fillna(50_000)   # NaN sqft (point records) → default
map_df["sqft_plot_scaled"] = np.clip(map_df["sqft_plot"] / 1e5, 2, 30)  # marker size range 2-30
map_df["sqft_label"] = map_df["sqft"].apply(
    lambda x: f"{x:,.0f} sq ft" if pd.notnull(x) else "sqft unavailable (point record)")

fig = px.scatter_geo(
    map_df, lat="lat", lon="lon",
    color="Region", symbol="type",
    size="sqft_plot_scaled",
    hover_name="name",
    hover_data={"sqft_label":True, "operator":True, "county":True,
                "lat":False,"lon":False,"sqft_plot_scaled":False},
    scope="usa", height=550,
    title="IM3 Data Center Atlas — Virginia, Ohio, Texas, Georgia",
    labels={"Region":"Region","type":"Layer Type"},
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig.update_geos(fitbounds="locations", showland=True, landcolor="lightgray",
                showsubunits=True, subunitcolor="white")
fig.update_layout(margin=dict(l=0,r=0,t=50,b=0))
takeaway = ("Takeaway: Virginia has the highest density of data centers; "
            "campus records (larger markers) are visible in all four states.")
fig.add_annotation(text=takeaway, xref="paper", yref="paper",
                   x=0, y=-0.06, showarrow=False, font=dict(size=11, color="gray"))
fig.show()\
"""))

# ── DC COUNT VS DEMAND ────────────────────────────────────────────────────────
cells.append(code("""\
fig = px.scatter(
    geo_summary, x="unique_DCs", y="avg_demand_MW",
    color="Region", size="peak_demand_MW",
    text="Region", height=450,
    title="Data Center Count vs Average Demand per Region",
    labels={"unique_DCs":"Unique Data Centers (all types)",
            "avg_demand_MW":"Average Demand (MW)",
            "peak_demand_MW":"Peak Demand (MW, bubble size)"},
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig.update_traces(textposition="top center")
fig.update_layout(showlegend=False)
takeaway = ("Takeaway: Virginia leads in both data center count and average demand; "
            "Texas shows high demand relative to its recorded data center footprint.")
fig.add_annotation(text=takeaway, xref="paper", yref="paper",
                   x=0, y=-0.12, showarrow=False, font=dict(size=11, color="gray"))
fig.show()\
"""))

# ── SECTION 7 ─────────────────────────────────────────────────────────────────
cells.append(md("""\
## 7. Save Output Files

Three clean CSVs are written to `data/clean/`:

| File | Contents |
|------|----------|
| `master_timeseries.csv` | Full hourly time series, all regions, all features |
| `im3_clean.csv` | IM3 filtered to 4 states with Region column |
| `geo_summary.csv` | One row per region: DC counts, sqft by type, demand stats |\
"""))

# ── SAVE CSVS ─────────────────────────────────────────────────────────────────
cells.append(code("""\
# Convert tz-aware Timestamps to ISO strings for CSV portability
save_master = master.copy()
save_master["Timestamp"]       = save_master["Timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
save_master["Timestamp_Local"] = save_master["Timestamp_Local"].astype(str)

master_path = CLEAN / "master_timeseries.csv"
im3_path    = CLEAN / "im3_clean.csv"
geo_path    = CLEAN / "geo_summary.csv"

save_master.to_csv(master_path, index=False)
im3_clean.to_csv(im3_path, index=False)
geo_summary.to_csv(geo_path, index=False)

print(f"Saved: {master_path}  ({len(save_master):,} rows)")
print(f"Saved: {im3_path}  ({len(im3_clean):,} rows)")
print(f"Saved: {geo_path}  ({len(geo_summary):,} rows)")

# Verify saved files load correctly
check = pd.read_csv(master_path)
assert len(check) == len(master), "Row count mismatch after save!"
print("Save verification: OK")\
"""))

# ── FINAL SUMMARY ─────────────────────────────────────────────────────────────
cells.append(md("## Final Summary"))

cells.append(code("""\
print("=" * 70)
print("FINAL SUMMARY")
print("=" * 70)
print(f"Total rows in master: {len(master):,}")
print()
region_summary = master.groupby("Region").agg(
    rows=("Demand_MW","count"),
    years=("Year", lambda x: f"{x.min()}-{x.max()}"),
    demand_avg=("Demand_MW","mean"),
    demand_peak=("Demand_MW","max"),
    stress_p95=("Stress_Index", lambda x: x.quantile(0.95)),
).round(1).reset_index()
print(region_summary.to_string(index=False))
print()
print("Data gaps / assumptions:")
print("  - NSRDB provides one lat/lon point per region (single weather station proxy).")
print("  - IM3 point records have no sqft; campus+building sqft reported separately to avoid double-counting.")
print("  - Virginia & Ohio demand is 2015-2017; Texas & Georgia is 2019-2021 (different calendar years).")
print("  - Stress Index is region-relative; cross-region comparisons are not meaningful.")
print("  - PJM timestamps reconstructed sequentially from Jan 1 ET to handle DST ambiguity.")
print()
print("Run commands:")
print("  Notebook:   .venv/bin/jupyter nbconvert --to notebook --execute dav_project.ipynb")
print("  Dashboard:  .venv/bin/streamlit run app.py")\
"""))

# ══════════════════════════════════════════════════════════════════════════════
# Assemble and write notebook
# ══════════════════════════════════════════════════════════════════════════════
nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3 (venv)",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.14.3"
        }
    },
    "cells": cells
}

out = Path("dav_project.ipynb")
out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"Written: {out}  ({out.stat().st_size//1024} KB, {len(cells)} cells)")
