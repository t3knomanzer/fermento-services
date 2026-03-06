# Fermento — Stage Editor & Analysis Dashboard

Two-mode web app for fermentation run analysis and stage boundary editing.

## Quick start

```bash
docker compose up --build
```

Open **http://localhost:3000**

## Modes

### Report mode (default)
- Upload multiple CSVs at once (multi-select)
- 4-panel interactive dashboard:
  - Temperature distribution histogram
  - Stage durations by run (stacked bars, sorted by temp)
  - Temperature vs duration scatter with trend lines
  - Max CO₂ vs temperature scatter
- Hover any data point for run details
- Click any data point to open that run in the sidebar editor
- Expand sidebar editor to full screen
- Stage edits automatically update the report panels
- Download all modified CSVs as a zip

### Editor mode
- Upload a single CSV for detailed stage boundary editing
- Drag diamond handles to adjust stage boundaries
- Toggle overlays (CO₂, temp, humidity, growth_norm, etc)
- Helper lines (max rate-of-change, max CO₂)
- Column management (exclude columns from export)
- Download modified CSV with original filename

## Architecture

| Layer    | Tech               | Port |
|----------|--------------------|------|
| Backend  | FastAPI + Uvicorn  | 8000 |
| Frontend | React 18 + SVG     | 3000 |
| Proxy    | Nginx              | 3000 |

## File structure

```
backend/
  main.py              — FastAPI (upload, upload-multi, download, download-zip)
  requirements.txt
  Dockerfile

frontend/src/
  App.js               — Mode switcher (Report / Editor tabs)
  shared.js            — Constants, helpers, profile builder
  Editor.js            — Single-run stage boundary editor
  Report.js            — Multi-run analysis dashboard (4 SVG panels)
  index.js             — React entry
```

## CSV format

```csv
"timestamp","distance","temperature","co2","humidity",stage
2026-02-27 14:02:12,98,31.8,1616,56.7,0
```

The `stage` column is auto-generated if missing (4 stages, evenly distributed).
A `growth` column is computed as `max(distance) - distance`.
