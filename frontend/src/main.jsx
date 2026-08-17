import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

const API_URL =
  import.meta.env.VITE_API_URL ||
  "https://agromind-api-w832.onrender.com";

const CROP_OPTIONS = ["Tomato", "Pepper"];

const DEFAULT_FARM = {
  crop_type: "Tomato",
  crop_age_days: 60,
  land_size_m2: 100,
  pump_flow_L_min: 10,
  application_efficiency: 0.75,
  start_time: "06:00",
};

const DEFAULT_TELEMETRY = {
  soil_moisture_pct: 0,
  soil_temperature_C: 0,
  humidity_pct: 0,

  soil_adc: null,

  water_sensor_adc: null,
  water_level_pct: 0,
  water_remaining_L: 0,
  water_status: "UNKNOWN",

  solar_irradiance_W_m2: 0,

  rain_0_24h_mm: 0,
  rain_probability_0_24h: 0,

  rain_24_48h_mm: 0,
  rain_probability_24_48h: 0,

  last_update: null,
};


// ============================================================
// READ SAVED FARM CONFIGURATION
// ============================================================

function readFarm() {
  try {
    const saved =
      localStorage.getItem("agromind_farm");

    return saved
      ? {
          ...DEFAULT_FARM,
          ...JSON.parse(saved),
        }
      : DEFAULT_FARM;

  } catch {
    return DEFAULT_FARM;
  }
}


// ============================================================
// APP
// ============================================================

