import json
import os
import numpy as np
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

app = FastAPI()

# -----------------------------
# CORS HEADERS
# -----------------------------
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Expose-Headers": "Access-Control-Allow-Origin",
}

# -----------------------------
# CORS Middleware
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Force headers (important on Vercel)
# -----------------------------
@app.middleware("http")
async def force_cors_headers(request, call_next):
    response = await call_next(request)
    for k, v in CORS_HEADERS.items():
        response.headers[k] = v
    return response

# -----------------------------
# OPTIONS handler
# -----------------------------
@app.options("/{path:path}")
async def options_handler():
    return Response(status_code=200, headers=CORS_HEADERS)

# -----------------------------
# Load telemetry safely
# -----------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "q-vercel-latency.json")

with open(DATA_PATH, "r") as f:
    telemetry = json.load(f)

# -----------------------------
# Helper functions
# -----------------------------
def average(values):
    return float(sum(values) / len(values)) if values else 0.0


def percentile_95(values):
    if not values:
        return 0.0
    values_sorted = sorted(values)
    index = int(0.95 * (len(values_sorted) - 1))
    return float(values_sorted[index])


# -----------------------------
# POST endpoint
# -----------------------------
@app.post("/latency")
async def latency_metrics(request: Request):
    body = await request.json()

    regions = body.get("regions", [])
    threshold = body.get("threshold_ms", 0)

    results = {}

    for region in regions:
        rows = [r for r in telemetry if r["region"] == region]

        latencies = [r["latency_ms"] for r in rows]
        uptimes = [r["uptime"] for r in rows]

        avg_latency = average(latencies)
        p95_latency = percentile_95(latencies)
        avg_uptime = average(uptimes)
        breaches = sum(1 for v in latencies if v > threshold)

        results[region] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
        }

    return JSONResponse(content=results, headers=CORS_HEADERS)