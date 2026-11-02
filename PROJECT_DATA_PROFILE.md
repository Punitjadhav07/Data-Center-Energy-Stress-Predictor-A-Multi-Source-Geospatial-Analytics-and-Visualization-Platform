# Project Data Profile — Data Center Energy Stress Predictor

*A Multi-Source Geospatial Analytics and Visualization Platform*

> **Real vs synthetic.** `master_timeseries.csv` contains 105,190 **real** rows and 20,000 **synthetic demonstration** rows (column `data_type`). Sections 1–11 profile the real data; Section 12 profiles the synthetic rows. Synthetic rows are generated, not measured, and are never part of the analytical results.

Generated from the current files on 2026-11-02 20:10. Every number below was computed directly from `data/clean/*.csv`, the raw inputs in the project root and `data/raw/`, and `dav_project.ipynb`. Nothing in the project was modified. Counts are integers; measurements carry their units; **derived** metrics are labelled as such.

## Executive Summary

- **Final time-series table:** 105,190 hourly observations × 16 columns across 4 regions (26 of 105,216 expected hours missing at the source, 0.025%; none filled).
- **Periods:** Virginia and Ohio 2015–2017 (PJM); Texas and Georgia 2019–2021 (EIA-930); 6 calendar years in total, local time.
- **Data quality:** 0 nulls, 0 duplicate (Region, Timestamp) pairs, 0 negative demand, 0 physically impossible weather values, 0 calendar-field inconsistencies in the master table. **4 isolated one-hour demand spikes look like source reporting errors** (Ohio 1, Georgia 3); they are kept and disclosed. One of them is Georgia's recorded minimum (6,913 MW, 2019-10-25 23:00); the lowest plausible Georgia value is 16,328 MW (2020-04-26 07:00).
- **Average demand:** Virginia 11,117 MW, Ohio 14,712 MW, Texas 43,994 MW, Georgia 26,574 MW.
- **Record peaks:** Virginia 21,651 MW (2015-02-20 07:00); Ohio 24,739 MW (2015-02-20 07:00); Texas 74,533 MW (2019-08-12 16:00); Georgia 45,515 MW (2019-08-13 16:00).
- **Seasonality:** highest-demand month — Virginia Jul, Ohio Jan, Texas Aug, Georgia Aug; demand peaks in the afternoon/evening (Virginia 18:00, Ohio 18:00, Texas 17:00, Georgia 18:00 local) and bottoms out at night (Virginia 03:00, Ohio 03:00, Texas 03:00, Georgia 03:00).
- **Temperature vs demand (Pearson r):** Virginia +0.131, Ohio -0.058, Texas +0.631, Georgia +0.476. The relationship is U-shaped (heating + cooling), so r understates it; split at 18 °C, r is strongly negative below and strongly positive above in every region.
- **Data-center atlas:** 1,479 records (1,474 unique ids) across 47 states; 577 records / 574 unique ids in the 4 focus states (Virginia 319). 105 point records have no floor area (never imputed).
- **Stress Index:** within-region percentile of demand, 0–100; 5,261 hours ≥ 95 and 1,055 hours ≥ 99 (≈1 % per region by construction). It is relative, not a grid-capacity measure.
- **Synthetic demonstration rows:** 20,000 rows (5,000 per region) appended after the real period and labelled `data_type = synthetic`; real rows verified unchanged: yes. They are profiled in Section 12 and excluded from every statistic in Sections 1–11.
- **Cross-checks:** every statistic re-computed here agrees with the notebook output and the live dashboard KPIs (all match).

## 1. Final Dataset Dimensions

| File                  | Rows    | Columns | Total cells | Size (MB) | Size (KB)  | Numerical | Categorical | Datetime | Boolean |
| --------------------- | ------- | ------- | ----------- | --------- | ---------- | --------- | ----------- | -------- | ------- |
| master_timeseries.csv | 125,190 | 17      | 2,128,230   | 17.131    | 17,131.458 | 11        | 3           | 2        | 1       |
| im3_clean.csv         | 577     | 14      | 8,078       | 0.079     | 78.521     | 3         | 11          | 0        | 0       |
| geo_summary.csv       | 4       | 10      | 40          | 0.000     | 0.378      | 9         | 1           | 0        | 0       |
| im3_atlas_full.csv    | 1,479   | 14      | 20,706      | 0.195     | 195.086    | 3         | 11          | 0        | 0       |

`master_timeseries.csv` now holds real **and** synthetic rows (column `data_type`); the file figures above describe the whole file. **From here to Section 11 every statistic uses the real rows only** (`data_type == "real"`); the synthetic rows are profiled separately in Section 12.

Classification is by meaning, not storage: timestamps are stored as ISO-8601 text; `Is_Weekend` is stored as 0/1; IM3 `id`, `state_id`, `county_id` are identifiers stored as integers and are counted as categorical.

**master_timeseries.csv — column types**

| Column          | Stored dtype | Semantic type                         | Unit / meaning                                                     | Non-null  |
| --------------- | ------------ | ------------------------------------- | ------------------------------------------------------------------ | --------- |
| Region          | str          | categorical                           | text                                                               | 125,190   |
| Timestamp       | str          | datetime                              | —                                                                 | 125,190   |
| Demand_MW       | float64      | numerical                             | MW (hourly average; EIA reports MWh per 1-h interval = average MW) | 125,190   |
| GHI             | float64      | numerical                             | W/m²                                                              | 125,190   |
| DNI             | float64      | numerical                             | W/m²                                                              | 125,190   |
| DHI             | float64      | numerical                             | W/m²                                                              | 125,190   |
| Temperature     | float64      | numerical                             | °C                                                                | 125,190   |
| Wind Speed      | float64      | numerical                             | m/s                                                                | 125,190   |
| Year            | int64        | numerical (integer calendar field)    | calendar year (local)                                              | 125,190   |
| Month           | int64        | numerical (integer calendar field)    | 1–12 (local)                                                      | 125,190   |
| Hour            | int64        | numerical (integer calendar field)    | 0–23, local start of the hour                                     | 125,190   |
| DayOfWeek       | int64        | numerical (integer calendar field)    | 0 = Monday … 6 = Sunday                                           | 125,190   |
| Is_Weekend      | int64        | boolean (stored 0/1)                  | 1 = Sat/Sun                                                        | 125,190   |
| Season          | str          | categorical                           | text                                                               | 125,190   |
| Timestamp_Local | str          | datetime                              | —                                                                 | 125,190   |
| Stress_Index    | float64      | numerical (derived)                   | dimensionless percentile, 0–100 (derived)                         | 125,190   |
| data_type       | str          | categorical (real / synthetic marker) | real                                                               | synthetic |

**im3_clean.csv — column types**

| Column    | Stored dtype | Semantic type                               | Unit / meaning                      | Non-null |
| --------- | ------------ | ------------------------------------------- | ----------------------------------- | -------- |
| id        | int64        | categorical (identifier stored as integer)  | identifier                          | 577      |
| state     | str          | categorical                                 | text                                | 577      |
| state_abb | str          | categorical                                 | text                                | 577      |
| state_id  | int64        | categorical (FIPS code stored as integer)   | code                                | 577      |
| county    | str          | categorical                                 | text                                | 577      |
| county_id | int64        | categorical (county code stored as integer) | code                                | 577      |
| operator  | str          | categorical (text)                          | text                                | 412      |
| ref       | str          | categorical (text)                          | text                                | 216      |
| name      | str          | categorical (text)                          | text                                | 488      |
| sqft      | float64      | numerical                                   | square feet (facility polygon area) | 562      |
| lon       | float64      | numerical                                   | decimal degrees                     | 577      |
| lat       | float64      | numerical                                   | decimal degrees                     | 577      |
| type      | str          | categorical                                 | text                                | 577      |
| Region    | str          | categorical (derived)                       | text                                | 577      |

**geo_summary.csv — column types**

| Column             | Stored dtype | Semantic type       | Unit / meaning      | Non-null |
| ------------------ | ------------ | ------------------- | ------------------- | -------- |
| Region             | str          | categorical         | text                | 4        |
| unique_DCs         | int64        | numerical (derived) | count of unique ids | 4        |
| n_building         | int64        | numerical (derived) | count               | 4        |
| n_campus           | int64        | numerical (derived) | count               | 4        |
| n_point            | int64        | numerical (derived) | count               | 4        |
| building_area_sqft | float64      | numerical (derived) | square feet         | 4        |
| campus_area_sqft   | float64      | numerical (derived) | square feet         | 4        |
| avg_demand_MW      | float64      | numerical (derived) | MW                  | 4        |
| peak_demand_MW     | float64      | numerical (derived) | MW                  | 4        |
| std_demand_MW      | float64      | numerical (derived) | MW                  | 4        |

**im3_atlas_full.csv — column types**

| Column    | Stored dtype | Semantic type                               | Unit / meaning                      | Non-null |
| --------- | ------------ | ------------------------------------------- | ----------------------------------- | -------- |
| id        | int64        | categorical (identifier stored as integer)  | identifier                          | 1,479    |
| state     | str          | categorical                                 | text                                | 1,479    |
| state_abb | str          | categorical                                 | text                                | 1,479    |
| state_id  | int64        | categorical (FIPS code stored as integer)   | code                                | 1,479    |
| county    | str          | categorical                                 | text                                | 1,479    |
| county_id | int64        | categorical (county code stored as integer) | code                                | 1,479    |
| operator  | str          | categorical (text)                          | text                                | 960      |
| ref       | str          | categorical (text)                          | text                                | 374      |
| name      | str          | categorical (text)                          | text                                | 1,204    |
| sqft      | float64      | numerical                                   | square feet (facility polygon area) | 1,374    |
| lon       | float64      | numerical                                   | decimal degrees                     | 1,479    |
| lat       | float64      | numerical                                   | decimal degrees                     | 1,479    |
| type      | str          | categorical                                 | text                                | 1,479    |
| Region    | str          | categorical (derived)                       | text                                | 1,479    |

### master_timeseries.csv — key facts

| Measure                                | Value                                                     |
| -------------------------------------- | --------------------------------------------------------- |
| File shape (real + synthetic)          | 125,190 rows × 17 columns                                |
| Synthetic rows (data_type = synthetic) | 20,000                                                    |
| Real rows — final analysis table      | 105,190 rows × 16 columns                                |
| Total observations (Region-hours)      | 105,190                                                   |
| Total features (columns)               | 16 (Region + 15 attributes)                               |
| Unique regions                         | 4                                                         |
| Unique years (local)                   | 6: 2015, 2016, 2017, 2019, 2020, 2021                     |
| Unique months                          | 12                                                        |
| Unique local dates (all regions)       | 2,192                                                     |
| Unique hours of day                    | 24                                                        |
| Unique UTC timestamps (all regions)    | 52,609                                                    |
| Unique (Region, Timestamp) pairs       | 105,190                                                   |
| Earliest timestamp                     | 2015-01-01 05:00 UTC  (= 2015-01-01 00:00:00-05:00 local) |
| Latest timestamp                       | 2022-01-01 05:00 UTC  (= 2021-12-31 23:00:00-06:00 local) |

Unique UTC timestamps are fewer than rows because the two regions in each cohort share the same UTC hours (Virginia/Ohio share 2015–2017; Texas/Georgia overlap in 2019–2021 except for the 1-hour Central/Eastern offset).

