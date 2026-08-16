import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Droplets,
  Sun,
  CloudRain,
  Thermometer,
  Leaf,
  Map,
  RefreshCw,
  Power,
  ChevronRight,
} from "lucide-react";

import "./styles.css";

const API =
  import.meta.env.VITE_API_URL ||
  "https://agromind-api-w832.onrender.com";

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [manual, setManual] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API}/api/dashboard`);

      if (!response.ok) {
        throw new Error("Dashboard API unavailable");
      }

      const json = await response.json();
      setData(json);
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to load dashboard");
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  /*
   * Safe fallback values.
   * These prevent the dashboard from crashing if the backend
   * temporarily doesn't return a particular field.
   */

  const telemetry = data?.telemetry || {};
  const schedule = data?.schedule || {};

  const soilMoisture = telemetry.soil_moisture_pct ?? 0;
  const soilTemperature = telemetry.soil_temperature_C ?? 0;
  const solarIrradiance = telemetry.solar_irradiance_W_m2 ?? 0;

  const rain24 = telemetry.rain_0_24h_mm ?? 0;
  const rain48 = telemetry.rain_24_48h_mm ?? 0;

  const rainProbability24 =
    telemetry.rain_probability_0_24h ?? 0;

  const rainProbability48 =
    telemetry.rain_probability_24_48h ?? 0;

  const crop = telemetry.crop_type || "Tomato";
  const landSize = telemetry.land_size_m2 ?? 100;

  const recommendedStart =
    schedule.recommended_start || "06:00";

  const recommendedEnd =
    schedule.recommended_end || "--";

  const waterRequired =
    schedule.water_required_L ?? 0;

  const pumpRuntime =
    schedule.pump_runtime_min ?? 0;

  const pumpFlow =
    schedule.pump_flow_L_min ?? 0;

  const needLevel =
    schedule.need_level ||
    schedule.irrigation_need ||
    "Unknown";

  return (
    <div className="app">

      {/* SIDEBAR */}
      <aside className="sidebar">

        <div className="brand">
          <div className="brandmark">A</div>

          <div>
            <b>Agromind</b>
            <span>Smart Agriculture</span>
          </div>
        </div>

        <nav>
          <a className="active">Overview</a>
          <a>Farm Map</a>
          <a>Irrigation</a>
          <a>Weather</a>
          <a>Plant Health</a>
        </nav>

        <div className="sidecard">
          <span>
            ● <strong>Online</strong>
          </span>

          <small>
            AOSIS v14 · Clay loam
          </small>
        </div>

      </aside>


      {/* MAIN */}
      <main>

        {/* HEADER */}
        <header>

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
            disabled={loading}
          >
            <RefreshCw size={16} />

            {loading ? "Updating..." : "Refresh"}
          </button>

        </header>


        {/* ERROR */}
        {error && (
          <div className="error">
            <strong>Dashboard connection problem</strong>
            <span>{error}</span>
          </div>
        )}


        {/* HERO */}
        <section className="hero">

          <div className="hero-content">

            <div className="eyebrow">
              TODAY'S IRRIGATION RECOMMENDATION
            </div>

            <div className="recommendation">

              <span className="dot"></span>

              <b>Need</b>

              <span>
                {needLevel}
              </span>

            </div>

            <h2>
              {schedule.irrigation_depth_mm ?? "--"} mm
            </h2>

            <small>
              Recommended daily application depth
            </small>

          </div>


          <div className="hero-actions">

            <button
              onClick={() => setManual(true)}
            >
              <Droplets size={17} />
              Irrigate Now
            </button>

            <button
              className="ghost"
              onClick={() =>
                document
                  .querySelector(".schedulebar")
                  ?.scrollIntoView({
                    behavior: "smooth",
                  })
              }
            >
              View Schedule
              <ChevronRight size={16} />
            </button>

          </div>


          <div className="hero-water">

            <div className="ring">
              <Droplets size={34} />

              <strong>
                {waterRequired}
              </strong>

              <span>Litres</span>
            </div>

          </div>

        </section>


        {/* METRICS */}
        <div className="grid">

          <Metric
            icon={<Droplets />}
            label="Soil Moisture"
            value={soilMoisture}
            unit="%"
            sub="Live sensor"
          />

          <Metric
            icon={<Thermometer />}
            label="Soil Temperature"
            value={soilTemperature}
            unit="°C"
            sub="ESP32-S3"
          />

          <Metric
            icon={<Sun />}
            label="Solar Irradiance"
            value={solarIrradiance}
            unit="W/m²"
            sub="OpenWeather"
          />

          <Metric
            icon={<CloudRain />}
            label="Rain - 48 hours"
            value={rain48}
            unit="mm"
            sub={`${Math.round(
              rainProbability48 * 100
            )}% probability`}
          />

        </div>


        {/* TWO COLUMN SECTION */}
        <div className="two">

          {/* FORECAST */}
          <section className="panel">

            <div className="panelhead">

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

              <div className="forecast-row">

                <span>
                  Next 24h
                </span>

                <b>
                  {rain24} mm
                </b>

                <small>
                  {Math.round(
                    rainProbability24 * 100
                  )}
                  % probability
                </small>

              </div>


              <div className="forecast-row">

                <span>
                  24–48h
                </span>

                <b>
                  {rain48} mm
                </b>

                <small>
                  {Math.round(
                    rainProbability48 * 100
                  )}
                  % probability
                </small>

              </div>

            </div>


            <div className="insight">

              <Leaf size={18} />

              <span>
                Agromind considers expected rainfall
                before calculating today's minimum
                irrigation dose.
              </span>

            </div>

          </section>


          {/* FARM VISUALIZATION */}
          <section className="panel">

            <div className="panelhead">

              <div>
                <h3>
                  Farm visualization
                </h3>

                <span>
                  {landSize} m² · {crop}
                </span>
              </div>

              <Map size={20} />

            </div>


            <div className="farm">

              <div className="farm-grid">

                {Array.from({ length: 24 }).map(
                  (_, index) => (
                    <div
                      key={index}
                      className={
                        index % 7 === 0
                          ? "plot wet"
                          : "plot"
                      }
                    />
                  )
                )}

              </div>

              <div className="farmlabel">
                <span>
                  ZONE A
                </span>

                <small>
                  Live monitoring
                </small>
              </div>

            </div>

          </section>

        </div>


        {/* SCHEDULE */}
        <section className="schedulebar">

          <div>

            <span className="eyebrow">
              TODAY'S PUMP WINDOW
            </span>

            <strong>
              {recommendedStart} – {recommendedEnd}
            </strong>

            <small>
              {waterRequired} L ·{" "}
              {pumpRuntime} minutes ·{" "}
              {pumpFlow} L/min
            </small>

          </div>


          <button
            onClick={() => setManual(true)}
          >
            <Power size={17} />
            Manual Override
          </button>

        </section>


        {/* FOOTER INFORMATION */}
        <section className="info-grid">

          <div className="info-card">

            <span className="eyebrow">
              WEATHER
            </span>

            <h3>
              Rainfall-aware irrigation
            </h3>

            <p>
              Weather forecasts are considered before
              Agromind determines the irrigation requirement.
            </p>

          </div>


          <div className="info-card">

            <span className="eyebrow">
              SOLAR POWER
            </span>

            <h3>
              Energy-aware scheduling
            </h3>

            <p>
              Pump operation is scheduled around available
              solar energy whenever possible.
            </p>

          </div>


          <div className="info-card">

            <span className="eyebrow">
              AI MODEL
            </span>

            <h3>
              Random Forest
            </h3>

            <p>
              Agromind combines soil, weather, crop and
              farm information to recommend irrigation.
            </p>

          </div>

        </section>

      </main>


      {/* MANUAL IRRIGATION MODAL */}
      {manual && (

        <div
          className="modal"
          onClick={() => setManual(false)}
        >

          <div
            className="modalbox"
            onClick={(event) =>
              event.stopPropagation()
            }
          >

            <h2>
              Manual Irrigation
            </h2>

            <p>
              Send a manual irrigation command
              to the pump controller.
            </p>


            <div className="manual-info">

              <div>
                <span>Farm</span>
                <strong>{landSize} m²</strong>
              </div>

              <div>
                <span>Crop</span>
                <strong>{crop}</strong>
              </div>

              <div>
                <span>Recommended water</span>
                <strong>{waterRequired} L</strong>
              </div>

            </div>


            <div className="modal-actions">

              <button
                className="ghost"
                onClick={() => setManual(false)}
              >
                Cancel
              </button>

              <button
                onClick={() => {
                  alert(
                    "Manual irrigation command queued."
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


/* METRIC COMPONENT */

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
          {value ?? "--"}

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


createRoot(
  document.getElementById("root")
).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
