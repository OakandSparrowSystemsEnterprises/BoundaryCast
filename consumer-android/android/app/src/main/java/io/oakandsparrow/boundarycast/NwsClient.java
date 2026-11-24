package io.oakandsparrow.boundarycast;

import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Locale;

final class NwsClient {
    static final String ROOT = "https://api.weather.gov";
    static final String USER_AGENT = "BoundaryCast/0.1 (contact@oakandsparrowsystemsenterprise.io)";
    private static final int MAX_BYTES = 4 * 1024 * 1024;
    private static final int TIMEOUT = 7000;
    private static boolean allowed(URI u) {
        if (!"https".equals(u.getScheme()) || !"api.weather.gov".equals(u.getHost())
                || u.getUserInfo()!=null || u.getFragment()!=null || (u.getPort()!=-1 && u.getPort()!=443)) return false;
        String p=u.getPath();
        return p!=null && (p.startsWith("/points/") || p.startsWith("/gridpoints/") ||
            p.startsWith("/stations/") || p.equals("/alerts") || p.startsWith("/alerts/active"));
    }
    static JSONObject get(String url) throws Exception {
        URI uri=new URI(url);
        for (int redirect=0;redirect<=2;redirect++) {
            if(Thread.currentThread().isInterrupted() || !allowed(uri))throw new IllegalArgumentException("invalid endpoint");
            HttpURLConnection conn=(HttpURLConnection)uri.toURL().openConnection();
            conn.setInstanceFollowRedirects(false);conn.setUseCaches(false);
            conn.setConnectTimeout(TIMEOUT);conn.setReadTimeout(TIMEOUT);
            conn.setRequestProperty("User-Agent",USER_AGENT);
            conn.setRequestProperty("Accept","application/geo+json");
            conn.setRequestProperty("Cache-Control","no-cache, no-store");
            try {
                int status=conn.getResponseCode();
                if(status>=300&&status<400) {
                    String next=conn.getHeaderField("Location");
                    if(next==null)throw new IllegalStateException("redirect");
                    uri=uri.resolve(next);continue;
                }
                if(status!=200)throw new IllegalStateException("provider response unavailable");
                try(InputStream in=conn.getInputStream(); ByteArrayOutputStream out=new ByteArrayOutputStream()) {
                    byte[] buffer=new byte[8192];int n,total=0;
                    while((n=in.read(buffer))!=-1){total+=n;if(total>MAX_BYTES||Thread.currentThread().isInterrupted())throw new IllegalStateException("response limit");out.write(buffer,0,n);}
                    return new JSONObject(out.toString(StandardCharsets.UTF_8.name()));
                }
            } finally {conn.disconnect();}
        }
        throw new IllegalStateException("redirect limit");
    }
    private static JSONObject props(JSONObject x){return x==null?null:x.optJSONObject("properties");}
    static double distanceKm(double a,double b,double c,double d){
        double p=Math.PI/180, x=Math.sin((c-a)*p/2), y=Math.sin((d-b)*p/2);
        double h=x*x+Math.cos(a*p)*Math.cos(c*p)*y*y;
        return 6371*2*Math.asin(Math.sqrt(Math.min(1,Math.max(0,h))));
    }
    private static final class Station {
        final String id,name; final double distance;
        Station(String id,String name,double distance){this.id=id;this.name=name;this.distance=distance;}
    }
    static JSONObject read(double lat,double lon, String inputKind,double accuracy) throws Exception{
        JSONObject out=new JSONObject();
        JSONObject status=new JSONObject();out.put("status",status);
        out.put("inputKind",inputKind);if(Double.isFinite(accuracy))out.put("accuracyM",accuracy);
        String location=String.format(Locale.US,"%.4f,%.4f",lat,lon);
        // The alert request is independent: a point/forecast failure must not erase a known official warning.
        try{JSONObject alerts=get(ROOT+"/alerts/active?point="+location);out.put("alerts",alerts);status.put("alerts","ok");}
        catch(Exception ignored){status.put("alerts","unavailable");}
        if(Thread.currentThread().isInterrupted())throw new InterruptedException();
        JSONObject point=null;
        try{point=props(get(ROOT+"/points/"+location));if(point==null)throw new IllegalStateException("point");status.put("point","ok");
            JSONObject relative=point.optJSONObject("relativeLocation");JSONObject place=props(relative);
            if(place!=null){out.put("city",place.optString("city",""));out.put("state",place.optString("state",""));}
            out.put("timeZone",point.optString("timeZone",""));
        }catch(Exception ignored){status.put("point","unavailable");}
        if(point!=null&&!Thread.currentThread().isInterrupted()){
            try{String url=point.getString("forecastHourly");out.put("forecast",get(url));status.put("forecast","ok");}
            catch(Exception ignored){status.put("forecast","unavailable");}
        }
        if(Thread.currentThread().isInterrupted())throw new InterruptedException();
        JSONArray observations=new JSONArray();out.put("observations",observations);
        if(point!=null){
            try {
                JSONObject list=get(point.getString("observationStations"));
                JSONArray features=list.getJSONArray("features");
                ArrayList<Station> stations=new ArrayList<>();
                for(int i=0;i<Math.min(features.length(),100);i++){
                    JSONObject s=features.optJSONObject(i);JSONObject p=props(s);
                    JSONObject geom=s==null?null:s.optJSONObject("geometry");
                    JSONArray coords=geom==null?null:geom.optJSONArray("coordinates");
                    if(p==null||coords==null||coords.length()<2)continue;
                    double x=coords.optDouble(0,Double.NaN),y=coords.optDouble(1,Double.NaN);
                    String id=p.optString("stationIdentifier","");
                    if(!id.matches("[A-Za-z0-9_-]{2,16}")||!Double.isFinite(x)||!Double.isFinite(y)||Math.abs(x)>180||Math.abs(y)>90)continue;
                    double distance=distanceKm(lat,lon,y,x);
                    if(distance<=10.0)stations.add(new Station(id,p.optString("name",id),distance));
                }
                stations.sort(Comparator.comparingDouble(s->s.distance));
                for(int i=0;i<Math.min(2,stations.size());i++){
                    if(Thread.currentThread().isInterrupted())throw new InterruptedException();
                    Station s=stations.get(i);
                    try{
                        JSONObject observation=get(ROOT+"/stations/"+s.id+"/observations/latest");
                        JSONObject o=props(observation);
                        if(o!=null)observations.put(new JSONObject().put("stationId",s.id).put("stationName",s.name).put("distanceKm",s.distance).put("properties",o));
                    }catch(Exception ignored){}
                }
                status.put("observations",observations.length()>0?"ok":"unavailable");
            }catch(Exception ignored){status.put("observations","unavailable");}
        }
        if(Thread.currentThread().isInterrupted())throw new InterruptedException();
        return out;
    }
}
