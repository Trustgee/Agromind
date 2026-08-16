import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Droplets,
  Sun,
  CloudRain,
  Thermometer,
  Leaf,
  Clock3,
  Map,
  RefreshCw,
  Power,
  ChevronRight,
  AlertTriangle,
  Gauge,
} from "lucide-react";

import "./styles.css";


/* =========================================================
   AGROMIND API
   ========================================================= */

const API =
  import.meta.env.VITE_API_URL ||
  "https://agromind-api-w832.onrender.com";


/* =========================================================
   MAIN APP
   ========================================================= */

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [manual, setManual] = useState(false);
  const [error, setError] = useState(null);

  /*
   * Load dashboard information from the backend.
   */
  async function loadDashboard() {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API}/api/dashboard`);

      if (!response.ok) {
        throw new Error(`Dashboard API returned ${response.status}`);
      }

      const result = await response.json();

      setData(result);
    } catch (err) {
      console.error("Dashboard error:", err);
      setError("Unable to load farm data.");
      setData(null);
    } finally {
      setLoading(false);
    }
  }


  /*
   * Load data when the dashboard opens.
   */
  useEffect(() => {
    loadDashboard();
  }, []);


  /* =======================================================
     LOADING SCREEN
     ======================================================= */

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-card">
          <Leaf size={42} />
          <h2>Agromind</h2>
          <p>Loading your farm intelligence...</p>
        </div>
      </div>
    );
  }


  /* =======================================================
     ERROR SCREEN
     ======================================================= */

  if (error || !data) {
    return (
      <div className="loading-screen">
        <div className="loading-card">
          <AlertTriangle size={42} />

          <h2>Agromind</h2>

          <p>
            {error || "No dashboard data is available."}
          </p>

          <button
            className="primary-button"
            onClick={loadDashboard}
          >
            <RefreshCw size={17} />
            Try Again
          </button>
        </div>
      </div>
    );
  }


  /* =======================================================
     DATA NORMALIZATION
     ======================================================= */

  const t = data.telemetry || data;

  const schedule = data.schedule || {};

  const soilMoisture =
    Number(
      t.soil_moisture_pct ??
      t.soil_moisture ??
      0
    );

  const soilTemperature =
    Number(
      t.soil_temperature_c ??
      t.soil_temperature_C ??
      t.soil_temp ??
      0
    );

  const solarIrradiance =
    Number(
      t.solar_irradiance_w_m2 ??
      t.solar_irradiance_W_m2 ??
      0
    );

  const rain24 =
    Number(
      t.rain_0_24h_mm ??
      t.rain_24h_mm ??
      t.rain_0_24h ??
      0
    );

  const rain48 =
    Number(
      t.rain_24_48h_mm ??
      t.rain_24_48h ??
      0
    );

  const rainProbability24 =
    Number(
      t.rain_probability_0_24h ??
      t.rain_probability_24h ??
      0
    );

  const rainProbability48 =
    Number(
      t.rain_probability_24_48h ??
      0
    );

  const crop =
    data.crop ||
    data.crop_type ||
    "Tomato";

  const need =
    data.need_level ||
    data.irrigation_need ||
    "MEDIUM";

  const irrigationDepth =
    Number(
      data.irrigation_depth_mm ??
      data.recommended_depth_mm ??
      data.recommended_daily_depth_mm ??
      0
    );

  const waterRequired =
    Number(
      data.water_required_l ??
      data.water_required_liters ??
      data.water_required ??
      0
    );

  const pumpRuntime =
    Number(
      schedule.pump_runtime_min ??
      data.pump_runtime_min ??
      0
    );

  const pumpFlow =
    Number(
      schedule.pump_flow_l_min ??
      data.pump_flow_l_min ??
      0
    );

  const recommendedStart =
    schedule.recommended_start ||
    data.recommended_start ||
    "06:00";

  const recommendedEnd =
    schedule.recommended_end ||
    data.recommended_end ||
    "07:00";


  /* =======================================================
     HELPER VALUES
     ======================================================= */

  const rain24ProbabilityText =
    Math.round(rainProbability24 * 100);

  const rain48ProbabilityText =
    Math.round(rainProbability48 * 100);


  /*
   * Some APIs return probability as 0–1.
   * Others return 0–100.
   * This keeps the dashboard correct either way.
   */

  const probabilityToPercent = (value) => {
    const number = Number(value || 0);

    if (number <= 1) {
      return Math.round(number * 100);
    }

    return Math.round(number);
  };


  const rain24Percent =
    probabilityToPercent(rainProbability24);

  const rain48Percent =
    probabilityToPercent(rainProbability48);


  /* =======================================================
     APP
     ======================================================= */

  return (
    <div className="app">

      {/* ===================================================
          SIDEBAR
          =================================================== */}

      <aside className="sidebar">

        <div className="brand">
          <div className="brand-mark">A</div>

          <div>
            <strong>Agromind</strong>
            <span>Smart Agriculture</span>
          </div>
        </div>


        <nav>

          <a className="active" href="#">
            Overview
          </a>

          <a href="#farm">
            Farm Map
          </a>

          <a href="#irrigation">
            Irrigation
          </a>

          <a href="#weather">
            Weather
          </a>

          <a href="#plant-health">
            Plant Health
          </a>

        </nav>


        <div className="side-card">

          <span>
            <span className="status-dot"></span>
            <strong>Online</strong>
          </span>

          <small>
            AOSIS v14 • Clay loam
          </small>

        </div>

      </aside>


      {/* ===================================================
          MAIN CONTENT
          =================================================== */}

      <main>


        {/* =================================================
            HEADER
            ================================================= */}

        <header>

          <div className="eyebrow">
            AI-OPTIMIZED IRRIGATION
          </div>

          <h1>
            Good morning, Farmer.
          </h1>

          <p>
            Here's what your farm needs today.
          </p>


          <button
            className="refresh"
            onClick={loadDashboard}
          >
            <RefreshCw size={16} />
            Refresh
          </button>

        </header>



        {/* =================================================
            HERO / RECOMMENDATION
            ================================================= */}

        <section className="hero">

          <div className="hero-content">

            <div className="eyebrow">
              TODAY'S IRRIGATION RECOMMENDATION
            </div>

            <div className="recommendation">

              <span className="dot">
                {need}
              </span>

              <strong>
                {irrigationDepth
                  ? irrigationDepth.toFixed(3)
                  : "0.000"}{" "}
                mm
              </strong>

              <span className="need-label">
                Recommended daily application depth
              </span>

            </div>


            <div className="hero-actions">

              <button
                className="primary-button"
                onClick={() => setManual(true)}
              >
                <Droplets size={17} />
                Irrigate Now
              </button>


              <button
                className="ghost-button"
                onClick={() =>
                  document
                    .getElementById("irrigation")
                    ?.scrollIntoView({
                      behavior: "smooth",
                    })
                }
              >
                View Schedule
                <ChevronRight size={17} />
              </button>

            </div>

          </div>


          <div className="water-ring">

            <Droplets size={32} />

            <strong>
              {waterRequired
                ? waterRequired.toFixed(2)
                : "0.00"}
            </strong>

            <span>
              Litres
            </span>

          </div>

        </section>



        {/* =================================================
            TELEMETRY GRID
            ================================================= */}

        <div className="grid">


          <Metric
            icon={<Droplets />}
            label="Soil Moisture"
            value={soilMoisture.toFixed(0)}
            unit="%"
            sub="Live sensor"
          />


          <Metric
            icon={<Thermometer />}
            label="Soil Temperature"
            value={soilTemperature.toFixed(1)}
            unit="°C"
            sub="ESP32-S3"
          />


          <Metric
            icon={<Sun />}
            label="Solar Irradiance"
            value={solarIrradiance.toFixed(0)}
            unit="W/m²"
            sub="OpenWeather"
          />


          <Metric
            icon={<CloudRain />}
            label="Rain - 48 hours"
            value={rain48.toFixed(1)}
            unit="mm"
            sub={`${rain48Percent}% probability`}
          />

        </div>



        {/* =================================================
            WEATHER / FORECAST
            ================================================= */}

        <div
          className="two"
          id="weather"
        >

          <section className="panel">

            <div className="panel-head">

              <div>
                <h3>
                  48-hour forecast
                </h3>

                <span>
                  Rainfall-aware scheduling
                </span>
              </div>

              <CloudRain />

            </div>


            <div className="forecast">

              <div>

                <span>
                  Next 24h
                </span>

                <b>
                  {rain24.toFixed(1)} mm
                </b>

                <small>
                  {rain24Percent}% probability
                </small>

              </div>


              <div>

                <span>
                  24–48h
                </span>

                <b>
                  {rain48.toFixed(1)} mm
                </b>

                <small>
                  {rain48Percent}% probability
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



          {/* =================================================
              FARM VISUALIZATION
              ================================================= */}

          <section
            className="panel"
            id="farm"
          >

            <div className="panel-head">

              <div>

                <h3>
                  Farm visualization
                </h3>

                <span>
                  100 m² • {crop}
                </span>

              </div>

              <Map />

            </div>


            <div className="farm">

              <div className="farm-grid">

                {Array.from({
                  length: 24,
                }).map((_, index) => (

                  <div
                    key={index}
                    className={
                      index % 7 === 0
                        ? "plot dry"
                        : "plot"
                    }
                  />

                ))}

              </div>


              <div className="farm-label">

                <strong>
                  ZONE A
                </strong>

                <span>
                  Live monitoring
                </span>

              </div>

            </div>

          </section>

        </div>



        {/* =================================================
            IRRIGATION SCHEDULE
            ================================================= */}

        <section
          className="schedulebar"
          id="irrigation"
        >

          <div>

            <span className="eyebrow">
              TODAY'S PUMP WINDOW
            </span>

            <strong>
              {recommendedStart} – {recommendedEnd}
            </strong>

            <small>
              {waterRequired
                ? `${waterRequired.toFixed(2)} L`
                : "Water requirement unavailable"}
              {" • "}
              {pumpRuntime
                ? `${pumpRuntime} minutes`
                : "Runtime unavailable"}
              {" • "}
              {pumpFlow
                ? `${pumpFlow.toFixed(2)} L/min`
                : "Flow rate unavailable"}
            </small>

          </div>


          <button
            onClick={() => setManual(true)}
          >
            <Power size={17} />
            Manual Override
          </button>

        </section>



        {/* =================================================
            EXTRA WEATHER INFORMATION
            ================================================= */}

        <section className="panel weather-summary">

          <div className="panel-head">

            <div>

              <h3>
                Current weather
              </h3>

              <span>
                OpenWeather
              </span>

            </div>

            <Gauge />

          </div>


          <div className="weather-details">

            <div>
              <span>
                Temperature
              </span>

              <strong>
                {Number(
                  t.current_temperature_c ??
                  t.temperature_c ??
                  0
                ).toFixed(1)}
                °C
              </strong>
            </div>


            <div>
              <span>
                Humidity
              </span>

              <strong>
                {Number(
                  t.current_humidity_pct ??
                  t.humidity_pct ??
                  0
                ).toFixed(0)}
                %
              </strong>
            </div>


            <div>
              <span>
                Rain probability
              </span>

              <strong>
                {rain24Percent}%
              </strong>
            </div>


            <div>
              <span>
                Solar
              </span>

              <strong>
                {solarIrradiance.toFixed(0)}
                {" "}
                W/m²
              </strong>
            </div>

          </div>

        </section>



        {/* =================================================
            FOOTER
            ================================================= */}

        <footer>

          <span>
            Agromind • AI-Optimized Solar Irrigation Scheduler
          </span>

          <span>
            AOSIS v14
          </span>

        </footer>

      </main>



      {/* ===================================================
          MANUAL IRRIGATION MODAL
          =================================================== */}

      {manual && (

        <div className="modal">

          <div className="modalbox">

            <div className="modal-icon">
              <Droplets size={30} />
            </div>

            <h2>
              Manual Irrigation
            </h2>

            <p>
              Send a manual irrigation command
              to the pump controller.
            </p>


            <div className="manual-info">

              <div>
                <span>
                  Recommended water
                </span>

                <strong>
                  {waterRequired.toFixed(2)} L
                </strong>
              </div>


              <div>
                <span>
                  Recommended runtime
                </span>

                <strong>
                  {pumpRuntime || "--"} min
                </strong>
              </div>

            </div>


            <div className="modal-actions">

              <button
                className="ghost-button"
                onClick={() => setManual(false)}
              >
                Cancel
              </button>


              <button
                className="primary-button"
                onClick={() => {

                  /*
                   * At this stage the modal is intentionally
                   * local. Your ESP32/pump endpoint can be
                   * connected here later.
                   */

                  alert(
                    "Manual irrigation command ready."
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



/* =========================================================
   METRIC COMPONENT
   ========================================================= */

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

      <div>

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



/* =========================================================
   REACT ROOT
   ========================================================= */

createRoot(
  document.getElementById("root")
).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
