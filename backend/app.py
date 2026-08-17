import os
import hashlib
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
# LATEST IRRIGATION COMMAND
# ============================================================

IRRIGATION_COMMAND = {

    "command_id": "NONE",

    "irrigate": False,

    "runtime_seconds": 0,

    "runtime_minutes": 0,

    "need_level": "UNKNOWN",

    "recommendation": "NO IRRIGATION",

    "water_required_L": 0,

    "irrigation_depth_mm": 0,

    "recommended_start": None,

    "recommended_end": None,

    "model_version": "AOSIS-v14",

    "last_decision": None
}


# ============================================================
# FARM CONFIGURATION
# ============================================================

FARM_CONFIG = {

    "crop_type": "Tomato",

    "crop_age_days": 60,

    "land_size_m2": 100.0,

    "pump_flow_L_min": 10.0,

    "application_efficiency": 0.75,

    "start_time": "06:00"
}


# ============================================================
# WEATHER / SOLAR CONFIGURATION
# ============================================================
#
# Rainfall is currently supplied by the weather configuration.
#
# The /api/weather endpoint below uses the OpenWeather service
# implemented in services/weather.py.
#
# These values are retained as fallback/demo values for the
# scheduler until live weather values are connected directly
# to this telemetry cycle.
# ============================================================

CURRENT_WEATHER = {

    "solar_irradiance_W_m2": 620.0,

    "rain_0_24h_mm": 0.0,

    "rain_probability_0_24h": 0.10,

    "rain_24_48h_mm": 8.0,

    "rain_probability_24_48h": 0.75
}


# ============================================================
# HELPER — COMMAND ID
# ============================================================

def generate_command_id(
    irrigate,
    runtime_seconds,
    need_level,
    irrigation_depth_mm,
    water_required_L
):

    raw = (

        f"{irrigate}|"
        f"{runtime_seconds}|"
        f"{need_level}|"
        f"{irrigation_depth_mm}|"
        f"{water_required_L}"

    )

    return hashlib.sha256(
        raw.encode()
    ).hexdigest()[:12]


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return jsonify({

        "project":
            "Agromind",

        "system":
            "AI-Optimized Solar Irrigation Scheduler",

        "version":
            "AOSIS-v14",

        "status":
            "online",

        "esp32_connected":
            LATEST_TELEMETRY[
                "connected"
            ],

        "irrigation_command":
            IRRIGATION_COMMAND

    })


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():

    return jsonify({

        "status":
            "healthy",

        "version":
            "AOSIS-v14",

        "esp32_connected":
            LATEST_TELEMETRY[
                "connected"
            ],

        "pump_command":
            IRRIGATION_COMMAND[
                "irrigate"
            ]

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

            "error":
                "Missing fields",

            "fields":
                missing

        }), 400

    try:

        result = create_schedule(
            **data
        )

        return jsonify(
            result
        )

    except Exception as exc:

        return jsonify({

            "error":
                str(exc)

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

            "error":
                "lat and lon are required"

        }), 400

    try:

        result = get_weather(
            lat,
            lon
        )

        return jsonify(
            result
        )

    except Exception as exc:

        return jsonify({

            "error":
                str(exc)

        }), 502


# ============================================================
# ESP32 TELEMETRY + AI IRRIGATION CONTROL
# ============================================================

