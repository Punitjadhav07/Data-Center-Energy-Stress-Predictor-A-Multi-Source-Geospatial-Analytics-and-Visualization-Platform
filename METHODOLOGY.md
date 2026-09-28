# Methodology

## Data Provenance

### 1. Virginia and Ohio — PJM Kaggle CSVs

- **Source:** Kaggle dataset `robikscube/hourly-energy-consumption`
- **Files:** `DOM_hourly.csv` (Virginia, zone DOM), `AEP_hourly.csv.zip` (Ohio, zone AEP)
- **Coverage:** DOM spans 2005-05-01 to 2018-08-03 (116,189 rows). AEP spans 2004-10-01 to 2018-08-03 (121,273 rows). Project uses 2015–2017 only.
- **Columns:** `Datetime` (Eastern prevailing time), `<ZONE>_MW` (hourly demand in MW).

### 2. Texas and Georgia — EIA-930 API

- **Source:** EIA Open Data API v2
- **Endpoint:** `https://api.eia.gov/v2/electricity/rto/region-data/data/`
- **Respondents:** ERCO (Texas, ERCOT grid), SOCO (Georgia, Southern Company)
- **Type filter:** `D` (demand only)
- **Period:** UTC timestamps in format `2019-01-01T00`
- **Coverage:** 2019–2021 for both respondents, fetched per calendar year and concatenated.

### 3. Weather and Solar — NREL NSRDB

- **Source:** NREL National Solar Radiation Database (NSRDB), via NLR API
- **Endpoint:** `https://developer.nlr.gov/api/nsrdb/v2/solar/nsrdb-GOES-aggregated-v4-0-0-download.csv`
- **Attributes:** GHI, DNI, DHI (W/m²), air temperature (°C), wind speed (m/s)
- **Interval:** 30 minutes, UTC, leap-day included
- **Coverage:** One representative lat/lon point per region (see table below); one API call per year (multi-year calls return HTTP 400).

| Region   | Lat    | Lon     |
|----------|--------|---------|
| Virginia | 38.95  | -77.45  |
| Ohio     | 39.96  | -82.99  |
| Texas    | 32.78  | -96.80  |
| Georgia  | 33.75  | -84.39  |

30-minute rows are resampled to hourly mean before merging with demand data.

### 4. IM3 Data Center Atlas

- **Source:** PNNL / DOE MSD-LIVE, record p147s-4h760
- **Version:** v2026.02.09, DOI 10.57931/3017294, ODbL license
- **Shape:** 1,479 rows, 13 columns
- **Layer types:** `building` (1,239 rows), `campus` (135 rows), `point` (105 rows)
- **Spatial scope:** Filtered to Virginia (VA), Ohio (OH), Texas (TX), Georgia (GA)

---

## UTC Time Alignment

All four demand streams are aligned to a single UTC `Timestamp` column before merging.

### PJM (Virginia and Ohio)

PJM files use **Eastern prevailing time** (EST in winter = UTC-5; EDT in summer = UTC-4). The files are not sorted and contain:
- A **duplicate** 02:00 timestamp each November (fall-back clock change — two consecutive rows with the same local label, both representing real elapsed hours).
- A **missing** 03:00 timestamp each March (spring-forward clock change).

**Reconstruction approach:**
1. Sort by `Datetime` string (lexicographic sort is correct within a single timezone convention year).
2. Filter to target years.
3. Assert that the first row is January 1.
4. Assign a **sequential** UTC clock starting from `Jan 1 01:00 ET = Jan 1 06:00 UTC` (EST offset, since January is always standard time).
5. Each subsequent row is exactly +1 hour UTC — this correctly resolves both the November duplicate and the March gap without discarding any real data.
6. Assert that the last row equals `Jan 1 05:00 UTC` of the following year.

Expected row counts: 8,760 (non-leap), 8,784 (leap year 2016).

### EIA-930 (Texas and Georgia)

EIA-930 `period` values are already UTC (`2019-01-01T00` format). Parsed directly with `pd.to_datetime(..., utc=True)`. No reconstruction needed.

### NSRDB (all regions)

NSRDB data is fetched with `utc=true`. Timestamps are built from `Year`, `Month`, `Day`, `Hour`, `Minute` columns and assigned UTC timezone. 30-min rows are resampled to hourly mean using `resample("h").mean()`.

---

## Derived Columns

After merging demand and weather on `Timestamp` (UTC), the following columns are derived from the **local** timestamp (using each region's IANA timezone):

| Column | Derivation |
|--------|------------|
| `Timestamp_Local` | UTC converted to region timezone, stored as ISO string |
| `Year` | Local year |
| `Month` | Local month (1–12) |
| `Hour` | Local hour (0–23) |
| `DayOfWeek` | Local day of week (0=Monday) |
| `Is_Weekend` | 1 if Saturday or Sunday, else 0 |
| `Season` | Winter (Dec–Feb), Spring (Mar–May), Summer (Jun–Aug), Fall (Sep–Nov) |

---

## Stress Index

```
Stress_Index = percentile_rank(Demand_MW) × 100
```

Computed within each region's own demand history using `scipy.stats.rankdata` with method `"average"`. Range: 0–100.

**This is a relative, descriptive measure.** It indicates where a given hour falls in that region's own demand distribution. A value of 95 means the hour is in the top 5 % of that region's observed demand. It does not represent an engineering capacity threshold or a probability of grid failure.

**Cross-region comparisons of Stress Index are not meaningful** because each region has a different absolute demand level and a different grid.

---

## geo_summary Construction

`geo_summary.csv` has one row per region. It is produced by joining:
1. **IM3 counts:** `nunique(id)` per region and per layer type. Multi-county rows for the same facility share the same `id`; `nunique` prevents double-counting.
2. **sqft by type:** Summed over unique `id`s per type separately (`building`, `campus`). Summing across types would double-count facilities recorded as both a building and a campus. `sqft` is `NaN` for all `point` records (by design in the source data).
3. **Demand statistics:** Average, peak, and standard deviation of `Demand_MW` from the master time series.

---

## Known Limitations

| Limitation | Impact |
|-----------|--------|
| **One weather point per region** | Weather represents a single lat/lon, not a spatial average across the balancing authority. Microclimatic variation is not captured. |
| **Missing sqft for point records** | 105 IM3 records (all `point` type) have no floor-area data. Dashboard and geo_summary display these as `sqft N/A`. |
| **Different calendar years per source** | Virginia/Ohio data is from 2015–2017; Texas/Georgia is from 2019–2021. Absolute demand levels cannot be compared across the two cohorts. |
| **IM3 is a snapshot** | The atlas reflects data center locations as of February 2026, which may not match the demand periods (2015–2021). |
| **EIA-930 null values** | A small number of EIA-930 hours have null demand values (reported in the notebook). These rows are dropped and reported as gaps. |
| **NSRDB boundary alignment** | Merging demand and NSRDB on UTC may drop a small number of rows at year boundaries if NSRDB coverage does not exactly match. Total master rows = 105,178 (target 105,216; gap 38 rows). |
