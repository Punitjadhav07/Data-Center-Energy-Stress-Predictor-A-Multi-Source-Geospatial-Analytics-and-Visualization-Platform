# Methodology

This project is descriptive. It summarizes historical data and makes **no predictions**.

## 1. Data Provenance

### 1.1 Virginia and Ohio — PJM Kaggle CSVs

- **Source:** Kaggle dataset `robikscube/hourly-energy-consumption` (data originate from PJM Interconnection).
- **Files:** `DOM_hourly.csv` (Virginia, zone DOM) and `AEP_hourly.csv.zip` (Ohio, zone AEP). The originals are never modified; the AEP zip is extracted to `data/raw/`.
- **Coverage in the files:** DOM 2005-05-01 to 2018-08-03 (116,189 rows); AEP 2004-10-01 to 2018-08-03 (121,273 rows). The project uses local years 2015–2017.
- **Columns:** `Datetime` (Eastern prevailing time, hour-ending; see Section 2), `<ZONE>_MW` (hourly demand).

### 1.2 Texas and Georgia — EIA-930 API

- **Endpoint:** `https://api.eia.gov/v2/electricity/rto/region-data/data/`, respondents `ERCO` (ERCOT) and `SOCO` (Southern Company), type `D` (demand).
- **Requests:** one per UTC calendar year 2019–2021, plus a small request for `2022-01-01T00`–`T08` so that the last local day of 2021 is complete. Cached in `data/raw/eia930_*.json`.
- **Units:** EIA reports `value` in **MWh** per one-hour interval. Energy over one hour in MWh equals the average power in MW over that hour, so the column is named `Demand_MW`.

### 1.3 Weather and Solar — NSRDB

- **Endpoint:** `https://developer.nlr.gov/api/nsrdb/v2/solar/nsrdb-GOES-aggregated-v4-0-0-download.csv`
- **Attributes:** GHI, DNI, DHI (W/m²), air temperature (°C), wind speed (m/s); 30-minute interval; UTC; leap day included.
- **Requests:** one per year (multi-year requests returned HTTP 400). The year after each region's last analysis year is also downloaded because the API only serves whole years; it is used only for the final 5–6 local hours, and everything else from that year is discarded by the merge.
- **Location:** one point per region:

| Region   | Lat   | Lon    | Time zone        |
|----------|-------|--------|------------------|
| Virginia | 38.95 | -77.45 | America/New_York |
| Ohio     | 39.96 | -82.99 | America/New_York |
| Texas    | 32.78 | -96.80 | America/Chicago  |
| Georgia  | 33.75 | -84.39 | America/New_York |

### 1.4 IM3 Data Center Atlas

- **Source:** PNNL / DOE MSD-LIVE, record p147s-4h760, v2026.02.09, DOI 10.57931/3017294, ODbL 1.0; derived from OpenStreetMap.
- **Shape:** 1,479 rows, 13 columns, 1,474 unique `id`s, 47 states, all rows have coordinates.
- **Layer types:** `building` (1,239 rows), `campus` (135), `point` (105).
- **`sqft`:** polygon surface area in **square feet** (IM3 README). Present for every building and campus row and absent for every point row. Missing areas are never imputed.
- **Snapshot date:** February 2026. The demand data cover 2015–2021, so some mapped facilities did not exist during the demand period.

---

## 2. Time Alignment

**Convention used throughout:** `Timestamp` is the **UTC start** of a one-hour interval.
`Timestamp_Local` and the derived `Hour` are the local start of that interval, so `Hour = 0`
means 00:00–01:00 local time.

### 2.1 PJM (hour-ending, Eastern prevailing time)

Evidence in the files: each November the `02:00` label appears twice and each March `03:00`
is missing. This matches PJM's hour-ending convention, where HE02 repeats on the fall-back
day and HE03 is skipped on the spring-forward day. (An hour-beginning file would instead
repeat `01:00` and skip `02:00`.) Label `01:00` is therefore the hour 00:00–01:00, and label
`00:00` is the last hour of the previous day.

Reconstruction for each local year Y:
1. Stable sort by `Datetime`. The two rows sharing the November label keep their file order.
2. Keep labels from Jan 1 Y 01:00 through Jan 1 Y+1 00:00 inclusive (8,760 or 8,784 rows).
3. Assign `Timestamp = Jan 1 Y 05:00 UTC + row number` (00:00 EST = 05:00 UTC). Each row is one elapsed hour, so no real hour is dropped.
4. Assert that the last row starts at Jan 1 Y+1 04:00 UTC.
5. Cross-check every row whose start time is unambiguous against a DST-aware conversion of `label − 1 h`. All rows agree.

### 2.2 EIA-930 (hour-ending, UTC)

EIA-930 instructions specify hourly values reported by hour-ending time with UTC stamps.
Interval start = `period − 1 h`. Rows are then restricted to hours that start inside the
region's local calendar years.

### 2.3 NSRDB (interval-start labels)

