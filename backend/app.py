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
# PROJECT CONFIGURATION
# ============================================================

MODEL_VERSION = "AOSIS-v14"


# ============================================================
# KNUST / KUMASI FARM LOCATION
# ============================================================

FARM_CONFIG = {

    # KNUST, Kumasi
    "latitude": 6.6747,
    "longitude": -1.5717,

    # Farm configuration
    "crop_type": "Tomato",
    "crop_age_days": 60,
    "land_size_m2": 100.0,

    # Pump
    "pump_flow_L_min": 10.0,

    # Irrigation efficiency
    "application_efficiency": 0.75,

    # Preferred irrigation start
    "start_time": "06:00"
}


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
# LATEST WEATHER
# ============================================================

LATEST_WEATHER = {

    "available": False,

    "latitude":
        FARM_CONFIG["latitude"],

    "longitude":
        FARM_CONFIG["longitude"],

    "current_temperature_C": None,

    "current_humidity_pct": None,

    "current_rain_mm": 0.0,

    "solar_irradiance_W_m2": 0.0,

    "rain_0_24h_mm": 0.0,

    "rain_probability_0_24h": 0.0,

    "rain_24_48h_mm": 0.0,

    "rain_probability_24_48h": 0.0,

    "weather": "",

    "weather_description": "",

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

    "model_version": MODEL_VERSION,

    "last_decision": None
}


# ============================================================
# COMMAND ID GENERATOR
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
# FAIL-SAFE COMMAND
# ============================================================

def set_failsafe_command(
    reason="FAILSAFE"
):

    global IRRIGATION_COMMAND

    IRRIGATION_COMMAND = {

        "command_id":
            reason,

        "irrigate":
            False,

        "runtime_seconds":
            0,

        "runtime_minutes":
            0,

        "need_level":
            "UNKNOWN",

        "recommendation":
            reason,

        "water_required_L":
            0,

        "irrigation_depth_mm":
            0,

        "recommended_start":
            None,

        "recommended_end":
            None,

        "model_version":
            MODEL_VERSION,

        "last_decision":
            datetime.now(
                timezone.utc
            ).isoformat()
    }


# ============================================================
# GET LIVE OPENWEATHER DATA
# ============================================================

def update_weather():

    global LATEST_WEATHER

    try:

        weather = get_weather(

            FARM_CONFIG["latitude"],

            FARM_CONFIG["longitude"]

        )

        LATEST_WEATHER = {

            "available":
                True,

            "latitude":
                weather.get(
                    "latitude",
                    FARM_CONFIG["latitude"]
                ),

            "longitude":
                weather.get(
                    "longitude",
                    FARM_CONFIG["longitude"]
                ),

            "current_temperature_C":
                weather.get(
                    "current_temperature_C"
                ),

            "current_humidity_pct":
                weather.get(
                    "current_humidity_pct"
                ),

            "current_rain_mm":
                weather.get(
                    "current_rain_mm",
                    0
                ),

            "solar_irradiance_W_m2":
                weather.get(
                    "solar_irradiance_W_m2",
                    0
                ),

            "rain_0_24h_mm":
                weather.get(
                    "rain_0_24h_mm",
                    0
                ),

            "rain_probability_0_24h":
                weather.get(
                    "rain_probability_0_24h",
                    0
                ),

            "rain_24_48h_mm":
                weather.get(
                    "rain_24_48h_mm",
                    0
                ),

            "rain_probability_24_48h":
                weather.get(
                    "rain_probability_24_48h",
                    0
                ),

            "weather":
                weather.get(
                    "weather",
                    ""
                ),

            "weather_description":
                weather.get(
                    "weather_description",
                    ""
                ),

            "last_update":
                datetime.now(
                    timezone.utc
                ).isoformat()
        }

        return True

    except Exception as exc:

        print(
            "[WEATHER] Error:",
            str(exc)
        )

        LATEST_WEATHER[
            "available"
        ] = False

        return False


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
            MODEL_VERSION,

        "status":
            "online",

        "location":
            "KNUST, Kumasi, Ghana",

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
            MODEL_VERSION,

        "esp32_connected":
            LATEST_TELEMETRY[
                "connected"
            ],

        "weather_available":
            LATEST_WEATHER[
                "available"
            ],

        "pump_command":
            IRRIGATION_COMMAND[
                "irrigate"
            ]
    })


