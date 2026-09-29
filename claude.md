# Data Center Energy Stress Predictor

A Multi-Source Geospatial Analytics and Visualization Platform

Third-year B.Tech IT, Data Analytics & Visualization (DAV) course project.
Pure analytics and visualization: NO machine learning or deep learning.
Runs locally (VS Code, Python venv), not Colab.

## Goal

Show when and where the electric grid is stressed in four U.S. data-center hub
regions and how that relates to weather, solar availability and data-center
concentration.
Pipeline: collect -> clean -> integrate -> EDA -> stress index -> geospatial
analysis -> visualization -> Streamlit dashboard.

## Hard requirements

- The master time-series table must have at least 100,000 rows (target about 105,000).
  The requirement was stated as both "above 1 lakh" and "75k-100k"; build for
  about 105k and keep the years configurable so it can be trimmed.
- 
- No fabricated data. No invented grid-capacity thresholds, carbon factors or
  simulated workloads. Anything derived must be labeled as derived.
- Never print, log or commit API keys. Keys live in `.env` (already created by
  the user; one key has leaked before). `.env` must be in `.gitignore`.
- Do not modify or move the raw input files. Work on copies in `data/`.

## Project folder (existing files, do not move)

    DAV_PROJECT/
      DOM_hourly.csv
      AEP_hourly.csv.zip
      p147s-4h760/im3_open_source_data_center_atlas_v2026.02.09/
        DISCLAIMER.pdf, README.pdf, CSV + one other data file
      .env                (EIA_API_KEY, NSRDB_API_KEY, NSRDB_FULL_NAME,
                           NSRDB_EMAIL, NSRDB_AFFILIATION)
Files to create: dav_project.ipynb (primary deliverable), app.py, requirements.txt,
.env.example, .gitignore, README.md, METHODOLOGY.md, data/raw/, data/clean/.

## Regions and demand sources (4 regions x 3 years)

| Region                                                              | Demand source                      | Years     | Weather point (lat, lon) | tz               |
| ------------------------------------------------------------------- | ---------------------------------- | --------- | ------------------------ | ---------------- |
| Virginia                                                            | PJM Kaggle DOM_hourly.csv (DOM_MW) | 2015-2017 | 38.95, -77.45            | America/New_York |
| Ohio                                                                | PJM Kaggle AEP_hourly.csv (AEP_MW) | 2015-2017 | 39.96, -82.99            | America/New_York |
| Texas                                                               | EIA-930 respondent ERCO            | 2019-2021 | 32.78, -96.80            | America/Chicago  |
| Georgia                                                             | EIA-930 respondent SOCO            | 2019-2021 | 33.75, -84.39            | America/New_York |
| Expected: about 26,304 hourly rows per region, about 105,216 total. |                                    |           |                          |                  |
| Verify actual coverage and report gaps; do not fill gaps silently.  |                                    |           |                          |                  |

## Data sources

### 1. PJM hourly consumption (Kaggle: robikscube/hourly-energy-consumption)

- Columns: `Datetime`, `<ZONE>_MW`. Rows are NOT sorted in the file.
- Timestamps are Eastern prevailing time (DST). Observed in DOM: 116,189 rows,
  2005-05-01 to 2018-08-03; duplicated 02:00 timestamps each November and a
  missing hour each March. Each row is still one real elapsed hour.
- Handling: sort (stable), filter years, rebuild a continuous UTC clock from the
  first row (Jan 1 = EST = UTC-5) plus row sequence, and check that the last row
  agrees. Do not blindly drop the November duplicates (that loses a real hour).

### 2. EIA-930 hourly demand (EIA Open Data API v2)

- Endpoint: https://api.eia.gov/v2/electricity/rto/region-data/data/
- Params: frequency=hourly, data[0]=value, facets[respondent][]=ERCO|SOCO,
  facets[type][]=D (demand), start/end like 2019-01-01T00, sort by period asc,
  paginate with offset/length=5000. `period` is UTC.
- Fetch per calendar year, concatenate, cache raw output in data/raw/.

### 3. NREL/NLR NSRDB weather and solar

- Endpoint that worked for the user (returned 200):
  https://developer.nlr.gov/api/nsrdb/v2/solar/nsrdb-GOES-aggregated-v4-0-0-download.csv
  (NREL has been renamed NLR; if that host fails, try developer.nrel.gov.)
