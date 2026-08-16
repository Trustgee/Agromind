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
# LATEST ESP32 TELEMETRY
# ============================================================

LATEST_TELEMETRY = {
    "connected": False,

    "device_id": None,

    "soil_moisture_pct": None,
    "soil_adc": None,

    "soil_temperature_C": None,
    "humidity_pct": None,

    "water_sensor_adc": None,
    "water_level_pct": None,
    "water_remaining_L": None,

    "water_status": "UNKNOWN",

    "last_update": None
}


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return jsonify({
        "project": "Agromind",
        "system": "AI-Optimized Solar Irrigation Scheduler",
        "version": "AOSIS-v14",
        "status": "online",
        "esp32_connected": LATEST_TELEMETRY["connected"]
    })


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():

    return jsonify({
        "status": "healthy",
        "version": "AOSIS-v14",
        "esp32_connected":
            LATEST_TELEMETRY["connected"]
    })


# ============================================================
# AI IRRIGATION SCHEDULE
# ============================================================

@app.post("/api/schedule")
def schedule():

    data = request.get_json(
        silent=True
    ) or {}

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
        key
        for key in required
        if key not in data
    ]

    if missing:

        return jsonify({
            "error": "Missing fields",
            "fields": missing
        }), 400

    try:

        result = create_schedule(
            **data
        )

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
# ESP32 TELEMETRY
# ============================================================

@app.post("/api/telemetry")
def telemetry():

    global LATEST_TELEMETRY

    data = request.get_json(
        silent=True
    ) or {}

    if not data:

        return jsonify({
            "status": "error",
            "message": "No telemetry data received"
        }), 400


    # --------------------------------------------------------
    # Save ESP32 readings
    # --------------------------------------------------------

    LATEST_TELEMETRY = {

        "connected": True,

        "device_id":
            data.get(
                "device_id",
                "AGROMIND-ESP32-S3"
            ),

        "soil_moisture_pct":
            data.get(
                "soil_moisture_pct"
            ),

        "soil_adc":
            data.get(
                "soil_adc"
            ),

        "soil_temperature_C":
            data.get(
                "soil_temperature_C"
            ),

        "humidity_pct":
            data.get(
                "humidity_pct"
            ),

        "water_sensor_adc":
            data.get(
                "water_sensor_adc"
            ),

        "water_level_pct":
            data.get(
                "water_level_pct"
            ),

        "water_remaining_L":
            data.get(
                "water_remaining_L"
            ),

        "water_status": "UNKNOWN",

        "last_update":
            datetime.now(
                timezone.utc
            ).isoformat()
    }


    # --------------------------------------------------------
    # Water tank status
    # --------------------------------------------------------

    water_level = data.get(
        "water_level_pct"
    )

    try:

        if water_level is not None:

            water_level = float(
                water_level
            )

            if water_level <= 10:

                LATEST_TELEMETRY[
                    "water_status"
                ] = "CRITICAL"

            elif water_level <= 25:

                LATEST_TELEMETRY[
                    "water_status"
                ] = "LOW"

            else:

                LATEST_TELEMETRY[
                    "water_status"
                ] = "NORMAL"

    except (
        ValueError,
        TypeError
    ):

        LATEST_TELEMETRY[
            "water_status"
        ] = "UNKNOWN"


    # --------------------------------------------------------
    # Respond to ESP32
    # --------------------------------------------------------

    return jsonify({

        "status": "received",

        "message":
            "ESP32 telemetry received successfully",

        "server_time":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "data":
            LATEST_TELEMETRY
    })


# ============================================================
# GET CURRENT ESP32 TELEMETRY
# ============================================================

