import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Droplets,
  Sun,
  CloudRain,
  Thermometer,
  Leaf,
  RefreshCw,
  Power,
  Map,
} from "lucide-react";
import "./styles.css";

const API_URL =
  import.meta.env.VITE_API_URL ||
  "https://agromind-api-w832.onrender.com";

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [manual, setManual] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(
        `${API_URL}/api/dashboard`,
        {
          cache: "no-store",
        }
      );

      if (!response.ok) {
        throw new Error(
          `Dashboard API returned ${response.status}`
        );
      }

      const result = await response.json();

      console.log("AgroMind API:", result);

      setData(result);
    } catch (err) {
      console.error(err);
      setError(
        err.message || "Unable to load dashboard"
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (loading) {
    return (
      <div className="loading-screen">
        <RefreshCw className="spin" size={24} />
        Loading AgroMind...
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-screen">
        <h2>AgroMind Dashboard</h2>
        <p>{error}</p>

        <button onClick={load}>
          <RefreshCw size={17} />
          Retry
        </button>
      </div>
    );
  }

  const schedule = data?.schedule || {};

  /*
   * YOUR API RETURNS TELEMETRY INSIDE SCHEDULE
   */
  const telemetry = schedule?.telemetry || {};

  /* ================================
     FARM
  ================================= */

  const crop = schedule.crop || "Tomato";

  const cropAge = Number(
    schedule.crop_age_days ?? 0
  );

  const landSize = Number(
    schedule.land_size_m2 ?? 100
  );

  /* ================================
     IRRIGATION
  ================================= */

  const irrigationDepth = Number(
    schedule.irrigation_depth_mm ?? 0
  );

  const needLevel =
    schedule.need_level || "LOW";

  /*
   * IMPORTANT:
   *
   * API uses water_required_L
   * API uses pump_flow_L_min
   *
   * Capital L matters.
   */

  const waterRequired = Number(
    schedule.water_required_L ?? 0
  );

  const pumpFlow = Number(
    schedule.pump_flow_L_min ?? 0
  );

  const pumpRuntime = Number(
    schedule.pump_runtime_min ?? 0
  );

  const recommendedStart =
    schedule.recommended_start || "06:00";

  const recommendedEnd =
    schedule.recommended_end || "08:24";

  /* ================================
     RAIN
  ================================= */

  const rain24 = Number(
    schedule.rain_next_24h_mm ?? 0
  );

  const rain48 = Number(
    schedule.rain_next_48h_mm ?? 0
  );

  const rainProbability = Number(
    schedule.rain_probability_next_48h ?? 0
  );

  /* ================================
     TELEMETRY
  ================================= */

  const soilMoisture = Number(
    telemetry.soil_moisture_pct ?? 0
  );

  const soilTemperature = Number(
    telemetry.soil_temperature_C ?? 0
  );

  const solarIrradiance = Number(
    telemetry.solar_irradiance_W_m2 ?? 0
  );

  const applicationEfficiency = Number(
    telemetry.application_efficiency ?? 0.75
  );

  const rainProbability24 = Number(
    telemetry.rain_probability_0_24h ?? 0
  );

  const rainProbability48 = Number(
    telemetry.rain_probability_24_48h ?? 0
  );

  const modelVersion =
    schedule.model_version || "AOSIS-v14";

  /* ================================
     HELPERS
  ================================= */

  function formatNumber(value, decimals = 0) {
    const n = Number(value);

    if (!Number.isFinite(n)) {
      return "0";
    }

    return n.toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }

  const rainProbabilityPercent = Math.round(
    rainProbability * 100
  );

  const rain24Percent = Math.round(
    rainProbability24 * 100
  );

  const rain48Percent = Math.round(
    rainProbability48 * 100
  );

  return (
    <div className="app">

      {/* =========================
          SIDEBAR
      ========================== */}

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-mark">
            A
          </div>

          <div>
            <strong>Agromind</strong>
            <span>Smart Agriculture</span>
          </div>

        </div>

        <nav>

          <a className="active">
            Overview
          </a>

          <a>
            Farm Map
          </a>

          <a>
            Irrigation
          </a>

          <a>
            Weather
          </a>

          <a>
            Plant Health
          </a>

        </nav>

        <div className="status-card">

          <span>
            <span className="status-dot"></span>
            Online
          </span>

          <small>
            {modelVersion} • {crop}
          </small>

        </div>

      </aside>


      {/* =========================
          MAIN
      ========================== */}

      <main>

        <header className="topbar">

          <div>

            <div className="eyebrow">
              AI-OPTIMIZED IRRIGATION
            </div>

            <h1>
              Good morning, Farmer.
            </h1>

            <p>
              Here's what your farm needs today.
            </p>

          </div>

          <button
            className="refresh"
            onClick={load}
          >
            <RefreshCw size={17} />
            Refresh
          </button>

        </header>


        {/* =========================
            RECOMMENDATION
        ========================== */}

        <section className="hero">

          <div className="hero-left">

            <div className="eyebrow">
              TODAY'S IRRIGATION RECOMMENDATION
            </div>

            <div className="recommendation">

              <span className="need-badge">
                Need {needLevel}
              </span>

              <h2>
                {formatNumber(
                  irrigationDepth,
                  3
                )} mm
              </h2>

              <p>
                Recommended daily application depth
              </p>

            </div>

            <div className="hero-actions">

              <button
                className="primary-button"
                onClick={() => setManual(true)}
              >
                <Droplets size={18} />
                Irrigate Now
              </button>

              <button
                className="secondary-button"
                onClick={() =>
                  document
                    .getElementById("schedule")
                    ?.scrollIntoView({
                      behavior: "smooth",
                    })
                }
              >
                View Schedule
                <span>›</span>
              </button>

            </div>

          </div>


          <div className="water-display">

            <Droplets size={40} />

            <strong>
              {formatNumber(
                waterRequired,
                2
              )}
            </strong>

            <span>
              Litres
            </span>

          </div>

        </section>


        {/* =========================
            SENSOR CARDS
        ========================== */}

        <section className="metrics">

          <Metric
            icon={<Droplets />}
            label="Soil Moisture"
            value={formatNumber(
              soilMoisture
            )}
            unit="%"
            sub="Live sensor"
          />

          <Metric
            icon={<Thermometer />}
            label="Soil Temperature"
            value={formatNumber(
              soilTemperature,
              1
            )}
            unit="°C"
            sub="ESP32-S3"
          />

          <Metric
            icon={<Sun />}
            label="Solar Irradiance"
            value={formatNumber(
              solarIrradiance
            )}
            unit="W/m²"
            sub="OpenWeather"
          />

          <Metric
            icon={<CloudRain />}
            label="Rain - 48 hours"
            value={formatNumber(
              rain48,
              1
            )}
            unit="mm"
            sub={`${rainProbabilityPercent}% probability`}
          />

        </section>


        {/* =========================
            FORECAST + FARM
        ========================== */}

        <div className="two-column">

          <section className="panel">

            <div className="panel-header">

              <div>
                <h3>
                  48-hour forecast
                </h3>

                <span>
                  Rainfall-aware scheduling
                </span>
              </div>

              <CloudRain size={20} />

            </div>

            <div className="forecast">

              <div className="forecast-item">

                <span>
                  Next 24h
                </span>

                <strong>
                  {formatNumber(
                    rain24,
                    1
                  )} mm
                </strong>

                <small>
                  {rain24Percent}%
                  probability
                </small>

              </div>

              <div className="forecast-item">

                <span>
                  24–48h
                </span>

                <strong>
                  {formatNumber(
                    rain48,
                    1
                  )} mm
                </strong>

                <small>
                  {rain48Percent}%
                  probability
                </small>

              </div>

            </div>

            <div className="insight">

              <Leaf size={18} />

              <span>
                AgroMind considers expected
                rainfall before calculating
                today's minimum irrigation dose.
              </span>

            </div>

          </section>


          {/* FARM VISUALIZATION */}

          <section className="panel">

            <div className="panel-header">

              <div>

                <h3>
                  Farm visualization
                </h3>

                <span>
                  {landSize} m² • {crop}
                </span>

              </div>

              <Map size={20} />

            </div>

            <div className="farm">

              {Array.from(
                { length: 24 },
                (_, index) => (
                  <div
                    key={index}
                    className="farm-zone"
                  >
                    <span>
                      {index + 1}
                    </span>
                  </div>
                )
              )}

            </div>

            <div className="farm-label">

              <strong>
                ZONE A
              </strong>

              <span>
                Live monitoring
              </span>

            </div>

          </section>

        </div>


        {/* =========================
            PUMP WINDOW
        ========================== */}

        <section
          className="schedulebar"
          id="schedule"
        >

          <div>

            <span className="eyebrow">
              TODAY'S PUMP WINDOW
            </span>

            <strong>
              {recommendedStart}
              {" – "}
              {recommendedEnd}
            </strong>

            <small>

              {formatNumber(
                pumpRuntime,
                2
              )} minutes

              {" • "}

              {formatNumber(
                pumpFlow,
                1
              )} L/min

              {" • "}

              {formatNumber(
                waterRequired,
                2
              )} L

            </small>

          </div>

          <button
            onClick={() => setManual(true)}
          >

            <Power size={17} />

            Manual Override

          </button>

        </section>


        {/* =========================
            DETAILS
        ========================== */}

        <section className="details-grid">

          <div className="detail-card">

            <span>
              Crop
            </span>

            <strong>
              {crop}
            </strong>

          </div>

          <div className="detail-card">

            <span>
              Crop age
            </span>

            <strong>
              {cropAge} days
            </strong>

          </div>

          <div className="detail-card">

            <span>
              Application efficiency
            </span>

            <strong>
              {Math.round(
                applicationEfficiency * 100
              )}%
            </strong>

          </div>

          <div className="detail-card">

            <span>
              Model
            </span>

            <strong>
              {modelVersion}
            </strong>

          </div>

        </section>

      </main>


      {/* =========================
          MANUAL MODAL
      ========================== */}

      {manual && (

        <div
          className="modal"
          onClick={() => setManual(false)}
        >

          <div
            className="modal-box"
            onClick={(e) =>
              e.stopPropagation()
            }
          >

            <h2>
              Manual Irrigation
            </h2>

            <p>
              Review the recommended irrigation
              amount before starting the pump.
            </p>

            <div className="manual-summary">

              <span>
                Recommended amount
              </span>

              <strong>
                {formatNumber(
                  waterRequired,
                  2
                )} L
              </strong>

            </div>

            <div className="manual-summary">

              <span>
                Pump runtime
              </span>

              <strong>
                {formatNumber(
                  pumpRuntime,
                  2
                )} minutes
              </strong>

            </div>

            <div className="modal-actions">

              <button
                className="secondary-button"
                onClick={() =>
                  setManual(false)
                }
              >
                Cancel
              </button>

              <button
                className="primary-button"
                onClick={() => {
                  alert(
                    "Manual irrigation command ready for pump controller."
                  );

                  setManual(false);
                }}
              >

                <Power size={17} />

                Start Irrigation

              </button>

            </div>

          </div>

        </div>

      )}

    </div>
  );
}


/* ================================
   METRIC COMPONENT
================================ */

function Metric({
  icon,
  label,
  value,
  unit,
  sub,
}) {
  return (
    <div className="metric">

      <div className="metric-icon">
        {icon}
      </div>

      <div className="metric-content">

        <span>
          {label}
        </span>

        <strong>

          {value}

          <small>
            {unit}
          </small>

        </strong>

        <em>
          {sub}
        </em>

      </div>

    </div>
  );
}


/* ================================
   REACT ROOT
================================ */

createRoot(
  document.getElementById("root")
).render(
  <App />
);