## 2. Regional Data Distribution

| Region   | Source           | Records | Expected hours | Missing hours | Coverage % | Earliest (local) | Latest (local)   | Unique local days | Dup timestamps | Null cells |
| -------- | ---------------- | ------- | -------------- | ------------- | ---------- | ---------------- | ---------------- | ----------------- | -------------- | ---------- |
| Virginia | PJM DOM (Kaggle) | 26,304  | 26,304         | 0             | 100.00     | 2015-01-01 00:00 | 2017-12-31 23:00 | 1,096             | 0              | 0          |
| Ohio     | PJM AEP (Kaggle) | 26,304  | 26,304         | 0             | 100.00     | 2015-01-01 00:00 | 2017-12-31 23:00 | 1,096             | 0              | 0          |
| Texas    | EIA-930 ERCO     | 26,303  | 26,304         | 1             | 100.00     | 2019-01-01 00:00 | 2021-12-31 23:00 | 1,096             | 0              | 0          |
| Georgia  | EIA-930 SOCO     | 26,279  | 26,304         | 25            | 99.90      | 2019-01-01 00:00 | 2021-12-31 23:00 | 1,096             | 0              | 0          |

**Records per local calendar year**

| Region   | 2015  | 2016  | 2017  | 2019  | 2020  | 2021  |
| -------- | ----- | ----- | ----- | ----- | ----- | ----- |
| Virginia | 8,760 | 8,784 | 8,760 | 0     | 0     | 0     |
| Ohio     | 8,760 | 8,784 | 8,760 | 0     | 0     | 0     |
| Texas    | 0     | 0     | 0     | 8,760 | 8,784 | 8,759 |
| Georgia  | 0     | 0     | 0     | 8,735 | 8,784 | 8,760 |

**Observations per month**

| index | Virginia | Ohio  | Texas | Georgia |
| ----- | -------- | ----- | ----- | ------- |
| Jan   | 2,232    | 2,232 | 2,232 | 2,232   |
| Feb   | 2,040    | 2,040 | 2,040 | 2,040   |
| Mar   | 2,229    | 2,229 | 2,229 | 2,229   |
| Apr   | 2,160    | 2,160 | 2,160 | 2,160   |
| May   | 2,232    | 2,232 | 2,232 | 2,232   |
| Jun   | 2,160    | 2,160 | 2,160 | 2,160   |
| Jul   | 2,232    | 2,232 | 2,232 | 2,232   |
| Aug   | 2,232    | 2,232 | 2,232 | 2,232   |
| Sep   | 2,160    | 2,160 | 2,160 | 2,160   |
| Oct   | 2,232    | 2,232 | 2,232 | 2,232   |
| Nov   | 2,163    | 2,163 | 2,162 | 2,138   |
| Dec   | 2,232    | 2,232 | 2,232 | 2,232   |

**Observations per local hour of day.** Hour = local start of the interval. Daylight-saving time makes the counts uneven by design: the spring-forward hour (02:00) does not exist once a year and the fall-back hour (01:00) occurs twice.

| Hour | Virginia | Ohio  | Texas | Georgia |
| ---- | -------- | ----- | ----- | ------- |
| 0    | 1,096    | 1,096 | 1,095 | 1,095   |
| 1    | 1,099    | 1,099 | 1,099 | 1,097   |
| 2    | 1,093    | 1,093 | 1,093 | 1,092   |
| 3    | 1,096    | 1,096 | 1,096 | 1,095   |
| 4    | 1,096    | 1,096 | 1,096 | 1,095   |
| 5    | 1,096    | 1,096 | 1,096 | 1,095   |
| 6    | 1,096    | 1,096 | 1,096 | 1,095   |
| 7    | 1,096    | 1,096 | 1,096 | 1,095   |
| 8    | 1,096    | 1,096 | 1,096 | 1,095   |
| 9    | 1,096    | 1,096 | 1,096 | 1,095   |
| 10   | 1,096    | 1,096 | 1,096 | 1,095   |
| 11   | 1,096    | 1,096 | 1,096 | 1,095   |
| 12   | 1,096    | 1,096 | 1,096 | 1,095   |
| 13   | 1,096    | 1,096 | 1,096 | 1,095   |
| 14   | 1,096    | 1,096 | 1,096 | 1,095   |
| 15   | 1,096    | 1,096 | 1,096 | 1,095   |
| 16   | 1,096    | 1,096 | 1,096 | 1,095   |
| 17   | 1,096    | 1,096 | 1,096 | 1,095   |
| 18   | 1,096    | 1,096 | 1,096 | 1,095   |
| 19   | 1,096    | 1,096 | 1,096 | 1,095   |
| 20   | 1,096    | 1,096 | 1,096 | 1,095   |
| 21   | 1,096    | 1,096 | 1,096 | 1,095   |
| 22   | 1,096    | 1,096 | 1,096 | 1,095   |
| 23   | 1,096    | 1,096 | 1,096 | 1,095   |