@app.get("/api/telemetry")
def get_telemetry():

    return jsonify(
        LATEST_TELEMETRY
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/api/dashboard")
def dashboard():

    # ========================================================
    # REAL ESP32 DATA
    # ========================================================

    if LATEST_TELEMETRY["connected"]:

        soil_moisture = (
            LATEST_TELEMETRY[
                "soil_moisture_pct"
            ]
        )

        soil_temperature = (
            LATEST_TELEMETRY[
                "soil_temperature_C"
            ]
        )

        humidity = (
            LATEST_TELEMETRY[
                "humidity_pct"
            ]
        )

        water_level = (
            LATEST_TELEMETRY[
                "water_level_pct"
            ]
        )

        water_remaining = (
            LATEST_TELEMETRY[
                "water_remaining_L"
            ]
        )

        telemetry_source = "ESP32-S3"

    else:

        # ----------------------------------------------------
        # Fallback demo values
        # ----------------------------------------------------

        soil_moisture = 42.0
        soil_temperature = 28.7
        humidity = 70.0

        water_level = 100.0
        water_remaining = 0.5

        telemetry_source = "DEMO"


    # ========================================================
    # FARM CONFIGURATION
    # ========================================================
    #
    # Crop type, crop age and land size are NOT sensor values.
    #
    # They come from the farmer's farm configuration.
    #
    # We will later connect these to your frontend controls.
    #

    crop_type = "Tomato"
    crop_age_days = 60
    land_size_m2 = 100.0


    # ========================================================
    # WEATHER / IRRADIANCE
    # ========================================================
    #
    # Rainfall comes from OpenWeather.
    #
    # Solar irradiance is currently a demo value.
    # We can connect your actual solar sensor later.
    #

    solar_irradiance = 620.0

    rain_0_24 = 0.0
    rain_probability_0_24 = 0.10

    rain_24_48 = 8.0
    rain_probability_24_48 = 0.75


    # ========================================================
    # AI SCHEDULER INPUT
    # ========================================================

    payload = {

        "soil_moisture_pct":
            float(
                soil_moisture
            ),

        "soil_temperature_C":
            float(
                soil_temperature
            ),

        "solar_irradiance_W_m2":
            float(
                solar_irradiance
            ),

        "rain_0_24h_mm":
            float(
                rain_0_24
            ),

        "rain_probability_0_24h":
            float(
                rain_probability_0_24
            ),

        "rain_24_48h_mm":
            float(
                rain_24_48
            ),

        "rain_probability_24_48h":
            float(
                rain_probability_24_48
            ),

        "crop_type":
            crop_type,

        "crop_age_days":
            crop_age_days,

        "land_size_m2":
            land_size_m2,

        "pump_flow_L_min":
            10.0,

        "application_efficiency":
            0.75,

        "start_time":
            "06:00"
    }


    # ========================================================
    # CREATE AI SCHEDULE
    # ========================================================

    try:

        schedule_result = create_schedule(
            **payload
        )

    except Exception as exc:

        return jsonify({

            "error":
                "Unable to generate irrigation schedule",

            "details":
                str(exc)

        }), 500


    # ========================================================
    # RETURN DASHBOARD DATA
    # ========================================================

    return jsonify({

        "timestamp":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "telemetry_source":
            telemetry_source,


        # ----------------------------------------------------
        # SENSOR DATA
        # ----------------------------------------------------

        "telemetry": {

            "soil_moisture_pct":
                soil_moisture,

            "soil_temperature_C":
                soil_temperature,

            "humidity_pct":
                humidity,

            "water_level_pct":
                water_level,

            "water_remaining_L":
                water_remaining,

            "water_status":
                LATEST_TELEMETRY.get(
                    "water_status",
                    "UNKNOWN"
                ),

            "water_sensor_adc":
                LATEST_TELEMETRY.get(
                    "water_sensor_adc"
                ),

            "soil_adc":
                LATEST_TELEMETRY.get(
                    "soil_adc"
                ),

            "last_update":
                LATEST_TELEMETRY.get(
                    "last_update"
                )
        },


        # ----------------------------------------------------
        # FARM
        # ----------------------------------------------------

        "farm": {

            "crop":
                crop_type,

            "crop_age_days":
                crop_age_days,

            "land_size_m2":
                land_size_m2
        },


        # ----------------------------------------------------
        # WEATHER
        # ----------------------------------------------------

        "weather": {

            "rain_next_24h_mm":
                rain_0_24,

            "rain_probability_next_24h":
                rain_probability_0_24,

            "rain_next_48h_mm":
                rain_24_48,

            "rain_probability_next_48h":
                rain_probability_24_48,

            "solar_irradiance_W_m2":
                solar_irradiance
        },


        # ----------------------------------------------------
        # AI SCHEDULE
        # ----------------------------------------------------

        "schedule":
            schedule_result
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
