
# Agromind Architecture

```text
ESP32-S3
   │
   ├── soil moisture
   └── soil temperature
          │
          ▼
     Agromind API
          │
          ├── OpenWeather
          │    ├── forecast rain 0–24 h
          │    ├── forecast rain 24–48 h
          │    └── weather inputs
          │
          ▼
  Gradient Boosting Classifier
          │
      LOW / MEDIUM / HIGH
          │
       LOW → 0 mm
          │
     MEDIUM/HIGH
          ▼
  Gradient Boosting Regressor
          │
       ≤ 12 mm/day
          │
          ▼
  volume + runtime calculation
          │
          ▼
     React dashboard
```

The deployed API is responsible for secrets and model inference. The browser never receives the OpenWeather secret.

The pump-control layer should ultimately be local to the ESP32-S3 or another authenticated controller so internet loss cannot create unsafe pump behavior.