function App() {

  const [farm, setFarm] =
    useState(readFarm);

  const [telemetry, setTelemetry] =
    useState(DEFAULT_TELEMETRY);

  const [schedule, setSchedule] =
    useState(null);

  const [telemetrySource, setTelemetrySource] =
    useState("DEMO");

  const [loading, setLoading] =
    useState(true);

  const [updating, setUpdating] =
    useState(false);

  const [error, setError] =
    useState("");

  const [manualMode, setManualMode] =
    useState(false);

  const [activeSection, setActiveSection] =
    useState("overview");


  // ============================================================
  // SAVE FARM SETTINGS
  // ============================================================

  useEffect(() => {

    localStorage.setItem(
      "agromind_farm",
      JSON.stringify(farm)
    );

  }, [farm]);


  // ============================================================
  // LOAD DASHBOARD
  // ============================================================

  async function loadDashboard(
    showLoading = true
  ) {

    try {

      if (showLoading) {
        setLoading(true);
      }

      setError("");

      const response =
        await fetch(
          `${API_URL}/api/dashboard`,
          {
            cache: "no-store",
          }
        );


      if (!response.ok) {

        throw new Error(
          `API returned ${response.status}`
        );

      }


      const result =
        await response.json();


      // ========================================================
      // UPDATE LIVE TELEMETRY
      // ========================================================

      setTelemetry({
        ...DEFAULT_TELEMETRY,
        ...(result.telemetry || {}),
      });


      // ========================================================
      // UPDATE TELEMETRY SOURCE
      // ========================================================

      setTelemetrySource(
        result.telemetry_source ||
        "DEMO"
      );


      // ========================================================
      // IMPORTANT FIX
      // ========================================================
      //
      // DO NOT overwrite the currently displayed AI
      // recommendation every 5 seconds.
      //
      // Before this fix:
      //
      // Update Recommendation
      //       ↓
      // 6.720 mm
      //       ↓
      // 5-second refresh
      //       ↓
      // /api/dashboard
      //       ↓
      // schedule replaced
      //       ↓
      // 0.000 mm
      //
      // Now the dashboard schedule is only used when
      // there is no recommendation already displayed.
      //
      // The actual recommendation can still be changed
      // by Update Recommendation / Recalculate.
      //

      setSchedule((previous) => {

        if (previous === null) {

          return result.schedule || null;

        }

        return previous;

      });


    } catch (err) {

      console.error(err);

      setError(
        "Unable to connect to the Agromind API."
      );


    } finally {

      if (showLoading) {
        setLoading(false);
      }

    }

  }


  // ============================================================
  // START DASHBOARD + AUTO REFRESH
  // ============================================================

  useEffect(() => {

    loadDashboard(true);


    const interval =
      setInterval(() => {

        loadDashboard(false);

      }, 5000);


    return () =>
      clearInterval(interval);

  }, []);


  // ============================================================
  // UPDATE FARM VALUE
  // ============================================================

  function updateFarm(
    key,
    value
  ) {

    setFarm((previous) => ({

      ...previous,

      [key]: value,

    }));

  }


  // ============================================================
  // UPDATE AI RECOMMENDATION
  // ============================================================

  async function updateRecommendation() {

    try {

      setUpdating(true);

      setError("");


      // ========================================================
      // BUILD AI INPUT
      // ========================================================

      const payload = {

        soil_moisture_pct:
          Number(
            telemetry.soil_moisture_pct
          ),

        soil_temperature_C:
          Number(
            telemetry.soil_temperature_C
          ),

        solar_irradiance_W_m2:
          Number(
            telemetry.solar_irradiance_W_m2
          ),

        rain_0_24h_mm:
          Number(
            telemetry.rain_0_24h_mm
          ),

        rain_probability_0_24h:
          Number(
            telemetry.rain_probability_0_24h
          ),

        rain_24_48h_mm:
          Number(
            telemetry.rain_24_48h_mm
          ),

        rain_probability_24_48h:
          Number(
            telemetry.rain_probability_24_48h
          ),

        crop_type:
          farm.crop_type,

        crop_age_days:
          Number(
            farm.crop_age_days
          ),

        land_size_m2:
          Number(
            farm.land_size_m2
          ),

        pump_flow_L_min:
          Number(
            farm.pump_flow_L_min
          ),

        application_efficiency:
          Number(
            farm.application_efficiency
          ),

        start_time:
          farm.start_time ||
          "06:00",

      };


      // ========================================================
      // SEND TO AI SCHEDULER
      // ========================================================

      const response =
        await fetch(
          `${API_URL}/api/schedule`,
          {

            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify(payload),

          }
        );


      const result =
        await response.json();


      if (!response.ok) {

        throw new Error(
          result.error ||
          "Unable to calculate irrigation schedule"
        );

      }


      // ========================================================
      // IMPORTANT
      // ========================================================
      //
      // This explicitly replaces the current recommendation.
      //
      // Therefore:
      //
      // 0.000 → 6.720
      //
      // or
      //
      // 6.720 → 4.500
      //
      // when the farmer deliberately recalculates.
      //

      setSchedule(result);


    } catch (err) {

      console.error(err);

      setError(
        err.message ||
        "Unable to update recommendation"
      );


    } finally {

      setUpdating(false);

    }

  }


  // ============================================================
  // SIDEBAR NAVIGATION
  // ============================================================

  function scrollToSection(id) {

    setActiveSection(id);

    document
      .getElementById(id)
      ?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });

  }


  // ============================================================
  // FORMATTERS
  // ============================================================

  function number(
    value,
    decimals = 1
  ) {

    const n =
      Number(value);

    if (!Number.isFinite(n)) {
      return "0";
    }

    return n.toLocaleString(
      undefined,
      {
        minimumFractionDigits:
          decimals,

        maximumFractionDigits:
          decimals,
      }
    );

  }


  function percent(value) {

    const n =
      Number(value);

    if (!Number.isFinite(n)) {
      return "0%";
    }

    return `${Math.round(n * 100)}%`;

  }


  // ============================================================
  // CALCULATED VALUES
  // ============================================================

  const irrigationDepth =
    Number(
      schedule?.irrigation_depth_mm ?? 0
    );


  const waterRequired =
    Number(
      schedule?.water_required_L ?? 0
    );


  const pumpRuntime =
    Number(
      schedule?.pump_runtime_min ?? 0
    );


  const pumpFlow =
    Number(
      schedule?.pump_flow_L_min ??
      farm.pump_flow_L_min ??
      0
    );


  const needLevel =
    schedule?.need_level ||
    "MEDIUM";


  // ============================================================
  // ESP32 STATUS
  // ============================================================

  const isRealEsp32 =
    String(
      telemetrySource
    )
      .toUpperCase()
      .includes("ESP32");


  // ============================================================
  // WATER TANK
  // ============================================================

  const waterLevel =
    Number(
      telemetry.water_level_pct ?? 0
    );


  const waterRemaining =
    Number(
      telemetry.water_remaining_L ?? 0
    );


  const waterStatus =
    telemetry.water_status ||
    (
      waterLevel <= 10
        ? "CRITICAL"
        : waterLevel <= 25
        ? "LOW"
        : "NORMAL"
    );


  const waterStatusClass =
    waterStatus === "CRITICAL"
      ? "critical"
      : waterStatus === "LOW"
      ? "low"
      : "normal";


  // ============================================================
  // UI
  // ============================================================

  return (

    <>

      <style>{`

        * {
          box-sizing: border-box;
        }

        html {
          scroll-behavior: smooth;
        }

        body {
          margin: 0;

          font-family:
            Inter,
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            sans-serif;

          background: #f5f7f3;
          color: #15251c;
        }

        button,
        input,
        select {
          font: inherit;
        }

        button {
          cursor: pointer;
        }


        /* ================================================
           APP
        ================================================ */

        .agro-app {
          min-height: 100vh;

          display: flex;

          background: #f5f7f3;
        }


        /* ================================================
           SIDEBAR
        ================================================ */

        .sidebar {
          width: 250px;

          min-height: 100vh;

          position: fixed;

          left: 0;
          top: 0;
          bottom: 0;

          background: #102117;

          color: white;

          padding: 28px 18px;

          display: flex;

          flex-direction: column;

          z-index: 20;
        }


        .brand {
          padding:
            5px 12px 30px;
        }


        .brand-small {
          font-size: 10px;

          color: #b9d95b;

          text-transform:
            uppercase;

          letter-spacing: 2px;

          font-weight: 800;
        }


        .brand-name {
          font-size: 26px;

          font-weight: 850;

          margin-top: 7px;
        }


        .brand-subtitle {
          color: #8fa396;

          font-size: 12px;

          margin-top: 5px;
        }


        .nav {
          display: flex;

          flex-direction: column;

          gap: 7px;
        }


        .nav-button {
          border: none;

          background: transparent;

          color: #d8e1db;

          padding: 14px;

          border-radius: 12px;

          text-align: left;

          font-weight: 650;

          display: flex;

          align-items: center;

          gap: 12px;

          transition: .2s;
        }


        .nav-button:hover {
          background:
            rgba(255,255,255,.09);

          color: white;
        }


        .nav-button.active {
          background:
            rgba(255,255,255,.09);

          color: white;

          box-shadow:
            inset 3px 0 #b9ef17;
        }


        .nav-icon {
          width: 24px;

          text-align: center;

          font-size: 17px;
        }


        .sidebar-bottom {
          margin-top: auto;

          padding:
            15px 12px;

          border-top:
            1px solid
            rgba(255,255,255,.1);
        }


        .online-dot {
          width: 8px;
          height: 8px;

          display: inline-block;

          border-radius: 50%;

          margin-right: 8px;

          background: #b8ef20;
        }


        .online-dot.demo {
          background: #f0ad27;
        }


        .online-text {
          color: #b8ef20;

          font-size: 12px;

          font-weight: 800;
        }


        .online-text.demo {
          color: #f0ad27;
        }


        .model-text {
          color: #8fa396;

          font-size: 11px;

          margin-top: 9px;
        }


        /* ================================================
           MAIN
        ================================================ */

        .main {
          margin-left: 250px;

          width:
            calc(100% - 250px);

          padding:
            38px 42px 60px;
        }


        .topbar {
          display: flex;

          align-items: center;

          justify-content:
            space-between;

          margin-bottom: 20px;

          gap: 20px;
        }


        .eyebrow {
          color: #78877e;

          font-size: 11px;

          text-transform:
            uppercase;

          letter-spacing: 1.7px;

          font-weight: 800;

          margin-bottom: 7px;
        }


        .page-title {
          margin: 0;

          font-size: 34px;

          line-height: 1.1;

          letter-spacing: -1px;
        }


        .page-subtitle {
          color: #718078;

          margin:
            8px 0 0;
        }


        .refresh-button {
          border:
            1px solid #d7dfd8;

          background: white;

          border-radius: 12px;

          padding:
            11px 16px;

          color: #26382d;

          font-weight: 700;
        }


        /* ================================================
           CONNECTION
        ================================================ */

        .connection-bar {
          display: flex;

          align-items: center;

          justify-content:
            space-between;

          gap: 12px;

          background: white;

          border:
            1px solid #e2e8e2;

          border-radius: 14px;

          padding:
            12px 16px;

          margin-bottom: 20px;

          font-size: 12px;
        }


        .connection-left {
          display: flex;

          align-items: center;

          gap: 9px;

          font-weight: 800;
        }


        .connection-led {
          width: 9px;
          height: 9px;

          border-radius: 50%;

          background: #f0ad27;
        }


        .connection-led.live {
          background: #58c72d;

          box-shadow:
            0 0 0 4px #e8f6e3;
        }


        .connection-time {
          color: #8a968f;
        }


        /* ================================================
           CONFIGURATION
        ================================================ */

        .configuration {
          background: white;

          border:
            1px solid #e2e8e2;

          border-radius: 18px;

          padding: 24px;

          margin-bottom: 22px;

          box-shadow:
            0 5px 20px
            rgba(27,55,38,.035);
        }


        .section-title {
          margin:
            0 0 6px;

          font-size: 22px;
        }


        .section-description {
          color: #78857e;

          font-size: 12px;

          margin-bottom: 20px;
        }


        .configuration-grid {
          display: grid;

          grid-template-columns:
            repeat(4,1fr);

          gap: 15px;

          align-items: end;
        }


        .field label {
          display: block;

          color: #637269;

          font-size: 12px;

          font-weight: 750;

          margin-bottom: 7px;
        }


        .field input,
        .field select {
          width: 100%;

          height: 45px;

          border:
            1px solid #d8e0d9;

          border-radius: 10px;

          background: #fbfcfb;

          padding:
            0 12px;

          color: #1a2c21;

          outline: none;
        }


        .input-unit {
          position: relative;
        }


        .input-unit input {
          padding-right: 55px;
        }


        .input-unit span {
          position: absolute;

          right: 12px;

          top: 50%;

          transform:
            translateY(-50%);

          color: #829087;

          font-size: 12px;

          font-weight: 700;
        }


        .update-button {
          height: 45px;

          border: none;

          border-radius: 10px;

          padding:
            0 18px;

          background: #b9ef17;

          color: #17230e;

          font-weight: 850;
        }


        .update-button:disabled {
          opacity: .6;

          cursor: wait;
        }


        /* ================================================
           HERO
        ================================================ */

        .hero {
          background:
            linear-gradient(
              135deg,
              #092c1e,
              #102c20 60%,
              #063722
            );

          color: white;

          border-radius: 22px;

          padding: 31px;

          min-height: 210px;

          display: grid;

          grid-template-columns:
            1fr auto;

          align-items: center;

          gap: 30px;

          box-shadow:
            0 15px 40px
            rgba(8,47,29,.15);

          margin-bottom: 22px;
        }


        .hero-label {
          color: #b8d55c;

          font-size: 11px;

          font-weight: 800;

          letter-spacing: 1.6px;

          text-transform:
            uppercase;
        }


        .hero-main {
          display: flex;

          align-items:
            baseline;

          gap: 10px;

          margin-top: 10px;

          flex-wrap: wrap;
        }


        .need {
          font-size: 15px;

          color: #d9e5dc;

          font-weight: 700;
        }


        .depth {
          font-size: 42px;

          font-weight: 850;

          letter-spacing: -1.5px;
        }


        .mm {
          font-size: 15px;

          color: #b8c9bf;
        }


        .hero-description {
          color: #aebfb5;

          font-size: 13px;

          margin-top: 9px;
        }


        .hero-actions {
          display: flex;

          gap: 10px;

          margin-top: 20px;

          flex-wrap: wrap;
        }


        .primary-button {
          border: none;

          background: #b9ef17;

          color: #14200e;

          border-radius: 10px;

          padding:
            12px 17px;

          font-weight: 850;
        }


        .secondary-button {
          border:
            1px solid
            rgba(255,255,255,.18);

          background:
            rgba(255,255,255,.08);

          color: white;

          border-radius: 10px;

          padding:
            12px 17px;

          font-weight: 750;
        }


        .water-total {
          min-width: 240px;

          text-align: center;

          padding: 20px;

          border:
            1px solid
            rgba(255,255,255,.12);

          border-radius: 18px;

          background:
            rgba(255,255,255,.04);
        }


        .water-number {
          font-size: 30px;

          font-weight: 850;

          margin-top: 4px;
        }


        .water-label {
          color: #aebfb5;

          font-size: 12px;
        }


        /* ================================================
           SENSOR CARDS
        ================================================ */

        .cards {
          display: grid;

          grid-template-columns:
            repeat(4,1fr);

          gap: 16px;

          margin-bottom: 22px;
        }


        .card {
          background: white;

          border:
            1px solid #e2e8e2;

          border-radius: 17px;

          padding: 20px;

          min-height: 145px;

          box-shadow:
            0 5px 20px
            rgba(27,55,38,.035);
        }


        .card-icon {
          width: 35px;
          height: 35px;

          border-radius: 10px;

          background: #f0f5e9;

          display: flex;

          align-items: center;

          justify-content: center;

          margin-bottom: 16px;
        }


        .card-title {
          color: #718078;

          font-size: 12px;

          font-weight: 700;
        }


        .card-value {
          margin-top: 5px;

          font-size: 26px;

          font-weight: 850;
        }


        .card-source {
          color: #9aa59f;

          font-size: 10px;

          margin-top: 4px;
        }


        /* ================================================
           PANELS
        ================================================ */

        .two-column {
          display: grid;

          grid-template-columns:
            1.15fr .85fr;

          gap: 18px;

          margin-bottom: 22px;
        }


        .panel {
          background: white;

          border:
            1px solid #e2e8e2;

          border-radius: 18px;

          padding: 24px;

          box-shadow:
            0 5px 20px
            rgba(27,55,38,.035);
        }


        .panel h3 {
          margin: 0;

          font-size: 20px;
        }


        .panel-description {
          color: #85918a;

          font-size: 12px;

          margin-top: 5px;
        }


        /* ================================================
           WEATHER
        ================================================ */

        .forecast-row {
          display: grid;

          grid-template-columns:
            1fr 1fr;

          gap: 15px;

          margin-top: 22px;
        }


        .forecast-item {
          padding: 18px;

          border-radius: 14px;

          background: #f7f9f6;

          border:
            1px solid #e8eee8;
        }


        .forecast-period {
          color: #7d8982;

          font-size: 11px;

          font-weight: 800;

          text-transform:
            uppercase;
        }


        .forecast-value {
          font-size: 25px;

          font-weight: 850;

          margin-top: 8px;
        }


        .forecast-probability {
          color: #77857c;

          font-size: 11px;

          margin-top: 4px;
        }


        .rain-note {
          margin-top: 15px;

          padding:
            12px 14px;

          background: #f1f7df;

          border-radius: 10px;

          color: #54622d;

          font-size: 12px;
        }


        /* ================================================
           INSIGHTS
        ================================================ */

        .insight-grid {
          display: grid;

          grid-template-columns:
            repeat(2,1fr);

          gap: 12px;

          margin-top: 20px;
        }


        .insight {
          padding: 17px;

          border-radius: 14px;

          background: #f8faf7;

          border:
            1px solid #e8eee8;
        }


        .insight-label {
          color: #7a8780;

          font-size: 11px;

          font-weight: 700;
        }


        .insight-value {
          font-size: 22px;

          font-weight: 850;

          margin-top: 5px;
        }


        /* ================================================
           WATER TANK
        ================================================ */

        .tank-panel {
          margin-bottom: 22px;
        }


        .tank-head {
          display: flex;

          justify-content:
            space-between;

          align-items: center;

          gap: 15px;
        }


        .tank-status {
          padding:
            6px 10px;

          border-radius: 999px;

          font-size: 10px;

          font-weight: 850;
        }


        .tank-status.normal {
          background: #edf7df;

          color: #4e7021;
        }


        .tank-status.low {
          background: #fff4d9;

          color: #8a6515;
        }


        .tank-status.critical {
          background: #ffe8e4;

          color: #a23d31;
        }


        .tank-bar {
          height: 18px;

          border-radius: 999px;

          background: #edf1ed;

          overflow: hidden;

          margin-top: 18px;
        }


        .tank-fill {
          height: 100%;

          border-radius: 999px;

          background: #8fcf32;

          transition: width .5s;
        }


        .tank-meta {
          display: flex;

          justify-content:
            space-between;

          gap: 10px;

          margin-top: 9px;

          color: #748078;

          font-size: 12px;
        }


        /* ================================================
           PUMP
        ================================================ */

        .pump {
          display: flex;

          justify-content:
            space-between;

          align-items: center;

          gap: 20px;

          padding: 20px;

          border-radius: 15px;

          background: #102117;

          color: white;
        }


        .pump-label {
          color: #b9d95b;

          font-size: 10px;

          font-weight: 800;

          letter-spacing: 1.5px;

          text-transform:
            uppercase;
        }


        .pump-time {
          font-size: 29px;

          font-weight: 850;

          margin-top: 5px;
        }


        .pump-details {
          color: #a9b9af;

          font-size: 12px;

          margin-top: 5px;
        }


        .manual-button {
          border:
            1px solid
            rgba(255,255,255,.15);

          background: white;

          color: #14241a;

          padding:
            11px 15px;

          border-radius: 10px;

          font-weight: 800;
        }


        .manual-button.active {
          background: #b9ef17;
        }


        /* ================================================
           PLANT HEALTH
        ================================================ */

        .health-status {
          display: flex;

          align-items: center;

          gap: 12px;

          margin: 20px 0;
        }


        .health-dot {
          width: 14px;
          height: 14px;

          background: #a8db22;

          border-radius: 50%;

          box-shadow:
            0 0 0 5px #eef6d9;
        }


        .health-message {
          color: #66736c;

          line-height: 1.6;

          font-size: 13px;
        }


        .health-list {
          display: grid;

          grid-template-columns:
            repeat(4,1fr);

          gap: 10px;

          margin-top: 18px;
        }


        .health-item {
          padding: 13px;

          background: #f7f9f6;

          border-radius: 10px;
        }


        .health-item span {
          display: block;

          color: #849088;

          font-size: 10px;
        }


        .health-item strong {
          display: block;

          margin-top: 4px;
        }


        /* ================================================
           ERROR
        ================================================ */

        .error {
          margin-bottom: 18px;

          padding:
            12px 15px;

          background: #fff2f0;

          color: #9d3b31;

          border:
            1px solid #f2d5d0;

          border-radius: 10px;

          font-size: 12px;
        }


        /* ================================================
           MOBILE
        ================================================ */

        @media (max-width:1100px) {

          .configuration-grid,
          .cards {
            grid-template-columns:
              repeat(2,1fr);
          }

          .two-column {
            grid-template-columns: 1fr;
          }

          .health-list {
            grid-template-columns:
              repeat(2,1fr);
          }

        }


        @media (max-width:800px) {

          .sidebar {
            width: 72px;

            padding:
              20px 10px;
          }

          .brand-name,
          .brand-small,
          .brand-subtitle,
          .sidebar-bottom,
          .nav-button span:not(.nav-icon) {
            display: none;
          }

          .nav-button {
            justify-content: center;
          }

          .main {
            margin-left: 72px;

            width:
              calc(100% - 72px);

            padding:
              25px 18px 45px;
          }

          .hero {
            grid-template-columns: 1fr;
          }

          .water-total {
            width: 100%;
          }

        }


        @media (max-width:600px) {

          .configuration-grid,
          .cards,
          .forecast-row,
          .insight-grid,
          .health-list {
            grid-template-columns: 1fr;
          }

          .topbar {
            align-items:
              flex-start;
          }

          .page-title {
            font-size: 27px;
          }

          .pump {
            align-items:
              flex-start;

            flex-direction:
              column;
          }

          .connection-bar {
            align-items:
              flex-start;

            flex-direction:
              column;
          }

        }

      `}</style>


      <div className="agro-app">


        {/* ==================================================
            SIDEBAR
        ================================================== */}

        <aside className="sidebar">

          <div className="brand">

            <div className="brand-small">
              Smart Agriculture
            </div>

            <div className="brand-name">
              Agromind
            </div>

            <div className="brand-subtitle">
              AI-Optimized Irrigation
            </div>

          </div>


          <nav className="nav">

            <button
              className={
                `nav-button ${
                  activeSection === "overview"
                    ? "active"
                    : ""
                }`
              }
              onClick={() =>
                scrollToSection("overview")
              }
            >

              <span className="nav-icon">
                ⌂
              </span>

              <span>
                Overview
              </span>

            </button>


            <button
              className={
                `nav-button ${
                  activeSection === "irrigation"
                    ? "active"
                    : ""
                }`
              }
              onClick={() =>
                scrollToSection("irrigation")
              }
            >

              <span className="nav-icon">
                💧
              </span>

              <span>
                Irrigation
              </span>

            </button>


            <button
              className={
                `nav-button ${
                  activeSection === "weather"
                    ? "active"
                    : ""
                }`
              }
              onClick={() =>
                scrollToSection("weather")
              }
            >

              <span className="nav-icon">
                ☁
              </span>

              <span>
                Weather
              </span>

            </button>


            <button
              className={
                `nav-button ${
                  activeSection === "water"
                    ? "active"
                    : ""
                }`
              }
              onClick={() =>
                scrollToSection("water")
              }
            >

              <span className="nav-icon">
                🚰
              </span>

              <span>
                Water Tank
              </span>

            </button>


            <button
              className={
                `nav-button ${
                  activeSection === "plant-health"
                    ? "active"
                    : ""
                }`
              }
              onClick={() =>
                scrollToSection("plant-health")
              }
            >

              <span className="nav-icon">
                🌱
              </span>

              <span>
                Plant Health
              </span>

            </button>

          </nav>


          <div className="sidebar-bottom">

            <div>

              <span
                className={
                  `online-dot ${
                    isRealEsp32
                      ? ""
                      : "demo"
                  }`
                }
              />

              <span
                className={
                  `online-text ${
                    isRealEsp32
                      ? ""
                      : "demo"
                  }`
                }
              >

                {isRealEsp32
                  ? "ESP32 Online"
                  : "Demo Mode"}

              </span>

            </div>


            <div className="model-text">

              AOSIS-v14 •{" "}
              {farm.crop_type}

            </div>

          </div>

        </aside>


        {/* ==================================================
            MAIN
        ================================================== */}

        <main className="main">


          {/* ==================================================
              HEADER
          ================================================== */}

          <header
            className="topbar"
            id="overview"
          >

            <div>

              <div className="eyebrow">
                AI-Optimized Irrigation
              </div>

              <h1 className="page-title">
                Good morning, Farmer.
              </h1>

              <p className="page-subtitle">

                {isRealEsp32
                  ? "Your ESP32-S3 is sending live farm data."
                  : "Here's what your farm needs today."}

              </p>

            </div>


            <button
              className="refresh-button"
              onClick={() =>
                loadDashboard(true)
              }
              disabled={loading}
            >

              ↻{" "}

              {loading
                ? "Refreshing..."
                : "Refresh"}

            </button>

          </header>


          {/* ==================================================
              CONNECTION
          ================================================== */}

          <div className="connection-bar">

            <div className="connection-left">

              <span
                className={
                  `connection-led ${
                    isRealEsp32
                      ? "live"
                      : ""
                  }`
                }
              />

              {isRealEsp32
                ? "Live ESP32-S3 telemetry connected"
                : "Waiting for ESP32-S3 telemetry"}

            </div>


            <div className="connection-time">

              {telemetry.last_update

                ? `Last update: ${
                    new Date(
                      telemetry.last_update
                    ).toLocaleTimeString()
                  }`

                : "No live sensor update yet"}

            </div>

          </div>


          {/* ==================================================
              ERROR
          ================================================== */}

          {error && (

            <div className="error">
              {error}
            </div>

          )}


          {/* ==================================================
              FARM CONFIGURATION
          ================================================== */}

          <section className="configuration">

            <div className="eyebrow">
              Farm Setup
            </div>

            <h2 className="section-title">
              Farm Configuration
            </h2>

            <div className="section-description">

              These values describe the farmer's
              field and irrigation equipment.
              They are not ESP32 sensor readings.

            </div>


            <div className="configuration-grid">


              {/* CROP */}

              <div className="field">

                <label>
                  Crop
                </label>

                <select
                  value={farm.crop_type}
                  onChange={(e) =>
                    updateFarm(
                      "crop_type",
                      e.target.value
                    )
                  }
                >

                  {CROP_OPTIONS.map(
                    (crop) => (

                      <option
                        key={crop}
                        value={crop}
                      >
                        {crop}
                      </option>

                    )
                  )}

                </select>

              </div>


              {/* LAND SIZE */}

              <div className="field">

                <label>
                  Land Size
                </label>

                <div className="input-unit">

                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={
                      farm.land_size_m2
                    }
                    onChange={(e) =>
                      updateFarm(
                        "land_size_m2",
                        e.target.value
                      )
                    }
                  />

                  <span>
                    m²
                  </span>

                </div>

              </div>


              {/* CROP AGE */}

              <div className="field">

                <label>
                  Crop Age
                </label>

                <div className="input-unit">

                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={
                      farm.crop_age_days
                    }
                    onChange={(e) =>
                      updateFarm(
                        "crop_age_days",
                        e.target.value
                      )
                    }
                  />

                  <span>
                    days
                  </span>

                </div>

              </div>


              {/* PUMP FLOW */}

              <div className="field">

                <label>
                  Pump Flow Rate
                </label>

                <div className="input-unit">

                  <input
                    type="number"
                    min="0.1"
                    step="0.1"
                    value={
                      farm.pump_flow_L_min
                    }
                    onChange={(e) =>
                      updateFarm(
                        "pump_flow_L_min",
                        e.target.value
                      )
                    }
                  />

                  <span>
                    L/min
                  </span>

                </div>

              </div>

            </div>


            <button
              className="update-button"
              style={{
                marginTop: "18px",
                width: "100%",
              }}
              onClick={
                updateRecommendation
              }
              disabled={updating}
            >

              {updating
                ? "Calculating New Recommendation..."
                : "Update Recommendation"}

            </button>

          </section>


          {/* ==================================================
              IRRIGATION
          ================================================== */}

          <section
            id="irrigation"
            className="hero"
          >

            <div>

              <div className="hero-label">
                Today's Irrigation Recommendation
              </div>


              <div className="hero-main">

                <span className="need">
                  Need {needLevel}
                </span>


                <span className="depth">
                  {number(
                    irrigationDepth,
                    3
                  )}
                </span>


                <span className="mm">
                  mm
                </span>

              </div>


              <div className="hero-description">

                Recommended daily application depth
                based on live soil, weather and
                crop conditions.

              </div>


              <div className="hero-actions">

                <button
                  className="primary-button"
                  onClick={() =>
                    scrollToSection(
                      "pump-window"
                    )
                  }
                >

                  💧 View Pump Schedule

                </button>


                <button
                  className="secondary-button"
                  onClick={
                    updateRecommendation
                  }
                  disabled={updating}
                >

                  ↻ Recalculate

                </button>

              </div>

            </div>


            <div className="water-total">

              <div
                style={{
                  fontSize: "35px",
                }}
              >
                💧
              </div>

              <div className="water-number">

                {number(
                  waterRequired,
                  2
                )}

              </div>

              <div className="water-label">

                Litres required today

              </div>

            </div>

          </section>


          {/* ==================================================
              SENSOR CARDS
          ================================================== */}

          <section className="cards">


            {/* SOIL */}

            <div className="card">

              <div className="card-icon">
                💧
              </div>

              <div className="card-title">
                Soil Moisture
              </div>

              <div className="card-value">

                {number(
                  telemetry.soil_moisture_pct,
                  0
                )}%

              </div>

              <div className="card-source">

                {isRealEsp32
                  ? "ESP32-S3 live sensor"
                  : "Waiting for sensor"}

              </div>

            </div>


            {/* TEMPERATURE */}

            <div className="card">

              <div className="card-icon">
                🌡
              </div>

              <div className="card-title">
                Temperature / Humidity
              </div>

              <div className="card-value">

                {number(
                  telemetry.soil_temperature_C,
                  1
                )}°C

              </div>

              <div className="card-source">

                {number(
                  telemetry.humidity_pct,
                  1
                )}% humidity • DHT22

              </div>

            </div>


            {/* WATER */}

            <div className="card">

              <div className="card-icon">
                🚰
              </div>

              <div className="card-title">
                Water Tank
              </div>

              <div className="card-value">

                {number(
                  waterLevel,
                  0
                )}%

              </div>

              <div className="card-source">

                {number(
                  waterRemaining,
                  3
                )} L remaining

                {" • "}

                ADC{" "}
                {telemetry.water_sensor_adc ?? "--"}

              </div>

            </div>


            {/* RAIN */}

            <div className="card">

              <div className="card-icon">
                🌧
              </div>

              <div className="card-title">
                Rain — 48 hours
              </div>

              <div className="card-value">

                {number(
                  telemetry.rain_24_48h_mm,
                  1
                )} mm

              </div>

              <div className="card-source">

                {percent(
                  telemetry.rain_probability_24_48h
                )}

                {" probability • OpenWeather"}

              </div>

            </div>

          </section>


          {/* ==================================================
              WEATHER
          ================================================== */}

          <section
            id="weather"
            className="two-column"
          >


            <div className="panel">

              <h3>
                48-hour forecast
              </h3>

              <div className="panel-description">

                Rainfall-aware scheduling from OpenWeather

              </div>


              <div className="forecast-row">


                <div className="forecast-item">

                  <div className="forecast-period">
                    Next 24 hours
                  </div>

                  <div className="forecast-value">

                    {number(
                      telemetry.rain_0_24h_mm,
                      1
                    )} mm

                  </div>

                  <div className="forecast-probability">

                    {percent(
                      telemetry.rain_probability_0_24h
                    )}

                    {" probability"}

                  </div>

                </div>


                <div className="forecast-item">

                  <div className="forecast-period">
                    24–48 hours
                  </div>

                  <div className="forecast-value">

                    {number(
                      telemetry.rain_24_48h_mm,
                      1
                    )} mm

                  </div>

                  <div className="forecast-probability">

                    {percent(
                      telemetry.rain_probability_24_48h
                    )}

                    {" probability"}

                  </div>

                </div>

              </div>


              <div className="rain-note">

                🌿 Agromind considers expected
                rainfall before calculating the
                irrigation requirement.

              </div>


              <div
                style={{
                  marginTop: "18px",
                  color: "#718078",
                  fontSize: "12px",
                }}
              >

                Solar irradiance:{" "}

                <strong>

                  {number(
                    telemetry.solar_irradiance_W_m2,
                    0
                  )}

                  {" W/m²"}

                </strong>

              </div>

            </div>


            {/* INSIGHTS */}

            <div className="panel">

              <h3>
                Water & Irrigation Insights
              </h3>

              <div className="panel-description">

                Calculated from your current
                farm settings

              </div>


              <div className="insight-grid">


                <div className="insight">

                  <div className="insight-label">
                    Water Required
                  </div>

                  <div className="insight-value">

                    {number(
                      waterRequired,
                      0
                    )} L

                  </div>

                </div>


                <div className="insight">

                  <div className="insight-label">
                    Pump Runtime
                  </div>

                  <div className="insight-value">

                    {number(
                      pumpRuntime,
                      2
                    )} min

                  </div>

                </div>


                <div className="insight">

                  <div className="insight-label">
                    Pump Flow
                  </div>

                  <div className="insight-value">

                    {number(
                      pumpFlow,
                      1
                    )} L/min

                  </div>

                </div>


                <div className="insight">

                  <div className="insight-label">
                    Efficiency
                  </div>

                  <div className="insight-value">

                    {number(
                      Number(
                        farm.application_efficiency
                      ) * 100,
                      0
                    )}%

                  </div>

                </div>

              </div>

            </div>

          </section>


          {/* ==================================================
              WATER TANK
          ================================================== */}

          <section
            id="water"
            className="panel tank-panel"
          >

            <div className="tank-head">

              <div>

                <div className="eyebrow">
                  Water Storage
                </div>

                <h3>
                  Tank Level
                </h3>

                <div className="panel-description">

                  Measured by the resistive
                  water-level sensor connected
                  to GPIO 3.

                </div>

              </div>


              <span
                className={
                  `tank-status ${
                    waterStatusClass
                  }`
                }
              >

                {waterStatus}

              </span>

            </div>


            <div className="tank-bar">

              <div
                className="tank-fill"
                style={{
                  width:
                    `${Math.max(
                      0,
                      Math.min(
                        100,
                        waterLevel
                      )
                    )}%`,
                }}
              />

            </div>


            <div className="tank-meta">

              <span>
                {number(
                  waterLevel,
                  1
                )}% full
              </span>

              <span>
                {number(
                  waterRemaining,
                  3
                )} L remaining
              </span>

              <span>
                ADC:{" "}
                {telemetry.water_sensor_adc ??
                  "--"}
              </span>

            </div>

          </section>


          {/* ==================================================
              PUMP WINDOW
          ================================================== */}

          <section
            id="pump-window"
            className="panel"
            style={{
              marginBottom: "22px",
            }}
          >

            <div className="eyebrow">
              Today's Pump Window
            </div>


            <div className="pump">

              <div>

                <div className="pump-label">
                  Recommended operation
                </div>


                <div className="pump-time">

                  {schedule?.recommended_start ||
                    farm.start_time ||
                    "06:00"}

                  {" – "}

                  {schedule?.recommended_end ||
                    "--:--"}

                </div>


                <div className="pump-details">

                  {number(
                    pumpRuntime,
                    2
                  )}

                  {" minutes • "}

                  {number(
                    pumpFlow,
                    1
                  )}

                  {" L/min • "}

                  {number(
                    waterRequired,
                    2
                  )}

                  {" L"}

                </div>

              </div>


              <button
                className={
                  manualMode
                    ? "manual-button active"
                    : "manual-button"
                }
                onClick={() =>
                  setManualMode(
                    (value) =>
                      !value
                  )
                }
              >

                ⚡{" "}

                {manualMode
                  ? "Manual Mode ON"
                  : "Manual Override"}

              </button>

            </div>

          </section>


          {/* ==================================================
              PLANT HEALTH
          ================================================== */}

          <section
            id="plant-health"
            className="panel"
          >

            <div className="eyebrow">
              Crop Monitoring
            </div>


            <h3>
              Plant Health
            </h3>


            <div className="health-status">

              <div className="health-dot"></div>

              <strong>
                {needLevel}
                {" "}
                irrigation requirement
              </strong>

            </div>


            <div className="health-message">

              Your{" "}
              {farm.crop_type}
              {" "}crop is{" "}
              {farm.crop_age_days}
              {" "}days old.

              {" "}Current soil moisture is{" "}
              {number(
                telemetry.soil_moisture_pct,
                0
              )}%.

              {" "}Agromind combines crop
              configuration, live soil data
              and weather information to
              calculate the irrigation
              requirement.

            </div>


            <div className="health-list">


              <div className="health-item">

                <span>
                  Crop
                </span>

                <strong>
                  {farm.crop_type}
                </strong>

              </div>


              <div className="health-item">

                <span>
                  Crop Age
                </span>

                <strong>

                  {farm.crop_age_days}
                  {" "}days

                </strong>

              </div>


              <div className="health-item">

                <span>
                  Land Size
                </span>

                <strong>

                  {number(
                    farm.land_size_m2,
                    0
                  )} m²

                </strong>

              </div>


              <div className="health-item">

                <span>
                  Soil ADC
                </span>

                <strong>

                  {telemetry.soil_adc ??
                    "--"}

                </strong>

              </div>

            </div>

          </section>

        </main>

      </div>

    </>

  );
}


// ============================================================
// REACT ROOT
// ============================================================

createRoot(
  document.getElementById("root")
).render(

  <React.StrictMode>

    <App />

  </React.StrictMode>

);
