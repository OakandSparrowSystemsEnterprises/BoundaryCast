const assert=require("node:assert/strict");
const E=require("./android/app/src/main/assets/engine.js");
const now=Date.parse("2026-11-23T20:00:00Z"),T=m=>new Date(now+m*60000).toISOString();
const base=()=>({status:{point:"ok",forecast:"ok",alerts:"ok",observations:"ok"},inputKind:"device",accuracyM:12,city:"Example",state:"KS",timeZone:"America/Chicago",latitude:39.7456,longitude:-97.0892,
 forecast:{properties:{updateTime:T(-60),periods:[{startTime:T(-30),endTime:T(30),temperature:55,temperatureUnit:"F",shortForecast:"Partly cloudy",windSpeed:"10 mph",windDirection:"N",probabilityOfPrecipitation:{unitCode:"wmoUnit:percent",value:20}}]}},
 observations:[{stationId:"KTEST",stationName:"Example station",distanceKm:5,properties:{timestamp:T(-20),temperature:{unitCode:"wmoUnit:degC",value:10,qualityControl:"V"},windSpeed:{unitCode:"wmoUnit:km_h-1",value:16.09344,qualityControl:"V"}}}],
 alerts:{features:[]}});
let n=0;const check=(v,m)=>{assert.ok(v,m);n++};
function scenario(mut,scope,verdict){let x=base();mut(x);let r=E.evaluate(x,now);check(r.decision.claimScope===scope&&r.decision.verdict===verdict,"scope "+scope);check(E.replay(r.receipt),"deterministic replay");if(verdict==="ABSTAIN"||verdict==="PROTOCOL")check(r.forecast===null&&r.observation===null,"withheld routine metrics");return r;}
const near=scenario(()=>{},"nearby_observation_area","PERMIT_WITH_CAUTION");
check(near.observation.temperatureF===50&&near.observation.windMph===10,"unit conversion");
check(near.forecast.hours[0].temperatureF===55,"forecast distinct from observation");
check(!E.canonical(near.receipt).includes("39.7456")&&!E.canonical(near.receipt).includes("-97.0892")&&!E.canonical(near.receipt).includes("Example"),"no coordinate or place in receipt");
for(const mut of [x=>x.observations=[],x=>x.observations[0].distanceKm=10.01,x=>x.observations[0].properties.timestamp=T(-91),x=>x.observations[0].properties.timestamp=T(6),x=>x.observations[0].properties.temperature.value=null,x=>x.observations[0].properties.temperature.unitCode="bad",x=>x.observations[0].properties.temperature.qualityControl="X"])scenario(mut,"official_forecast_area","PERMIT_WITH_CAUTION");
for(const mut of [x=>x.status.alerts="unavailable",x=>x.alerts={},x=>x.alerts.features=[{}],x=>x.forecast=null,x=>x.forecast.properties.updateTime=T(-721),x=>x.forecast.properties.updateTime="bad",x=>x.forecast.properties.periods=[],x=>x.forecast.properties.periods[0].temperature="55",x=>x.forecast.properties.periods[0].endTime=T(-1),x=>{x.forecast.properties.periods[0].startTime=T(121);x.forecast.properties.periods[0].endTime=T(181)}])scenario(mut,"unsupported_specific_claim","ABSTAIN");
const alert=(severity,status="Actual",expires=T(60))=>({properties:{event:"Example warning",severity,status,messageType:"Alert",headline:"Controlled fixture",description:"Fixture",instruction:"Follow official instructions",expires,effective:T(-5)}});
for(const sev of ["Severe","Extreme"])scenario(x=>{x.alerts.features=[alert(sev)];x.forecast=null},"official_alert_only","PROTOCOL");
scenario(x=>{x.alerts.features=[alert("Severe"),{}];x.forecast=null},"official_alert_only","PROTOCOL");
scenario(x=>x.alerts.features=[alert("Moderate")],"nearby_observation_area","PERMIT_WITH_CAUTION");
scenario(x=>x.alerts.features=[alert("Extreme","Test")],"nearby_observation_area","PERMIT_WITH_CAUTION");
scenario(x=>x.alerts.features=[alert("Extreme","Actual",T(-1))],"nearby_observation_area","PERMIT_WITH_CAUTION");
scenario(x=>x.status.point="unavailable","unsupported_specific_claim","ABSTAIN");
const uncovered=E.evaluate({...base(),status:{point:"unavailable",alerts:"ok"}},now);check(uncovered.alertStatus==="unavailable","unsupported point never produces all-clear");
scenario(x=>{x.status.point="unavailable";x.alerts.features=[alert("Severe")]},"official_alert_only","PROTOCOL");
const unknown=E.evaluate({},now);check(unknown.decision.verdict==="ABSTAIN"&&unknown.alertStatus==="unavailable","empty evidence no all-clear");
let p=base();p.forecast.properties.periods[0].probabilityOfPrecipitation.value=null;check(E.evaluate(p,now).forecast.hours[0].precipPercent===null,"missing precipitation stays unknown");
p=base();p.forecast.properties.periods[0].probabilityOfPrecipitation.value=101;check(E.evaluate(p,now).forecast.hours[0].precipPercent===null,"invalid probability");
p=base();p.forecast.properties.periods[0].temperatureUnit="C";p.forecast.properties.periods[0].temperature=10;check(E.evaluate(p,now).forecast.hours[0].temperatureF===50,"C conversion");
const altered=JSON.parse(JSON.stringify(near.receipt));altered.decision.claimScope="exact_location";check(!E.replay(altered),"tampered decision rejected");
for(let mask=0;mask<16;mask++){const d=E.decide({severeAlert:!!(mask&1),alertChecked:!!(mask&2),officialForecast:!!(mask&4),observation:!!(mask&8)});check(!["exact_location","microclimate_adjusted"].includes(d.claimScope),"no unsupported personal precision");if(mask&1)check(d.verdict==="PROTOCOL","alert precedence");}
const fs=require("node:fs"),path=require("node:path");
const root=path.join(__dirname,"android/app/src/main");
const native=fs.readFileSync(path.join(root,"java/io/oakandsparrow/boundarycast/MainActivity.java"),"utf8");
const network=fs.readFileSync(path.join(root,"java/io/oakandsparrow/boundarycast/NwsClient.java"),"utf8");
const manifest=fs.readFileSync(path.join(root,"AndroidManifest.xml"),"utf8");
const html=fs.readFileSync(path.join(root,"assets/index.html"),"utf8");
check(!manifest.includes("ACCESS_BACKGROUND_LOCATION")&&manifest.includes('android:allowBackup="false"'),"foreground permissions and no backup");
check(native.includes("setDomStorageEnabled(false)")&&native.includes("setWebContentsDebuggingEnabled(false)")&&native.includes("shouldInterceptRequest"),"local WebView boundaries");
check(network.includes('!"api.weather.gov".equals(u.getHost())')&&network.includes("setInstanceFollowRedirects(false)")&&network.includes("setUseCaches(false)")&&network.includes("hasUrgentAlert(alerts)"),"provider transport boundary");
check(!native.includes("Set.of(")&&native.includes("!locating"),"API 26 compatible set and single location launch");
check(html.includes("connect-src 'none'")&&html.includes("No demo weather is shown."),"UI evidence and CSP");
console.log("PASS: "+n+" deterministic mobile policy and fixture checks. Not a native build or live provider acceptance.");