**Missing hours** (expected = every hour of each region's local calendar years; nothing was filled):

| Region  | day        | Missing hours |
| ------- | ---------- | ------------- |
| Georgia | 2019-11-03 | 24            |
| Georgia | 2019-11-04 | 1             |
| Texas   | 2021-11-07 | 1             |

| Region  | Missing hour start (UTC) | Local                |
| ------- | ------------------------ | -------------------- |
| Texas   | 2021-11-07 05:00         | 2021-11-07 00:00 CDT |
| Georgia | 2019-11-03 05:00         | 2019-11-03 01:00 EDT |
| Georgia | 2019-11-03 06:00         | 2019-11-03 01:00 EST |
| Georgia | 2019-11-03 07:00         | 2019-11-03 02:00 EST |
| Georgia | 2019-11-03 08:00         | 2019-11-03 03:00 EST |
| Georgia | 2019-11-03 09:00         | 2019-11-03 04:00 EST |
| Georgia | 2019-11-03 10:00         | 2019-11-03 05:00 EST |
| Georgia | 2019-11-03 11:00         | 2019-11-03 06:00 EST |
| Georgia | 2019-11-03 12:00         | 2019-11-03 07:00 EST |
| Georgia | 2019-11-03 13:00         | 2019-11-03 08:00 EST |
| Georgia | 2019-11-03 14:00         | 2019-11-03 09:00 EST |
| Georgia | 2019-11-03 15:00         | 2019-11-03 10:00 EST |
| Georgia | 2019-11-03 16:00         | 2019-11-03 11:00 EST |
| Georgia | 2019-11-03 17:00         | 2019-11-03 12:00 EST |
| Georgia | 2019-11-03 18:00         | 2019-11-03 13:00 EST |
| Georgia | 2019-11-03 19:00         | 2019-11-03 14:00 EST |
| Georgia | 2019-11-03 20:00         | 2019-11-03 15:00 EST |
| Georgia | 2019-11-03 21:00         | 2019-11-03 16:00 EST |
| Georgia | 2019-11-03 22:00         | 2019-11-03 17:00 EST |
| Georgia | 2019-11-03 23:00         | 2019-11-03 18:00 EST |
| Georgia | 2019-11-04 00:00         | 2019-11-03 19:00 EST |
| Georgia | 2019-11-04 01:00         | 2019-11-03 20:00 EST |
| Georgia | 2019-11-04 02:00         | 2019-11-03 21:00 EST |
| Georgia | 2019-11-04 03:00         | 2019-11-03 22:00 EST |
| Georgia | 2019-11-04 04:00         | 2019-11-03 23:00 EST |
| Georgia | 2019-11-04 05:00         | 2019-11-04 00:00 EST |

Georgia's gap is one continuous block of 25 hours starting on the 2019-11-03 DST fall-back date: 24 hours came back from EIA-930 as null values and the 25th (2019-11-04 00:00 EST) was not returned at all. Texas's single missing hour (2021-11-07 00:00 CDT) is also on a DST fall-back date and was not returned by the API.

## 3. Column-wise Statistics

master_timeseries.csv statistics use **real rows only**; synthetic rows are profiled in Section 12.

Units: Demand MW; irradiance W/m²; temperature °C; wind m/s; Stress Index dimensionless 0–100 (derived); floor area square feet; coordinates decimal degrees. Identifier columns are listed for completeness — their averages have no meaning.

### master_timeseries.csv

| Column       | Unit                                                               | Count   | Mean       | Median     | Std        | Min     | P25    | P50        | P75     | Max       | IQR     | Missing | Zeros  |
| ------------ | ------------------------------------------------------------------ | ------- | ---------- | ---------- | ---------- | ------- | ------ | ---------- | ------- | --------- | ------- | ------- | ------ |
| Demand_MW    | MW (hourly average; EIA reports MWh per 1-h interval = average MW) | 105,190 | 24,098.666 | 19,354.500 | 14,071.907 | 6,598   | 12,756 | 19,354.500 | 34,221  | 74,533    | 21,465  | 0       | 0      |
| GHI          | W/m²                                                              | 105,190 | 181.989    | 9.000      | 266.531    | 0.000   | 0.000  | 9.000      | 313.000 | 1,049.500 | 313.000 | 0       | 49,749 |
| DNI          | W/m²                                                              | 105,190 | 191.168    | 0.000      | 306.994    | 0.000   | 0.000  | 0.000      | 315.000 | 1,053     | 315.000 | 0       | 55,627 |
| DHI          | W/m²                                                              | 105,190 | 70.165     | 8.000      | 102.410    | 0.000   | 0.000  | 8.000      | 108.000 | 561.500   | 108.000 | 0       | 49,749 |
| Temperature  | °C                                                                | 105,190 | 15.318     | 16.350     | 10.636     | -19.000 | 7.400  | 16.350     | 23.400  | 42.550    | 16.000  | 0       | 98     |
| Wind Speed   | m/s                                                                | 105,190 | 2.214      | 1.750      | 1.529      | 0.050   | 1.000  | 1.750      | 3.050   | 11.500    | 2.050   | 0       | 0      |
| Year         | calendar year (local)                                              | 105,190 | 2,018.000  | 2,017      | 2.160      | 2,015   | 2,016  | 2,017      | 2,020   | 2,021     | 4.000   | 0       | 0      |
| Month        | 1–12 (local)                                                      | 105,190 | 6.522      | 7.000      | 3.449      | 1.000   | 4.000  | 7.000      | 10.000  | 12.000    | 6.000   | 0       | 0      |
| Hour         | 0–23, local start of the hour                                     | 105,190 | 11.500     | 12.000     | 6.922      | 0.000   | 6.000  | 12.000     | 17.750  | 23.000    | 11.750  | 0       | 4,382  |
| DayOfWeek    | 0 = Monday … 6 = Sunday                                           | 105,190 | 3.001      | 3.000      | 1.998      | 0.000   | 1.000  | 3.000      | 5.000   | 6.000     | 4.000   | 0       | 14,975 |
| Is_Weekend   | 1 = Sat/Sun                                                        | 105,190 | 0.285      | 0.000      | 0.452      | 0.000   | 0.000  | 0.000      | 1.000   | 1.000     | 1.000   | 0       | 75,167 |
| Stress_Index | dimensionless percentile, 0–100 (derived)                         | 105,190 | 50.000     | 50.002     | 28.869     | 0.000   | 24.996 | 50.002     | 75.004  | 100.000   | 50.007  | 0       | 4      |

### im3_clean.csv

| Column    | Unit                                | Count | Mean              | Median      | Std               | Min        | P25         | P50         | P75           | Max            | IQR         | Missing | Zeros |
| --------- | ----------------------------------- | ----- | ----------------- | ----------- | ----------------- | ---------- | ----------- | ----------- | ------------- | -------------- | ----------- | ------- | ----- |
| id        | identifier                          | 577   | 1,083,914,286.180 | 886,028,872 | 1,590,449,964.820 | 14,997,588 | 507,673,418 | 886,028,872 | 1,253,282,099 | 13,465,438,761 | 745,608,681 | 0       | 0     |
| state_id  | code                                | 577   | 45.903            | 51.000      | 9.720             | 13.000     | 48.000      | 51.000      | 51.000        | 51.000         | 3.000       | 0       | 0     |
| county_id | code                                | 577   | 123.350           | 107.000     | 92.864            | 5.000      | 89.000      | 107.000     | 121.000       | 683.000        | 32.000      | 0       | 0     |
| sqft      | square feet (facility polygon area) | 562   | 469,316.972       | 148,341.500 | 1,901,355.046     | 445.000    | 100,232.500 | 148,341.500 | 246,657.250   | 22,688,090     | 146,424.750 | 15      | 0     |
| lon       | decimal degrees                     | 577   | -83.207           | -77.559     | 7.943             | -103.449   | -84.420     | -77.559     | -77.463       | -77.196        | 6.957       | 0       | 0     |
| lat       | decimal degrees                     | 577   | 37.106            | 38.949      | 3.442             | 29.293     | 33.765      | 38.949      | 39.022        | 41.506         | 5.257       | 0       | 0     |

### geo_summary.csv

| Column             | Unit                | Count | Mean           | Median         | Std            | Min        | P25            | P50            | P75            | Max        | IQR            | Missing | Zeros |
| ------------------ | ------------------- | ----- | -------------- | -------------- | -------------- | ---------- | -------------- | -------------- | -------------- | ---------- | -------------- | ------- | ----- |
| unique_DCs         | count of unique ids | 4     | 143.500        | 109.000        | 122.707        | 37.000     | 77.500         | 109.000        | 175.000        | 319.000    | 97.500         | 0       | 0     |
| n_building         | count               | 4     | 125.500        | 97.000         | 109.573        | 27.000     | 67.500         | 97.000         | 155.000        | 281.000    | 87.500         | 0       | 0     |
| n_campus           | count               | 4     | 14.250         | 9.500          | 11.236         | 7.000      | 8.500          | 9.500          | 15.250         | 31.000     | 6.750          | 0       | 0     |
| n_point            | count               | 4     | 3.750          | 3.500          | 2.500          | 1.000      | 2.500          | 3.500          | 4.750          | 7.000      | 2.250          | 0       | 0     |
| building_area_sqft | square feet         | 4     | 20,665,979.750 | 17,130,730.500 | 14,994,149.507 | 6,618,529  | 13,184,414.500 | 17,130,730.500 | 24,612,295.750 | 41,783,929 | 11,427,881.250 | 0       | 0     |
| campus_area_sqft   | square feet         | 4     | 39,450,766.750 | 39,141,961     | 24,527,904.994 | 15,577,999 | 19,887,326.500 | 39,141,961     | 58,705,401.250 | 63,941,146 | 38,818,074.750 | 0       | 0     |
| avg_demand_MW      | MW                  | 4     | 24,099.425     | 20,643.300     | 14,816.383     | 11,117.100 | 13,813.575     | 20,643.300     | 30,929.150     | 43,994     | 17,115.575     | 0       | 0     |
| peak_demand_MW     | MW                  | 4     | 41,609.500     | 35,127         | 24,373.245     | 21,651     | 23,967         | 35,127         | 52,769.500     | 74,533     | 28,802.500     | 0       | 0     |
| std_demand_MW      | MW                  | 4     | 5,000.150      | 3,986.850      | 3,334.040      | 2,489.100  | 2,500.200      | 3,986.850      | 6,486.800      | 9,537.800  | 3,986.600      | 0       | 0     |

### im3_atlas_full.csv

| Column    | Unit                                | Count | Mean              | Median      | Std               | Min       | P25             | P50         | P75               | Max            | IQR         | Missing | Zeros |
| --------- | ----------------------------------- | ----- | ----------------- | ----------- | ----------------- | --------- | --------------- | ----------- | ----------------- | -------------- | ----------- | ------- | ----- |
| id        | identifier                          | 1,479 | 1,415,364,053.362 | 830,881,743 | 2,479,063,717.697 | 2,744,301 | 446,243,591.500 | 830,881,743 | 1,252,196,809.500 | 13,527,396,782 | 805,953,218 | 0       | 0     |
| state_id  | code                                | 1,479 | 35.089            | 39.000      | 16.865            | 1.000     | 19.000          | 39.000      | 51.000            | 72.000         | 32.000      | 0       | 0     |
| county_id | code                                | 1,479 | 86.587            | 75.000      | 82.705            | 1.000     | 31.000          | 75.000      | 107.000           | 683.000        | 76.000      | 0       | 0     |
| sqft      | square feet (facility polygon area) | 1,374 | 604,174.146       | 135,001     | 2,452,628.009     | 204.000   | 60,050.250      | 135,001     | 242,613.250       | 26,612,163     | 182,563     | 105     | 0     |
| lon       | decimal degrees                     | 1,479 | -94.940           | -92.130     | 17.176            | -123.329  | -111.992        | -92.130     | -77.542           | -66.052        | 34.450      | 0       | 0     |
| lat       | decimal degrees                     | 1,479 | 38.924            | 39.016      | 4.472             | 18.417    | 36.199          | 39.016      | 41.197            | 48.757         | 4.998       | 0       | 0     |

### Key columns by region (master_timeseries.csv)

| Column       | Region   | Mean      | Median | Std      | Min    | P25       | P75    | Max      | IQR       | Zeros  |
| ------------ | -------- | --------- | ------ | -------- | ------ | --------- | ------ | -------- | --------- | ------ |
| Demand_MW    | Virginia | 11,117.12 | 10,572 | 2,489.07 | 6,598  | 9,408     | 12,590 | 21,651   | 3,182     | 0      |
| Demand_MW    | Ohio     | 14,712.45 | 14,375 | 2,503.94 | 9,581  | 12,876.75 | 16,283 | 24,739   | 3,406.25  | 0      |
| Demand_MW    | Texas    | 43,994.00 | 41,449 | 9,537.84 | 27,449 | 37,294.50 | 48,697 | 74,533   | 11,402.50 | 0      |
| Demand_MW    | Georgia  | 26,574.20 | 25,322 | 5,469.82 | 6,913  | 22,805.50 | 29,426 | 45,515   | 6,620.50  | 0      |
| Temperature  | Virginia | 13.43     | 14.15  | 10.85    | -18.95 | 4.75      | 22.05  | 38.00    | 17.30     | 40     |
| Temperature  | Ohio     | 11.91     | 13.15  | 11.13    | -19.00 | 2.95      | 20.90  | 35.30    | 17.95     | 34     |
| Temperature  | Texas    | 19.08     | 20.00  | 9.76     | -15.35 | 11.70     | 26.30  | 42.55    | 14.60     | 12     |
| Temperature  | Georgia  | 16.85     | 17.70  | 9.15     | -6.80  | 9.90      | 23.30  | 38.95    | 13.40     | 12     |
| GHI          | Virginia | 176.68    | 8.50   | 259.47   | 0.00   | 0.00      | 302.00 | 1,033    | 302.00    | 12,700 |
| GHI          | Ohio     | 167.82    | 8.00   | 248.40   | 0.00   | 0.00      | 279.50 | 1,024.50 | 279.50    | 12,708 |
| GHI          | Texas    | 196.70    | 10.00  | 283.74   | 0.00   | 0.00      | 351.50 | 1,047.50 | 351.50    | 12,098 |
| GHI          | Georgia  | 186.76    | 10.00  | 272.32   | 0.00   | 0.00      | 328.00 | 1,049.50 | 328.00    | 12,243 |
| Stress_Index | Virginia | 50.00     | 49.99  | 28.87    | 0.00   | 24.99     | 75.00  | 100.00   | 50.02     | 1      |
| Stress_Index | Ohio     | 50.00     | 50.01  | 28.87    | 0.00   | 25.00     | 75.01  | 100.00   | 50.01     | 1      |
| Stress_Index | Texas    | 50.00     | 50.00  | 28.87    | 0.00   | 25.00     | 75.00  | 100.00   | 50.00     | 1      |
| Stress_Index | Georgia  | 50.00     | 50.01  | 28.87    | 0.00   | 25.00     | 75.00  | 100.00   | 50.00     | 1      |

Zeros in GHI/DNI/DHI are night-time hours (no sunlight), not missing data.

## 4. Data Quality Report

Nothing was removed or filled for this report.

### master_timeseries.csv

| Check                                                  | Count (% of rows)              | Note                             |
| ------------------------------------------------------ | ------------------------------ | -------------------------------- |
| Missing values (any column)                            | 0 (0.000%)                     | None found                       |
| Duplicate full rows                                    | 0 (0.000%)                     | —                               |
| Duplicate (Region, Timestamp)                          | 0 (0.000%)                     | —                               |
| Unparseable Timestamp (UTC)                            | 0 (0.000%)                     | —                               |
| Unparseable Timestamp_Local                            | 0 (0.000%)                     | —                               |
| Timestamp_Local ≠ Timestamp (same instant check)      | 0 (0.000%)                     | —                               |
| Year/Month/Hour/DayOfWeek inconsistent with local time | 0 (0.000%)                     | —                               |
| Season inconsistent with Month                         | 0 (0.000%)                     | —                               |
| Is_Weekend inconsistent with DayOfWeek                 | 0 (0.000%)                     | —                               |
| Rows outside each region's configured local years      | 0 (0.000%)                     | —                               |
| Missing hours (vs. full local-year coverage)           | 26 (0.025%)                    | Source gaps; dropped, not filled |
| Negative demand                                        | 0 (0.000%)                     | —                               |
| Zero demand                                            | 0 (0.000%)                     | —                               |
| GHI / DNI / DHI < 0                                    | 0 (0.000%)                     | —                               |
| GHI or DNI > 1,361 W/m² (solar constant)              | 0 (0.000%)                     | Physically implausible if > 0    |
| DHI > GHI + 1 W/m²                                    | 0 (0.000%)                     | Diffuse cannot exceed global     |
| Temperature outside −60 … +60 °C                    | 0 (0.000%)                     | —                               |
| Wind speed < 0 or > 70 m/s                             | 0 (0.000%)                     | —                               |
| Stress_Index outside 0–100                            | 0 (0.000%)                     | —                               |
| Region names                                           | Georgia, Ohio, Texas, Virginia | Consistent across all 4 files    |

### Demand outliers

High/low outliers use the 1.5 × IQR rule per region; robust z uses the median absolute deviation. An **isolated 1-hour spike** (demand > 10 % above or below *both* neighbouring hours) is the usual signature of a data error; multi-hour runs tied to extreme temperatures are genuine events.

| Region | IQR upper fence (MW) | IQR lower fence (MW) | High outliers (IQR) | Low outliers (IQR) | % of region | |robust z| > 3.5 | Isolated 1-h spikes (>10%) | Days with IQR outliers | Mean temp at high outliers (°C) |
|---|---|---|---|---|---|---|---|---|---|
| Virginia | 17,363 | 4,635 | 434 | 0 | 1.65 | 158 | 0 | 73 | 17.65 |
| Ohio | 21,392.38 | 7,767.38 | 156 | 0 | 0.59 | 16 | 1 | 28 | 3.59 |
| Texas | 65,800.75 | 20,190.75 | 925 | 0 | 3.52 | 565 | 0 | 163 | 35.65 |
| Georgia | 39,356.75 | 12,874.75 | 839 | 1 | 3.20 | 340 | 3 | 162 | 33.51 |

**Isolated 1-hour spikes found (suspected source errors, kept unchanged):**

| Region  | Local time       | Demand (MW) | Previous hour (MW) | Next hour (MW) |
| ------- | ---------------- | ----------- | ------------------ | -------------- |
| Ohio    | 2015-12-27 13:00 | 15,488      | 12,364             | 12,413         |
| Georgia | 2019-10-23 11:00 | 25,831      | 18,944             | 19,598         |
| Georgia | 2019-10-25 22:00 | 35,329      | 22,284             | 6,913          |
| Georgia | 2019-10-25 23:00 | 6,913       | 35,329             | 20,011         |

Evidence they are errors, not events: each value jumps away from both neighbouring hours and returns immediately, while temperature changes smoothly (no matching one-hour reversal; e.g. Georgia stays near 18 °C through both 2019-10-25 spikes). On 2019-10-25 Georgia reads 35,329 MW at 22:00 and 6,913 MW at 23:00; the two hours sum to 42,242 MW, about twice the 22,855 MW average of the preceding hours — the signature of energy assigned to the wrong hour. The 23:00 value is Georgia's recorded minimum; the lowest plausible Georgia value is 16,328 MW (2020-04-26 07:00). These hours also receive Stress Index values (the 23:00 hour scores 0). They were not removed because no correction source is available; a future pipeline version could flag them.

**Where the high outliers fall:**

| Region   | High-outlier hours | Distinct days | Top day    | Hours that day | Temp range on outlier hours (°C) |
| -------- | ------------------ | ------------- | ---------- | -------------- | --------------------------------- |
| Virginia | 434                | 73            | 2015-02-16 | 19             | -18.9 to 38.0                     |
| Ohio     | 156                | 28            | 2015-02-19 | 19             | -19.0 to 35.3                     |
| Texas    | 925                | 163           | 2019-08-12 | 10             | -10.1 to 42.5                     |
| Georgia  | 839                | 161           | 2019-08-13 | 11             | -4.4 to 39.0                      |

**Genuine-event evidence for the IQR high outliers.** Real demand peaks last several hours and coincide with very cold or very hot weather:

| Region   | High-outlier hours | In runs of ≥ 3 consecutive hours | % in runs | At ≤ 0 °C or ≥ 30 °C | % at extreme temp | Also an isolated spike |
| -------- | ------------------ | --------------------------------- | --------- | ------------------------ | ----------------- | ---------------------- |
| Virginia | 434                | 411                               | 94.70     | 418                      | 96.31             | 0                      |
| Ohio     | 156                | 142                               | 91.03     | 155                      | 99.36             | 0                      |
| Texas    | 925                | 899                               | 97.19     | 919                      | 99.35             | 0                      |
| Georgia  | 839                | 803                               | 95.71     | 804                      | 95.83             | 0                      |

Nearly all IQR outliers sit in multi-hour runs at temperature extremes, so they are treated as **genuine weather-driven peaks**, not errors. The IQR rule is a screening tool here; flagged values are not removed.

**Weather IQR outlier counts** (informational; all values are within physical limits, see checks above):

| Variable    | Virginia | Ohio  | Texas | Georgia |
| ----------- | -------- | ----- | ----- | ------- |
| DHI         | 1,876    | 2,091 | 1,369 | 1,864   |
| DNI         | 3,266    | 4,068 | 0     | 1,994   |
| GHI         | 1,394    | 1,571 | 874   | 1,073   |
| Temperature | 0        | 0     | 27    | 0       |
| Wind Speed  | 1,012    | 476   | 219   | 1,319   |

### IM3 datasets

| File           | Check                                                               | Count (%)       |
| -------------- | ------------------------------------------------------------------- | --------------- |
| im3_atlas_full | Missing lat or lon                                                  | 0 (0.000%)      |
| im3_atlas_full | Duplicate full rows                                                 | 0 (0.000%)      |
| im3_atlas_full | Rows sharing an id with another row                                 | 10 (0.676%)     |
| im3_atlas_full | Building rows missing sqft                                          | 0 (0.000%)      |
| im3_atlas_full | Campus rows missing sqft                                            | 0 (0.000%)      |
| im3_atlas_full | Point rows missing sqft (by design)                                 | 105 (100.000%)  |
| im3_atlas_full | sqft ≤ 0                                                           | 0 (0.000%)      |
| im3_atlas_full | Missing operator                                                    | 519 (35.091%)   |
| im3_atlas_full | Missing name                                                        | 275 (18.594%)   |
| im3_atlas_full | Missing ref (OSM tag, optional)                                     | 1,105 (74.713%) |
| im3_clean      | Missing lat or lon                                                  | 0 (0.000%)      |
| im3_clean      | Duplicate full rows                                                 | 0 (0.000%)      |
| im3_clean      | Rows sharing an id with another row                                 | 6 (1.040%)      |
| im3_clean      | Building rows missing sqft                                          | 0 (0.000%)      |
| im3_clean      | Campus rows missing sqft                                            | 0 (0.000%)      |
| im3_clean      | Point rows missing sqft (by design)                                 | 15 (100.000%)   |
| im3_clean      | sqft ≤ 0                                                           | 0 (0.000%)      |
| im3_clean      | Missing operator                                                    | 165 (28.596%)   |
| im3_clean      | Missing name                                                        | 89 (15.425%)    |
| im3_clean      | Missing ref (OSM tag, optional)                                     | 361 (62.565%)   |
| im3_atlas_full | Coordinates outside U.S. bounding box (lat 18–72, lon −180…−65) | 0 (0.000%)      |
| im3_clean      | Coordinates outside own state's bounding box (approx.)              | 0 (0.000%)      |

**Rows that share an id** — these are facilities that straddle a county line (same facility, one row per county), which is why data centers are always counted with `nunique(id)`:

| id            | type     | state_abb | county          | name                         | sqft       |
| ------------- | -------- | --------- | --------------- | ---------------------------- | ---------- |
| 830,885,779   | campus   | IA        | Madison County  | Project Osmium               | 3,691,114  |
| 830,885,779   | campus   | IA        | Warren County   | Project Osmium               | 3,691,114  |
| 844,391,357   | campus   | OH        | Franklin County | Google Data Center           | 22,688,090 |
| 844,391,357   | campus   | OH        | Licking County  | Google Data Center           | 22,688,090 |
| 975,064,000   | building | GA        | Douglas County  | Digital Realty Atlanta ATL11 | 313,479    |
| 975,064,000   | building | GA        | Cobb County     | Digital Realty Atlanta ATL11 | 313,479    |
| 1,126,774,147 | campus   | MO        | Clay County     | Meta Kansas City Data Center | 13,516,765 |
| 1,126,774,147 | campus   | MO        | Platte County   | Meta Kansas City Data Center | 13,516,765 |
| 1,386,016,633 | building | OH        | Franklin County | Google NBY-6                 | 287,583    |
| 1,386,016,633 | building | OH        | Licking County  | Google NBY-6                 | 287,583    |

### geo_summary.csv — recomputed from im3_clean.csv and master_timeseries.csv

| Region   | Columns checked | Mismatches |
| -------- | --------------- | ---------- |
| Virginia | 9               | 0          |
| Ohio     | 9               | 0          |
| Texas    | 9               | 0          |
| Georgia  | 9               | 0          |

State bounding boxes are approximate rectangles, so a facility near a border could fall inside the box of a neighbouring state; this check only catches gross coordinate errors.

## 5. Energy Demand Analysis

> **Comparability warning.** Each region is a different balancing area or utility zone (DOM, AEP, ERCOT, Southern Company) with a different customer base, and the two cohorts cover different years (2015–2017 vs 2019–2021). Compare *patterns* (shape, timing, seasonality) across regions, not absolute MW.

| Region   | Period     | Obs    | Mean      | Median | Std      | Min    | P95       | P99       | Max    | CV %  |
| -------- | ---------- | ------ | --------- | ------ | -------- | ------ | --------- | --------- | ------ | ----- |
| Virginia | 2015–2017 | 26,304 | 11,117.12 | 10,572 | 2,489.07 | 6,598  | 16,001.85 | 17,851.94 | 21,651 | 22.39 |
| Ohio     | 2015–2017 | 26,304 | 14,712.45 | 14,375 | 2,503.94 | 9,581  | 19,382    | 20,974.91 | 24,739 | 17.02 |
| Texas    | 2019–2021 | 26,303 | 43,994.00 | 41,449 | 9,537.84 | 27,449 | 64,037.80 | 70,296.56 | 74,533 | 21.68 |
| Georgia  | 2019–2021 | 26,279 | 26,574.20 | 25,322 | 5,469.82 | 6,913  | 37,851.20 | 41,674.20 | 45,515 | 20.58 |

CV = coefficient of variation (std / mean), a derived, unit-free measure of variability.

| Region   | Peak (MW) | Peak time (local) | Temp at peak (°C) | Minimum (MW) | Minimum time (local) | Temp at min (°C) |
| -------- | --------- | ----------------- | ------------------ | ------------ | -------------------- | ----------------- |
| Virginia | 21,651    | 2015-02-20 07:00  | -16.90             | 6,598        | 2016-10-09 04:00     | 12.00             |
| Ohio     | 24,739    | 2015-02-20 07:00  | -18.05             | 9,581        | 2016-10-02 04:00     | 11.70             |
| Texas    | 74,533    | 2019-08-12 16:00  | 40.85              | 27,449       | 2020-05-10 05:00     | 10.80             |
| Georgia  | 45,515    | 2019-08-13 16:00  | 38.05              | 6,913        | 2019-10-25 23:00     | 18.20             |

**Caution — Georgia minimum.** Georgia's minimum (6,913 MW) is a suspected source error (Section 4). The lowest plausible Georgia hour is 16,328 MW (2020-04-26 07:00). The same value appears as Georgia's Min MW in the notebook statistics and the dashboard's Region Summary table.

**Average demand by year (MW)**

| Year  | Virginia  | Ohio      | Texas     | Georgia   |
| ----- | --------- | --------- | --------- | --------- |
| 2,015 | 11,150.16 | 14,868.59 | —        | —        |
| 2,016 | 11,142.49 | 14,784.20 | —        | —        |
| 2,017 | 11,058.63 | 14,484.36 | —        | —        |
| 2,019 | —        | —        | 43,797.57 | 27,236.57 |
| 2,020 | —        | —        | 43,376.73 | 25,893.87 |
| 2,021 | —        | —        | 44,809.50 | 26,595.92 |

**Average demand by month (MW)**

| index | Virginia  | Ohio      | Texas     | Georgia   |
| ----- | --------- | --------- | --------- | --------- |
| Jan   | 12,414.06 | 16,552.75 | 40,111.59 | 26,795.79 |
| Feb   | 12,254.85 | 16,317.84 | 40,694.87 | 25,610.80 |
| Mar   | 10,399.43 | 14,475.79 | 37,335.32 | 23,208.52 |
| Apr   | 9,276.71  | 13,074.89 | 37,875.72 | 22,183.91 |
| May   | 9,918.62  | 13,299.37 | 42,570.90 | 25,508.89 |
| Jun   | 11,896.92 | 14,962.92 | 49,936.99 | 29,105.94 |
| Jul   | 13,103.38 | 15,718.17 | 53,304.44 | 31,599.94 |
| Aug   | 12,530.66 | 15,688.23 | 55,547.88 | 31,745.56 |
| Sep   | 10,986.49 | 14,349.03 | 49,358.58 | 28,790.41 |
| Oct   | 9,394.57  | 13,050.91 | 42,347.31 | 24,416.19 |
| Nov   | 9,974.52  | 13,793.50 | 38,366.53 | 24,019.67 |
| Dec   | 11,278.38 | 15,318.89 | 40,176.08 | 25,721.36 |

**Average demand by weekday (MW)**

| index | Virginia  | Ohio      | Texas     | Georgia   |
| ----- | --------- | --------- | --------- | --------- |
| Mon   | 11,228.36 | 15,014.06 | 44,384.50 | 26,907.42 |
| Tue   | 11,345.95 | 15,156.93 | 44,669.06 | 27,251.48 |
| Wed   | 11,221.99 | 15,120.21 | 44,694.70 | 27,254.15 |
| Thu   | 11,268.12 | 15,220.48 | 44,787.28 | 27,199.31 |
| Fri   | 11,333.59 | 15,031.65 | 44,361.83 | 26,735.36 |
| Sat   | 10,811.74 | 13,895.99 | 42,651.29 | 25,515.95 |
| Sun   | 10,612.92 | 13,555.17 | 42,392.70 | 25,132.84 |

Weekday vs weekend difference (derived): Virginia +5.30%, Ohio +10.08%, Texas +4.84%, Georgia +6.89%.

**Average demand by local hour (MW)**

| Hour | Virginia  | Ohio      | Texas     | Georgia   |
| ---- | --------- | --------- | --------- | --------- |
| 0    | 9,619.49  | 13,133.37 | 39,227.90 | 23,750.26 |
| 1    | 9,260.11  | 12,715.98 | 37,665.86 | 23,048.97 |
| 2    | 9,074.39  | 12,496.55 | 36,705.84 | 22,604.93 |
| 3    | 9,030.75  | 12,425.43 | 36,203.39 | 22,310.09 |
| 4    | 9,202.32  | 12,579.09 | 36,372.10 | 22,319.11 |
| 5    | 9,714.34  | 13,113.83 | 37,519.85 | 22,821.49 |
| 6    | 10,500.95 | 14,016.70 | 39,460.00 | 23,925.32 |
| 7    | 11,031.06 | 14,636.88 | 40,613.71 | 24,857.12 |
| 8    | 11,264.87 | 14,953.87 | 41,726.44 | 25,535.21 |
| 9    | 11,437.77 | 15,212.27 | 43,195.23 | 26,236.05 |
| 10   | 11,606.05 | 15,440.61 | 44,736.04 | 27,008.84 |
| 11   | 11,733.74 | 15,565.63 | 46,161.92 | 27,777.04 |
| 12   | 11,839.06 | 15,676.44 | 47,400.50 | 28,466.11 |
| 13   | 11,932.40 | 15,765.10 | 48,535.11 | 29,079.19 |
| 14   | 12,000.62 | 15,754.21 | 49,359.56 | 29,501.67 |
| 15   | 12,102.18 | 15,735.50 | 49,918.81 | 29,749.13 |
| 16   | 12,299.50 | 15,830.91 | 50,318.15 | 29,904.07 |
| 17   | 12,599.92 | 16,024.57 | 50,527.23 | 30,001.51 |
| 18   | 12,637.69 | 16,087.03 | 50,288.91 | 30,073.11 |
| 19   | 12,512.70 | 16,005.17 | 49,289.52 | 29,702.61 |
| 20   | 12,324.52 | 15,895.24 | 48,264.94 | 29,144.34 |
| 21   | 11,826.09 | 15,521.27 | 46,710.21 | 28,247.96 |
| 22   | 11,032.75 | 14,702.64 | 44,182.56 | 26,696.26 |
| 23   | 10,227.07 | 13,809.91 | 41,465.37 | 25,016.00 |

## 6. Weather and Solar Analysis

Units confirmed from the NSRDB file header: temperature `c`, GHI `w/m2`, wind `m/s`. EIA-930 value units: `megawatthours`. All weather comes from one NSRDB point per region.

| Region   | Avg T (°C) | Min T  | Max T | Avg wind (m/s) | Max wind | Avg GHI (W/m²) | Max GHI  | Avg DNI | Max DNI  | Avg DHI | Max DHI |
| -------- | ----------- | ------ | ----- | -------------- | -------- | --------------- | -------- | ------- | -------- | ------- | ------- |
| Virginia | 13.43       | -18.95 | 38.00 | 1.92           | 8.80     | 176.68          | 1,033    | 183.61  | 1,034    | 71.54   | 561.50  |
| Ohio     | 11.91       | -19.00 | 35.30 | 2.86           | 11.50    | 167.82          | 1,024.50 | 162.43  | 1,053    | 75.98   | 520.00  |
| Texas    | 19.08       | -15.35 | 42.55 | 2.98           | 10.10    | 196.70          | 1,047.50 | 218.62  | 1,038    | 65.09   | 506.00  |
| Georgia  | 16.85       | -6.80  | 38.95 | 1.09           | 4.30     | 186.76          | 1,049.50 | 200.02  | 1,037.50 | 68.05   | 523.50  |

### Pearson correlation with demand

| Region   | Temperature | GHI (all hours) | DNI (all hours) | DHI (all hours) | Wind speed | GHI (daytime) | Daytime n |
| -------- | ----------- | --------------- | --------------- | --------------- | ---------- | ------------- | --------- |
| Virginia | 0.131       | 0.317           | 0.223           | 0.304           | 0.084      | 0.213         | 13,604    |
| Ohio     | -0.058      | 0.292           | 0.187           | 0.319           | 0.105      | 0.156         | 13,596    |
| Texas    | 0.631       | 0.463           | 0.360           | 0.406           | 0.009      | 0.360         | 14,205    |
| Georgia  | 0.476       | 0.404           | 0.277           | 0.418           | -0.022     | 0.284         | 14,036    |

**Supplementary (derived): temperature–demand correlation split at 18 °C** (a common heating/cooling balance point):

| Region   | r when T < 18 °C | n (cold) | r when T ≥ 18 °C | n (warm) |
| -------- | ----------------- | -------- | ------------------ | -------- |
| Virginia | -0.735            | 16,140   | 0.862              | 10,164   |
| Ohio     | -0.717            | 17,050   | 0.793              | 9,254    |
| Texas    | -0.506            | 11,326   | 0.888              | 14,977   |
| Georgia  | -0.581            | 13,441   | 0.878              | 12,838   |

**Limitations of Pearson r.** It measures *linear* association only. Temperature affects demand in a U shape (heating when cold, cooling when hot), so a single r near zero — e.g. Ohio — can hide two strong opposite relationships, as the split table shows. Irradiance correlations are confounded by time of day and season (sunny hours are also working hours and warm hours), and hourly observations are autocorrelated, so conventional significance tests would overstate certainty. **Correlation is not causation:** none of these values shows that weather or sunlight *causes* a demand change.

## 7. Data Center Atlas Statistics

**Layer types (IM3 README):** `building` = a single data-center structure mapped as a polygon (has floor area); `campus` = a site polygon enclosing several buildings (has floor area, overlaps the buildings inside it); `point` = a location only, with no polygon and therefore no area. Building and campus areas must never be added together.

| index               | im3_atlas_full (all states) | im3_clean (4 focus states) |
| ------------------- | --------------------------- | -------------------------- |
| Records (rows)      | 1,479                       | 577                        |
| Unique ids          | 1,474                       | 574                        |
| Building rows       | 1,239                       | 504                        |
| Campus rows         | 135                         | 58                         |
| Point rows          | 105                         | 15                         |
| Unique building ids | 1,237                       | 502                        |
| Unique campus ids   | 132                         | 57                         |
| Unique point ids    | 105                         | 15                         |
| Unique states       | 47                          | 4                          |
| Rows with sqft      | 1,374                       | 562                        |
| Rows without sqft   | 105                         | 15                         |

**Records per region**

| Region   | Rows | Unique_ids |
| -------- | ---- | ---------- |
| Virginia | 319  | 319        |
| Ohio     | 93   | 91         |
| Texas    | 127  | 127        |
| Georgia  | 38   | 37         |
| Other    | 902  | 900        |

**Records per state** (47 states)

| state_abb | state                | Rows | Unique_ids | Buildings | Campuses | Points |
| --------- | -------------------- | ---- | ---------- | --------- | -------- | ------ |
| VA        | Virginia             | 319  | 319        | 281       | 31       | 7      |
| TX        | Texas                | 127  | 127        | 113       | 10       | 4      |
| CA        | California           | 112  | 112        | 97        | 3        | 12     |
| OR        | Oregon               | 109  | 109        | 100       | 6        | 3      |
| OH        | Ohio                 | 93   | 91         | 82        | 10       | 1      |
| WA        | Washington           | 82   | 82         | 71        | 10       | 1      |
| AZ        | Arizona              | 65   | 65         | 42        | 8        | 15     |
| IA        | Iowa                 | 64   | 63         | 58        | 6        | 0      |
| NJ        | New Jersey           | 53   | 53         | 46        | 4        | 3      |
| IL        | Illinois             | 50   | 50         | 42        | 2        | 6      |
| GA        | Georgia              | 38   | 37         | 28        | 7        | 3      |
| NV        | Nevada               | 38   | 38         | 33        | 3        | 2      |
| NE        | Nebraska             | 26   | 26         | 21        | 5        | 0      |
| NC        | North Carolina       | 23   | 23         | 14        | 5        | 4      |
| TN        | Tennessee            | 22   | 22         | 15        | 5        | 2      |
| NY        | New York             | 21   | 21         | 16        | 0        | 5      |
| CO        | Colorado             | 20   | 20         | 17        | 0        | 3      |
| WY        | Wyoming              | 19   | 19         | 15        | 4        | 0      |
| FL        | Florida              | 16   | 16         | 11        | 0        | 5      |
| MO        | Missouri             | 16   | 15         | 12        | 2        | 2      |
| NM        | New Mexico           | 16   | 16         | 10        | 1        | 5      |
| UT        | Utah                 | 15   | 15         | 13        | 1        | 1      |
| MD        | Maryland             | 13   | 13         | 8         | 0        | 5      |
| WI        | Wisconsin            | 13   | 13         | 9         | 1        | 3      |
| SC        | South Carolina       | 12   | 12         | 10        | 2        | 0      |
| AL        | Alabama              | 11   | 11         | 8         | 3        | 0      |
| MN        | Minnesota            | 11   | 11         | 10        | 1        | 0      |
| MI        | Michigan             | 10   | 10         | 8         | 0        | 2      |
| PA        | Pennsylvania         | 9    | 9          | 8         | 0        | 1      |
| KS        | Kansas               | 7    | 7          | 7         | 0        | 0      |
| OK        | Oklahoma             | 6    | 6          | 4         | 0        | 2      |
| KY        | Kentucky             | 5    | 5          | 3         | 2        | 0      |
| CT        | Connecticut          | 5    | 5          | 4         | 0        | 1      |
| ID        | Idaho                | 5    | 5          | 4         | 1        | 0      |
| IN        | Indiana              | 5    | 5          | 3         | 0        | 2      |
| MA        | Massachusetts        | 3    | 3          | 3         | 0        | 0      |
| NH        | New Hampshire        | 3    | 3          | 3         | 0        | 0      |
| ND        | North Dakota         | 2    | 2          | 1         | 1        | 0      |
| PR        | Puerto Rico          | 2    | 2          | 1         | 0        | 1      |
| SD        | South Dakota         | 2    | 2          | 2         | 0        | 0      |
| ME        | Maine                | 2    | 2          | 1         | 0        | 1      |
| MS        | Mississippi          | 2    | 2          | 1         | 1        | 0      |
| AR        | Arkansas             | 2    | 2          | 2         | 0        | 0      |
| MT        | Montana              | 2    | 2          | 2         | 0        | 0      |
| LA        | Louisiana            | 1    | 1          | 0         | 0        | 1      |
| DC        | District of Columbia | 1    | 1          | 0         | 0        | 1      |
| WV        | West Virginia        | 1    | 1          | 0         | 0        | 1      |

**Floor area by type** (unique ids; square feet; derived totals are per type and never summed across types)

| Scope      | Type     | Unique ids with area | Total (sq ft) | Mean      | Median    | Min     | Max        |
| ---------- | -------- | -------------------- | ------------- | --------- | --------- | ------- | ---------- |
| All states | building | 1,237                | 191,079,242   | 154,470   | 123,665   | 204     | 2,238,928  |
| All states | campus   | 132                  | 598,559,003   | 4,534,538 | 1,588,891 | 9,139   | 26,612,163 |
| Virginia   | building | 281                  | 41,783,929    | 148,697   | 132,942   | 10,175  | 604,696    |
| Virginia   | campus   | 31                   | 56,960,153    | 1,837,424 | 1,291,753 | 222,846 | 11,273,954 |
| Ohio       | building | 81                   | 15,373,043    | 189,791   | 163,319   | 13,074  | 663,286    |
| Ohio       | campus   | 9                    | 63,941,146    | 7,104,572 | 1,543,625 | 563,283 | 22,688,090 |
| Texas      | building | 113                  | 18,888,418    | 167,154   | 113,970   | 445     | 2,238,928  |
| Texas      | campus   | 10                   | 21,323,769    | 2,132,377 | 555,034   | 249,430 | 11,717,820 |
| Georgia    | building | 27                   | 6,618,529     | 245,131   | 184,012   | 18,558  | 763,506    |
| Georgia    | campus   | 7                    | 15,577,999    | 2,225,428 | 1,294,301 | 174,649 | 9,032,398  |

Largest single record: Google Montgomery Data Center (campus, TN), 26,612,163 sq ft. Point records: 105, all without area — no area was assigned to any of them.

## 8. Stress Index Analysis

**Implementation in the notebook (verbatim):**

```python
def stress_index(series):
    """Percentile rank within the series, 0–100: (average rank - 1) / (n - 1) * 100."""
    ranks = series.rank(method="average")
    return (ranks - 1) / (len(ranks) - 1) * 100

master["Stress_Index"] = (
    master.groupby("Region")["Demand_MW"]
    .transform(stress_index)
)

print("Stress_Index stats per region:")
print(master.groupby("Region")["Stress_Index"].describe().round(2).to_string())
print()
print("Master schema:")
print(master.dtypes.to_string())
```

- **Formula:** `Stress_Index = (rank − 1) / (n − 1) × 100`, where `rank` is the average rank of the hour's `Demand_MW` among the region's `n` hours.
- **Ranking method:** `average` — tied demand values share the mean of their ranks.
- **Per region:** yes — `groupby('Region').transform(...)`, so each region is ranked only against itself.
- **Verification:** recomputed from `Demand_MW`; maximum absolute difference = 1.42e-14. Stress order equals demand order within every region: yes.
- **High-stress hour (dashboard KPI):** Stress_Index ≥ 95. **Top 1 % event:** Stress_Index ≥ 99.

| Region   | n      | ≥ 90 | ≥ 95 | ≥ 99 (top 1%) | Demand at ≥99 threshold (MW) | Top-1% most common hour | Top-1% most common month | Top-1% in Summer % | Top-1% in Winter % | Mean Stress |
| -------- | ------ | ----- | ----- | -------------- | ----------------------------- | ----------------------- | ------------------------ | ------------------ | ------------------ | ----------- |
| Virginia | 26,304 | 2,631 | 1,316 | 264            | 17,852                        | 16                      | Jul                      | 64.39              | 34.85              | 50.00       |
| Ohio     | 26,304 | 2,630 | 1,315 | 264            | 20,975                        | 16                      | Feb                      | 39.77              | 53.03              | 50.00       |
| Texas    | 26,303 | 2,631 | 1,316 | 264            | 70,297                        | 16                      | Aug                      | 93.56              | 0.00               | 50.00       |
| Georgia  | 26,279 | 2,629 | 1,314 | 263            | 41,682                        | 16                      | Aug                      | 68.82              | 0.00               | 50.00       |

**Distribution of Stress_Index values (count of hours per 10-point band).** Near-uniform by construction — a percentile rank spreads observations evenly; small deviations come from ties.

| bin     | Virginia | Ohio  | Texas | Georgia |
| ------- | -------- | ----- | ----- | ------- |
| 0–10   | 2,632    | 2,630 | 2,631 | 2,628   |
| 10–20  | 2,631    | 2,630 | 2,630 | 2,629   |
| 20–30  | 2,630    | 2,631 | 2,631 | 2,628   |
| 30–40  | 2,630    | 2,628 | 2,629 | 2,626   |
| 40–50  | 2,631    | 2,632 | 2,631 | 2,627   |
| 50–60  | 2,629    | 2,632 | 2,629 | 2,629   |
| 60–70  | 2,630    | 2,629 | 2,631 | 2,629   |
| 70–80  | 2,630    | 2,631 | 2,630 | 2,626   |
| 80–90  | 2,630    | 2,631 | 2,630 | 2,628   |
| 90–100 | 2,631    | 2,630 | 2,631 | 2,629   |

**Top-1 % events by local hour**

| Hour | Virginia | Ohio | Texas | Georgia |
| ---- | -------- | ---- | ----- | ------- |
| 0    | 2        | 1    | 0     | 0       |
| 1    | 2        | 1    | 0     | 0       |
| 2    | 1        | 1    | 0     | 0       |
| 3    | 1        | 2    | 0     | 0       |
| 4    | 1        | 3    | 0     | 0       |
| 5    | 5        | 3    | 0     | 0       |
| 6    | 13       | 12   | 0     | 0       |
| 7    | 18       | 19   | 0     | 0       |
| 8    | 10       | 17   | 0     | 0       |
| 9    | 7        | 11   | 0     | 0       |
| 10   | 4        | 7    | 0     | 0       |
| 11   | 3        | 6    | 0     | 0       |
| 12   | 7        | 7    | 0     | 1       |
| 13   | 20       | 12   | 10    | 7       |
| 14   | 26       | 22   | 37    | 37      |
| 15   | 28       | 27   | 54    | 66      |
| 16   | 33       | 30   | 63    | 70      |
| 17   | 29       | 23   | 62    | 55      |
| 18   | 25       | 20   | 33    | 21      |
| 19   | 15       | 15   | 5     | 4       |
| 20   | 7        | 12   | 0     | 2       |
| 21   | 3        | 8    | 0     | 0       |
| 22   | 2        | 3    | 0     | 0       |
| 23   | 2        | 2    | 0     | 0       |

**Peak stress events (top 3 per region)**

| Region   | Timestamp_Local  | Demand_MW | Temperature | Stress_Index |
| -------- | ---------------- | --------- | ----------- | ------------ |
| Virginia | 2015-02-20 07:00 | 21,651    | -16.900     | 100.000      |
| Virginia | 2015-02-20 06:00 | 21,324    | -18.450     | 99.996       |
| Virginia | 2015-02-20 08:00 | 20,860    | -14.200     | 99.992       |
| Ohio     | 2015-02-20 07:00 | 24,739    | -18.050     | 100.000      |
| Ohio     | 2015-02-20 08:00 | 24,348    | -16.250     | 99.996       |
| Ohio     | 2015-02-20 06:00 | 24,210    | -18.400     | 99.992       |
| Texas    | 2019-08-12 16:00 | 74,533    | 40.850      | 100.000      |
| Texas    | 2019-08-12 17:00 | 74,457    | 40.050      | 99.996       |
| Texas    | 2019-08-26 16:00 | 74,338    | 40.550      | 99.992       |
| Georgia  | 2019-08-13 16:00 | 45,515    | 38.050      | 100.000      |
| Georgia  | 2019-08-13 15:00 | 45,486    | 38.100      | 99.996       |
| Georgia  | 2019-08-13 17:00 | 45,304    | 37.300      | 99.992       |

**Why it is relative, not grid capacity.** The index only says where an hour sits within that region's own observed demand. It contains no information about generation capacity, reserves, transmission limits or outages, so a value of 100 means "this region's highest observed hour", not "the grid was at its limit". Because each region is ranked against itself, the same value in two regions does not mean the same physical stress.

## 9. Final Data Pipeline

### Stage 1 — Raw demand inputs (PJM, local files)

| Input                     | Raw rows | Raw columns | Raw range                | Rows kept (2015–2017 local) | Rows outside period | Null MW | Duplicate labels kept (Nov DST) |
| ------------------------- | -------- | ----------- | ------------------------ | ---------------------------- | ------------------- | ------- | ------------------------------- |
| DOM_hourly.csv (Virginia) | 116,189  | 2           | 2005-05-01 → 2018-08-03 | 26,304                       | 89,885              | 0       | 3                               |
| AEP_hourly.csv.zip (Ohio) | 121,273  | 2           | 2004-10-01 → 2018-08-03 | 26,304                       | 94,969              | 0       | 3                               |

PJM labels are **hour-ending** Eastern prevailing time (evidence: each November `02:00` appears twice and each March `03:00` is missing). Each kept row is one elapsed hour; UTC interval starts are assigned sequentially from 05:00 UTC on 1 January and every unambiguous row is cross-checked against a DST-aware conversion. Columns created: `Region`, `Timestamp`, `Demand_MW`.

### Stage 2 — API acquisition (EIA-930, cached in data/raw/)

| Input                  | Files | Raw records | Fields per record | Outside local years | In local years | Null values dropped | Rows kept | Units         |
| ---------------------- | ----- | ----------- | ----------------- | ------------------- | -------------- | ------------------- | --------- | ------------- |
| EIA-930 ERCO (Texas)   | 4     | 26,312      | 7                 | 9                   | 26,303         | 0                   | 26,303    | megawatthours |
| EIA-930 SOCO (Georgia) | 4     | 26,312      | 7                 | 9                   | 26,303         | 24                  | 26,279    | megawatthours |

`period` is UTC hour-ending → `Timestamp = period − 1 h`, then restricted to hours starting inside the local years. Null values are dropped and reported, never filled.

### Stage 3 — Weather acquisition and resampling (NSRDB, cached in data/raw/)

| Region   | Files (years)          | Raw 30-min rows | Raw columns | Hourly rows after resample | Null hourly values | Hourly rows used in master | Hourly rows not needed (outside local years) |
| -------- | ---------------------- | --------------- | ----------- | -------------------------- | ------------------ | -------------------------- | -------------------------------------------- |
| Virginia | 2015, 2016, 2017, 2018 | 70,128          | 10          | 35,064                     | 0                  | 26,304                     | 8,760                                        |
| Ohio     | 2015, 2016, 2017, 2018 | 70,128          | 10          | 35,064                     | 0                  | 26,304                     | 8,760                                        |
| Texas    | 2019, 2020, 2021, 2022 | 70,128          | 10          | 35,064                     | 0                  | 26,303                     | 8,761                                        |
| Georgia  | 2019, 2020, 2021, 2022 | 70,128          | 10          | 35,064                     | 0                  | 26,279                     | 8,785                                        |

Each half-hour value is labelled at the start of its interval; the hourly value is the mean of the `:00` and `:30` values. The extra year per region is downloaded only to cover the last 5–6 local hours of the final year.

### Stage 4 — Merge, feature creation, Stress Index

| Region   | Demand rows in | Rows after inner join | Rows lost in join |
| -------- | -------------- | --------------------- | ----------------- |
| Virginia | 26,304         | 26,304                | 0                 |
| Ohio     | 26,304         | 26,304                | 0                 |
| Texas    | 26,303         | 26,303                | 0                 |
| Georgia  | 26,279         | 26,279                | 0                 |

Inner join on UTC `Timestamp`; every demand hour found a weather hour. Columns created from local time: `Timestamp_Local`, `Year`, `Month`, `Hour`, `DayOfWeek`, `Is_Weekend`, `Season`; then `Stress_Index` (derived). Missing values introduced: 0.

### Stage 5 — IM3 atlas

| Step                                                                                     | Rows  | Columns | Change                      |
| ---------------------------------------------------------------------------------------- | ----- | ------- | --------------------------- |
| Raw CSV                                                                                  | 1,479 | 13      | —                          |
| Drop rows without coordinates; add Region (focus state or 'Other') → im3_atlas_full.csv | 1,479 | 14      | 0 rows removed; +1 column   |
| Keep 4 focus states → im3_clean.csv                                                     | 577   | 14      | 902 non-focus rows excluded |
| Aggregate per region + demand stats → geo_summary.csv                                   | 4     | 10      | derived summary             |

### Stage 6 — Outputs and dashboard

| File                  | Rows    | Columns | Size (MB) |
| --------------------- | ------- | ------- | --------- |
| master_timeseries.csv | 125,190 | 17      | 17.131    |
| im3_clean.csv         | 577     | 14      | 0.079     |
| geo_summary.csv       | 4       | 10      | 0.000     |
| im3_atlas_full.csv    | 1,479   | 14      | 0.195     |

`app.py` reads `master_timeseries.csv`, `geo_summary.csv` and `im3_atlas_full.csv` (it derives the 4-state subset itself; `im3_clean.csv` is a notebook deliverable not read by the app). The app adds one helper column, `Date_Local`, for daily aggregation, and makes no API calls.

## 10. Dashboard KPI and Visual Inventory

All items are recalculated on every interaction from the filtered dataframe. **Filters:** Region (multiselect) and Season (multiselect) filter `master`; Region also filters the IM3 records; Resolution only switches the Overview time series between daily and hourly.

| Item                              | Formula / aggregation                                                                                               | Source                        | Columns                                                    | Filters                                | Units                  | Dynamic | Assumptions / caveats                             |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ----------------------------- | ---------------------------------------------------------- | -------------------------------------- | ---------------------- | ------- | ------------------------------------------------- |
| KPI: Regions                      | count of selected regions                                                                                           | sidebar                       | —                                                         | Region                                 | count                  | Yes     | —                                                |
| KPI: Data Centers                 | nunique(id) of IM3 rows in selected regions; 'of N nationwide' = nunique(id) of full atlas                          | im3_atlas_full                | id, Region                                                 | Region                                 | count                  | Yes     | Atlas is a 2026 snapshot                          |
| KPI: Avg Demand                   | mean(Demand_MW) per selected region (never pooled)                                                                  | master                        | Demand_MW                                                  | Region, Season                         | MW                     | Yes     | —                                                |
| KPI: Highest Regional Peak        | max(Demand_MW) with its region and local date                                                                       | master                        | Demand_MW, Region, Timestamp_Local                         | Region, Season                         | MW                     | Yes     | —                                                |
| KPI: High Stress Hours            | share of filtered hours with Stress_Index ≥ 95                                                                     | master                        | Stress_Index                                               | Region, Season                         | %                      | Yes     | ≥ 95 threshold; relative index                   |
| Demand time series                | daily: mean by Region × local date; hourly: raw                                                                    | master                        | Demand_MW, Timestamp_Local                                 | Region, Season, Resolution             | MW                     | Yes     | —                                                |
| Region snapshot cards             | peak + local time, mean Temperature, mean GHI, DC count                                                             | master + geo_summary          | Demand_MW, Temperature, GHI, unique_DCs                    | Region, Season (DC count: Region only) | MW, °C, W/m², count  | Yes     | Single weather point                              |
| Hourly profile weekday vs weekend | mean Demand by Region × Hour × Is_Weekend                                                                         | master                        | Demand_MW, Hour, Is_Weekend                                | Region, Season                         | MW                     | Yes     | Hour = local start                                |
| Seasonal demand bars              | mean Demand by Region × Season                                                                                     | master                        | Demand_MW, Season                                          | Region, Season                         | MW                     | Yes     | Meteorological seasons                            |
| Day-of-week bars                  | mean Demand by Region × DayOfWeek                                                                                  | master                        | Demand_MW, DayOfWeek                                       | Region, Season                         | MW                     | Yes     | —                                                |
| Demand violin                     | distribution of hourly Demand per region                                                                            | master                        | Demand_MW                                                  | Region, Season                         | MW                     | Yes     | —                                                |
| Monthly trend                     | mean Demand by Region × Year × Month                                                                              | master                        | Demand_MW, Year, Month                                     | Region, Season                         | MW                     | Yes     | —                                                |
| Stress box plot                   | distribution of Stress_Index per region                                                                             | master                        | Stress_Index                                               | Region, Season                         | 0–100                 | Yes     | Relative index                                    |
| Stress by season bars             | mean Stress_Index by Region × Season                                                                               | master                        | Stress_Index, Season                                       | Region, Season                         | 0–100                 | Yes     | Relative index                                    |
| Hour × Month heatmap             | mean Stress_Index by Hour × Month for one chosen region                                                            | master                        | Stress_Index, Hour, Month                                  | Region, Season, region selectbox       | 0–100                 | Yes     | Relative index                                    |
| Top stress events table           | top ⌊20 / regions⌋ hours per region by Stress_Index; rank within region (ties share)                              | master                        | Stress_Index, Demand_MW, Temperature, GHI, Timestamp_Local | Region, Season                         | MW, °C, W/m², 0–100 | Yes     | Rank within filtered hours; Stress vs full record |
| Temperature vs demand scatter     | random 1/6 sample per region (seed 42)                                                                              | master                        | Temperature, Demand_MW                                     | Region, Season                         | °C, MW                | Yes     | Sampled for display only                          |
| Pearson r table                   | corr(Temperature, Demand_MW) per region, all filtered hours                                                         | master                        | Temperature, Demand_MW                                     | Region, Season                         | unitless               | Yes     | Linear association only                           |
| GHI vs demand scatter + caption r | daytime (GHI > 0) points of the same sample; r over all filtered daytime hours                                      | master                        | GHI, Demand_MW                                             | Region, Season                         | W/m², MW              | Yes     | Confounded by time of day                         |
| Solar profile by hour             | mean GHI by Region × Hour (overlapping, not stacked)                                                               | master                        | GHI, Hour                                                  | Region, Season                         | W/m²                  | Yes     | —                                                |
| Wind speed by hour                | mean Wind Speed by Region × Hour                                                                                   | master                        | Wind Speed, Hour                                           | Region, Season                         | m/s                    | Yes     | —                                                |
| Monthly solar components          | mean GHI, DNI, DHI by Month for one chosen region                                                                   | master                        | GHI, DNI, DHI, Month                                       | Region, Season, region selectbox       | W/m²                  | Yes     | —                                                |
| Data-center map                   | all atlas points of selected regions (color) + other states (gray); marker area ∝ sqft (2–30 px); points as rings | im3_atlas_full                | lat, lon, sqft, type, Region                               | Region                                 | sq ft (size)           | Yes     | Display size clamped; 2026 snapshot               |
| DC type breakdown                 | nunique(id) by Region × type                                                                                       | im3_atlas_full (focus subset) | id, type, Region                                           | Region                                 | count                  | Yes     | —                                                |
| DC concentration vs peak bubble   | x = nunique(id), y = max(Demand), area ∝ mean(Demand)                                                              | master + im3                  | id, Demand_MW                                              | Region, Season (demand)                | count, MW              | Yes     | 4 points cannot show a relationship               |
| Region summary table              | mean/max/min/std Demand, mean & P95 Stress, mean & max Temperature, DC count                                        | master + im3                  | Demand_MW, Stress_Index, Temperature, id                   | Region, Season                         | MW, 0–100, °C, count | Yes     | —                                                |

## 11. Final Project Summary

| #   | Item                           | Value                                                                                                                                                                                  |
| --- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Total time-series observations | 105,190 real Region-hours (file also holds 20,000 labelled synthetic rows = 125,190)                                                                                                   |
| 2   | Time-series features           | 16 columns (Region + 15)                                                                                                                                                               |
| 3   | Regions                        | 4 (Virginia, Ohio, Texas, Georgia)                                                                                                                                                     |
| 4   | Years covered                  | 6 calendar years: 2015–2017 (VA, OH) and 2019–2021 (TX, GA), local time                                                                                                              |
| 5   | Data-center records            | 1,479 (atlas); 577 in the 4 focus states                                                                                                                                               |
| 6   | Unique data-center ids         | 1,474 (atlas); 574 in the 4 focus states                                                                                                                                               |
| 7   | Geographic coverage            | 4 demand regions (one weather point each); atlas covers 47 states                                                                                                                      |
| 8   | Original data sources          | 4 (PJM via Kaggle, EIA-930 API, NREL NSRDB API, IM3 Data Center Atlas)                                                                                                                 |
| 9   | Processed datasets             | 4 CSV files in data/clean/                                                                                                                                                             |
| 10  | Missing observations           | 26 demand hours of 105,216 expected (0.025%); 0 nulls in master; 105 point records without area (by design)                                                                            |
| 11  | Duplicate records              | 0 duplicate rows in every file; 0 duplicate (Region, Timestamp); 5 atlas ids repeated across counties (legitimate)                                                                     |
| 11b | Suspected data errors          | 4 isolated one-hour demand spikes (Ohio 1, Georgia 3); kept and disclosed                                                                                                              |
| 12  | Date ranges                    | Virginia: 2015-01-01 00:00 → 2017-12-31 23:00; Ohio: 2015-01-01 00:00 → 2017-12-31 23:00; Texas: 2019-01-01 00:00 → 2021-12-31 23:00; Georgia: 2019-01-01 00:00 → 2021-12-31 23:00 |

**13. Most important statistical findings**

- **Average demand:** Virginia 11,117 MW, Ohio 14,712 MW, Texas 43,994 MW, Georgia 26,574 MW.
- **Record peaks:** Virginia 21,651 MW (2015-02-20 07:00); Ohio 24,739 MW (2015-02-20 07:00); Texas 74,533 MW (2019-08-12 16:00); Georgia 45,515 MW (2019-08-13 16:00).
- **Seasonality:** highest-demand month — Virginia Jul, Ohio Jan, Texas Aug, Georgia Aug; demand peaks in the afternoon/evening (Virginia 18:00, Ohio 18:00, Texas 17:00, Georgia 18:00 local) and bottoms out at night (Virginia 03:00, Ohio 03:00, Texas 03:00, Georgia 03:00).
- **Temperature vs demand (Pearson r):** Virginia +0.131, Ohio -0.058, Texas +0.631, Georgia +0.476. The relationship is U-shaped (heating + cooling), so r understates it; split at 18 °C, r is strongly negative below and strongly positive above in every region.
- Weekday demand exceeds weekend demand in every region (Virginia +5.3%, Ohio +10.1%, Texas +4.8%, Georgia +6.9%).
- The highest-stress hours cluster in the late afternoon: the most common top-1 % hour is Virginia 16:00, Ohio 16:00, Texas 16:00, Georgia 16:00 local.
- Virginia has by far the most data centers (319 unique ids) but the lowest average demand of the four regions; with only four regions, no relationship between data-center counts and demand can be established.

**14. Important limitations**

- Stress Index is a within-region percentile, not a grid-capacity or reliability measure, and is not comparable across regions.
- The two cohorts cover different years (2015–2017 vs 2019–2021); absolute MW across cohorts reflect different periods.
- Demand is reported for balancing areas/zones (DOM, AEP, ERCOT, Southern Company), while data centers are counted by state.
- Weather comes from a single NSRDB point per region.
- 4 suspected one-hour reporting errors remain in the demand data (Section 4), including Georgia's recorded minimum.
- The IM3 atlas is a February 2026 snapshot derived from crowd-sourced OpenStreetMap data; facilities and sizes may not match 2015–2021.
- Pearson correlations are linear, confounded by time of day/season, and do not imply causation.
- Timing uncertainty: NSRDB interval semantics are inferred empirically (< 30 min); the two repeated November PJM hours keep file order.
- No prediction or forecasting is performed despite the project name.
- The Kaggle dataset license and NSRDB redistribution terms were not verified.

## 12. Synthetic Demonstration Rows (generated, not measured)

Synthetic rows were added for the dashboard's demonstration mode only. Each region re-plays one continuous stretch of its own real data (one real year's January–July, weekday-aligned) with small seeded AR(1) noise (seed 42); see METHODOLOGY.md, Section 9. They contain no new information, never overlap real hours, and are excluded from every statistic in Sections 1–11.