Timestamps are built from Year/Month/Day/Hour/Minute (UTC). Checked empirically: the
average GHI curve for Texas is centred about 16 minutes before theoretical solar noon. That
is consistent with each 30-minute value covering the half hour that starts at its label. The
hourly value is the mean of the `:00` and `:30` values, labeled at the hour start.

### 2.4 Merge

Demand and weather are inner-joined on `Timestamp`. After the boundary data above, every
demand hour has a matching weather hour (0 rows lost in the merge).

### 2.5 Remaining timing uncertainty

- The NSRDB interval semantics are inferred from the data (Section 2.3), not from a documentation statement. Any residual offset is under 30 minutes.
- For the repeated November label in PJM data, the order of the two rows is taken from the file. If the file order is reversed, those two hours (one per year) swap values.
- The sanity check (mode of the daily-minimum hour should be 03:00–05:00 local) gives Virginia 03, Ohio 03, Texas 03 and Georgia 04.

---

## 3. Derived Columns

| Column | Derivation |
|--------|------------|
| `Timestamp_Local` | Interval start in the region's time zone (ISO string) |
| `Year`, `Month`, `Hour` | From local interval start |
| `DayOfWeek` | Local day of week (0 = Monday) |
| `Is_Weekend` | 1 if Saturday or Sunday |
| `Season` | Winter (Dec–Feb), Spring (Mar–May), Summer (Jun–Aug), Fall (Sep–Nov) |
| `Stress_Index` | See Section 4 |

Daily aggregates in the notebook and dashboard use the **local** calendar date.

---

## 4. Stress Index

```
Stress_Index = (rank − 1) / (n − 1) × 100
```

`rank` is the average rank of the hour's `Demand_MW` among the `n` hours of the same region
(ties share their average rank). The lowest hour scores 0 and the highest 100. This gives the
same values as `scipy.stats.rankdata(method="average")`, which earlier versions used.

**It is a relative, descriptive percentile, not a grid-capacity or reliability measure.** A value
of 95 means the hour is in the top 5 % of that region's own observed demand. It says nothing
about how close the grid was to its limits. Because each region is ranked against itself,
**comparisons of Stress Index across regions are not meaningful**.

---

## 5. Missing Data and Dropped Observations

| Region | Expected hours | Rows kept | Dropped | Reason |
|--------|---------------:|----------:|--------:|--------|
| Virginia | 26,304 | 26,304 | 0 | — |
| Ohio     | 26,304 | 26,304 | 0 | — |
| Texas    | 26,304 | 26,303 | 1 | Hour starting 2021-11-07 05:00 UTC not returned by the API |
| Georgia  | 26,304 | 26,279 | 25 | 24 null values on local date 2019-11-03; hour starting 2019-11-04 05:00 UTC not returned by the API |

No value is interpolated, filled or synthesized. The notebook prints these gaps every run.

---

## 6. geo_summary Construction

One row per region:
1. **Counts:** `nunique(id)` overall and per type. A facility that straddles a county line appears as several rows with the same `id`.
2. **Floor area:** `building_area_sqft` and `campus_area_sqft`, each summed over unique ids of that type, **in square feet**. They are never added together, because building and campus polygons overlap. Point records have no area.
3. **Demand statistics:** mean, max and standard deviation of `Demand_MW` from the master table.

`im3_atlas_full.csv` holds all atlas rows, with `Region = "Other"` outside the four focus states. It is used only as national context on the dashboard map. `im3_clean.csv` is the four-state subset.

---

## 7. Visualization Notes

- Scatter plots draw a random sample per region with a fixed seed (1/6 of hours for temperature, 1/4 of daytime hours for GHI). Every hour of the day is represented. All correlations use every hour, not the sample.
- Map markers for buildings and campuses are sized so that marker **area** is proportional to floor area. On the dashboard, the on-screen radius is limited to 2–30 px so small sites stay visible and large ones do not cover neighbors. Point records are drawn as fixed 3 px hollow rings (dashboard) or `x` markers (notebook) and are never given an area.
- Chart takeaways are computed from the data at run time.

### Dashboard summary figures

- **Average demand is shown per region, never pooled.** The regions are different balancing areas (ERCOT's load is about four times Dominion's) observed in different years (2015–2017 vs 2019–2021). A single pooled mean would mostly reflect which regions happen to be selected, would change when a small region is added, and would describe no real grid or period. With one region selected, the card shows that region's mean and years.
- **Highest regional peak** names the region and local date it belongs to. It is the largest single-hour value among the selected regions, not a combined peak.
- **High-stress hours** is the share of filtered hours at or above each region's **own** 95th percentile. With all seasons selected it is 5 % by construction; season filters show where those hours fall.
- **Top stress events** are ranked **within each region** (20 rows split evenly across the selected regions, e.g. top 5 each for four regions). An earlier version ranked all regions together. Every region's top hours score close to 100, so the cross-region order was decided only by tiny differences caused by each region's hour count. Rank uses the season-filtered hours; tied demand values share a rank. The Stress value itself is still the percentile within the region's full record.

---

## 8. Known Limitations

