# Data Center Energy Stress Predictor

### A Multi-Source Geospatial Analytics and Visualization Platform

*B.Tech IT — Data Analytics & Visualization (DAV) course project*

This project shows **when and where the electric grid is under the most pressure** in four U.S.
data-center hub regions — Virginia, Ohio, Texas and Georgia — and how that relates to weather,
sunlight and the number of data centers in each region.

> **What it is not.** Despite "Predictor" in the name, the project makes **no predictions or forecasts**
> and uses **no machine learning**. Everything is descriptive statistics and visualization of
> historical data.

---

## At a glance

| | |
|---|---|
| **Regions** | 4 — Virginia, Ohio, Texas, Georgia |
| **Real hourly observations** | **105,190** (one row per region per hour) |
| **Period** | Virginia & Ohio 2015–2017 · Texas & Georgia 2019–2021 |
| **Variables per hour** | Electricity demand, temperature, wind speed, solar radiation (GHI, DNI, DHI), Stress Index |
| **Data centers** | 1,479 atlas records (1,474 unique) across 47 states; 574 in the four focus states |
| **Data sources** | 4 — PJM (via Kaggle), EIA-930 API, NREL NSRDB API, IM3 Data Center Atlas |
| **Deliverables** | Jupyter notebook (full pipeline + analysis) and a Streamlit dashboard |
| **Synthetic demo rows** | 20,000, clearly labelled and **off by default** ([details](#synthetic-demonstration-data)) |

---

## Quick start

**1. Install** (Python 3.12; all versions in `requirements.txt` are pinned and tested)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**2. Add API keys** — only needed the first time the notebook downloads data

```bash
cp .env.example .env               # then fill in the five values below
```

| Variable | Where to get it |
|---|---|
| `EIA_API_KEY` | Free key from the [EIA Open Data portal](https://www.eia.gov/opendata/) |
| `NSRDB_API_KEY` | Free key from the NREL developer network |
| `NSRDB_FULL_NAME`, `NSRDB_EMAIL`, `NSRDB_AFFILIATION` | Required by the NSRDB download API |

`.env` is git-ignored and is read only by the notebook — the dashboard needs no keys.

**3. Build the data** — runs the whole pipeline and writes `data/clean/`

```bash
.venv/bin/jupyter nbconvert --to notebook --execute --inplace \
    --ExecutePreprocessor.timeout=1200 dav_project.ipynb
```

The first run downloads EIA-930 and NSRDB data into `data/raw/` (about 2–3 minutes). Later runs use
that cache, make no API calls, and reproduce `data/clean/` byte for byte.

**4. Open the dashboard**

```bash
source .venv/bin/activate && streamlit run app.py
```

Then open <http://localhost:8501>. The dashboard only reads `data/clean/*.csv` and makes no API calls
(the browser loads the map tiles and a web font, neither of which needs a key).

---

## Regions and data

| Region | Demand source | Years | Real hours | Gaps at source |
|---|---|---|---:|---|
| Virginia | PJM zone **DOM** (Dominion) | 2015–2017 | 26,304 | none |
| Ohio | PJM zone **AEP** | 2015–2017 | 26,304 | none |
| Texas | EIA-930 **ERCO** (ERCOT) | 2019–2021 | 26,303 | 1 hour not returned by the API |
| Georgia | EIA-930 **SOCO** (Southern Company) | 2019–2021 | 26,279 | 24 null hours + 1 hour not returned |

Missing hours are **reported, never filled**. Weather and solar data come from one NSRDB location per
region, and data-center locations from the IM3 atlas.

| Source | Provides | Terms |
|---|---|---|
| PJM hourly consumption — Kaggle `robikscube/hourly-energy-consumption` | Virginia and Ohio demand | Data originate from PJM Interconnection. ⚠️ **License not verified** — check the Kaggle page before redistributing. |
| EIA-930 — EIA Open Data API v2 | Texas and Georgia demand | Public domain; EIA asks for attribution ([terms](https://www.eia.gov/about/copyrights_reuse.php)). |
| NREL NSRDB — GOES aggregated v4.0.0 | Temperature, wind, GHI, DNI, DHI (30-min → hourly) | NREL Developer Network terms; cite the NSRDB. ⚠️ **Redistribution terms not verified** — check before sharing `data/raw/`. |
| IM3 Open Source Data Center Atlas — PNNL / DOE MSD-LIVE, v2026.02.09, DOI 10.57931/3017294 | Data-center locations, type and floor area | Open Database License (ODbL) 1.0; built from OpenStreetMap (© OpenStreetMap contributors). |

---

## How the pipeline works

Everything runs in `dav_project.ipynb`, top to bottom:

1. **Collect** — read the PJM CSVs, download EIA-930 and NSRDB data (cached in `data/raw/`), load the IM3 atlas.
2. **Align time** — put every source on the same clock: each row is one hour, keyed by the **UTC start of that hour**.
   PJM and EIA-930 label hours by their *end*, so they are shifted back one hour; daylight-saving changes are handled
   explicitly and checked row by row.
3. **Clean and merge** — keep each region's local calendar years, drop (and report) missing values, resample weather
   from 30-minute to hourly, and join demand with weather.
4. **Add features** — local year, month, hour, weekday, weekend flag, season, and the **Stress Index**.
5. **Check quality** — zero duplicates, zero unexplained nulls, full coverage report, and a clock sanity check
   (demand is lowest at 3–4 AM local time in every region).
6. **Analyze** — descriptive statistics, seasonal and daily patterns, weather relationships, stress heat maps and
   data-center maps, each with a takeaway computed from the data.
7. **Save** — write the four files in `data/clean/` that the dashboard reads.

Full details, including the evidence for each time convention, are in [METHODOLOGY.md](METHODOLOGY.md).

---

## Key definitions

- **Demand (MW)** — average electricity demand in a one-hour interval. (EIA reports MWh per hour, which equals average MW.)
- **Hour** — local *start* of the hour: `Hour = 0` means 00:00–01:00 local time.
- **Stress Index (0–100)** — where an hour's demand ranks within **its own region's** history:
  `(rank − 1) / (n − 1) × 100`. A value of 95 means the hour is in that region's top 5 % of demand.
  It is a **relative** measure — not grid capacity — and **cannot be compared across regions**.
- **High-stress hour** — Stress Index ≥ 95. **Top 1 % event** — Stress Index ≥ 99.
- **Data-center count** — unique facility IDs. Building and campus floor areas are never added together
  because campuses contain buildings; "point" records have no floor area, and none is invented.

---

## The dashboard

| Tab | What it shows |
|---|---|
| **Overview** | Demand over time (daily or hourly) and a snapshot card per region |
| **Demand** | Weekday vs weekend daily profile, seasons, days of the week, distribution, monthly trend |
| **Stress Analysis** | Stress Index distribution, stress by season, hour × month heat map, top stress events per region |
| **Weather & Solar** | Temperature vs demand (with correlations), sunlight vs demand, daily solar and wind profiles |
| **Geospatial** | Map of all data centers, facility types, data-center count vs peak demand, region summary |

Filters in the sidebar (region, season, daily/hourly) update every KPI, chart, table and map.
Average demand is always shown **per region** — never pooled — because the regions are different grids
observed in different years.

---

## Synthetic demonstration data

For classroom demonstration, `master_timeseries.csv` also contains **20,000 synthetic rows**
(5,000 per region), so the file holds **125,190 rows × 17 columns**.

- **Clearly marked.** The column `data_type` is `real` or `synthetic`. The 105,190 real rows come first and are
  byte-for-byte unchanged.
- **Off by default.** The dashboard's *Data mode* starts on **Real data**. Choosing *Real + synthetic (demo)* shows a
  warning banner, dotted lines for synthetic periods, "(synthetic)" tags, and a real-only vs combined comparison table.
- **Never used for analysis.** Every result in the notebook uses real rows only.
- **How they were made.** Each region re-plays one real year's January–July with small, smooth, seeded noise
  (seed 42), labelled with the period right after the real data (Virginia/Ohio Jan–Jul 2018,
  Texas/Georgia Jan–Jul 2022). Those dates are labels only — the rows do **not** describe what happened then.
- **Not measurements.** They add no new information and must never be cited as real demand or weather.

Method, validation results and limitations: [METHODOLOGY.md, Section 9](METHODOLOGY.md#9-synthetic-demonstration-data).

---

## Limitations to keep in mind

- The Stress Index is relative to each region's own history; it says nothing about grid capacity or reliability.
- Virginia/Ohio (2015–2017) and Texas/Georgia (2019–2021) cover different years, so compare patterns, not raw MW.
- Demand is measured for utility or grid areas, while data centers are counted by state.
- Each region's weather comes from a single location.
- The data-center atlas is a 2026 snapshot built from crowd-sourced map data; it may not match 2015–2021.
- Four regions are too few to show any relationship between data-center count and demand.
- Correlations are associations, not causes.
- Four isolated one-hour demand readings (Ohio 1, Georgia 3) look like source reporting errors; they are kept and
  disclosed. One of them is Georgia's recorded minimum (6,913 MW).

---

## Project structure

```
dav_project/
├── dav_project.ipynb          # Main deliverable: full pipeline + analysis
├── app.py                     # Streamlit dashboard
├── README.md                  # This file
├── METHODOLOGY.md             # Detailed pipeline, conventions, validation and limitations
├── PROJECT_DATA_PROFILE.md    # Complete statistical profile of every dataset
├── requirements.txt           # Pinned Python dependencies
├── .env.example               # Template for API credentials (copy to .env)
├── .streamlit/config.toml     # Dashboard theme (dark mode regardless of OS setting)
├── DOM_hourly.csv             # Raw Virginia demand (never modified)
├── AEP_hourly.csv.zip         # Raw Ohio demand (never modified)
├── p147s-4h760/               # IM3 Data Center Atlas v2026.02.09 (never modified)
└── data/                      # Created by the notebook (git-ignored)
    ├── raw/                   # Cached API downloads
    └── clean/
        ├── master_timeseries.csv   # One row per region-hour (data_type = real | synthetic)
        ├── geo_summary.csv         # One row per region: data-center counts, floor area, demand stats
        ├── im3_clean.csv           # Data centers in the four focus states
        └── im3_atlas_full.csv      # Data centers in all 47 states (others labelled "Other")
```

## Further reading

- **[METHODOLOGY.md](METHODOLOGY.md)** — how every step works and why, with the evidence for each decision.
- **[PROJECT_DATA_PROFILE.md](PROJECT_DATA_PROFILE.md)** — every dataset profiled: dimensions, statistics, quality
  checks, regional comparisons and the synthetic-data audit.