**Counts and periods**

| Region   | Synthetic rows | Period (local)                       | Months covered                    | Overlap with real hours | Duplicate timestamps |
| -------- | -------------- | ------------------------------------ | --------------------------------- | ----------------------- | -------------------- |
| Virginia | 5,000          | 2018-01-01 00:00 → 2018-07-28 08:00 | Jan, Feb, Mar, Apr, May, Jun, Jul | 0                       | 0                    |
| Ohio     | 5,000          | 2018-01-01 00:00 → 2018-07-28 08:00 | Jan, Feb, Mar, Apr, May, Jun, Jul | 0                       | 0                    |
| Texas    | 5,000          | 2022-01-01 00:00 → 2022-07-28 08:00 | Jan, Feb, Mar, Apr, May, Jun, Jul | 0                       | 0                    |
| Georgia  | 5,000          | 2022-01-01 00:00 → 2022-07-28 08:00 | Jan, Feb, Mar, Apr, May, Jun, Jul | 0                       | 0                    |

**Templates used (from the notebook output)**

```

  Region  Synthetic rows            Synthetic period (local) Template stretch (real, local dates)  Excluded real days (incomplete or spike)
Virginia            5000 2018-01-01 00:00 → 2018-07-28 08:00              2017-01-02 → 2017-07-29                                         0
    Ohio            5000 2018-01-01 00:00 → 2018-07-28 08:00              2015-01-05 → 2015-08-01                                         1
   Texas            5000 2022-01-01 00:00 → 2022-07-28 08:00              2021-01-02 → 2021-07-29                                         1
 Georgia            5000 2022-01-01 00:00 → 2022-07-28 08:00              2019-01-05 → 2019-08-01                                         4
```

