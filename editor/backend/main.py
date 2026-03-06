"""
Fermento — FastAPI Backend
Handles CSV upload (single + multi), profile computation, download (single + zip).
"""
import io
import csv
import json
import zipfile
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Fermento")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_value(key: str, val: str):
    val = val.strip()
    if key == "timestamp":
        return val
    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            return val


def parse_csv_bytes(raw: bytes, filename: str) -> dict:
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    headers = list(reader.fieldnames or [])
    rows = [{h: parse_value(h, row.get(h, "")) for h in headers} for row in reader]
    return {"filename": filename, "headers": headers, "data": rows, "rowCount": len(rows)}


# ---------------------------------------------------------------------------
# Single-file upload (editor mode)
# ---------------------------------------------------------------------------

@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only .csv files are supported")
    raw = await file.read()
    return parse_csv_bytes(raw, file.filename)


# ---------------------------------------------------------------------------
# Multi-file upload (report mode)
# ---------------------------------------------------------------------------

@app.post("/api/upload-multi")
async def upload_multi(files: list[UploadFile] = File(...)):
    results = []
    for f in files:
        if not f.filename.lower().endswith(".csv"):
            continue
        raw = await f.read()
        results.append(parse_csv_bytes(raw, f.filename))
    if not results:
        raise HTTPException(400, "No valid CSV files uploaded")
    return {"runs": results}


# ---------------------------------------------------------------------------
# Single CSV download
# ---------------------------------------------------------------------------

class DownloadPayload(BaseModel):
    filename: str
    headers: list[str]
    data: list[dict]


@app.post("/api/download")
async def download_csv(payload: DownloadPayload):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=payload.headers,
                            quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writeheader()
    for row in payload.data:
        writer.writerow({h: row.get(h, "") for h in payload.headers})
    content = buf.getvalue().encode("utf-8")
    return StreamingResponse(
        io.BytesIO(content), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{payload.filename}"'},
    )


# ---------------------------------------------------------------------------
# Multi CSV download (zip)
# ---------------------------------------------------------------------------

class MultiDownloadPayload(BaseModel):
    runs: list[DownloadPayload]


@app.post("/api/download-zip")
async def download_zip(payload: MultiDownloadPayload):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for run in payload.runs:
            csv_buf = io.StringIO()
            writer = csv.DictWriter(csv_buf, fieldnames=run.headers,
                                    quoting=csv.QUOTE_ALL, lineterminator="\r\n")
            writer.writeheader()
            for row in run.data:
                writer.writerow({h: row.get(h, "") for h in run.headers})
            zf.writestr(run.filename, csv_buf.getvalue())
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="fermento-runs.zip"'},
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}
