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

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": "*"
        }
    }
)


# ============================================================
# HELPERS
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def safe_float(value, default=0.0):
    try:

        if value is None:
            return default

        number = float(value)

        if number != number:
            return default

        return number

    except (ValueError, TypeError):

        return default


def safe_int(value, default=0):
    try:

        return int(float(value))

    except (ValueError, TypeError):

        return default


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

    "irrigation_status": "WAITING",

    "last_decision": None
}


# ============================================================
# LAST AI SCHEDULE
# ============================================================

LAST_SCHEDULE = None


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
# WEATHER CONFIGURATION
#
# Weather information comes from the weather service /
# OpenWeather integration.
#
# There is NO rain sensor being used.
# ============================================================

CURRENT_WEATHER = {

    "solar_irradiance_W_m2": 620.0,

    "rain_0_24h_mm": 0.0,

    "rain_probability_0_24h": 0.10,

    "rain_24_48h_mm": 8.0,

    "rain_probability_24_48h": 0.75
}


# ============================================================
# COMMAND ID
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
# BUILD AI SCHEDULER PAYLOAD
# ============================================================

def build_scheduler_payload(
    soil_moisture_pct,
    soil_temperature_C
):

    return {

        "soil_moisture_pct":
            safe_float(
                soil_moisture_pct
            ),

        "soil_temperature_C":
            safe_float(
                soil_temperature_C
            ),

        "solar_irradiance_W_m2":
            safe_float(
                CURRENT_WEATHER[
                    "solar_irradiance_W_m2"
                ]
            ),

        "rain_0_24h_mm":
            safe_float(
                CURRENT_WEATHER[
                    "rain_0_24h_mm"
                ]
            ),

        "rain_probability_0_24h":
            safe_float(
                CURRENT_WEATHER[
                    "rain_probability_0_24h"
                ]
            ),

        "rain_24_48h_mm":
            safe_float(
                CURRENT_WEATHER[
                    "rain_24_48h_mm"
                ]
            ),

        "rain_probability_24_48h":
            safe_float(
                CURRENT_WEATHER[
                    "rain_probability_24_48h"
                ]
            ),

        "crop_type":
            FARM_CONFIG[
                "crop_type"
            ],

        "crop_age_days":
            safe_int(
                FARM_CONFIG[
                    "crop_age_days"
                ]
            ),

        "land_size_m2":
            safe_float(
                FARM_CONFIG[
                    "land_size_m2"
                ]
            ),

        "pump_flow_L_min":
            safe_float(
                FARM_CONFIG[
                    "pump_flow_L_min"
                ]
            ),

        "application_efficiency":
            safe_float(
                FARM_CONFIG[
                    "application_efficiency"
                ]
            ),

        "start_time":
            FARM_CONFIG[
                "start_time"
            ]
    }


# ============================================================
# SAVE IRRIGATION COMMAND
# ============================================================

