import os
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


# ============================================================
# PATHS / MODELS
# ============================================================

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE, "models")

classifier = joblib.load(
    os.path.join(MODEL_DIR, "aosis_v14_need_classifier.pkl")
)

regressor = joblib.load(
    os.path.join(MODEL_DIR, "aosis_v14_dose_regressor.pkl")
)

META = joblib.load(
    os.path.join(MODEL_DIR, "aosis_v14_metadata.pkl")
)

FEATURES = META["features"]
MODEL_VERSION = META.get("model_version", "AOSIS-v14")


# ============================================================
# AGRONOMIC SAFETY LIMITS
# ============================================================
#
# These limits prevent the ML model from recommending an
# unrealistic daily application depth.
#
# They are safety limits, NOT replacements for the ML model.
# The ML model still determines the initial irrigation need.
#

CROP_MAX_DEPTH_MM = {
    "Tomato": 7.0,
    "Pepper": 7.0,
}

DEFAULT_MAX_DEPTH_MM = 7.0


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clamp(value, minimum, maximum):
    return max(minimum, min(float(value), maximum))


def calculate_rain_adjustment(
    rain_0_24h_mm,
    rain_probability_0_24h,
    rain_24_48h_mm,
    rain_probability_24_48h
):
    """
    Reduce irrigation when meaningful rainfall is expected.

    Returns a multiplier between 0 and 1.

    1.00 = no reduction
    0.70 = 30% reduction
    0.50 = 50% reduction
    0.00 = irrigation cancelled
    """

    rain_now = float(rain_0_24h_mm)
    rain_now_probability = float(rain_probability_0_24h)

    rain_later = float(rain_24_48h_mm)
    rain_later_probability = float(rain_probability_24_48h)

    # --------------------------------------------------------
    # Strong rainfall expected in the next 24 hours
    # --------------------------------------------------------

    if rain_now >= 5.0 and rain_now_probability >= 0.70:
        return 0.0

    if rain_now >= 3.0 and rain_now_probability >= 0.60:
        return 0.30

    # --------------------------------------------------------
    # Meaningful rainfall expected between 24–48 hours
    # --------------------------------------------------------

    if rain_later >= 10.0 and rain_later_probability >= 0.70:
        return 0.40

    if rain_later >= 5.0 and rain_later_probability >= 0.65:
        return 0.70

    return 1.00


def calculate_soil_adjustment(soil_moisture_pct):
    """
    Adjust irrigation based on measured soil moisture.

    Very wet soil:
        irrigation is reduced.

    Normal soil:
        no adjustment.

    Very dry soil:
        full recommended dose.
    """

    moisture = float(soil_moisture_pct)

    if moisture >= 70:
        return 0.0

    if moisture >= 60:
        return 0.30

    if moisture >= 50:
        return 0.70

    return 1.00


def calculate_schedule_times(start_time, runtime_minutes):
    """
    Convert start time + runtime into readable start/end times.
    """

    try:
        hours, minutes = map(int, start_time.split(":"))
    except Exception:
        raise ValueError("start_time must be in HH:MM format")

    if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
        raise ValueError("start_time must be a valid 24-hour time")

    start = datetime(2000, 1, 1, hours, minutes)
    end = start + timedelta(minutes=float(runtime_minutes))

    return (
        start.strftime("%H:%M"),
        end.strftime("%H:%M")
    )


# ============================================================
# MAIN SCHEDULER
# ============================================================

