## 📊 Hệ Thống Giám Sát Phần Cứng Real-Time Cao Cấp
< **© 2026 DevTung. All rights reserved.** > 
Hệ thống giám sát và quản lý thiết bị máy tính từ xa dựa trên nền tảng Flask (Server) và Python (Client).

## ✨ Tính Năng Chính
- **Giám sát hiệu năng:** Cập nhật CPU, RAM, Ổ đĩa, GPU và Top 5 ứng dụng tiêu tốn tài nguyên nhất.
- **Quản lý file:** Duyệt thư mục ẩn, chạy file hoặc xóa file từ xa qua giao diện Web.
- **Điều khiển đa phương tiện:** Tự động quét và tương tác với mọi Camera/Microphone có trên thiết bị.
- **Lệnh hệ thống:** Gửi lệnh Tắt máy (Shutdown), Khởi động lại (Restart), Ngủ (Sleep).

## 🛠️ Công Nghệ Sử Dụng
Backend: Flask, Requests

System Monitoring: Psutil, GPUtil

Multimedia: OpenCV, SoundDevice, SoundFile, Pillow

Frontend: Bootstrap 5 (Giao diện đáp ứng)

## 🚀 Hướng Dẫn Cài Đặt

# 1. Cài đặt thư viện (Cho cả Client và Server)
Mở terminal tại thư mục gốc của dự án và chạy lệnh:


    pip install -r requirements.txt
   

# 2. Triển khai Server

B1: Đăng ký tài khoản

- Truy cập vào trang web pythonanywhere.com.

- Chọn Pricing & signup -> Chọn Create a Beginner account (Tài khoản miễn phí).

- Điền thông tin đăng ký (Username, Email, Password).

⚠️ Lưu ý quan trọng: Username của bạn sẽ là một phần của đường dẫn trang web sau này (Ví dụ: tên của bạn là username thì link web sẽ là username.pythonanywhere.com).

B2: Tạo ứng dụng Web Flask mới

- Sau khi đăng nhập, tại giao diện Dashboard, bạn chọn tab Web ở menu phía trên.

- Bấm vào nút Add a new web app.

- Một hộp thoại hiện ra, bấm Next.

- Chọn Framework: Chọn Flask.

- Chọn phiên bản Python: Nên chọn Python 3.11 hoặc Python 3.12 để đảm bảo tính tương thích tốt nhất với các thư viện hiện tại.

- Hệ thống sẽ hỏi đường dẫn lưu file (mặc định dạng /home/username/mysite/flask_app.py), bạn cứ bấm Next để hoàn thành.

B3: Cài đặt các thư viện cần thiết (pip)

- Mặc dù Server của bạn chỉ cần Flask và requests, nhưng PythonAnywhere đã cài sẵn Flask. Bạn chỉ cần cài thêm thư viện requests nếu chưa có bằng cách:

- Quay lại trang Dashboard -> Chọn tab Consoles.

- Tại mục Start a new console, chọn Bash.

- Giao diện dòng lệnh (Terminal) màu đen sẽ hiện ra. Bạn gõ lệnh sau rồi nhấn Enter:


		pip install --user requests
	
	
Đợi hệ thống chạy cài đặt xong xuôi thì bạn có thể tắt tab Bash này đi.

B4: Tải mã nguồn app.py lên hệ thống

- Quay lại Dashboard -> Chọn tab Files.

- Trong danh sách thư mục, bạn bấm vào thư mục tên là mysite/ (đây là nơi chứa mã nguồn trang web của bạn).

- Tại đây bạn sẽ thấy một file tên là flask_app.py (do hệ thống tự tạo lúc nãy). Hãy bấm vào biểu tượng Thùng rác bên cạnh để xóa nó đi.

- Nhìn sang góc bên phải, tại mục Upload a file, bạn bấm chọn và tải file *app.py* từ folder setup lên.

B5: Cấu hình lại file WSGI của PythonAnywhere
- Do file bạn tải lên tên là app.py còn cấu hình mặc định của hệ thống tìm file flask_app.py, bạn cần chỉnh sửa lại một dòng nhỏ để web hiểu được code:

- Quay lại tab Web trên thanh menu.

- Kéo xuống mục Code, tìm dòng có tên là WSGI configuration file (Nó là một đường dẫn dạng link màu xanh, ví dụ: /var/www/username_pythonanywhere_com_wsgi.py). Bấm vào đường dẫn đó.

- Trình chỉnh sửa code sẽ hiện ra. Bạn kéo xuống gần cuối file, tìm các dòng có nội dung tương tự như sau:


		# import flask app but need to call it "application" for WSGI to work
		from flask_app import app as application  # <-- TÌM DÒNG NÀY


- Sửa chữ flask_app thành app (vì file của bạn là app.py). Dòng code sau khi sửa sẽ trông như thế này:


		from app import app as application
	
	
- Bấm nút Save ở góc trên bên phải để lưu lại.

B6: Khởi chạy và kiểm tra kết quả
- Quay lại tab Web.

- Kéo lên trên cùng và bấm vào nút màu xanh lớn Reload <tên-miền-của-bạn>.

- Bây giờ, bạn có thể bấm trực tiếp vào đường link trang web của bạn ở phía trên (Ví dụ: http://username.pythonanywhere.com/). Nếu giao diện bảng điều khiển giám sát màu xám-trắng hiện ra với dòng chữ "Chưa có thiết bị nào kích hoạt..." là bạn đã cấu hình Server thành công 100%!

-  Bước cuối cùng: Đừng quên copy đường link trang web mới này của bạn, mở file info.pyw ở máy Client lên, tìm đến biến URL và thay thế nó vào nhé (Ví dụ: URL = "http://username.pythonanywhere.com/update-status"). 

## 3. Khởi chạy Client

- Cấu hình lại biến URL trong file client/info.pyw để trỏ về địa chỉ Server của bạn:

- Cấu hình file info.pyw như sau, mở file lên

- Tại gần cuối file dòng 233 :

  	  URL = "http://username.pythonanywhere.com/update-status"
	
- Thay chỗ "username" thành tên tài khoản của bạn và lưu file lại

- Rồi chạy file bằng cách click đúp vào file hoặc mở cmd tại folder đó và chạy lệnh

		python info.pyw
	
- Trên web của bạn sẽ phát hiện thấy máy tính của bạn ấn vào nút "Bảng điều khiển" để điều khiển máy

## 4. Cách chạy file info.pyw ẩn mỗi khi khởi động máy
- Tại folder client chuột phải vào file info.pyw rồi chọn "Show more options" và chọn "Create shortcut" 
- Bạn sẽ nhận được 1 file có tên là "info.pyw - Shortcut" 
- Dùng tổ hợp phín Win + r và nhập:

		shell:startup
	
- Và ấn "OK" folder startup sẽ được mở lên, copy file "info.pyw - Shortcut" lúc nãy vào folder này
- Lần sau khi bạn mở máy file info.pyw sẽ tự động được mở và chạy ngầm


---
