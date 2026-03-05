"""
Fermento CSV Stage Editor — FastAPI Backend
"""
import io
import csv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Fermento Stage Editor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def parse_value(key: str, val: str):
    """Try to cast non-timestamp fields to int then float."""
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


@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only .csv files are supported")

    raw = await file.read()
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    headers = list(reader.fieldnames or [])
    rows = [{h: parse_value(h, row.get(h, "")) for h in headers} for row in reader]

    return {
        "filename": file.filename,
        "headers": headers,
        "data": rows,
        "rowCount": len(rows),
    }


class DownloadPayload(BaseModel):
    filename: str
    headers: list[str]
    data: list[dict]


@app.post("/api/download")
async def download_csv(payload: DownloadPayload):
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=payload.headers,
        quoting=csv.QUOTE_ALL,
        lineterminator="\r\n",
    )
    writer.writeheader()
    for row in payload.data:
        writer.writerow({h: row.get(h, "") for h in payload.headers})

    content = buf.getvalue().encode("utf-8")
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{payload.filename}"'},
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}
