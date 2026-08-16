
import os
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR=os.path.join(BASE,"models")
classifier=joblib.load(os.path.join(MODEL_DIR,"aosis_v14_need_classifier.pkl"))
regressor=joblib.load(os.path.join(MODEL_DIR,"aosis_v14_dose_regressor.pkl"))
META=joblib.load(os.path.join(MODEL_DIR,"aosis_v14_metadata.pkl"))

FEATURES=META["features"]
MAX_DEPTH=float(META["max_daily_application_depth_mm"])

def create_schedule(
    soil_moisture_pct, soil_temperature_C, solar_irradiance_W_m2,
    rain_0_24h_mm, rain_probability_0_24h,
    rain_24_48h_mm, rain_probability_24_48h,
    crop_type, crop_age_days, land_size_m2,
    pump_flow_L_min=10.0, application_efficiency=0.75,
    start_time="06:00"
):
    if crop_type not in META["crops"]:
        raise ValueError("crop_type must be Tomato or Pepper")
    if land_size_m2<=0 or pump_flow_L_min<=0:
        raise ValueError("land_size_m2 and pump_flow_L_min must be positive")
    if not 0 < application_efficiency <= 1:
        raise ValueError("application_efficiency must be between 0 and 1")

    X=pd.DataFrame([{
        "soil_moisture_pct":float(soil_moisture_pct),
        "soil_temperature_C":float(soil_temperature_C),
        "solar_irradiance_W_m2":float(solar_irradiance_W_m2),
        "rain_0_24h_mm":float(rain_0_24h_mm),
        "rain_probability_0_24h":float(rain_probability_0_24h),
        "rain_24_48h_mm":float(rain_24_48h_mm),
        "rain_probability_24_48h":float(rain_probability_24_48h),
        "crop_code":META["crops"][crop_type],
        "crop_age_days":float(crop_age_days)
    }])[FEATURES]

    need=str(classifier.predict(X)[0])
    dose=0.0 if need=="LOW" else float(np.clip(regressor.predict(X)[0],0,MAX_DEPTH))

    volume=(dose*float(land_size_m2))/float(application_efficiency)
    runtime=volume/float(pump_flow_L_min)

    h,m=map(int,start_time.split(":"))
    start=datetime(2000,1,1,h,m)
    end=start+timedelta(minutes=runtime)

    return {
        "model_version":META["model_version"],
        "crop":crop_type,
        "crop_age_days":int(crop_age_days),
        "need_level":need,
        "irrigation_depth_mm":round(dose,3),
        "land_size_m2":round(float(land_size_m2),2),
        "water_required_L":round(volume,2),
        "pump_flow_L_min":round(float(pump_flow_L_min),2),
        "pump_runtime_min":round(runtime,2),
        "rain_next_24h_mm":round(float(rain_0_24h_mm),2),
        "rain_next_48h_mm":round(float(rain_24_48h_mm),2),
        "rain_probability_next_48h":round(float(rain_probability_24_48h),2),
        "max_daily_depth_mm":MAX_DEPTH,
        "recommended_start":start.strftime("%H:%M"),
        "recommended_end":end.strftime("%H:%M")
    }
