(function(){
"use strict";
const E=window.BoundaryEngine, $=id=>document.getElementById(id),result=$("results"), status=$("status");
let pending=null,seq=0,receipt=null;
const node=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
const add=(p,...items)=>{p.append(...items.filter(Boolean));return p;};
const card=(...items)=>add(node("section",undefined,"card"),...items);
const line=(s,cls="muted")=>node("p",s,cls);
const bridge=()=>window.AndroidWeather;
function setBusy(on){for(const id of ["geo","example"])$(id).disabled=on;$("coords").querySelector("button").disabled=on;}
function reset(){pending=null;receipt=null;setBusy(false);result.replaceChildren();$("lat").value="";$("lon").value="";status.textContent="Choose a location to request live evidence. No demo weather is shown.";}
function request(kind,lat,lon){
 if(pending)return;
 if(!bridge()){status.textContent="Open the Android app to request live evidence. This local preview has no provider connection.";return;}
 result.replaceChildren();receipt=null;pending="request-"+(++seq);setBusy(true);
 status.textContent="Checking live NWS evidence. Location, alerts, forecast and nearby stations may take several seconds.";
 try{if(kind==="device")bridge().locate(pending);else bridge().check(pending,lat,lon);}
 catch{pending=null;setBusy(false);status.textContent="Could not start a weather request.";}
}
function fmt(t,tz,short=false){
 if(!t)return "Unavailable";
 const d=new Date(t);if(!Number.isFinite(d.getTime()))return "Unavailable";
 const opts=short?{hour:"numeric",minute:"2-digit"}:{month:"short",day:"numeric",hour:"numeric",minute:"2-digit",timeZoneName:"short"};
 try{return new Intl.DateTimeFormat(undefined,{...opts,timeZone:tz||"UTC"}).format(d)+(tz?"":" UTC");}catch{return d.toISOString();}
}
function render(model){
 const d=model.decision;result.replaceChildren();
 const h=card(node("div",model.place,"eyebrow"));
 h.classList.add("scope");
 const labels={official_alert_only:"Official alert takes precedence",unsupported_specific_claim:"Live claim withheld",nearby_observation_area:"Nearby-area weather",official_forecast_area:"Official forecast area"};
 if(d.verdict==="PROTOCOL")h.classList.add("alert");
 if(d.verdict==="ABSTAIN")h.classList.add("hold");
 add(h,node("div",d.verdict==="PROTOCOL"?"OFFICIAL ALERT":d.verdict==="ABSTAIN"?"INSUFFICIENT EVIDENCE":"PUBLISH WITH CAUTION","tag"),node("h2",labels[d.claimScope]),line("Checked "+fmt(model.asOf,model.timeZone)));
 if(model.accuracyM!==null)add(h,line("Device location accuracy reported: approximately "+model.accuracyM+" m. Weather resolution is independent of GPS accuracy.","subtle"));
 if(d.verdict==="ABSTAIN")add(h,line("Required live evidence was unavailable or stale. BoundaryCast will not substitute synthetic weather. Check official NWS channels."));
 else if(d.verdict==="PROTOCOL")add(h,line("Follow official alert instructions. Routine forecast and station values are withheld in this view."));
 else add(h,line("This is area-level weather, not a measurement at your precise location. No microclimate correction is asserted."));
 result.append(h);
 if(model.alerts.length){
  const alerts=card(node("h2","Active official alerts"),line("National Weather Service. Read the official instructions. "+(model.alertStatus==="unavailable"?"Complete area/alert coverage could not be verified.":"")));
  for(const a of model.alerts){const item=node("div",undefined,"alertItem");add(item,node("h3",a.event),line(a.severity+" · Expires "+fmt(a.expires,model.timeZone)),a.headline?line(a.headline,"notice"):null,a.instruction?line(a.instruction,"notice"):null);if(a.description){const details=node("details");add(details,node("summary","Full alert description"),line(a.description,"notice"));item.append(details);}alerts.append(item);}
  result.append(alerts);
 }else result.append(card(node("h2","Official alert check"),line(model.alertStatus==="checked"?"No active alerts returned for this requested point at the time of the check. This is not a guarantee of safety.":"Alert status is unavailable. Do not interpret this as an all-clear.")));
 if(model.observation){
  const o=model.observation;result.append(card(node("div","NEARBY STATION · MEASURED","eyebrow"),node("h2",o.stationName),node("div",Math.round(o.temperatureF)+"°F","temp"),line(o.description||"Reported station temperature"),line(o.distanceKm.toFixed(1)+" km away · "+fmt(o.observedAt,model.timeZone)),line("Wind: "+(o.windMph===null?"Unavailable":o.windMph+" mph")),line("Station "+o.stationId+" · NWS observation. This is not a sensor at your exact location.","subtle")));
 }
 if(model.forecast){
  const f=model.forecast,first=f.hours[0],section=card(node("div","NWS GRID FORECAST · MODEL / FORECAST","eyebrow"),node("h2","Next forecast period"),node("div",first.temperatureF+"°F","temp"),line(first.summary),line(fmt(first.start,model.timeZone)+" to "+fmt(first.end,model.timeZone,true)),line("Wind: "+(first.wind||"Unavailable")+(first.direction?" "+first.direction:"")+" · Precipitation chance: "+(first.precipPercent===null?"Unavailable":first.precipPercent+"%")),line("Forecast updated "+fmt(f.issuedAt,model.timeZone),"subtle"),node("h3","Next 24 hours"));
  const hours=node("div",undefined,"hours");for(const x of f.hours){hours.append(add(node("div",undefined,"hour"),node("span",fmt(x.start,model.timeZone,true)),node("strong",x.temperatureF+"°"),node("span",x.summary),node("span",x.precipPercent===null?"Rain: —":"Precip: "+x.precipPercent+"%")));}section.append(hours);result.append(section);
 }
 const proof=card(node("h2","Evidence and decision receipt"),line("Public mobile policy "+E.POLICY+". Exact-location and microclimate claims are withheld."));
 const checks=node("div",undefined,"evidence");for(const [label,value] of [["Official alert evidence",model.checks.alertChecked],["Fresh area forecast",model.checks.officialForecast],["Fresh measured station within 10 km",model.checks.observation],["Severe or extreme alert",model.checks.severeAlert]])checks.append(node("div",label+": "+(value?"Yes":"No")));proof.append(checks);
 for(const reason of d.reasons)proof.append(line(reason.replaceAll("_"," ")));
 const hash=node("p","Local receipt digest pending…","hash"),replay=node("button","Replay policy decision","secondary"),message=node("p","","muted");
 receipt=model.receipt;const current=receipt;replay.addEventListener("click",()=>{message.textContent=E.replay(current)?"Policy replay matches the recorded decision.":"Policy replay mismatch.";});
 add(proof,hash,replay,message,line("In-memory receipt only. Not signed, not an independent weather accuracy proof. No coordinates or location history stored.","subtle"));result.append(proof);
 if(globalThis.crypto?.subtle){crypto.subtle.digest("SHA-256",new TextEncoder().encode(E.canonical(current))).then(b=>{if(receipt===current)hash.textContent="SHA-256: "+Array.from(new Uint8Array(b),x=>x.toString(16).padStart(2,"0")).join("");}).catch(()=>hash.textContent="Digest unavailable; policy replay remains available.");}else hash.textContent="Digest unavailable on this device.";
}
window.BoundaryCast={reset,receive(id,json){
 if(id!==pending)return;pending=null;setBusy(false);
 try{const raw=JSON.parse(json);if(raw.error){status.textContent=raw.error;return;}const model=E.evaluate(raw);status.textContent="Live check complete. Evidence limitations are shown below.";render(model);}
 catch{status.textContent="Evidence could not be evaluated. No live claim published.";result.replaceChildren();receipt=null;}
}};
$("geo").addEventListener("click",()=>request("device"));
$("coords").addEventListener("submit",ev=>{ev.preventDefault();if(!$("lat").value||!$("lon").value)return;const lat=Number($("lat").value),lon=Number($("lon").value);if(!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180){status.textContent="Enter valid coordinates.";return;}$("lat").value="";$("lon").value="";request("manual",lat,lon);});
$("example").addEventListener("click",()=>request("manual",39.7456,-97.0892));
$("clear").addEventListener("click",()=>{bridge()?.clear();reset();});
$("official").addEventListener("click",()=>bridge()?.openOfficial());
reset();
})();
