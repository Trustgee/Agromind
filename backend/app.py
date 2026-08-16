import os
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

from services.scheduler import create_schedule
from services.weather import get_weather


app = Flask(__name__)
CORS(app)


# ============================================================
# BASIC ROUTES
# ============================================================

@app.get("/")
def root():
    return jsonify({
        "project": "Agromind",
        "system": "AI-Optimized Solar Irrigation Scheduler",
        "version": "AOSIS-v14",
        "status": "online"
    })


@app.get("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "version": "AOSIS-v14"
    })


# ============================================================
# IRRIGATION SCHEDULE
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
        field for field in required
        if field not in data
    ]

    if missing:
        return jsonify({
            "error": "Missing fields",
            "fields": missing
        }), 400

    try:

        # ----------------------------------------------------
        # Basic validation
        # ----------------------------------------------------

        crop_type = str(data["crop_type"]).strip()

        crop_age_days = float(data["crop_age_days"])
        land_size_m2 = float(data["land_size_m2"])

        if crop_age_days < 0:
            return jsonify({
                "error": "Crop age cannot be negative"
            }), 400

        if land_size_m2 <= 0:
            return jsonify({
                "error": "Land size must be greater than 0"
            }), 400

        # ----------------------------------------------------
        # Normalise values
        # ----------------------------------------------------

        data["crop_type"] = crop_type
        data["crop_age_days"] = crop_age_days
        data["land_size_m2"] = land_size_m2

        # ----------------------------------------------------
        # Generate AI irrigation schedule
        # ----------------------------------------------------

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

    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)

    if lat is None or lon is None:
        return jsonify({
            "error": "lat and lon are required"
        }), 400

    try:

        return jsonify(
            get_weather(lat, lon)
        )

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
    # Default farm configuration
    # --------------------------------------------------------

    crop_type = request.args.get(
        "crop_type",
        default="Tomato"
    )

    crop_age_days = request.args.get(
        "crop_age_days",
        default=60,
        type=float
    )

    land_size_m2 = request.args.get(
        "land_size_m2",
        default=100,
        type=float
    )

    # --------------------------------------------------------
    # Demo sensor telemetry
    #
    # Replace these with ESP32 telemetry later.
    # --------------------------------------------------------

    payload = {

        "soil_moisture_pct": 42.0,

        "soil_temperature_C": 28.7,

        "solar_irradiance_W_m2": 620.0,

        "rain_0_24h_mm": 0.0,

        "rain_probability_0_24h": 0.10,

        "rain_24_48h_mm": 8.0,

        "rain_probability_24_48h": 0.75,

        "crop_type": crop_type,

        "crop_age_days": crop_age_days,

        "land_size_m2": land_size_m2,

        "pump_flow_L_min": 10.0,

        "application_efficiency": 0.75,

        "start_time": "06:00"
    }

    try:

        result = create_schedule(**payload)

        return jsonify({

            "timestamp":
                datetime.now(timezone.utc).isoformat(),

            "telemetry":
                payload,

            "schedule":
                result

        })

    except Exception as exc:

        return jsonify({
            "error": str(exc)
        }), 400


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv("PORT", "10000")
        )
    )        "rain_24_48h_mm":8.0,
        "rain_probability_24_48h":0.75,
        "crop_type":"Tomato",
        "crop_age_days":60,
        "land_size_m2":100.0,
        "pump_flow_L_min":10.0,
        "application_efficiency":0.75,
        "start_time":"06:00"
    }
    result=create_schedule(**payload)
    return jsonify({
        "timestamp":datetime.now(timezone.utc).isoformat(),
        "telemetry":payload,
        "schedule":result
    })

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","10000")))