@app.post("/api/telemetry")
def telemetry():

    global LATEST_TELEMETRY
    global IRRIGATION_COMMAND

    # ========================================================
    # RECEIVE JSON
    # ========================================================

    data = request.get_json(
        silent=True
    ) or {}

    if not data:

        return jsonify({

            "status":
                "error",

            "message":
                "No telemetry data received",

            "irrigate":
                False,

            "runtime_seconds":
                0,

            "need_level":
                "UNKNOWN",

            "command_id":
                "FAILSAFE"

        }), 400


    # ========================================================
    # SAVE ESP32 TELEMETRY
    # ========================================================

    LATEST_TELEMETRY = {

        "connected":
            True,

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

        "water_status":
            "UNKNOWN",

        "last_update":
            datetime.now(
                timezone.utc
            ).isoformat()
    }


    # ========================================================
    # WATER TANK STATUS
    # ========================================================

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


    # ========================================================
    # REQUIRED SENSOR VALIDATION
    # ========================================================

    required_sensor_values = [

        "soil_moisture_pct",

        "soil_temperature_C"
    ]

    missing_sensor_values = [

        key
        for key in required_sensor_values
        if data.get(key) is None

    ]

    if missing_sensor_values:

        IRRIGATION_COMMAND = {

            "command_id":
                "FAILSAFE",

            "irrigate":
                False,

            "runtime_seconds":
                0,

            "runtime_minutes":
                0,

            "need_level":
                "UNKNOWN",

            "recommendation":
                "INVALID SENSOR DATA",

            "water_required_L":
                0,

            "irrigation_depth_mm":
                0,

            "recommended_start":
                None,

            "recommended_end":
                None,

            "model_version":
                "AOSIS-v14",

            "last_decision":
                datetime.now(
                    timezone.utc
                ).isoformat()
        }

        return jsonify({

            "status":
                "received",

            "message":
                "Telemetry received but required sensor data is missing",

            "irrigate":
                False,

            "runtime_seconds":
                0,

            "need_level":
                "UNKNOWN",

            "command_id":
                "FAILSAFE",

            "data":
                LATEST_TELEMETRY

        }), 200


    # ========================================================
    # AI SCHEDULER
    # ========================================================

    try:

        schedule_result = create_schedule(

            soil_moisture_pct=
                float(
                    data[
                        "soil_moisture_pct"
                    ]
                ),

            soil_temperature_C=
                float(
                    data[
                        "soil_temperature_C"
                    ]
                ),

            solar_irradiance_W_m2=
                float(
                    CURRENT_WEATHER[
                        "solar_irradiance_W_m2"
                    ]
                ),

            rain_0_24h_mm=
                float(
                    CURRENT_WEATHER[
                        "rain_0_24h_mm"
                    ]
                ),

            rain_probability_0_24h=
                float(
                    CURRENT_WEATHER[
                        "rain_probability_0_24h"
                    ]
                ),

            rain_24_48h_mm=
                float(
                    CURRENT_WEATHER[
                        "rain_24_48h_mm"
                    ]
                ),

            rain_probability_24_48h=
                float(
                    CURRENT_WEATHER[
                        "rain_probability_24_48h"
                    ]
                ),

            crop_type=
                FARM_CONFIG[
                    "crop_type"
                ],

            crop_age_days=
                FARM_CONFIG[
                    "crop_age_days"
                ],

            land_size_m2=
                FARM_CONFIG[
                    "land_size_m2"
                ],

            pump_flow_L_min=
                FARM_CONFIG[
                    "pump_flow_L_min"
                ],

            application_efficiency=
                FARM_CONFIG[
                    "application_efficiency"
                ],

            start_time=
                FARM_CONFIG[
                    "start_time"
                ]
        )

    except Exception as exc:

        # ----------------------------------------------------
        # AI FAILURE = PUMP OFF
        # ----------------------------------------------------

        IRRIGATION_COMMAND = {

            "command_id":
                "AI-FAILSAFE",

            "irrigate":
                False,

            "runtime_seconds":
                0,

            "runtime_minutes":
                0,

            "need_level":
                "UNKNOWN",

            "recommendation":
                "AI SCHEDULER ERROR",

            "water_required_L":
                0,

            "irrigation_depth_mm":
                0,

            "recommended_start":
                None,

            "recommended_end":
                None,

            "model_version":
                "AOSIS-v14",

            "last_decision":
                datetime.now(
                    timezone.utc
                ).isoformat()
        }

        return jsonify({

            "status":
                "received",

            "message":
                "Telemetry received but AI scheduling failed",

            "irrigate":
                False,

            "runtime_seconds":
                0,

            "need_level":
                "UNKNOWN",

            "command_id":
                "AI-FAILSAFE",

            "error":
                str(exc),

            "data":
                LATEST_TELEMETRY

        }), 200


    # ========================================================
    # EXTRACT AI RESULT
    # ========================================================

    pump_runtime_minutes = float(

        schedule_result.get(
            "pump_runtime_min",
            0
        )

    )

    pump_runtime_minutes = max(
        0,
        pump_runtime_minutes
    )


    irrigation_depth = float(

        schedule_result.get(
            "irrigation_depth_mm",
            0
        )

    )

    irrigation_depth = max(
        0,
        irrigation_depth
    )


    need_level = str(

        schedule_result.get(
            "need_level",
            "LOW"
        )

    ).upper()


    recommendation = schedule_result.get(

        "recommendation",

        "NO IRRIGATION"

    )


    water_required = float(

        schedule_result.get(
            "water_required_L",
            0
        )

    )


    # ========================================================
    # AI CONTROL DECISION
    # ========================================================
    #
    # IMPORTANT:
    #
    # The ESP32 pump is authorized ONLY when the AI
    # scheduler classifies the irrigation requirement as HIGH.
    #
    # LOW    -> Pump OFF
    # MEDIUM -> Pump OFF
    # HIGH   -> Pump ON if runtime > 0
    #
    # This keeps the AI model responsible for the irrigation
    # decision rather than making the ESP32 independently
    # determine irrigation need.
    # ========================================================

    irrigate = (

        need_level == "HIGH"

        and irrigation_depth > 0

        and pump_runtime_minutes > 0

    )


    # ========================================================
    # CRITICAL WATER LEVEL SAFETY
    # ========================================================
    #
    # Even if the AI says HIGH, the pump must NOT operate
    # when the tank is critically low.
    # ========================================================

    try:

        if water_level is not None:

            current_water_level = float(
                water_level
            )

            if current_water_level <= 10:

                irrigate = False

                pump_runtime_minutes = 0

                recommendation = (
                    "IRRIGATION CANCELLED - "
                    "CRITICAL WATER LEVEL"
                )

    except (
        ValueError,
        TypeError
    ):

        # Invalid tank reading = safe state

        irrigate = False

        pump_runtime_minutes = 0

        recommendation = (
            "IRRIGATION CANCELLED - "
            "INVALID WATER LEVEL"
        )


    # ========================================================
    # RUNTIME CONVERSION
    # ========================================================

    runtime_seconds = int(

        round(
            pump_runtime_minutes * 60
        )

    )


    if not irrigate:

        runtime_seconds = 0


    # ========================================================
    # COMMAND ID
    # ========================================================

    command_id = generate_command_id(

        irrigate,

        runtime_seconds,

        need_level,

        round(
            irrigation_depth,
            3
        ),

        round(
            water_required,
            2
        )

    )


    # ========================================================
    # SAVE IRRIGATION COMMAND
    # ========================================================

    IRRIGATION_COMMAND = {

        "command_id":
            command_id,

        "irrigate":
            bool(
                irrigate
            ),

        "runtime_seconds":
            runtime_seconds,

        "runtime_minutes":
            round(
                runtime_seconds / 60,
                2
            ),

        "need_level":
            need_level,

        "recommendation":
            recommendation,

        "water_required_L":
            round(
                water_required,
                2
            ),

        "irrigation_depth_mm":
            round(
                irrigation_depth,
                3
            ),

        "recommended_start":
            schedule_result.get(
                "recommended_start"
            ),

        "recommended_end":
            schedule_result.get(
                "recommended_end"
            ),

        "model_version":
            schedule_result.get(
                "model_version",
                "AOSIS-v14"
            ),

        "last_decision":
            datetime.now(
                timezone.utc
            ).isoformat()
    }


    # ========================================================
    # SEND AI COMMAND BACK TO ESP32
    # ========================================================

    return jsonify({

        "status":
            "received",

        "message":
            "Telemetry received and AI irrigation decision generated",

        "server_time":
            datetime.now(
                timezone.utc
            ).isoformat(),

        # ----------------------------------------------------
        # HARDWARE COMMAND
        # ----------------------------------------------------

        "command_id":
            IRRIGATION_COMMAND[
                "command_id"
            ],

        "irrigate":
            IRRIGATION_COMMAND[
                "irrigate"
            ],

        "runtime_seconds":
            IRRIGATION_COMMAND[
                "runtime_seconds"
            ],

        "runtime_minutes":
            IRRIGATION_COMMAND[
                "runtime_minutes"
            ],

        # ----------------------------------------------------
        # AI INFORMATION
        # ----------------------------------------------------

        "need_level":
            IRRIGATION_COMMAND[
                "need_level"
            ],

        "recommendation":
            IRRIGATION_COMMAND[
                "recommendation"
            ],

        "water_required_L":
            IRRIGATION_COMMAND[
                "water_required_L"
            ],

        "irrigation_depth_mm":
            IRRIGATION_COMMAND[
                "irrigation_depth_mm"
            ],

        "recommended_start":
            IRRIGATION_COMMAND[
                "recommended_start"
            ],

        "recommended_end":
            IRRIGATION_COMMAND[
                "recommended_end"
            ],

        "model_version":
            IRRIGATION_COMMAND[
                "model_version"
            ],

        # ----------------------------------------------------
        # TELEMETRY
        # ----------------------------------------------------

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
# GET CURRENT IRRIGATION COMMAND
# ============================================================

@app.get("/api/control")
def get_control():

    return jsonify(
        IRRIGATION_COMMAND
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
        # DEMO VALUES
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

    crop_type = FARM_CONFIG[
        "crop_type"
    ]

    crop_age_days = FARM_CONFIG[
        "crop_age_days"
    ]

    land_size_m2 = FARM_CONFIG[
        "land_size_m2"
    ]


    # ========================================================
    # WEATHER
    # ========================================================

    solar_irradiance = CURRENT_WEATHER[
        "solar_irradiance_W_m2"
    ]

    rain_0_24 = CURRENT_WEATHER[
        "rain_0_24h_mm"
    ]

    rain_probability_0_24 = CURRENT_WEATHER[
        "rain_probability_0_24h"
    ]

    rain_24_48 = CURRENT_WEATHER[
        "rain_24_48h_mm"
    ]

    rain_probability_24_48 = CURRENT_WEATHER[
        "rain_probability_24_48h"
    ]


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
            FARM_CONFIG[
                "pump_flow_L_min"
            ],

        "application_efficiency":
            FARM_CONFIG[
                "application_efficiency"
            ],

        "start_time":
            FARM_CONFIG[
                "start_time"
            ]
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
            schedule_result,


        # ----------------------------------------------------
        # CURRENT HARDWARE COMMAND
        # ----------------------------------------------------

        "irrigation_command":
            IRRIGATION_COMMAND

    })


# ============================================================
# RUN LOCALLY / RENDER
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
