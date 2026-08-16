import os
import requests


OPENWEATHER_CURRENT_URL = (
    "https://api.openweathermap.org/data/4.0/onecall/current"
)

OPENWEATHER_HOURLY_URL = (
    "https://api.openweathermap.org/data/4.0/onecall/timeline/1h"
)


def get_weather(lat, lon):

    # ---------------------------------------------------------
    # GET API KEY FROM RENDER ENVIRONMENT
    # ---------------------------------------------------------

    key = os.getenv("OPENWEATHER_API_KEY")

    if not key:
        raise RuntimeError(
            "OPENWEATHER_API_KEY is not configured on the server"
        )

    # Common parameters
    params = {
        "lat": lat,
        "lon": lon,
        "appid": key,
        "units": "metric",
    }

    # =========================================================
    # 1. CURRENT WEATHER
    # =========================================================

    current_response = requests.get(
        OPENWEATHER_CURRENT_URL,
        params=params,
        timeout=12
    )

    current_response.raise_for_status()

    current_raw = current_response.json()

    # One Call 4.0 returns current weather inside data[]
    current_data = (
        current_raw.get("data", [{}])[0]
    )

    # =========================================================
    # 2. HOURLY WEATHER FORECAST
    # =========================================================

    hourly = []

    next_url = OPENWEATHER_HOURLY_URL

    while len(hourly) < 48 and next_url:

        # First request uses normal parameters.
        if next_url == OPENWEATHER_HOURLY_URL:

            hourly_response = requests.get(
                next_url,
                params=params,
                timeout=12
            )

        # Pagination URLs returned by OpenWeather already
        # contain the required parameters.
        else:

            hourly_response = requests.get(
                next_url,
                timeout=12
            )

        hourly_response.raise_for_status()

        hourly_raw = hourly_response.json()

        batch = hourly_raw.get("data", [])

        hourly.extend(batch)

        next_url = hourly_raw.get("next")

    # Only keep the first 48 hours
    hourly = hourly[:48]

    # =========================================================
    # 3. RAINFALL HELPER
    # =========================================================

    def get_rain_mm(item):

        rain = item.get("rain", {})

        if isinstance(rain, dict):

            value = rain.get("1h", 0)

            try:
                return float(value or 0)
            except (TypeError, ValueError):
                return 0.0

        return 0.0

    # =========================================================
    # 4. RAINFALL FOR NEXT 24 HOURS
    # =========================================================

    rain24 = sum(
        get_rain_mm(hour)
        for hour in hourly[:24]
    )

    # =========================================================
    # 5. RAINFALL FOR HOURS 24–48
    # =========================================================

    rain48 = sum(
        get_rain_mm(hour)
        for hour in hourly[24:48]
    )

    # =========================================================
    # 6. RAIN PROBABILITY
    # =========================================================

    def rain_probability(items):

        if not items:
            return 0.0

        probabilities = []

        for item in items:

            try:
                pop = float(
                    item.get("pop", 0) or 0
                )

                probabilities.append(pop)

            except (TypeError, ValueError):
                pass

        if not probabilities:
            return 0.0

        # OpenWeather POP is 0–1.
        # Convert to percentage.
        return max(probabilities) * 100.0

    rain_probability_24 = rain_probability(
        hourly[:24]
    )

    rain_probability_48 = rain_probability(
        hourly[24:48]
    )

    # =========================================================
    # 7. CURRENT WEATHER DESCRIPTION
    # =========================================================

    weather_info = current_data.get(
        "weather",
        []
    )

    if weather_info:

        weather_main = weather_info[0].get(
            "main",
            ""
        )

        weather_description = weather_info[0].get(
            "description",
            ""
        )

        weather_icon = weather_info[0].get(
            "icon",
            ""
        )

    else:

        weather_main = ""
        weather_description = ""
        weather_icon = ""

    # =========================================================
    # 8. CURRENT CLOUD COVER
    # =========================================================

    clouds = float(
        current_data.get(
            "clouds",
            0
        ) or 0
    )

    # =========================================================
    # 9. ESTIMATED SOLAR IRRADIANCE
    # =========================================================
    #
    # This is an estimate based on cloud cover.
    #
    # Later, when your BH1750 sensor is connected,
    # this value can be replaced with the actual
    # hardware measurement.
    #

    solar_irradiance = max(
        0.0,
        1000.0 * (
            1.0 - clouds / 100.0
        )
    )

    # =========================================================
    # 10. CURRENT RAIN
    # =========================================================

    current_rain = get_rain_mm(
        current_data
    )

    # =========================================================
    # 11. RETURN AGROMIND WEATHER DATA
    # =========================================================

    return {

        # Location
        "latitude": lat,
        "longitude": lon,

        # Current weather
        "current_temperature_C": current_data.get(
            "temp"
        ),

        "current_humidity_pct": current_data.get(
            "humidity"
        ),

        "feels_like_C": current_data.get(
            "feels_like"
        ),

        "pressure_hPa": current_data.get(
            "pressure"
        ),

        "clouds_pct": current_data.get(
            "clouds"
        ),

        "visibility_m": current_data.get(
            "visibility"
        ),

        "wind_speed_m_s": current_data.get(
            "wind_speed"
        ),

        "wind_direction_deg": current_data.get(
            "wind_deg"
        ),

        # Weather condition
        "weather": weather_main,

        "weather_description": weather_description,

        "weather_icon": weather_icon,

        # Current rainfall
        "current_rain_mm": round(
            current_rain,
            2
        ),

        # Solar estimate
        "solar_irradiance_W_m2": round(
            solar_irradiance,
            1
        ),

        # Rain forecast
        "rain_0_24h_mm": round(
            rain24,
            2
        ),

        "rain_probability_0_24h": round(
            rain_probability_24,
            1
        ),

        "rain_24_48h_mm": round(
            rain48,
            2
        ),

        "rain_probability_24_48h": round(
            rain_probability_48,
            1
        ),

        # Number of forecast records successfully retrieved
        "forecast_hours_available": len(
            hourly
        ),

        # Source
        "raw_source": "OpenWeather One Call 4.0"
    }