**Integrity and plausibility checks**

| Check                                                      | Result     |
| ---------------------------------------------------------- | ---------- |
| Real rows identical to the pre-synthetic file              | yes        |
| Real rows first in file, synthetic after                   | yes        |
| Labels other than real/synthetic                           | 0          |
| Missing values in synthetic rows                           | 0 (0.000%) |
| Duplicate (Region, Timestamp) across the whole file        | 0 (0.000%) |
| Synthetic hours overlapping real hours                     | 0 (0.000%) |
| Demand ≤ 0                                                | 0 (0.000%) |
| Irradiance < 0 or GHI/DNI > 1,361 W/m²                    | 0 (0.000%) |
| DHI > GHI + 1 W/m²                                        | 0 (0.000%) |
| Temperature outside −60…60 °C or wind < 0               | 0 (0.000%) |
| Stress_Index outside 0–100                                | 0 (0.000%) |
| Isolated one-hour demand spikes (>10 % vs both neighbours) | 0 (0.000%) |
| Synthetic hours above the region's real maximum            | 2 (0.010%) |

**Synthetic demand vs real demand from the same months** (MW; derived comparison)

| Region   | Real mean MW (same months) | Synthetic mean MW | Real std  | Synthetic std | Real min | Synthetic min | Real max (all months) | Synthetic max | Hourly-profile r | Temp–demand r real | Temp–demand r synthetic |
| -------- | -------------------------- | ----------------- | --------- | ------------- | -------- | ------------- | --------------------- | ------------- | ---------------- | ------------------- | ------------------------ |
| Virginia | 11,318.844                 | 11,060.631        | 2,604.092 | 2,429.657     | 6,694    | 6,846         | 21,651                | 19,816        | 0.999            | 0.045               | 0.252                    |
| Ohio     | 14,905.430                 | 15,575.434        | 2,582.337 | 2,761.394     | 9,662    | 9,746         | 24,739                | 25,080        | 0.999            | -0.179              | -0.350                   |
| Texas    | 43,142.706                 | 43,746.054        | 9,127.923 | 9,103.945     | 27,449   | 27,540        | 74,533                | 73,136        | 0.999            | 0.536               | 0.422                    |
| Georgia  | 26,302.846                 | 26,962.221        | 5,406.744 | 5,603.551     | 16,328   | 17,417        | 45,515                | 45,656        | 1.000            | 0.411               | 0.455                    |

