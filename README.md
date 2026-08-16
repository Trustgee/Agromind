
# Agromind

**AI-Optimized Solar Irrigation Scheduler (AOSIS)**

Agromind is a web-based agricultural decision-support system built around the AOSIS v14 physics-labelled irrigation policy. It combines ESP32-S3 soil observations, OpenWeather forecast information, and Gradient Boosting models to generate a daily irrigation recommendation.

## Current model

- Soil type: clay loam
- Crops: tomato and pepper
- Classifier: Histogram Gradient Boosting — LOW / MEDIUM / HIGH
- Regressor: Histogram Gradient Boosting — daily irrigation depth
- Forecast horizon: 48 hours
- Maximum practical application: 12 mm/day
- LOW class: exactly 0 mm
- Water volume and pump runtime: deterministic calculations from depth, farm area, efficiency and pump flow
- Physics-labelled dataset: 50,000 records
- Validation test accuracy: 98.9% classifier
- Validation regressor R²: 0.9765 on the held-out test set

> These metrics describe the synthetic physics-to-ML surrogate validation. They should not be presented as field-validation accuracy.

## Repository

```text
Agromind/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── models/
│   │   ├── aosis_v14_need_classifier.pkl
│   │   ├── aosis_v14_dose_regressor.pkl
│   │   └── aosis_v14_metadata.pkl
│   └── services/
│       ├── scheduler.py
│       └── weather.py
├── frontend/
│   ├── package.json
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       └── styles.css
├── render.yaml
├── .env.example
└── README.md
```

## Run backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
gunicorn app:app
```

Windows activation:

```powershell
.venv\Scripts\activate
```

## Run frontend

```bash
cd frontend
npm install
npm run dev
```

Set the API URL:

```bash
VITE_API_URL=http://localhost:10000
```

## API

### Health

`GET /api/health`

### Dashboard

`GET /api/dashboard`

### Schedule

`POST /api/schedule`

Example:

```json
{
  "soil_moisture_pct": 42,
  "soil_temperature_C": 28.7,
  "solar_irradiance_W_m2": 620,
  "rain_0_24h_mm": 0,
  "rain_probability_0_24h": 0.10,
  "rain_24_48h_mm": 8,
  "rain_probability_24_48h": 0.75,
  "crop_type": "Tomato",
  "crop_age_days": 60,
  "land_size_m2": 100,
  "pump_flow_L_min": 10,
  "application_efficiency": 0.75,
  "start_time": "06:00"
}
```

### Weather

`GET /api/weather?lat=6.69&lon=-1.62`

The OpenWeather key is server-side only.

## Render deployment

The included `render.yaml` defines:

1. `agromind-api` — Flask/Gunicorn API
2. `agromind-dashboard` — React/Vite static dashboard

Render can connect to a GitHub repository and automatically redeploy a linked branch when changes are pushed. The Flask service uses `pip install -r requirements.txt` and `gunicorn app:app`; the frontend builds to `dist`.

Set these Render environment variables:

### Backend

```text
OPENWEATHER_API_KEY=YOUR_KEY
```

### Frontend

```text
VITE_API_URL=https://YOUR-BACKEND.onrender.com
```

## Hardware integration

The dashboard currently uses a demonstration telemetry endpoint. The next hardware integration should add an authenticated ESP32-S3 endpoint such as:

`POST /api/sensor-data`

with:

```json
{
  "soil_moisture_pct": 42.3,
  "soil_temperature_C": 28.7
}
```

The pump should remain behind a hardware safety layer; the web dashboard should not directly energize a pump without authentication, local fail-safe logic, and manual emergency shutoff.

## Research note

The physics engine remains the authoritative policy used to generate the training labels. The Gradient Boosting models are a computational surrogate of that policy.

The 48-hour forecast is part of the decision logic so the scheduler can avoid unnecessary irrigation when forecast rainfall can contribute to the root-zone water balance.

## License

For academic/project use. Add your preferred license before publishing the repository publicly.
