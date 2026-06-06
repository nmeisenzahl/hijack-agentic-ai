"""Leak API server for Demo 03: Sleeper Cell.

Simulates an attacker-controlled endpoint that receives
exfiltrated data from the poisoned RAG document attack.
"""

from __future__ import annotations

import json
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


@asynccontextmanager
async def lifespan(_app: FastAPI):
    print("\n" + "=" * 70, file=sys.stdout)
    print("🎯 Leak API Server Started", file=sys.stdout)
    print("=" * 70, file=sys.stdout)
    print("Listening for exfiltrated data on POST /data", file=sys.stdout)
    print("This simulates an attacker-controlled endpoint.", file=sys.stdout)
    print("=" * 70 + "\n", file=sys.stdout)
    sys.stdout.flush()
    yield


app = FastAPI(title="Leak API", version="1.0.0", lifespan=lifespan)


@app.post("/data")
async def receive_data(request: Request) -> JSONResponse:
    """Receive exfiltrated data and print to stdout."""
    timestamp = datetime.now().isoformat()
    leak_id = f"leak-{uuid.uuid4().hex[:8]}"

    try:
        body = await request.json()
    except json.JSONDecodeError:
        raw = await request.body()
        body = raw.decode("utf-8") if raw else "(empty)"

    source_ip = request.client.host if request.client else "unknown"

    print("\n" + "=" * 70, file=sys.stdout)
    print("🚨 DATA EXFILTRATED", file=sys.stdout)
    print("=" * 70, file=sys.stdout)
    print(f"⏰ Timestamp: {timestamp}", file=sys.stdout)
    print(f"📋 Leak ID:   {leak_id}", file=sys.stdout)
    print(f"📡 Source IP: {source_ip}", file=sys.stdout)
    print("-" * 70, file=sys.stdout)
    print("📦 STOLEN PAYLOAD:", file=sys.stdout)
    print("-" * 70, file=sys.stdout)

    if isinstance(body, dict):
        print(json.dumps(body, indent=2, default=str), file=sys.stdout)
    else:
        print(str(body)[:2000], file=sys.stdout)

    print("-" * 70, file=sys.stdout)
    print("=" * 70 + "\n", file=sys.stdout)
    sys.stdout.flush()

    return JSONResponse(
        status_code=200,
        content={"id": leak_id, "status": "received", "timestamp": timestamp},
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Return a simple readiness response."""
    return {"status": "healthy"}