# ============================================================
# MANUAL SCHEDULE API
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
# WEATHER API
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

    # --------------------------------------------------------
    # If coordinates are not supplied, use KNUST.
    # --------------------------------------------------------

    if lat is None:
        lat = FARM_CONFIG["latitude"]

    if lon is None:
        lon = FARM_CONFIG["longitude"]

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
# ESP32 TELEMETRY
# ============================================================

@app.post("/api/telemetry")
def telemetry():

    global LATEST_TELEMETRY
    global IRRIGATION_COMMAND


    # ========================================================
    # RECEIVE ESP32 JSON
    # ========================================================

    data = request.get_json(
        silent=True
    ) or {}

    if not data:

        set_failsafe_command(
            "EMPTY_TELEMETRY"
        )

        return jsonify({

            "status":
                "error",

            "message":
                "No telemetry data received",

            "irrigate":
                False,

            "runtime_seconds":
                0,

            "command_id":
                "EMPTY_TELEMETRY"

        }), 400


    # ========================================================
    # SAVE TELEMETRY
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
    # WATER LEVEL STATUS
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

    if (

        data.get(
            "soil_moisture_pct"
        ) is None

        or

        data.get(
            "soil_temperature_C"
        ) is None

    ):

        set_failsafe_command(
            "INVALID_SENSOR_DATA"
        )

        return jsonify({

            "status":
                "received",

            "message":
                "Required sensor data is missing",

            "irrigate":
                False,

            "runtime_seconds":
                0,

            "command_id":
                "INVALID_SENSOR_DATA",

            "data":
                LATEST_TELEMETRY

        })


    # ========================================================
    # GET LIVE WEATHER
    # ========================================================

    weather_success = update_weather()


    if not weather_success:

        # ----------------------------------------------------
        # SAFETY:
        # Do not make an automatic irrigation decision if
        # the weather service is unavailable.
        # ----------------------------------------------------

        set_failsafe_command(
            "WEATHER_FAILSAFE"
        )

        return jsonify({

            "status":
                "received",

            "message":
                "Weather data unavailable; irrigation disabled",

            "irrigate":
                False,

            "runtime_seconds":
                0,

            "command_id":
                "WEATHER_FAILSAFE",

            "data":
                LATEST_TELEMETRY

        })


    # ========================================================
    # BUILD AI INPUT
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
                    LATEST_WEATHER[
                        "solar_irradiance_W_m2"
                    ]
                ),

            rain_0_24h_mm=
                float(
                    LATEST_WEATHER[
                        "rain_0_24h_mm"
                    ]
                ),

            rain_probability_0_24h=
                float(
                    LATEST_WEATHER[
                        "rain_probability_0_24h"
                    ]
                ),

            rain_24_48h_mm=
                float(
                    LATEST_WEATHER[
                        "rain_24_48h_mm"
                    ]
                ),

            rain_probability_24_48h=
                float(
                    LATEST_WEATHER[
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

        print(
            "[AI] Scheduler error:",
            str(exc)
        )

        set_failsafe_command(
            "AI_FAILSAFE"
        )

        return jsonify({

            "status":
                "received",

            "message":
                "AI scheduler failed",

            "irrigate":
                False,

            "runtime_seconds":
                0,

            "command_id":
                "AI_FAILSAFE",

            "error":
                str(exc),

            "data":
                LATEST_TELEMETRY

        })


    # ========================================================
    # EXTRACT AI OUTPUT
    # ========================================================

    irrigation_depth = max(

        0.0,

        float(
            schedule_result.get(
                "irrigation_depth_mm",
                0
            )
        )

    )


    pump_runtime_minutes = max(

        0.0,

        float(
            schedule_result.get(
                "pump_runtime_min",
                0
            )
        )

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


    water_required = max(

        0.0,

        float(
            schedule_result.get(
                "water_required_L",
                0
            )
        )

    )


    # ========================================================
    # AUTOMATIC IRRIGATION RULE
    # ========================================================
    #
    # IMPORTANT:
    #
    # The physical pump is only authorized when:
    #
    # 1. AI says HIGH
    # 2. Irrigation depth > 0
    # 3. Runtime > 0
    # 4. Tank has sufficient water
    #
    # MEDIUM and LOW remain OFF.
    #

    irrigate = (

        need_level == "HIGH"

        and irrigation_depth > 0

        and pump_runtime_minutes > 0

    )


    # ========================================================
    # WATER LEVEL SAFETY
    # ========================================================

    try:

        if water_level is not None:

            current_water_level = float(
                water_level
            )

            if current_water_level <= 10:

                irrigate = False

                pump_runtime_minutes = 0

    except (
        ValueError,
        TypeError
    ):

        irrigate = False

        pump_runtime_minutes = 0


    # ========================================================
    # RUNTIME
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
    # SAVE COMMAND
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
                MODEL_VERSION
            ),

        "last_decision":
            datetime.now(
                timezone.utc
            ).isoformat()
    }


    # ========================================================
    # RETURN COMMAND TO ESP32
    # ========================================================

    return jsonify({

        "status":
            "received",

        "message":
            "Telemetry received and irrigation decision generated",

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
        # AI RESULT
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
        # WEATHER
        # ----------------------------------------------------

        "weather":
            LATEST_WEATHER,

        # ----------------------------------------------------
        # ESP32 TELEMETRY
        # ----------------------------------------------------

        "data":
            LATEST_TELEMETRY
    })


# ============================================================
# GET CURRENT TELEMETRY
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
    # TELEMETRY
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

        soil_moisture = 42.0
        soil_temperature = 28.7
        humidity = 70.0
        water_level = 100.0
        water_remaining = 0.5

        telemetry_source = "DEMO"


    # ========================================================
    # UPDATE WEATHER
    # ========================================================

    update_weather()


    # ========================================================
    # AI SCHEDULE
    # ========================================================

    try:

        schedule_result = create_schedule(

            soil_moisture_pct=
                float(
                    soil_moisture
                ),

            soil_temperature_C=
                float(
                    soil_temperature
                ),

            solar_irradiance_W_m2=
                float(
                    LATEST_WEATHER[
                        "solar_irradiance_W_m2"
                    ]
                ),

            rain_0_24h_mm=
                float(
                    LATEST_WEATHER[
                        "rain_0_24h_mm"
                    ]
                ),

            rain_probability_0_24h=
                float(
                    LATEST_WEATHER[
                        "rain_probability_0_24h"
                    ]
                ),

            rain_24_48h_mm=
                float(
                    LATEST_WEATHER[
                        "rain_24_48h_mm"
                    ]
                ),

            rain_probability_24_48h=
                float(
                    LATEST_WEATHER[
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

        return jsonify({

            "error":
                "Unable to generate irrigation schedule",

            "details":
                str(exc)

        }), 500


    # ========================================================
    # RETURN DASHBOARD
    # ========================================================

    return jsonify({

        "timestamp":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "telemetry_source":
            telemetry_source,

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

        "farm": {

            "location":
                "KNUST, Kumasi, Ghana",

            "latitude":
                FARM_CONFIG[
                    "latitude"
                ],

            "longitude":
                FARM_CONFIG[
                    "longitude"
                ],

            "crop":
                FARM_CONFIG[
                    "crop_type"
                ],

            "crop_age_days":
                FARM_CONFIG[
                    "crop_age_days"
                ],

            "land_size_m2":
                FARM_CONFIG[
                    "land_size_m2"
                ]
        },

        "weather":
            LATEST_WEATHER,

        "schedule":
            schedule_result,

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
