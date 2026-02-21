import json
import os
import math
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI()

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Expose-Headers": "Access-Control-Allow-Origin",
}

@app.middleware("http")
async def add_cors(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@app.options("/{path:path}")
async def options_handler():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }
    )


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

        latencies = [r["latency_ms"] for r in rows if "latency_ms" in r]
        uptimes = [r["uptime_pct"] for r in rows if "uptime_pct" in r]

        if not latencies:
            results[region] = {
                "avg_latency": 0,
                "p95_latency": 0,
                "avg_uptime": 0,
                "breaches": 0
            }
            continue

        # Mean
        avg_latency = sum(latencies) / len(latencies)

        # Correct percentile calculation
        sorted_lat = sorted(latencies)
        n = len(sorted_lat)

        pos = 0.95 * (n - 1)
        lower = math.floor(pos)
        upper = math.ceil(pos)

        if lower == upper:
            p95_latency = sorted_lat[int(pos)]
        else:
            weight = pos - lower
            p95_latency = sorted_lat[lower] * (1 - weight) + sorted_lat[upper] * weight

        # Mean uptime
        avg_uptime = sum(uptimes) / len(uptimes) if uptimes else 0

        breaches = sum(1 for v in latencies if v > threshold)

        results[region] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
        }

    return JSONResponse(content={"regions": results}, headers=CORS_HEADERS)