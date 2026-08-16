
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
        <section className="schedulebar">

  <div>
    <span className="eyebrow">
      TODAY'S PUMP WINDOW
    </span>

    <strong>
      {s.recommended_start || "06:00"} –{" "}
      {s.recommended_end || "--"}
    </strong>

    <small>
      {s.water_required_L ?? 0} L ·{" "}
      {s.pump_runtime_min ?? 0} minutes ·{" "}
      {s.pump_flow_L_min ?? 0} L/min
    </small>
  </div>

  <button onClick={() => setManual(true)}>
    <Power size={17} />
    Manual Override
  </button>

</section>
      </section>

      {manual && <div className="modal"><div className="modalbox"><h2>Manual irrigation</h2><p>Send a manual irrigation command to the pump controller.</p><div className="warning">Hardware control is not connected in this web-only deployment.</div><button onClick={()=>setManual(false)}>Close</button></div></div>}
    </main>
  </div>
}

function Metric({icon,label,value,unit,sub}){
 return <div className="metric"><div className="metricicon">{icon}</div><span>{label}</span><strong>{value??"—"}<small>{unit}</small></strong><em>{sub}</em></div>
}
createRoot(document.getElementById("root")).render(<App/>);
