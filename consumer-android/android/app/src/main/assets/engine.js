/* BoundaryCast mobile public-policy subset.
 * Derived from public claim_scope.py, checks.py and rule_engine.py at 584bea49.
 * No private provider, synthetic live values, probability calibration or production Gatekeeper authority.
 */
(function(root){
"use strict";
const POLICY="boundarycast-mobile-nws-v1.0.0",HOUR=3600000,MIN=60000;
const object=x=>x&&typeof x==="object"&&!Array.isArray(x)?x:null;
const finite=x=>typeof x==="number"&&Number.isFinite(x);
const str=(x,max=200)=>typeof x==="string"?x.trim().slice(0,max):"";
const timestamp=x=>typeof x==="string"&&/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(x)?Date.parse(x):NaN;
const iso=x=>Number.isFinite(x)?new Date(x).toISOString():null;
const recent=(t,now,minutes)=>Number.isFinite(t)&&t<=now+5*MIN&&t>=now-minutes*MIN;
const bounded=(x,lo,hi)=>finite(x)&&x>=lo&&x<=hi;
function quant(q,kind){
 if(!object(q)||!finite(q.value))return null;
 if(q.qualityControl!==undefined&&q.qualityControl!==null&&!["V","S","C"].includes(q.qualityControl))return null;
 const u=q.unitCode,v=q.value;let n;
 if(kind==="temp"){if(u==="wmoUnit:degC")n=v*9/5+32;else if(u==="wmoUnit:degF")n=v;else return null;return bounded(n,-130,140)?Math.round(n*10)/10:null;}
 if(kind==="wind"){if(u==="wmoUnit:km_h-1")n=v/1.609344;else if(u==="wmoUnit:m_s-1")n=v*2.236936292;else if(u==="wmoUnit:mi_h-1")n=v;else if(u==="wmoUnit:kn")n=v*1.15077945;else return null;return bounded(n,0,350)?Math.round(n*10)/10:null;}
 return null;
}
function parseAlerts(raw,now){
 if(raw?.status?.alerts!=="ok"||!Array.isArray(raw.alerts?.features))return {checked:false,active:[],malformed:false};
 const active=[];let malformed=false;
 for(const feature of raw.alerts.features){
  const p=object(feature?.properties);
  if(!p){malformed=true;continue;}
  if(p.status==="Test"||p.status==="Exercise"||p.status==="Draft"||p.status==="System"||p.messageType==="Cancel")continue;
  // Active endpoint supplies active events. Do not discard a future-onset active warning.
  if(p.status!=="Actual"||!str(p.event)||!["Extreme","Severe","Moderate","Minor","Unknown"].includes(p.severity)){malformed=true;continue;}
  const expires=timestamp(p.expires);if(!Number.isFinite(expires)){malformed=true;continue;}if(expires<=now)continue;
  active.push({event:str(p.event),severity:p.severity,headline:str(p.headline,500),description:str(p.description,12000),instruction:str(p.instruction,12000),expires:iso(expires),effective:iso(timestamp(p.effective))});
 }
 return {checked:!malformed,active,malformed};
}
function parseForecast(raw,now){
 const p=object(raw?.forecast?.properties);
 if(raw?.status?.forecast!=="ok"||!p||!Array.isArray(p.periods))return null;
 // Area-forecast freshness is a public mobile policy, not a calibrated private threshold.
 const issue=timestamp(p.updateTime);if(!recent(issue,now,720))return null;
 const seen=new Set(),hours=[];
 for(const x of p.periods){
  const start=timestamp(x?.startTime),end=timestamp(x?.endTime);
  if(!Number.isFinite(start)||!Number.isFinite(end)||end<=start||end-start>2*HOUR||end<=now||start>now+24*HOUR||seen.has(start))continue;
  const t=x.temperatureUnit==="F"?x.temperature:x.temperatureUnit==="C"&&finite(x.temperature)?x.temperature*9/5+32:null;
  if(!bounded(t,-130,140)||!str(x.shortForecast))continue;
  let rain=x.probabilityOfPrecipitation?.value;
  if(!bounded(rain,0,100)||x.probabilityOfPrecipitation?.unitCode!=="wmoUnit:percent")rain=null;
  seen.add(start);hours.push({start:iso(start),end:iso(end),temperatureF:Math.round(t),summary:str(x.shortForecast),wind:str(x.windSpeed,60)||null,direction:str(x.windDirection,20)||null,precipPercent:rain});
 }
 hours.sort((a,b)=>Date.parse(a.start)-Date.parse(b.start));
 if(!hours.length||Date.parse(hours[0].start)>now+2*HOUR)return null;
 return {issuedAt:iso(issue),hours:hours.slice(0,24)};
}
function parseObservation(raw,now){
 const candidates=[];
 for(const x of Array.isArray(raw?.observations)?raw.observations:[]){
  const p=object(x?.properties),distance=x?.distanceKm,when=timestamp(p?.timestamp);
  if(!p||!bounded(distance,0,10)||!recent(when,now,90)||!str(x.stationId,16))continue;
  const temp=quant(p.temperature,"temp"),wind=quant(p.windSpeed,"wind");
  if(temp===null)continue; // Only a fresh real temperature observation supports the nearby scope.
  candidates.push({stationId:str(x.stationId,16),stationName:str(x.stationName)||str(x.stationId,16),distanceKm:Math.round(distance*10)/10,observedAt:iso(when),temperatureF:temp,windMph:wind,description:str(p.textDescription)||null});
 }
 candidates.sort((a,b)=>a.distanceKm-b.distanceKm);
 return candidates[0]||null;
}
function decide(checks){
 if(checks.severeAlert===true)return {verdict:"PROTOCOL",claimScope:"official_alert_only",reasons:["official_alert_supremacy","official_alert_scope_governs"]};
 const reasons=[];
 if(checks.alertChecked!==true)reasons.push("official_alert_check_unavailable");
 if(checks.officialForecast!==true)reasons.push("missing_or_stale_official_forecast");
 if(reasons.length)return {verdict:"ABSTAIN",claimScope:"unsupported_specific_claim",reasons:[...reasons,"unsupported_specific_claim"]};
 if(checks.observation===true)return {verdict:"PERMIT_WITH_CAUTION",claimScope:"nearby_observation_area",reasons:["nearby_observation_scope_supported","low_microclimate_confidence","unsupported_specific_claim"]};
 return {verdict:"PERMIT_WITH_CAUTION",claimScope:"official_forecast_area",reasons:["official_area_scope_supported","observation_stale_or_missing","low_microclimate_confidence","unsupported_specific_claim"]};
}
function evaluate(raw,now=Date.now()){
 const alerts=parseAlerts(raw,now),forecast=parseForecast(raw,now),obs=parseObservation(raw,now);
 const checks={severeAlert:alerts.active.some(a=>a.severity==="Severe"||a.severity==="Extreme"),alertChecked:alerts.checked&&raw?.status?.point==="ok",officialForecast:!!forecast&&raw?.status?.point==="ok",observation:!!obs};
 const decision=decide(checks),publish=decision.verdict==="PERMIT_WITH_CAUTION";
 // Receipt is an in-memory policy replay record. No raw point, city, device identifier, provider URL or exact location is included.
 const receipt={policy:POLICY,asOf:iso(now),requestedScope:"exact_location",checks,decision,
    evidence:{forecastIssuedAt:forecast?.issuedAt||null,observationTime:obs?.observedAt||null,station:obs?.stationId||null,activeAlerts:alerts.active.length}};
 return {decision,checks,receipt,alertStatus:checks.alertChecked?"checked":"unavailable",alerts:alerts.active,forecast:publish?forecast:null,observation:publish&&decision.claimScope==="nearby_observation_area"?obs:null,
  place:[str(raw?.city,80),str(raw?.state,20)].filter(Boolean).join(", ")||"Requested location",timeZone:str(raw?.timeZone,100),
  inputKind:raw?.inputKind==="device"?"device":"manual",accuracyM:bounded(raw?.accuracyM,0,100000)?Math.round(raw.accuracyM):null,asOf:iso(now)};
}
function canonical(x){if(x===null||typeof x!=="object")return JSON.stringify(x);if(Array.isArray(x))return "["+x.map(canonical).join(",")+"]";return "{"+Object.keys(x).sort().map(k=>JSON.stringify(k)+":"+canonical(x[k])).join(",")+"}";}
function replay(receipt){return receipt?.policy===POLICY&&canonical(decide(receipt.checks||{}))===canonical(receipt.decision);}
const api={POLICY,evaluate,decide,replay,canonical,quant,parseForecast,parseAlerts};
if(typeof module!=="undefined")module.exports=api;else root.BoundaryEngine=api;
})(globalThis);