| Limitation | Impact |
|-----------|--------|
| No prediction | The name says "Predictor", but every result is descriptive. |
| Stress Index is relative | Percentile within each region; not grid capacity; not comparable across regions. |
| Different years | Virginia/Ohio cover 2015–2017 and Texas/Georgia cover 2019–2021. Absolute levels across the two groups reflect different periods; the dashboard therefore reports demand per region, and side-by-side charts compare regions from different years. |
| Grid areas ≠ states | Demand is for balancing areas or zones (DOM, AEP, ERCOT, Southern Company), while data centers are counted by state. |
| One weather point per region | A single NSRDB location stands in for a whole balancing area. |
| IM3 snapshot (Feb 2026) | Built from crowd-sourced OpenStreetMap data; facility presence and size may not match 2015–2021; 105 point records have no area. |
| Four regions | Data-center count vs demand has only four points and cannot establish a relationship. |
| Correlation only | Temperature and GHI correlations are associations, not causal effects. |
| Timing | See Section 2.5. |
| Licensing not fully verified | The Kaggle dataset license and NSRDB redistribution terms were not confirmed (see README). EIA-930 (public domain) and IM3 (ODbL) are documented. |
| Synthetic demonstration rows | 20,000 generated rows exist in `master_timeseries.csv` for the dashboard's demo mode (Section 9). They are not measurements and are excluded from every analysis. |

---

## 9. Synthetic Demonstration Data

**Purpose.** A larger dataset for classroom demonstration of the dashboard. The real data alone already meets the
size requirement (105,190 rows); synthetic rows add no evidence and are **never** used in the notebook's analysis.

**Marker.** Column `data_type` (`real` / `synthetic`). `master_timeseries.csv` = 105,190 real rows (first, unchanged)
+ 20,000 synthetic rows = 125,190 rows × 17 columns. The IM3 files and `geo_summary.csv` contain real data only.

**Method** (notebook Section 7, seed `SYN_SEED = 42`, `SYN_HOURS_PER_REGION = 5,000`):

1. **Period.** 5,000 consecutive hours per region starting at local midnight on 1 January after the real period:
   Virginia/Ohio 2018-01-01 → 2018-07-28 08:00, Texas/Georgia 2022-01-01 → 2022-07-28 08:00. These dates are labels for
   a synthetic period; they do not describe what happened then (real data exists for some of them and is not used).
2. **Template.** One continuous stretch of the region's own real data from a seeded real year, starting on the first
   date on or after 1 January with the same weekday as the synthetic start. All variables are copied together, so the
   hourly shape, weekly rhythm, season and demand–weather relationships are preserved. Stretches containing a missing
   hour or a suspected one-hour spike are rejected. Templates drawn: Virginia 2017, Ohio 2015, Texas 2021, Georgia 2019.
3. **Noise.** Demand × (1 + a), temperature + b, wind × clip(1 + c, 0.7, 1.3), where a, b, c are AR(1) processes
   (φ = 0.98, 0.97, 0.95; stationary s.d. 1.5 %, 0.6 °C, 10 %); GHI, DNI and DHI × one daily factor clipped to 0.85–1.15.
4. **Derived columns.** Local calendar fields and Season use the same `merge_region` code as the real data.
   `Stress_Index` uses the same formula positioned on each region's **real** demand distribution, so real rows keep their
   exact values; synthetic demand above the real maximum is capped at 100.
5. **Rejected first design.** Day-by-day resampling from different real years was tried first and rejected: the
   validation found isolated one-hour demand spikes at the day seams.

**Validation** (notebook, every run; all pass): real rows identical to the real table; exactly 20,000 synthetic rows;
schema and dtypes; no duplicate (Region, Timestamp); no overlap with real hours; no missing values; demand > 0;
irradiance within 0–1,361 W/m² and DHI ≤ GHI; temperature and wind within physical limits; Stress 0–100; no isolated
one-hour spikes; largest hour-to-hour demand and temperature changes no more than 5 % above the real maximum (the
tolerance allows for noise added on top of copied real steps). Distributions are compared with real data from the
same months (hourly-profile correlation ≈ 1.00 in every region). Outside the notebook, the real rows of the new CSV were
confirmed byte-identical to the previous file, the default dashboard view was confirmed identical to the previous
version, and a clean rerun reproduces all outputs byte for byte.

**Dashboard.** Default *Real data* mode filters to `data_type == "real"` before any calculation. *Real + synthetic
(demo)* shows a warning banner with the synthetic share, dotted lines for synthetic periods in the time series and
monthly trend, "(synthetic)" tags on peaks, a `Data` column in the stress-event table, "incl. synthetic" on the
affected KPIs, and a real-only vs real + synthetic comparison table.

**Limitations.** Each region's synthetic period is one real year's January–July re-played with small noise: it adds no
information, repeats that year's extreme events (Texas's template 2021 includes Winter Storm Uri in February), cannot
contain events absent from the template, misaligns public holidays, ignores load growth, and covers January–July only,
so pooled real + synthetic averages shift toward winter/spring. Monthly-mean and temperature–demand correlations differ
somewhat from the 3-year real averages because one template year is used. Synthetic rows must never be cited as
measured demand or weather.
