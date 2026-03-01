"""Leak API server for Demo 3: RAG Poisoning.

This server simulates an attacker-controlled endpoint that receives
exfiltrated data from the poisoned RAG document attack.
"""

import json
import sys
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Leak API",
    description="Attacker-controlled endpoint for Demo 3: RAG Poisoning",
    version="1.0.0"
)


@app.post("/data")
async def receive_data(request: Request):
    """Receive exfiltrated data and print to stdout."""
    
    timestamp = datetime.now().isoformat()
    
    # Get the raw body
    try:
        body = await request.json()
    except Exception:
        body = await request.body()
        body = body.decode("utf-8") if body else "(empty)"
    
    # Print prominent banner to stdout
    print("\n" + "=" * 70, file=sys.stdout)
    print("=" * 70, file=sys.stdout)
    print(f"⏰ Timestamp: {timestamp}", file=sys.stdout)
    print(f"📡 Source IP: {request.client.host}", file=sys.stdout)
    print("-" * 70, file=sys.stdout)
    print("📦 PAYLOAD:", file=sys.stdout)
    print("-" * 70, file=sys.stdout)
    
    if isinstance(body, dict):
        print(json.dumps(body, indent=2, default=str), file=sys.stdout)
    else:
        print(body, file=sys.stdout)
    
    print("-" * 70, file=sys.stdout)
    print("=" * 70 + "\n", file=sys.stdout)
    
    # Flush to ensure immediate output in Docker logs
    sys.stdout.flush()
    
    return JSONResponse(
        status_code=200,
        content={"status": "received", "timestamp": timestamp}
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "leak-api"}


@app.on_event("startup")
async def startup_event():
    """Log startup message."""
    print("\n" + "=" * 70, file=sys.stdout)
    print("🎯 Leak API Server Started", file=sys.stdout)
    print("=" * 70, file=sys.stdout)
    print("Listening for exfiltrated data on POST /data", file=sys.stdout)
    print("This simulates an attacker-controlled endpoint.", file=sys.stdout)
    print("=" * 70 + "\n", file=sys.stdout)
    sys.stdout.flush()
