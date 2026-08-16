import os
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

from services.scheduler import create_schedule
from services.weather import get_weather


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)
CORS(app)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return jsonify({
        "project": "Agromind",
        "system": "AI-Optimized Solar Irrigation Scheduler",
        "version": "AOSIS-v14",
        "status": "online"
    })


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "version": "AOSIS-v14"
    })


# ============================================================
# AI IRRIGATION SCHEDULE
# ============================================================

@app.post("/api/schedule")
def schedule():

    data = request.get_json(silent=True) or {}

    required = [
        "soil_moisture_pct",
        "soil_temperature_C",
        "solar_irradiance_W_m2",

        "rain_0_24h_mm",
        "rain_probability_0_24h",

        "rain_24_48h_mm",
        "rain_probability_24_48h",

        "crop_type",
        "crop_age_days",
        "land_size_m2"
    ]

    missing = [
        key for key in required
        if key not in data
    ]

    if missing:
        return jsonify({
            "error": "Missing fields",
            "fields": missing
        }), 400

    try:

        result = create_schedule(**data)

        return jsonify(result)

    except Exception as exc:

        return jsonify({
            "error": str(exc)
        }), 400


# ============================================================
# WEATHER
# ============================================================

@app.get("/api/weather")
def weather():

    lat = request.args.get(
        "lat",
        type=float
    )

    lon = request.args.get(
        "lon",
        type=float
    )

    if lat is None or lon is None:

        return jsonify({
            "error": "lat and lon are required"
        }), 400

    try:

        result = get_weather(
            lat,
            lon
        )

        return jsonify(result)

    except Exception as exc:

        return jsonify({
            "error": str(exc)
        }), 502


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/api/dashboard")
def dashboard():

    # --------------------------------------------------------
    # DEMO TELEMETRY
    #
    # This is temporary until the ESP32-S3 sends real data.
    # --------------------------------------------------------

    payload = {

        "soil_moisture_pct": 42.0,

        "soil_temperature_C": 28.7,

        "solar_irradiance_W_m2": 620.0,

        "rain_0_24h_mm": 0.0,

        "rain_probability_0_24h": 0.10,

        "rain_24_48h_mm": 8.0,

        "rain_probability_24_48h": 0.75,

        "crop_type": "Tomato",

        "crop_age_days": 60,

        "land_size_m2": 100.0,

        "pump_flow_L_min": 10.0,

        "application_efficiency": 0.75,

        "start_time": "06:00"
    }

    try:

        result = create_schedule(
            **payload
        )

        return jsonify({

            "timestamp":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "telemetry":
                payload,

            "schedule":
                result
        })

    except Exception as exc:

        return jsonify({
            "error": str(exc)
        }), 500


# ============================================================
# ESP32 TELEMETRY
# ============================================================

@app.post("/api/telemetry")
def telemetry():

    data = request.get_json(
        silent=True
    ) or {}

    return jsonify({

        "status": "received",

        "message":
            "ESP32 telemetry received",

        "data":
            data,

        "timestamp":
            datetime.now(
                timezone.utc
            ).isoformat()
    })


# ============================================================
# RUN LOCALLY
# ============================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "10000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
