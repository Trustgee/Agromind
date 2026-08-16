
import React,{useEffect,useState} from "react";
import {createRoot} from "react-dom/client";
import {Droplets,Sun,CloudRain,Thermometer,Leaf,Clock3,Map,RefreshCw,Power,ChevronRight} from "lucide-react";
import "./styles.css";

const API=import.meta.env.VITE_API_URL||"";

function App(){
  const [data,setData]=useState(null);
  const [loading,setLoading]=useState(true);
  const [manual,setManual]=useState(false);

  async function load(){
    setLoading(true);
    try{
      const r=await fetch(`${API}/api/dashboard`);
      if(!r.ok) throw new Error("Dashboard API unavailable");
      setData(await r.json());
    }catch(e){
      setData(null);
    }finally{setLoading(false);}
  }
  useEffect(()=>{load()},[]);

  const t=data?.telemetry||{};
  const s=data?.schedule||{};
  const need=s.need_level||"—";

  return <div className="app">
    <aside className="sidebar">
      <div className="brand"><div className="brandmark">A</div><div><b>Agromind</b><span>Smart Agriculture</span></div></div>
      <nav>
        <a className="active">Overview</a><a>Farm Map</a><a>Irrigation</a><a>Weather</a><a>Plant Health</a>
      </nav>
      <div className="sidecard">
        <span>System</span><strong><i></i> Online</strong>
        <small>AOSIS v14 · Clay loam</small>
      </div>
    </aside>

    <main>
      <header>
        <div><div className="eyebrow">AI-OPTIMIZED IRRIGATION</div><h1>Good morning, Farmer.</h1><p>Here's what your farm needs today.</p></div>
        <button className="refresh" onClick={load}><RefreshCw size={16}/>{loading?"Updating":"Refresh"}</button>
      </header>

      <section className="hero">
        <div><div className="eyebrow">TODAY'S IRRIGATION RECOMMENDATION</div>
          <div className="recommend"><span className={`dot ${need.toLowerCase()}`}></span><b>{need}</b><span>need level</span></div>
          <h2>{s.irrigation_depth_mm??"—"} <small>mm</small></h2>
          <p>Recommended daily application depth for your {s.crop||"crop"} farm.</p>
          <div className="hero-actions"><button onClick={()=>setManual(true)}><Droplets size={17}/> Irrigate Now</button><button className="ghost">View Schedule <ChevronRight size={16}/></button></div>
        </div>
        <div className="hero-water"><div className="ring"><Droplets size={34}/><strong>{s.water_required_L??"—"}</strong><span>litres</span></div><div className="runtime"><Clock3 size={16}/> {s.pump_runtime_min??"—"} min runtime</div></div>
      </section>

      <div className="grid4">
        <Metric icon={<Droplets/>} label="Soil Moisture" value={t.soil_moisture_pct} unit="%" sub="Live sensor"/>
        <Metric icon={<Thermometer/>} label="Soil Temperature" value={t.soil_temperature_C} unit="°C" sub="ESP32-S3"/>
        <Metric icon={<Sun/>} label="Solar Irradiance" value={t.solar_irradiance_W_m2} unit="W/m²" sub="OpenWeather"/>
        <Metric icon={<CloudRain/>} label="Rain · 48 hours" value={t.rain_24_48h_mm} unit="mm" sub={`${Math.round((t.rain_probability_24_48h||0)*100)}% probability`}/>
      </div>

      <div className="two">
        <section className="panel">
          <div className="panelhead"><div><h3>48-hour forecast</h3><span>Rainfall-aware scheduling</span></div><CloudRain/></div>
          <div className="forecast">
            <div><span>Next 24h</span><b>{t.rain_0_24h_mm??0} mm</b><small>{Math.round((t.rain_probability_0_24h||0)*100)}% probability</small></div>
            <div className="divider"></div>
            <div><span>24–48h</span><b>{t.rain_24_48h_mm??0} mm</b><small>{Math.round((t.rain_probability_24_48h||0)*100)}% probability</small></div>
          </div>
          <div className="insight"><Leaf size={18}/><span>Agromind considers expected rainfall before calculating today's minimum irrigation dose.</span></div>
        </section>

        <section className="panel">
          <div className="panelhead"><div><h3>Farm visualization</h3><span>100 m² · {s.crop||"Tomato"}</span></div><Map/></div>
          <div className="farm">
            {[...Array(24)].map((_,i)=><div key={i} className={`plot ${i%7===0?"dry":""}`}></div>)}
            <div className="farmlabel">ZONE A<br/><small>Live monitoring</small></div>
          </div>
        </section>
      </div>

      <section className="schedulebar">
        <div><span className="eyebrow">TODAY'S PUMP WINDOW</span><strong>{s.recommended_start||"06:00"} — {s.recommended_end||"—"}</strong><small>{s.water_required_L??0} L · {s.pump_runtime_min??0} minutes · {s.pump_flow_L_min??0} L/min</small></div>
        <button onClick={()=>setManual(true)}><Power size={17}/> Manual Override</button>
      </section>

      {manual && <div className="modal"><div className="modalbox"><h2>Manual irrigation</h2><p>Send a manual irrigation command to the pump controller.</p><div className="warning">Hardware control is not connected in this web-only deployment.</div><button onClick={()=>setManual(false)}>Close</button></div></div>}
    </main>
  </div>
}

function Metric({icon,label,value,unit,sub}){
 return <div className="metric"><div className="metricicon">{icon}</div><span>{label}</span><strong>{value??"—"}<small>{unit}</small></strong><em>{sub}</em></div>
}
createRoot(document.getElementById("root")).render(<App/>);