def save_irrigation_command(
    schedule_result
):

    global IRRIGATION_COMMAND

    pump_runtime_minutes = safe_float(
        schedule_result.get(
            "pump_runtime_min",
            0
        )
    )

    pump_runtime_minutes = max(
        0,
        pump_runtime_minutes
    )


    irrigation_depth = safe_float(
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


    water_required = safe_float(
        schedule_result.get(
            "water_required_L",
            0
        )
    )

    water_required = max(
        0,
        water_required
    )


    # ========================================================
    # INITIAL AI DECISION
    # ========================================================

    irrigate = (

        irrigation_depth > 0

        and pump_runtime_minutes > 0

    )


    irrigation_status = (

        "IRRIGATION APPROVED"

        if irrigate

        else

        "NO IRRIGATION"

    )


    # ========================================================
    # TANK SAFETY
    # ========================================================

    water_level = (
        LATEST_TELEMETRY.get(
            "water_level_pct"
        )
    )


    if water_level is not None:

        try:

            current_water_level = float(
                water_level
            )


            if current_water_level <= 10:

                irrigate = False

                pump_runtime_minutes = 0

                irrigation_status = (
                    "BLOCKED — TANK CRITICALLY LOW"
                )


        except (
            ValueError,
            TypeError
        ):

            pass


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
                "AOSIS-v14"
            ),

        "irrigation_status":
            irrigation_status,

        "last_decision":
            utc_now()
    }


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

    global FARM_CONFIG
    global LAST_SCHEDULE


    data = request.get_json(
        silent=True
    ) or {}


    # ========================================================
    # REQUIRED FIELDS
    # ========================================================

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

        # ====================================================
        # SAVE FARM SETTINGS
        # ====================================================

        FARM_CONFIG[
            "crop_type"
        ] = str(
            data.get(
                "crop_type",
                FARM_CONFIG[
                    "crop_type"
                ]
            )
        )


        FARM_CONFIG[
            "crop_age_days"
        ] = safe_int(
            data.get(
                "crop_age_days",
                FARM_CONFIG[
                    "crop_age_days"
                ]
            )
        )


        FARM_CONFIG[
            "land_size_m2"
        ] = safe_float(
            data.get(
                "land_size_m2",
                FARM_CONFIG[
                    "land_size_m2"
                ]
            )
        )


        FARM_CONFIG[
            "pump_flow_L_min"
        ] = safe_float(
            data.get(
                "pump_flow_L_min",
                FARM_CONFIG[
                    "pump_flow_L_min"
                ]
            )
        )


        FARM_CONFIG[
            "application_efficiency"
        ] = safe_float(
            data.get(
                "application_efficiency",
                FARM_CONFIG[
                    "application_efficiency"
                ]
            )
        )


        FARM_CONFIG[
            "start_time"
        ] = data.get(
            "start_time",
            FARM_CONFIG[
                "start_time"
            ]
        )


        # ====================================================
        # CREATE AI SCHEDULE
        # ====================================================

        result = create_schedule(

            soil_moisture_pct=
                safe_float(
                    data.get(
                        "soil_moisture_pct"
                    )
                ),

            soil_temperature_C=
                safe_float(
                    data.get(
                        "soil_temperature_C"
                    )
                ),

            solar_irradiance_W_m2=
                safe_float(
                    data.get(
                        "solar_irradiance_W_m2"
                    )
                ),

            rain_0_24h_mm=
                safe_float(
                    data.get(
                        "rain_0_24h_mm"
                    )
                ),

            rain_probability_0_24h=
                safe_float(
                    data.get(
                        "rain_probability_0_24h"
                    )
                ),

            rain_24_48h_mm=
                safe_float(
                    data.get(
                        "rain_24_48h_mm"
                    )
                ),

            rain_probability_24_48h=
                safe_float(
                    data.get(
                        "rain_probability_24_48h"
                    )
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


        # ====================================================
        # SAVE SCHEDULE
        # ====================================================

        LAST_SCHEDULE = result


        # ====================================================
        # UPDATE IRRIGATION COMMAND
        # ====================================================

        save_irrigation_command(
            result
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
# ESP32 TELEMETRY
# ============================================================

@app.post("/api/telemetry")
def telemetry():

    global LATEST_TELEMETRY
    global IRRIGATION_COMMAND
    global LAST_SCHEDULE


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
                0

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
            utc_now()

    }


    # ========================================================
    # WATER STATUS
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

            "irrigation_status":
                "FAILSAFE",

            "last_decision":
                utc_now()

        }


        LAST_SCHEDULE = None


        return jsonify({

            "status":
                "received",

            "message":
                "Telemetry received but required sensor data is missing",

            "irrigate":
                False,

            "runtime_seconds":
                0,

            "command_id":
                "FAILSAFE",

            "data":
                LATEST_TELEMETRY

        }), 200


    # ========================================================
    # AI SCHEDULER
    # ========================================================

    try:

        scheduler_payload = build_scheduler_payload(

            soil_moisture_pct=
                data.get(
                    "soil_moisture_pct"
                ),

            soil_temperature_C=
                data.get(
                    "soil_temperature_C"
                )

        )


        schedule_result = create_schedule(
            **scheduler_payload
        )


        LAST_SCHEDULE = (
            schedule_result
        )


        # ====================================================
        # SAVE CURRENT COMMAND
        # ====================================================

        save_irrigation_command(
            schedule_result
        )


    except Exception as exc:

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

            "irrigation_status":
                "AI FAILSAFE",

            "last_decision":
                utc_now()

        }


        LAST_SCHEDULE = None


        return jsonify({

            "status":
                "received",

            "message":
                "Telemetry received but AI scheduling failed",

            "irrigate":
                False,

            "runtime_seconds":
                0,

            "command_id":
                "AI-FAILSAFE",

            "error":
                str(exc),

            "data":
                LATEST_TELEMETRY

        }), 200


    # ========================================================
    # RESPONSE TO ESP32
    # ========================================================

    return jsonify({

        "status":
            "received",

        "message":
            "Telemetry received and irrigation decision generated",

        "server_time":
            utc_now(),

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

        "irrigation_status":
            IRRIGATION_COMMAND[
                "irrigation_status"
            ],

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

    global LAST_SCHEDULE
    global IRRIGATION_COMMAND


    try:

        # ====================================================
        # DETERMINE TELEMETRY SOURCE
        # ====================================================

        esp32_connected = bool(
            LATEST_TELEMETRY.get(
                "connected",
                False
            )
        )


        # ====================================================
        # LIVE ESP32 DATA
        # ====================================================

        if esp32_connected:

            soil_moisture = safe_float(
                LATEST_TELEMETRY.get(
                    "soil_moisture_pct"
                ),
                0.0
            )


            soil_temperature = safe_float(
                LATEST_TELEMETRY.get(
                    "soil_temperature_C"
                ),
                0.0
            )


            humidity = safe_float(
                LATEST_TELEMETRY.get(
                    "humidity_pct"
                ),
                0.0
            )


            water_level = safe_float(
                LATEST_TELEMETRY.get(
                    "water_level_pct"
                ),
                0.0
            )


            water_remaining = safe_float(
                LATEST_TELEMETRY.get(
                    "water_remaining_L"
                ),
                0.0
            )


            telemetry_source = (
                "ESP32-S3"
            )


        else:

            # =================================================
            # DEMO DATA ONLY IF ESP32 HAS NOT CONNECTED
            # =================================================

            soil_moisture = 42.0

            soil_temperature = 28.7

            humidity = 70.0

            water_level = 100.0

            water_remaining = 0.5

            telemetry_source = "DEMO"


        # ====================================================
        # WEATHER
        # ====================================================

        solar_irradiance = safe_float(
            CURRENT_WEATHER.get(
                "solar_irradiance_W_m2"
            ),
            0.0
        )


        rain_0_24 = safe_float(
            CURRENT_WEATHER.get(
                "rain_0_24h_mm"
            ),
            0.0
        )


        rain_probability_0_24 = safe_float(
            CURRENT_WEATHER.get(
                "rain_probability_0_24h"
            ),
            0.0
        )


        rain_24_48 = safe_float(
            CURRENT_WEATHER.get(
                "rain_24_48h_mm"
            ),
            0.0
        )


        rain_probability_24_48 = safe_float(
            CURRENT_WEATHER.get(
                "rain_probability_24_48h"
            ),
            0.0
        )


        # ====================================================
        # FARM CONFIGURATION
        # ====================================================

        crop_type = FARM_CONFIG.get(
            "crop_type",
            "Tomato"
        )


        crop_age_days = safe_int(
            FARM_CONFIG.get(
                "crop_age_days",
                60
            ),
            60
        )


        land_size_m2 = safe_float(
            FARM_CONFIG.get(
                "land_size_m2",
                100
            ),
            100.0
        )


        pump_flow = safe_float(
            FARM_CONFIG.get(
                "pump_flow_L_min",
                10
            ),
            10.0
        )


        efficiency = safe_float(
            FARM_CONFIG.get(
                "application_efficiency",
                0.75
            ),
            0.75
        )


        start_time = FARM_CONFIG.get(
            "start_time",
            "06:00"
        )


        # ====================================================
        # AI SCHEDULE
        #
        # Do not recalculate on every dashboard refresh.
        #
        # A schedule is generated when:
        #
        # 1. ESP32 sends new telemetry
        # 2. Farmer presses Update Recommendation
        #
        # ====================================================

        schedule_result = LAST_SCHEDULE

        schedule_error = None


        # ====================================================
        # CREATE INITIAL SCHEDULE IF NECESSARY
        # ====================================================

        if schedule_result is None:

            try:

                scheduler_payload = {

                    "soil_moisture_pct":
                        soil_moisture,

                    "soil_temperature_C":
                        soil_temperature,

                    "solar_irradiance_W_m2":
                        solar_irradiance,

                    "rain_0_24h_mm":
                        rain_0_24,

                    "rain_probability_0_24h":
                        rain_probability_0_24,

                    "rain_24_48h_mm":
                        rain_24_48,

                    "rain_probability_24_48h":
                        rain_probability_24_48,

                    "crop_type":
                        crop_type,

                    "crop_age_days":
                        crop_age_days,

                    "land_size_m2":
                        land_size_m2,

                    "pump_flow_L_min":
                        pump_flow,

                    "application_efficiency":
                        efficiency,

                    "start_time":
                        start_time

                }


                schedule_result = create_schedule(
                    **scheduler_payload
                )


                LAST_SCHEDULE = (
                    schedule_result
                )


                save_irrigation_command(
                    schedule_result
                )


            except Exception as exc:

                schedule_error = str(
                    exc
                )


                # --------------------------------------------
                # DO NOT CRASH DASHBOARD
                # --------------------------------------------

                schedule_result = {

                    "need_level":
                        "UNKNOWN",

                    "recommendation":
                        "AI SCHEDULE UNAVAILABLE",

                    "irrigation_depth_mm":
                        0,

                    "water_required_L":
                        0,

                    "pump_runtime_min":
                        0,

                    "recommended_start":
                        start_time,

                    "recommended_end":
                        None,

                    "pump_flow_L_min":
                        pump_flow,

                    "model_version":
                        "AOSIS-v14"

                }


        # ====================================================
        # WATER TANK STATUS
        # ====================================================

        tank_critical = (
            water_level <= 10
        )


        tank_low = (
            water_level > 10
            and water_level <= 25
        )


        if tank_critical:

            dashboard_irrigation_status = (
                "BLOCKED — TANK CRITICALLY LOW"
            )

        elif tank_low:

            dashboard_irrigation_status = (
                "WARNING — TANK LOW"
            )

        else:

            dashboard_irrigation_status = (
                "IRRIGATION AVAILABLE"
            )


        # ====================================================
        # WATER STATUS
        # ====================================================

        water_status = (
            LATEST_TELEMETRY.get(
                "water_status"
            )
        )


        if not water_status or water_status == "UNKNOWN":

            if tank_critical:

                water_status = "CRITICAL"

            elif tank_low:

                water_status = "LOW"

            else:

                water_status = "NORMAL"


        # ====================================================
        # DASHBOARD RESPONSE
        # ====================================================

        response = {

            "timestamp":
                utc_now(),


            # =================================================
            # THIS IS CRITICAL FOR THE REACT FRONTEND
            # =================================================

            "telemetry_source":
                telemetry_source,


            # =================================================
            # TELEMETRY
            # =================================================

            "telemetry": {

                "connected":
                    esp32_connected,

                "device_id":
                    LATEST_TELEMETRY.get(
                        "device_id"
                    ),

                "soil_moisture_pct":
                    soil_moisture,

                "soil_temperature_C":
                    soil_temperature,

                "humidity_pct":
                    humidity,

                "soil_adc":
                    LATEST_TELEMETRY.get(
                        "soil_adc"
                    ),

                "water_sensor_adc":
                    LATEST_TELEMETRY.get(
                        "water_sensor_adc"
                    ),

                "water_level_pct":
                    water_level,

                "water_remaining_L":
                    water_remaining,

                "water_status":
                    water_status,

                "last_update":
                    LATEST_TELEMETRY.get(
                        "last_update"
                    ),

                # --------------------------------------------
                # WEATHER IS INCLUDED HERE BECAUSE YOUR
                # REACT FRONTEND READS THESE VALUES FROM
                # telemetry.*
                # --------------------------------------------

                "solar_irradiance_W_m2":
                    solar_irradiance,

                "rain_0_24h_mm":
                    rain_0_24,

                "rain_probability_0_24h":
                    rain_probability_0_24,

                "rain_24_48h_mm":
                    rain_24_48,

                "rain_probability_24_48h":
                    rain_probability_24_48

            },


            # =================================================
            # FARM
            # =================================================

            "farm": {

                "crop":
                    crop_type,

                "crop_type":
                    crop_type,

                "crop_age_days":
                    crop_age_days,

                "land_size_m2":
                    land_size_m2,

                "pump_flow_L_min":
                    pump_flow,

                "application_efficiency":
                    efficiency,

                "start_time":
                    start_time

            },


            # =================================================
            # WEATHER
            # =================================================

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


            # =================================================
            # AI SCHEDULE
            # =================================================

            "schedule":
                schedule_result,


            # =================================================
            # AI SCHEDULE ERROR
            # =================================================

            "schedule_error":
                schedule_error,


            # =================================================
            # TANK SAFETY
            # =================================================

            "irrigation_safety": {

                "status":
                    dashboard_irrigation_status,

                "tank_level_pct":
                    water_level,

                "water_remaining_L":
                    water_remaining,

                "tank_critical":
                    tank_critical,

                "tank_low":
                    tank_low,

                "pump_allowed":
                    not tank_critical,

                "message": (

                    "AI recommends irrigation, "
                    "but pump operation is blocked "
                    "because the water tank is critically low."

                    if tank_critical

                    else

                    "Water tank is low. Irrigation "
                    "should be used cautiously."

                    if tank_low

                    else

                    "Water level is sufficient "
                    "for irrigation."

                )

            },


            # =================================================
            # CURRENT HARDWARE COMMAND
            # =================================================

            "irrigation_command":
                IRRIGATION_COMMAND

        }


        # ====================================================
        # ALWAYS RETURN HTTP 200 FOR A VALID DASHBOARD
        # ====================================================

        return jsonify(
            response
        ), 200


    # ========================================================
    # ABSOLUTE DASHBOARD FAILSAFE
    # ========================================================

    except Exception as exc:

        # ----------------------------------------------------
        # The dashboard should never show the generic Flask
        # Internal Server Error page.
        #
        # Even if something unexpected happens, return the
        # telemetry that we already have.
        # ----------------------------------------------------

        return jsonify({

            "status":
                "dashboard_failsafe",

            "telemetry_source": (

                "ESP32-S3"

                if LATEST_TELEMETRY.get(
                    "connected",
                    False
                )

                else

                "DEMO"

            ),

            "telemetry": {

                "connected":
                    LATEST_TELEMETRY.get(
                        "connected",
                        False
                    ),

                "device_id":
                    LATEST_TELEMETRY.get(
                        "device_id"
                    ),

                "soil_moisture_pct":
                    LATEST_TELEMETRY.get(
                        "soil_moisture_pct"
                    ),

                "soil_temperature_C":
                    LATEST_TELEMETRY.get(
                        "soil_temperature_C"
                    ),

                "humidity_pct":
                    LATEST_TELEMETRY.get(
                        "humidity_pct"
                    ),

                "soil_adc":
                    LATEST_TELEMETRY.get(
                        "soil_adc"
                    ),

                "water_sensor_adc":
                    LATEST_TELEMETRY.get(
                        "water_sensor_adc"
                    ),

                "water_level_pct":
                    LATEST_TELEMETRY.get(
                        "water_level_pct"
                    ),

                "water_remaining_L":
                    LATEST_TELEMETRY.get(
                        "water_remaining_L"
                    ),

                "water_status":
                    LATEST_TELEMETRY.get(
                        "water_status",
                        "UNKNOWN"
                    ),

                "last_update":
                    LATEST_TELEMETRY.get(
                        "last_update"
                    ),

                "solar_irradiance_W_m2":
                    CURRENT_WEATHER.get(
                        "solar_irradiance_W_m2",
                        0
                    ),

                "rain_0_24h_mm":
                    CURRENT_WEATHER.get(
                        "rain_0_24h_mm",
                        0
                    ),

                "rain_probability_0_24h":
                    CURRENT_WEATHER.get(
                        "rain_probability_0_24h",
                        0
                    ),

                "rain_24_48h_mm":
                    CURRENT_WEATHER.get(
                        "rain_24_48h_mm",
                        0
                    ),

                "rain_probability_24_48h":
                    CURRENT_WEATHER.get(
                        "rain_probability_24_48h",
                        0
                    )

            },

            "farm":
                FARM_CONFIG,

            "weather":
                CURRENT_WEATHER,

            "schedule":
                LAST_SCHEDULE,

            "irrigation_command":
                IRRIGATION_COMMAND,

            "error":
                str(exc)

        }), 200


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
