import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Droplets,
  Sun,
  CloudRain,
  Thermometer,
  Leaf,
  Map,
  Power,
  RefreshCw,
  ChevronRight,
  Settings,
  Clock3,
  Sprout,
} from "lucide-react";

import "./styles.css";


// ============================================================
// API CONFIGURATION
// ============================================================

const API_URL =
  import.meta.env.VITE_API_URL ||
  "https://agromind-api-w832.onrender.com";


// ============================================================
// DEFAULT FARM SETTINGS
// ============================================================

const DEFAULT_FARM = {
  crop_type: "Tomato",
  crop_age_days: 60,
  land_size_m2: 100,
};


// ============================================================
// MAIN APP
// ============================================================

function App() {

  // ----------------------------------------------------------
  // Dashboard data
  // ----------------------------------------------------------

  const [data, setData] = useState(null);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");

  const [manual, setManual] = useState(false);


  // ----------------------------------------------------------
  // Farm settings
  // ----------------------------------------------------------

  const [farm, setFarm] = useState(DEFAULT_FARM);

  const [draftFarm, setDraftFarm] = useState(DEFAULT_FARM);

  const [savingFarm, setSavingFarm] = useState(false);


  // ==========================================================
  // LOAD DASHBOARD
  // ==========================================================

  async function loadDashboard(
    farmSettings = farm
  ) {

    setLoading(true);
    setError("");

    try {

      const params = new URLSearchParams({
        crop_type: farmSettings.crop_type,
        crop_age_days: farmSettings.crop_age_days,
        land_size_m2: farmSettings.land_size_m2,
      });

      const response = await fetch(
        `${API_URL}/api/dashboard?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error(
          `Dashboard API returned ${response.status}`
        );
      }

      const result = await response.json();

      setData(result);

    } catch (err) {

      console.error(err);

      setError(
        "Unable to connect to the Agromind API."
      );

    } finally {

      setLoading(false);

    }
  }


  // ==========================================================
  // INITIAL LOAD
  // ==========================================================

  useEffect(() => {

    loadDashboard(DEFAULT_FARM);

  }, []);


  // ==========================================================
  // UPDATE FARM
  // ==========================================================

  async function updateFarm() {

    const crop = draftFarm.crop_type;

    const age = Number(
      draftFarm.crop_age_days
    );

    const land = Number(
      draftFarm.land_size_m2
    );


    if (!crop) {
      alert("Please select a crop.");
      return;
    }

    if (!age || age < 0) {
      alert("Please enter a valid crop age.");
      return;
    }

    if (!land || land <= 0) {
      alert("Please enter a valid land size.");
      return;
    }


    const newFarm = {
      crop_type: crop,
      crop_age_days: age,
      land_size_m2: land,
    };


    setFarm(newFarm);

    setSavingFarm(true);

    await loadDashboard(newFarm);

    setSavingFarm(false);
  }


  // ==========================================================
  // REFRESH
  // ==========================================================

  function refreshDashboard() {

    loadDashboard(farm);

  }


  // ==========================================================
  // LOADING STATE
  // ==========================================================

  if (loading && !data) {

    return (
      <div className="loading-screen">

        <div className="loading-card">

          <Leaf size={32} />

          <h2>Agromind</h2>

          <p>
            Loading your farm data...
          </p>

        </div>

      </div>
    );

  }


  // ==========================================================
  // ERROR STATE
  // ==========================================================

  if (error && !data) {

    return (
      <div className="loading-screen">

        <div className="loading-card">

          <CloudRain size={32} />

          <h2>Agromind</h2>

          <p>{error}</p>

          <button
            className="primary-button"
            onClick={() =>
              loadDashboard(farm)
            }
          >
            <RefreshCw size={16} />
            Try Again
          </button>

        </div>

      </div>
    );

  }


  // ==========================================================
  // SAFE DATA
  // ==========================================================

  const telemetry =
    data?.telemetry || {};

  const schedule =
    data?.schedule || {};


  // ----------------------------------------------------------
  // Sensor values
  // ----------------------------------------------------------

  const soilMoisture =
    Number(
      telemetry.soil_moisture_pct ?? 0
    );

  const soilTemperature =
    Number(
      telemetry.soil_temperature_C ?? 0
    );

  const solarIrradiance =
    Number(
      telemetry.solar_irradiance_W_m2 ?? 0
    );

  const rain48 =
    Number(
      telemetry.rain_24_48h_mm ?? 0
    );

  const rainProbability =
    Number(
      telemetry.rain_probability_24_48h ?? 0
    );


  // ----------------------------------------------------------
  // Schedule values
  // ----------------------------------------------------------

  const irrigationDepth =
    Number(
      schedule.irrigation_depth_mm ?? 0
    );

  const waterRequired =
    Number(
      schedule.water_required_L ?? 0
    );

  const needLevel =
    schedule.need_level ||
    "UNKNOWN";

  const recommendedStart =
    schedule.recommended_start ||
    "06:00";

  const recommendedEnd =
    schedule.recommended_end ||
    "--:--";

  const pumpRuntime =
    Number(
      schedule.pump_runtime_min ?? 0
    );

  const pumpFlow =
    Number(
      schedule.pump_flow_L_min ??
      telemetry.pump_flow_L_min ??
      0
    );


  // ----------------------------------------------------------
  // Forecast
  // ----------------------------------------------------------

  const rainNext24 =
    Number(
      schedule.rain_next_24h_mm ??
      telemetry.rain_0_24h_mm ??
      0
    );

  const probabilityNext24 =
    Number(
      schedule.rain_probability_next_24h ??
      telemetry.rain_probability_0_24h ??
      0
    );


  // ==========================================================
  // UI
  // ==========================================================

  return (

    <div className="app">


      {/* ====================================================
          SIDEBAR
      ==================================================== */}

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-mark">
            A
          </div>

          <div>
            <strong>Agromind</strong>

            <span>
              Smart Agriculture
            </span>
          </div>

        </div>


        <nav className="navigation">

          <a
            href="#overview"
            className="active"
          >
            Overview
          </a>

          <a href="#farm">
            <Map size={16} />
            Farm Map
          </a>

          <a href="#irrigation">
            <Droplets size={16} />
            Irrigation
          </a>

          <a href="#weather">
            <CloudRain size={16} />
            Weather
          </a>

          <a href="#plant">
            <Sprout size={16} />
            Plant Health
          </a>

        </nav>


        <div className="side-card">

          <span className="status-dot"></span>

          <strong>Online</strong>

          <small>
            AOSIS v14
          </small>

          <small>
            {farm.crop_type}
          </small>

        </div>

      </aside>


      {/* ====================================================
          MAIN CONTENT
      ==================================================== */}

      <main className="main">


        {/* ==================================================
            HEADER
        ================================================== */}

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
            className="refresh-button"
            onClick={refreshDashboard}
            disabled={loading}
          >

            <RefreshCw
              size={17}
              className={
                loading
                  ? "spin"
                  : ""
              }
            />

            {loading
              ? "Updating..."
              : "Refresh"}

          </button>

        </header>



        {/* ==================================================
            FARM SETUP
        ================================================== */}

        <section
          className="farm-settings"
          id="farm-settings"
        >

          <div className="section-heading">

            <div>

              <div className="eyebrow">
                FARM SETUP
              </div>

              <h2>
                Farm Configuration
              </h2>

              <p>
                Select the crop and enter your farm size.
              </p>

            </div>

            <Settings size={22} />

          </div>


          <div className="farm-form">


            {/* CROP */}

            <div className="form-group">

              <label>
                Crop
              </label>

              <select
                value={draftFarm.crop_type}
                onChange={(e) =>
                  setDraftFarm({
                    ...draftFarm,
                    crop_type:
                      e.target.value
                  })
                }
              >

                <option value="Tomato">
                  Tomato
                </option>

                <option value="Maize">
                  Maize
                </option>

                <option value="Pepper">
                  Pepper
                </option>

              </select>

            </div>


            {/* LAND SIZE */}

            <div className="form-group">

              <label>
                Land Size
              </label>

              <div className="input-with-unit">

                <input
                  type="number"
                  min="1"
                  value={
                    draftFarm.land_size_m2
                  }
                  onChange={(e) =>
                    setDraftFarm({
                      ...draftFarm,
                      land_size_m2:
                        e.target.value
                    })
                  }
                />

                <span>
                  m²
                </span>

              </div>

            </div>


            {/* CROP AGE */}

            <div className="form-group">

              <label>
                Crop Age
              </label>

              <div className="input-with-unit">

                <input
                  type="number"
                  min="0"
                  value={
                    draftFarm.crop_age_days
                  }
                  onChange={(e) =>
                    setDraftFarm({
                      ...draftFarm,
                      crop_age_days:
                        e.target.value
                    })
                  }
                />

                <span>
                  days
                </span>

              </div>

            </div>


            {/* UPDATE BUTTON */}

            <button
              className="update-button"
              onClick={updateFarm}
              disabled={savingFarm}
            >

              <RefreshCw size={17} />

              {savingFarm
                ? "Calculating..."
                : "Update Recommendation"}

            </button>

          </div>

        </section>



        {/* ==================================================
            HERO / IRRIGATION RECOMMENDATION
        ================================================== */}

        <section
          className="hero"
          id="overview"
        >

          <div className="hero-content">

            <div className="eyebrow">
              TODAY'S IRRIGATION RECOMMENDATION
            </div>

            <div className="recommendation-line">

              <span>
                Need{" "}
                <strong>
                  {needLevel}
                </strong>
              </span>

              <strong className="depth">
                {irrigationDepth.toFixed(3)}
                {" "}mm
              </strong>

              <span>
                Recommended daily application depth
              </span>

            </div>


            <div className="hero-actions">

              <button
                className="irrigate-button"
                onClick={() =>
                  alert(
                    "Irrigation command ready for ESP32."
                  )
                }
              >

                <Droplets size={17} />

                Irrigate Now

              </button>


              <button
                className="schedule-button"
                onClick={() =>
                  document
                    .getElementById("irrigation")
                    ?.scrollIntoView({
                      behavior: "smooth"
                    })
                }
              >

                View Schedule

                <ChevronRight size={17} />

              </button>

            </div>

          </div>


          <div className="water-total">

            <Droplets size={38} />

            <strong>
              {waterRequired.toLocaleString(
                undefined,
                {
                  maximumFractionDigits: 2
                }
              )}
            </strong>

            <span>
              Litres
            </span>

          </div>

        </section>



        {/* ==================================================
            SENSOR METRICS
        ================================================== */}

        <section className="metrics-grid">


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
              rainProbability * 100
            )}% probability`}
          />

        </section>



        {/* ==================================================
            TWO COLUMN AREA
        ================================================== */}

        <div className="two-column">


          {/* =================================================
              WEATHER
          ================================================= */}

          <section
            className="panel"
            id="weather"
          >

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
                  {rainNext24.toFixed(1)}
                  {" "}mm
                </strong>

                <small>
                  {Math.round(
                    probabilityNext24 * 100
                  )}
                  % probability
                </small>

              </div>


              <div className="forecast-item">

                <span>
                  24–48h
                </span>

                <strong>
                  {rain48.toFixed(1)}
                  {" "}mm
                </strong>

                <small>
                  {Math.round(
                    rainProbability * 100
                  )}
                  % probability
                </small>

              </div>

            </div>


            <div className="insight">

              <Leaf size={17} />

              <span>
                Agromind considers expected
                rainfall before calculating
                today's minimum irrigation dose.
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

            <div className="panel-header">

              <div>

                <h3>
                  Farm visualization
                </h3>

                <span>
                  {farm.land_size_m2} m²
                  {" • "}
                  {farm.crop_type}
                </span>

              </div>

              <Map size={20} />

            </div>


            <div className="farm-map">

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


            <div className="farm-status">

              <span>
                ZONE A
              </span>

              <span>
                Live monitoring
              </span>

            </div>

          </section>

        </div>



        {/* ==================================================
            IRRIGATION SCHEDULE
        ================================================== */}

        <section
          className="schedule-panel"
          id="irrigation"
        >

          <div>

            <div className="eyebrow">
              TODAY'S PUMP WINDOW
            </div>

            <h2>
              {recommendedStart}
              {" – "}
              {recommendedEnd}
            </h2>

            <p>

              {pumpRuntime.toFixed(2)}
              {" "}minutes

              {" • "}

              {pumpFlow.toFixed(1)}
              {" "}L/min

              {" • "}

              {waterRequired.toFixed(2)}
              {" "}L

            </p>

          </div>


          <button
            className="manual-button"
            onClick={() =>
              setManual(true)
            }
          >

            <Power size={17} />

            Manual Override

          </button>

        </section>



        {/* ==================================================
            FARM INFORMATION
        ================================================== */}

        <section className="farm-info">

          <div>
            <strong>
              Crop
            </strong>

            <span>
              {farm.crop_type}
            </span>
          </div>


          <div>
            <strong>
              Crop age
            </strong>

            <span>
              {farm.crop_age_days} days
            </span>
          </div>


          <div>
            <strong>
              Land size
            </strong>

            <span>
              {farm.land_size_m2} m²
            </span>
          </div>


          <div>
            <strong>
              Application efficiency
            </strong>

            <span>
              {(
                Number(
                  telemetry.application_efficiency ??
                  0.75
                ) * 100
              ).toFixed(0)}
              %
            </span>
          </div>


          <div>
            <strong>
              Model
            </strong>

            <span>
              {schedule.model_version ||
                "AOSIS-v14"}
            </span>
          </div>

        </section>



        {/* ==================================================
            ERROR MESSAGE
        ================================================== */}

        {error && (

          <div className="error-banner">

            {error}

            <button
              onClick={() =>
                loadDashboard(farm)
              }
            >
              Retry
            </button>

          </div>

        )}

      </main>



      {/* ====================================================
          MANUAL OVERRIDE MODAL
      ==================================================== */}

      {manual && (

        <div
          className="modal-overlay"
          onClick={() =>
            setManual(false)
          }
        >

          <div
            className="modal-box"
            onClick={(e) =>
              e.stopPropagation()
            }
          >

            <Power size={28} />

            <h2>
              Manual Irrigation
            </h2>

            <p>
              Send a manual irrigation
              command to the pump controller.
            </p>


            <div className="modal-actions">

              <button
                className="cancel-button"
                onClick={() =>
                  setManual(false)
                }
              >
                Cancel
              </button>


              <button
                className="irrigate-button"
                onClick={() => {

                  alert(
                    "Manual irrigation command sent."
                  );

                  setManual(false);

                }}
              >

                <Power size={16} />

                Start Pump

              </button>

            </div>

          </div>

        </div>

      )}

    </div>
  );
}


// ============================================================
// METRIC COMPONENT
// ============================================================

function Metric({
  icon,
  label,
  value,
  unit,
  sub
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


// ============================================================
// START REACT
// ============================================================

createRoot(
  document.getElementById("root")
).render(
  <App />
);
