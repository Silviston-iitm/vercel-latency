import json
import os
import numpy as np
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

app = FastAPI()

# ---- CORS HEADERS ----
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Expose-Headers": "Access-Control-Allow-Origin",
}

# ---- FastAPI CORS Middleware ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Force headers (important for some graders / proxies) ----
@app.middleware("http")
async def force_cors_headers(request, call_next):
    response = await call_next(request)
    for k, v in CORS_HEADERS.items():
        response.headers[k] = v
    return response

# ---- Handle OPTIONS preflight ----
@app.options("/{path:path}")
async def options_handler():
    return Response(headers=CORS_HEADERS)

# ---- Load telemetry data ----
DATA_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "q-vercel-latency.json"
)

with open(DATA_PATH) as f:
    telemetry = json.load(f)

# ---- POST endpoint ----
@app.post("/")
async def latency_metrics(request: Request):
    body = await request.json()

    regions = body["regions"]
    threshold = body["threshold_ms"]

    results = {}

    for region in regions:
        rows = [r for r in telemetry if r["region"] == region]

        latencies = [r["latency_ms"] for r in rows]
        uptimes = [r["uptime"] for r in rows]

        avg_latency = float(np.mean(latencies))
        p95_latency = float(np.percentile(latencies, 95))
        avg_uptime = float(np.mean(uptimes))
        breaches = sum(1 for v in latencies if v > threshold)

        results[region] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
        }

    return JSONResponse(content=results, headers=CORS_HEADERS)