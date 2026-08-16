
import os
import requests

def get_weather(lat, lon):
    key=os.getenv("OPENWEATHER_API_KEY")
    if not key:
        raise RuntimeError("OPENWEATHER_API_KEY is not configured on the server")

    # One Call API access varies by OpenWeather subscription.
    # The endpoint is configurable so the backend remains easy to adapt.
    url="https://api.openweathermap.org/data/3.0/onecall"
    params={
        "lat":lat,
        "lon":lon,
        "appid":key,
        "units":"metric",
        "exclude":"minutely,alerts"
    }
    r=requests.get(url,params=params,timeout=12)
    r.raise_for_status()
    raw=r.json()

    current=raw.get("current",{})
    hourly=raw.get("hourly",[])[:48]

    rain24=sum(float(h.get("rain",{}).get("1h",0) or 0) for h in hourly[:24])
    rain48=sum(float(h.get("rain",{}).get("1h",0) or 0) for h in hourly[24:48])

    def rain_probability(items):
        if not items:
            return 0.0
        return max(float(h.get("pop",0) or 0) for h in items)

    # OpenWeather provides current weather and precipitation forecast;
    # solar irradiance is estimated from cloud/clear-sky conditions here
    # and should be replaced by a dedicated irradiance feed if required
    # for the thesis hardware deployment.
    cloud=float(current.get("clouds",0) or 0)
    solar=max(0.0,1000.0*(1-cloud/100.0))

    return {
        "current_temperature_C":current.get("temp"),
        "current_humidity_pct":current.get("humidity"),
        "solar_irradiance_W_m2":round(solar,1),
        "rain_0_24h_mm":round(rain24,2),
        "rain_probability_0_24h":round(rain_probability(hourly[:24]),3),
        "rain_24_48h_mm":round(rain48,2),
        "rain_probability_24_48h":round(rain_probability(hourly[24:48]),3),
        "raw_source":"OpenWeather",
    }
