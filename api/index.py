import json
import os
import numpy as np
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

app = FastAPI()

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.options("/{path:path}")
async def options_handler():
    return Response(status_code=200, headers=CORS_HEADERS)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "q-vercel-latency.json")

with open(DATA_PATH) as f:
    telemetry = json.load(f)



@app.post("/latency")
async def latency_metrics(request: Request):

    body = await request.json()
    regions = body.get("regions", [])
    threshold = body.get("threshold_ms", 0)

    results = {}

    for region in regions:

        rows = [r for r in telemetry if r.get("region") == region]

        latencies = [r.get("latency_ms", 0) for r in rows if "latency_ms" in r]
        uptimes = [r.get("uptime", 0) for r in rows if "uptime" in r]

        if not latencies:
            results[region] = {
                "avg_latency": 0,
                "p95_latency": 0,
                "avg_uptime": 0,
                "breaches": 0
            }
            continue

        avg_latency = float(sum(latencies) / len(latencies))

        sorted_lat = sorted(latencies)
        idx = int(0.95 * (len(sorted_lat) - 1))
        p95_latency = float(sorted_lat[idx])

        avg_uptime = float(sum(uptimes) / len(uptimes)) if uptimes else 0

        breaches = sum(1 for v in latencies if v > threshold)

        results[region] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
        }

    return JSONResponse(content=results, headers=CORS_HEADERS)