The hourly shape matches almost exactly because whole real days are re-played. Means, spreads and the temperature–demand r differ somewhat from the real 3-year figures because each region copies a single real year.

**Synthetic values above the real record** — noise added on top of a copied real peak can exceed the real maximum slightly:

| Region   | Hours above real max | Synthetic max (MW) | Real max (MW) | Excess % |
| -------- | -------------------- | ------------------ | ------------- | -------- |
| Virginia | 0                    | 19,816             | 21,651        | -8.48    |
| Ohio     | 1                    | 25,080             | 24,739        | 1.38     |
| Texas    | 0                    | 73,136             | 74,533        | -1.87    |
| Georgia  | 1                    | 45,656             | 45,515        | 0.31     |

**Synthetic weather ranges** (°C, m/s, W/m²)

| Region   | Temperature min | Temperature max | Wind Speed min | Wind Speed max | GHI min | GHI max  | DNI min | DNI max  | DHI min | DHI max |
| -------- | --------------- | --------------- | -------------- | -------------- | ------- | -------- | ------- | -------- | ------- | ------- |
| Virginia | -11.01          | 37.51           | 0.14           | 8.70           | 0.00    | 1,077.10 | 0.00    | 1,057.60 | 0.00    | 565.50  |
| Ohio     | -18.87          | 34.06           | 0.10           | 12.32          | 0.00    | 1,135.60 | 0.00    | 1,088.10 | 0.00    | 541.00  |
| Texas    | -15.81          | 39.58           | 0.22           | 10.91          | 0.00    | 1,100.10 | 0.00    | 1,080.60 | 0.00    | 520.90  |
| Georgia  | -5.91           | 36.57           | 0.12           | 4.30           | 0.00    | 1,095.20 | 0.00    | 1,088.50 | 0.00    | 543.50  |