def create_schedule(
    soil_moisture_pct,
    soil_temperature_C,
    solar_irradiance_W_m2,

    rain_0_24h_mm,
    rain_probability_0_24h,

    rain_24_48h_mm,
    rain_probability_24_48h,

    crop_type,
    crop_age_days,
    land_size_m2,

    pump_flow_L_min=10.0,
    application_efficiency=0.75,

    start_time="06:00"
):

    # ========================================================
    # INPUT VALIDATION
    # ========================================================

    if crop_type not in META["crops"]:
        allowed_crops = ", ".join(META["crops"].keys())

        raise ValueError(
            f"crop_type must be one of: {allowed_crops}"
        )

    if float(land_size_m2) <= 0:
        raise ValueError("land_size_m2 must be positive")

    if float(pump_flow_L_min) <= 0:
        raise ValueError("pump_flow_L_min must be positive")

    if not 0 < float(application_efficiency) <= 1:
        raise ValueError(
            "application_efficiency must be between 0 and 1"
        )

    if float(crop_age_days) < 0:
        raise ValueError("crop_age_days cannot be negative")

    # ========================================================
    # CLEAN SENSOR / WEATHER VALUES
    # ========================================================

    soil_moisture = clamp(
        soil_moisture_pct,
        0,
        100
    )

    soil_temperature = float(soil_temperature_C)

    solar_irradiance = max(
        0,
        float(solar_irradiance_W_m2)
    )

    rain_0_24 = max(
        0,
        float(rain_0_24h_mm)
    )

    rain_prob_0_24 = clamp(
        rain_probability_0_24h,
        0,
        1
    )

    rain_24_48 = max(
        0,
        float(rain_24_48h_mm)
    )

    rain_prob_24_48 = clamp(
        rain_probability_24_48h,
        0,
        1
    )

    crop_age = float(crop_age_days)
    land_size = float(land_size_m2)
    flow_rate = float(pump_flow_L_min)
    efficiency = float(application_efficiency)

    # ========================================================
    # BUILD MACHINE-LEARNING INPUT
    # ========================================================

    X = pd.DataFrame([{
        "soil_moisture_pct": soil_moisture,

        "soil_temperature_C": soil_temperature,

        "solar_irradiance_W_m2": solar_irradiance,

        "rain_0_24h_mm": rain_0_24,

        "rain_probability_0_24h": rain_prob_0_24,

        "rain_24_48h_mm": rain_24_48,

        "rain_probability_24_48h": rain_prob_24_48,

        "crop_code": META["crops"][crop_type],

        "crop_age_days": crop_age
    }])[FEATURES]

    # ========================================================
    # AI IRRIGATION NEED CLASSIFICATION
    # ========================================================

    need = str(
        classifier.predict(X)[0]
    ).upper()

    # Normalize possible model labels
    if need in ["LOW", "LOW NEED"]:
        need = "LOW"

    elif need in ["MEDIUM", "MEDIUM NEED"]:
        need = "MEDIUM"

    elif need in ["HIGH", "HIGH NEED"]:
        need = "HIGH"

    # ========================================================
    # AI DOSE PREDICTION
    # ========================================================

    raw_model_dose = float(
        regressor.predict(X)[0]
    )

    raw_model_dose = max(
        0.0,
        raw_model_dose
    )

    # ========================================================
    # AGRONOMIC SAFETY CAP
    # ========================================================

    crop_max_depth = CROP_MAX_DEPTH_MM.get(
        crop_type,
        DEFAULT_MAX_DEPTH_MM
    )

    # Also respect metadata limit if it exists.
    metadata_max = float(
        META.get("max_daily_application_depth_mm", crop_max_depth)
    )

    safe_max_depth = min(
        crop_max_depth,
        metadata_max
    )

    # Prevent model from producing excessive daily depth.
    base_dose = min(
        raw_model_dose,
        safe_max_depth
    )

    # ========================================================
    # LOW IRRIGATION NEED
    # ========================================================

    if need == "LOW":
        base_dose = 0.0

    # ========================================================
    # SOIL MOISTURE ADJUSTMENT
    # ========================================================

    soil_adjustment = calculate_soil_adjustment(
        soil_moisture
    )

    dose_after_soil = (
        base_dose * soil_adjustment
    )

    # ========================================================
    # RAINFALL ADJUSTMENT
    # ========================================================

    rain_adjustment = calculate_rain_adjustment(
        rain_0_24,
        rain_prob_0_24,
        rain_24_48,
        rain_prob_24_48
    )

    final_dose = (
        dose_after_soil * rain_adjustment
    )

    # ========================================================
    # FINAL SAFETY CLAMP
    # ========================================================

    final_dose = clamp(
        final_dose,
        0,
        safe_max_depth
    )

    # Avoid meaningless tiny irrigation values.
    if final_dose < 0.10:
        final_dose = 0.0

    # ========================================================
    # WATER REQUIREMENT
    # ========================================================
    #
    # 1 mm over 1 m² = 1 litre
    #
    # Example:
    #
    # 5 mm × 100 m² = 500 L net
    #
    # At 75% efficiency:
    #
    # 500 / 0.75 = 666.67 L
    #

    net_water_litres = (
        final_dose * land_size
    )

    gross_water_litres = (
        net_water_litres / efficiency
    )

    # ========================================================
    # PUMP RUNTIME
    # ========================================================

    runtime_minutes = (
        gross_water_litres / flow_rate
    )

    # ========================================================
    # SCHEDULE TIMES
    # ========================================================

    recommended_start, recommended_end = (
        calculate_schedule_times(
            start_time,
            runtime_minutes
        )
    )

    # ========================================================
    # HUMAN-READABLE STATUS
    # ========================================================

    if final_dose == 0:
        recommendation = "NO IRRIGATION"

    elif need == "HIGH":
        recommendation = "HIGH IRRIGATION REQUIREMENT"

    elif need == "MEDIUM":
        recommendation = "MEDIUM IRRIGATION REQUIREMENT"

    else:
        recommendation = "LOW IRRIGATION REQUIREMENT"

    # ========================================================
    # RETURN RESULT
    # ========================================================

    return {

        # ----------------------------------------------------
        # MODEL
        # ----------------------------------------------------

        "model_version": MODEL_VERSION,

        "recommendation": recommendation,

        "need_level": need,

        # ----------------------------------------------------
        # CROP / FARM
        # ----------------------------------------------------

        "crop": crop_type,

        "crop_age_days": int(crop_age),

        "land_size_m2": round(
            land_size,
            2
        ),

        # ----------------------------------------------------
        # IRRIGATION
        # ----------------------------------------------------

        "irrigation_depth_mm": round(
            final_dose,
            3
        ),

        "raw_model_depth_mm": round(
            raw_model_dose,
            3
        ),

        "safe_max_depth_mm": round(
            safe_max_depth,
            3
        ),

        "water_required_L": round(
            gross_water_litres,
            2
        ),

        # ----------------------------------------------------
        # PUMP
        # ----------------------------------------------------

        "pump_flow_L_min": round(
            flow_rate,
            2
        ),

        "pump_runtime_min": round(
            runtime_minutes,
            2
        ),

        "recommended_start": recommended_start,

        "recommended_end": recommended_end,

        # ----------------------------------------------------
        # WEATHER
        # ----------------------------------------------------

        "rain_next_24h_mm": round(
            rain_0_24,
            2
        ),

        "rain_probability_next_24h": round(
            rain_prob_0_24,
            2
        ),

        "rain_next_48h_mm": round(
            rain_24_48,
            2
        ),

        "rain_probability_next_48h": round(
            rain_prob_24_48,
            2
        ),

        # ----------------------------------------------------
        # SENSOR INFORMATION
        # ----------------------------------------------------

        "soil_moisture_pct": round(
            soil_moisture,
            1
        ),

        "soil_temperature_C": round(
            soil_temperature,
            1
        ),

        "solar_irradiance_W_m2": round(
            solar_irradiance,
            1
        ),

        # ----------------------------------------------------
        # CALCULATION INFORMATION
        # ----------------------------------------------------

        "application_efficiency": round(
            efficiency,
            2
        ),

        "soil_adjustment": round(
            soil_adjustment,
            2
        ),

        "rain_adjustment": round(
            rain_adjustment,
            2
        ),

        "max_daily_depth_mm": round(
            safe_max_depth,
            3
        )
    }
