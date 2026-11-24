package io.oakandsparrow.boundarycast;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Insets;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.View;
import android.view.WindowInsets;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.widget.FrameLayout;
import androidx.webkit.WebViewAssetLoader;
import androidx.webkit.WebViewClientCompat;
import org.json.JSONObject;
import java.io.ByteArrayInputStream;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

public final class MainActivity extends Activity {
    private static final String HOST="appassets.androidplatform.net";
    private static final String ENTRY="https://"+HOST+"/assets/index.html";
    private static final Set<String> ASSETS=Set.of("/assets/index.html","/assets/styles.css","/assets/engine.js","/assets/app.js","/assets/LICENSE.txt");
    private static final int LOCATION_REQUEST=41;
    private final Handler main=new Handler(Looper.getMainLooper());
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private WebView web;
    private LocationManager locations;
    private LocationListener listener;
    private Runnable locationTimeout;
    private Future<?> running;
    private int generation;
    private boolean busy,permissionPending,visible;
    private String activeId="";
    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        if(Build.VERSION.SDK_INT>=33)setRecentsScreenshotEnabled(false);
        FrameLayout frame=new FrameLayout(this);frame.setBackgroundColor(Color.rgb(238,244,248));
        frame.setOnApplyWindowInsetsListener((v,i)->{
            if(Build.VERSION.SDK_INT>=30){Insets x=i.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout());v.setPadding(x.left,x.top,x.right,x.bottom);}
            else v.setPadding(i.getSystemWindowInsetLeft(),i.getSystemWindowInsetTop(),i.getSystemWindowInsetRight(),i.getSystemWindowInsetBottom());
            return i;
        });
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR|View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        web=new WebView(this);web.setBackgroundColor(Color.rgb(238,244,248));web.setSaveEnabled(false);
        web.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS);
        if(Build.VERSION.SDK_INT>=29)web.setImportantForContentCapture(View.IMPORTANT_FOR_CONTENT_CAPTURE_NO_EXCLUDE_DESCENDANTS);
        WebView.setWebContentsDebuggingEnabled(false);
        frame.addView(web,new FrameLayout.LayoutParams(-1,-1));setContentView(frame);frame.requestApplyInsets();
        WebSettings s=web.getSettings();s.setJavaScriptEnabled(true);s.setDomStorageEnabled(false);
        s.setAllowFileAccess(false);s.setAllowContentAccess(false);s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        s.setJavaScriptCanOpenWindowsAutomatically(false);s.setSupportMultipleWindows(false);s.setGeolocationEnabled(false);s.setCacheMode(WebSettings.LOAD_NO_CACHE);
        final WebViewAssetLoader loader=new WebViewAssetLoader.Builder().addPathHandler("/assets/",new WebViewAssetLoader.AssetsPathHandler(this)).build();
        web.setWebViewClient(new WebViewClientCompat(){
            @Override public WebResourceResponse shouldInterceptRequest(WebView v,WebResourceRequest r){
                Uri u=r.getUrl();if("https".equals(u.getScheme())&&HOST.equals(u.getHost())&&ASSETS.contains(u.getPath())&&u.getQuery()==null){
                    WebResourceResponse response=loader.shouldInterceptRequest(u);if(response!=null)return response;
                }
                return new WebResourceResponse("text/plain","UTF-8",403,"Blocked",java.util.Collections.emptyMap(),new ByteArrayInputStream(new byte[0]));
            }
            @Override public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest r){return !ENTRY.equals(r.getUrl().toString());}
        });
        web.addJavascriptInterface(new Bridge(),"AndroidWeather");web.loadUrl(ENTRY);
    }
    private final class Bridge{
        @JavascriptInterface public void locate(String id){main.post(()->begin(id,true,0,0));}
        @JavascriptInterface public void check(String id,double lat,double lon){main.post(()->begin(id,false,lat,lon));}
        @JavascriptInterface public void clear(){main.post(()->cancelAll());}
        @JavascriptInterface public void openOfficial(){main.post(()->{
            if(!visible)return;
            try{startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse("https://www.weather.gov/")));}catch(Exception ignored){}
        });}
    }
    private boolean permission(){return checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED||checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)==PackageManager.PERMISSION_GRANTED;}
    private void begin(String id,boolean gps,double lat,double lon){
        if(!visible||busy||id==null||!id.matches("[a-zA-Z0-9-]{1,40}"))return;
        busy=true;activeId=id;int token=++generation;
        if(!gps){
            if(!Double.isFinite(lat)||!Double.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180){fail(token,"Enter valid latitude and longitude.");return;}
            launch(token,lat,lon,"manual",Double.NaN);return;
        }
        if(!permission()){permissionPending=true;requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION,Manifest.permission.ACCESS_COARSE_LOCATION},LOCATION_REQUEST);return;}
        locate(token);
    }
    @Override public void onRequestPermissionsResult(int req,String[] p,int[] result){
        super.onRequestPermissionsResult(req,p,result);
        if(req!=LOCATION_REQUEST)return;permissionPending=false;
        if(!busy||!visible){cancelAll();return;}
        if(permission())locate(generation);else fail(generation,"Location permission declined. You can enter coordinates instead.");
    }
    private void locate(int token){
        locations=(LocationManager)getSystemService(LOCATION_SERVICE);
        if(locations==null){fail(token,"Location service unavailable. Enter coordinates instead.");return;}
        // An explicitly requested, foreground one-shot fix. Never store coordinates or register a background listener.
        listener=new LocationListener(){
            @Override public void onLocationChanged(Location location){acceptLocation(token,location);}
            @Override public void onProviderEnabled(String provider){}
            @Override public void onProviderDisabled(String provider){}
            @Override public void onStatusChanged(String provider,int status,Bundle extras){}
        };
        locationTimeout=()->{if(token==generation&&busy){stopLocation();fail(token,"No current location fix. Check location settings or enter coordinates.");}};
        boolean registered=false;
        for(String provider:new String[]{LocationManager.GPS_PROVIDER,LocationManager.NETWORK_PROVIDER}){
            try{
                if(locations.isProviderEnabled(provider)){
                    Location last=locations.getLastKnownLocation(provider);
                    if(last!=null&&fresh(last)){acceptLocation(token,last);return;}
                    locations.requestLocationUpdates(provider,1000L,0f,listener,Looper.getMainLooper());registered=true;
                }
            }catch(RuntimeException ignored){}
        }
        if(registered)main.postDelayed(locationTimeout,18000);
        else{stopLocation();fail(token,"Location is unavailable. Turn on device location or enter coordinates.");}
    }
    private boolean fresh(Location l){
        long age=SystemClock.elapsedRealtimeNanos()-l.getElapsedRealtimeNanos();
        return age>=0&&age<=120_000_000_000L&&l.hasAccuracy()&&Float.isFinite(l.getAccuracy())&&l.getAccuracy()>=0&&
          Double.isFinite(l.getLatitude())&&Double.isFinite(l.getLongitude())&&Math.abs(l.getLatitude())<=90&&Math.abs(l.getLongitude())<=180;
    }
    private void acceptLocation(int token,Location l){
        if(token!=generation||!busy||!visible||!fresh(l))return;
        stopLocation();launch(token,l.getLatitude(),l.getLongitude(),"device",l.getAccuracy());
    }
    private void stopLocation(){
        if(locationTimeout!=null){main.removeCallbacks(locationTimeout);locationTimeout=null;}
        if(locations!=null&&listener!=null)try{locations.removeUpdates(listener);}catch(RuntimeException ignored){}
        listener=null;locations=null;
    }
    private void launch(int token,double lat,double lon,String kind,double accuracy){
        running=worker.submit(()->{
            try{JSONObject result=NwsClient.read(lat,lon,kind,accuracy);main.post(()->deliver(token,result));}
            catch(Exception ignored){main.post(()->fail(token,"Live weather evidence could not be retrieved. Try again later."));}
        });
    }
    private void deliver(int token,JSONObject result){
        if(token!=generation||web==null||!visible)return;
        busy=false;running=null;String id=activeId;activeId="";
        web.evaluateJavascript("window.BoundaryCast.receive("+JSONObject.quote(id)+","+JSONObject.quote(result.toString()).replace("\u2028","\\u2028").replace("\u2029","\\u2029")+")",null);
    }
    private void fail(int token,String message){try{deliver(token,new JSONObject().put("error",message));}catch(Exception ignored){}}
    private void cancelAll(){
        generation++;busy=false;activeId="";stopLocation();if(running!=null){running.cancel(true);running=null;}
    }
    @Override protected void onResume(){super.onResume();visible=true;}
    @Override protected void onStop(){super.onStop();visible=false;if(!permissionPending){cancelAll();if(web!=null)web.evaluateJavascript("window.BoundaryCast.reset()",null);}}
    @Override protected void onDestroy(){cancelAll();worker.shutdownNow();if(web!=null){web.removeJavascriptInterface("AndroidWeather");web.stopLoading();((FrameLayout)web.getParent()).removeView(web);web.destroy();web=null;}super.onDestroy();}
}
