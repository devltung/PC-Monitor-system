package com.devtung.monitor;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Timer;
import java.util.TimerTask;
import org.json.JSONObject;

public class MonitorService extends Service {
    private Timer timer = new Timer();
    private final String SERVER_URL = "http://devtung.pythonanywhere.com/update-status";

    @Override
    public void onCreate() {
        super.onCreate();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel("monitor", "Monitor ngầm", NotificationManager.IMPORTANCE_LOW);
            getSystemService(NotificationManager.class).createNotificationChannel(channel);
            Notification notification = new Notification.Builder(this, "monitor")
                .setContentTitle("Devtung System Online")
                .setContentText("Đang đồng bộ phần cứng...")
                .setSmallIcon(android.R.drawable.ic_menu_info_details)
                .build();
            startForeground(1, notification);
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        timer.scheduleAtFixedRate(new TimerTask() {
            @Override
            public void run() {
                sendData();
            }
        }, 0, 2000); 
        return START_STICKY;
    }

    private void sendData() {
        try {
            URL url = new URL(SERVER_URL);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json; utf-8");
            conn.setDoOutput(true);

            JSONObject json = new JSONObject();
            json.put("computer_name", (Build.BRAND + "_" + Build.MODEL).toUpperCase().replace(" ", "_"));
            json.put("os", "Android " + Build.VERSION.RELEASE);
            json.put("architecture", Build.CPU_ABI);
            json.put("uptime", "Đang chạy ngầm vĩnh viễn");
            
            JSONObject ramObj = new JSONObject();
            ramObj.put("percentage", "50%");
            ramObj.put("used", "3.0 GB");
            ramObj.put("total", "6.0 GB");
            json.put("ram", ramObj);

            String jsonInputString = json.toString();
            try (OutputStream os = conn.getOutputStream()) {
                byte[] input = jsonInputString.getBytes("utf-8");
                os.write(input, 0, input.length);
            }

            int code = conn.getResponseCode();
            conn.disconnect();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }
}
