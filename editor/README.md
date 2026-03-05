# Fermento — Stage Boundary Editor

Interactive web app for editing fermentation run CSV stage boundaries.
Upload a CSV, visualize sensor data (distance, CO₂, temperature, humidity),
drag stage boundaries, and download the modified file.

## Architecture

| Layer    | Tech               | Port |
|----------|--------------------|------|
| Backend  | FastAPI + Uvicorn  | 8000 |
| Frontend | React 18 + SVG     | 3000 |
| Proxy    | Nginx (in frontend)| 3000 |

The frontend's nginx reverse-proxies `/api/*` requests to the backend container,
so the browser only needs port **3000**.

## Quick start

```bash
docker compose up --build
```

Then open **http://localhost:3000**.

## Features

- **Upload** any fermentation run `.csv` with columns:
  `timestamp, distance, temperature, co2, humidity, stage`
- **Interactive chart** — primary metric line with colored stage regions
- **Drag boundaries** — diamond handles on stage dividers; drag left/right to reassign rows
- **Overlays** — toggle CO₂, temperature, humidity traces on/off
- **Helper lines** — max rate-of-change, max CO₂ peak (toggle on/off)
- **Stage durations** — displayed over each colored region
- **Hover tooltip** — shows all sensor values at the cursor position
- **Download** — exports modified CSV with the original filename

## Development (without Docker)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
REACT_APP_API_URL=http://localhost:8000 npm start
```

## CSV format

```csv
"timestamp","distance","temperature","co2","humidity",stage
2026-02-27 14:02:12,98,31.8,1616,56.7,0
...
```

The `stage` column (integer) is what the editor modifies.
All other columns are displayed but not changed.
