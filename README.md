# Data Center Energy Stress Predictor
### A Multi-Source Geospatial Analytics and Visualization Platform

B.Tech IT — Data Analytics & Visualization course project.
No machine learning or deep learning. All analysis is descriptive and statistical.

---

## Regions covered

| Region   | Demand source | Years     |
|----------|---------------|-----------|
| Virginia | PJM DOM       | 2015–2017 |
| Ohio     | PJM AEP       | 2015–2017 |
| Texas    | EIA-930 ERCO  | 2019–2021 |
| Georgia  | EIA-930 SOCO  | 2019–2021 |

---

## Setup

### 1. Clone / open the project folder

```bash
cd dav_project
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API keys

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
# Edit .env with your EIA_API_KEY, NSRDB_API_KEY, NSRDB_FULL_NAME,
# NSRDB_EMAIL, and NSRDB_AFFILIATION
```

The `.env` file is listed in `.gitignore` and will never be committed.

---

## Running the notebook

```bash
# Interactive (VS Code / JupyterLab)
.venv/bin/jupyter lab dav_project.ipynb

# Headless execution (re-runs all cells top to bottom)
.venv/bin/jupyter nbconvert --to notebook --execute \
    --ExecutePreprocessor.timeout=1200 \
    dav_project.ipynb --output dav_project.ipynb
```

On first run the notebook fetches data from the EIA-930 and NSRDB APIs and
caches the results in `data/raw/`. Subsequent runs use the cache and complete
in under two minutes.

---

## Running the dashboard

```bash
.venv/bin/streamlit run app.py
```

The dashboard reads only `data/clean/*.csv` and makes no API calls.
Open the URL printed in the terminal (usually `http://localhost:8501`).

---

## Project structure

```
dav_project/
├── DOM_hourly.csv               # Raw Virginia demand (do not modify)
├── AEP_hourly.csv.zip           # Raw Ohio demand (do not modify)
├── p147s-4h760/                 # IM3 Data Center Atlas (do not modify)
├── dav_project.ipynb            # Primary deliverable — notebook
├── app.py                       # Streamlit dashboard
├── make_notebook.py             # Script that generates the notebook JSON
├── requirements.txt
├── .env                         # API keys (not committed)
├── .env.example                 # Template
├── .gitignore
├── README.md
├── METHODOLOGY.md
├── data/
│   ├── raw/                     # Cached API responses (auto-created)
│   └── clean/
│       ├── master_timeseries.csv
│       ├── im3_clean.csv
│       └── geo_summary.csv
```

---

## Data sources

1. **PJM Kaggle hourly consumption** — robikscube/hourly-energy-consumption
2. **EIA-930 Open Data API v2** — hourly demand by balancing authority
3. **NREL NSRDB** — 30-min solar and weather data (resampled to hourly)
4. **IM3 Data Center Atlas** — PNNL / DOE MSD-LIVE, v2026.02.09, ODbL license