**Synthetic Stress_Index** (placed on each region's *real* percentile scale, so real rows keep their values; values above the real maximum are capped at 100)

| Region   | Mean Stress | P95 Stress | Hours ≥ 95 | Hours capped at 100 |
| -------- | ----------- | ---------- | ----------- | ------------------- |
| Virginia | 49.51       | 95.17      | 257         | 0                   |
| Ohio     | 58.98       | 97.74      | 481         | 1                   |
| Texas    | 49.67       | 94.22      | 208         | 0                   |
| Georgia  | 51.54       | 95.58      | 299         | 1                   |

**Limitations.** Synthetic rows repeat the template year's events (Texas's template is 2021, so its synthetic February repeats Winter Storm Uri), cannot contain events absent from the template, misalign public holidays, ignore load growth and cover January–July only, so pooled real + synthetic figures shift toward winter/spring. They must never be cited as measured data.

## Appendix — Cross-checks against notebook and dashboard

| Statistic                                 | This report (from CSV) | Notebook / dashboard |
| ----------------------------------------- | ---------------------- | -------------------- |
| Total master rows                         | 105,190                | 105,190              |
| Hours with Stress ≥ 99                   | 1,055                  | 1,055                |
| Mode hour of daily minimum (VA/OH/TX/GA)  | 03/03/03/04            | 03/03/03/04          |
| Georgia null demand values dropped        | 24                     | 24                   |
| Dashboard KPI: Virginia avg demand (MW)   | 11,117                 | 11,117               |
| Dashboard KPI: Ohio avg demand (MW)       | 14,712                 | 14,712               |
| Dashboard KPI: Texas avg demand (MW)      | 43,994                 | 43,994               |
| Dashboard KPI: Georgia avg demand (MW)    | 26,574                 | 26,574               |
| Dashboard KPI: data centers (4 regions)   | 574                    | 574                  |
| Dashboard KPI: high-stress hours          | 5.0%                   | 5.0%                 |
| Dashboard KPI: highest regional peak (MW) | 74,533                 | 74,533               |

Dashboard AppTest ran without exceptions: yes.