- Params: api_key, wkt=POINT(lon lat), names=<years></years>, attributes=
  ghi,dni,dhi,air_temperature,wind_speed, interval=30, utc=true, leap_day=true,
  full_name, email, affiliation, reason ("Academic research and data analytics
  project"), mailing_list=false.
- Response: 2 metadata lines, then header
  `Year,Month,Day,Hour,Minute,GHI,DNI,DHI,Temperature,Wind Speed`; 30-minute rows.
- The user only tested a single year. Verify that a multi-year `names` value
  returns all years in one CSV; if not, request one year per call and concatenate.
- Build a timestamp from Year/Month/Day/Hour/Minute (UTC), resample to hourly mean.
- Cache raw output in data/raw/. Skip the API call if the cache exists.

### 4. IM3 Open Source Data Center Atlas (PNNL / DOE, MSD-LIVE)

- Record p147s-4h760, v2026.02.09, DOI 10.57931/3017294, ODbL license.
- Columns: id, state, state_abb, state_id, county, county_id, operator, ref, name,
  sqft, lon, lat, type. Inspect the actual CSV first; an earlier version had 1,242 rows.
- Layers via `type`: point, building, campus. `sqft` exists only for building and
  campus. Buildings and campuses overlap, so summing sqft double counts.
- A campus or building that straddles a county line appears as several rows with
  the same `id`. Count data centers with nunique(id), never row count.
- Filter to Virginia, Ohio, Texas, Georgia and drop rows with no coordinates.

## Key design decisions

1. Time alignment: merge demand and weather on a UTC `Timestamp`. Add
   `Timestamp_Local` per region (its tz) and derive Hour, Month, DayOfWeek,
   Is_Weekend, Season from local time.
2. Master schema (time-series grain, one row per Region-hour): Region, Timestamp,
   Timestamp_Local, Demand_MW, GHI, DNI, DHI, Temperature, Wind Speed, Year, Month,
   Hour, DayOfWeek, Is_Weekend, Season, Stress_Index.
3. Stress_Index = percentile rank (0-100) of Demand_MW within each region's own
   data. It is a relative measure, not an engineering threshold. Label it that way
   everywhere (charts, dashboard, methodology).
4. IM3 is spatial, not time-series. Never join it row-to-row with the hourly table.
   Connect them at region level in geo_summary: unique data-center count, sqft
   reported per layer type (not one summed total), plus avg, peak and std demand.
5. Sanity check for clock alignment: the hour of daily minimum demand should fall
   about 3-5 AM local in every region. Investigate any region that is off.
6. Report per-region row counts against full coverage, duplicate (Region,
   Timestamp) pairs (must be 0) and missing values after merging.

## Analysis and visualizations to include

Descriptive stats per region; peak and minimum demand with timestamps; daily
average demand per region (faceted); hourly profile (weekday vs weekend);
seasonal and monthly demand; temperature vs demand (with correlation); solar
(GHI) vs demand; Stress_Index distribution per region; hour x month stress
heatmap; top 1% stress hours and when they occur; data-center map sized by sqft
(NaN sqft handled); data-center count vs average or peak demand per region.
Every chart gets a title, axis labels with units and a one-line takeaway written
from the real numbers, not assumed ones.

## Dashboard (Streamlit, reads data/clean/*.csv only, no API calls at runtime)

Stack: Python, pandas, numpy, plotly, pydeck, streamlit.
**IMPORTANT:** Run with `source .venv/bin/activate && streamlit run app.py`.
The venv must be activated first — streamlit is installed only there.

- Flat dark theme: page #0F1419, cards #1A2233, borders #2A3444, Inter font.
  No gradients anywhere. Palette defined once in REGION_COLOR / REGION_RGB dicts:
  Virginia #4A90D9 (steel blue), Ohio #E89B3E (amber), Texas #3AAFA9 (teal),
  Georgia #D9534F (coral red). All charts use the same apply_theme() helper.
- Sidebar: region multiselect, season multiselect, daily/hourly resolution,
  "About this project" expander.
- Custom HTML KPI row (5 flat bordered cards): regions, data centers, avg demand,
  peak demand with region label, high-stress-hour percentage.
- Pydeck map uses CARTO dark-matter basemap (free, no Mapbox token needed).
  Previous mapbox:// style URL failed silently without MAPBOX_API_KEY.
- 5 tabbed panels:
  1. **Overview**: demand time series (daily/hourly), per-region snapshot cards
     (peak demand + timestamp, avg temp, avg GHI, DC count).
  2. **Demand**: hourly weekday/weekend profile, seasonal demand bars, day-of-week
     pattern, demand violin distribution, monthly trend with markers.
  3. **Stress Analysis**: stress box plot, stress-by-season bars, hour × month
     heatmap (Inferno colorscale), top-20 stress events table.
  4. **Weather & Solar**: temperature vs demand scatter (go.Scatter, no OLS dep)
     with Pearson r table, GHI vs demand (daytime only), hourly solar area chart,
     wind speed profile, monthly GHI/DNI/DHI breakdown.
  5. **Geospatial**: pydeck ScatterplotLayer on CARTO dark-matter basemap, DC
     type stacked bar, DC concentration vs peak demand bubble chart, region
     summary table.
- Handle empty selections gracefully.
- Footer caption explaining that Stress Index is relative and percentile-based.

## Working rules

- Notebook is the primary deliverable: clean, sequential, markdown between
  sections, runs top to bottom with "Restart and Run All".
- Use requirements.txt (pandas>=2, numpy, requests, plotly, seaborn, matplotlib,
  pydeck, streamlit, python-dotenv, ipykernel, nbconvert).
- Standard English, professional tone in all markdown and docs.
- Build in stages and check each stage's output before moving on.
- Verify by executing: run the notebook end to end (nbconvert --execute) and smoke
  test the app (streamlit AppTest or headless launch) before saying anything is done.
