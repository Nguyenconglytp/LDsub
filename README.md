# LDsub - Video Subtitle Generator

## Mô tả
Ứng dụng web hỗ trợ tạo phụ đề tự động cho video bằng Python Flask.

## Tính năng
- Upload video và tạo phụ đề tự động
- Hỗ trợ nhiều định dạng video
- Giao diện web đơn giản, dễ sử dụng
- Quản lý người dùng với đăng nhập/đăng ký
- Dịch phụ đề sang nhiều ngôn ngữ
- Thêm phụ đề vào video (burn subtitles)

## Triển khai trên Render.com

### Bước 1: Chuẩn bị
1. Fork repository này về GitHub của bạn
2. Đăng ký tài khoản tại [Render.com](https://render.com)

### Bước 2: Triển khai
1. Vào Render Dashboard, chọn "New Web Service"
2. Kết nối với GitHub repository của bạn
3. Chọn repository `LDsub`
4. Cấu hình như sau:
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT app:app`
   - **Environment**: `Python 3`
   - **Plan**: `Free` (hoặc Starter tùy nhu cầu)

### Bước 3: Biến môi trường
Thêm các biến môi trường sau trong Render Dashboard:
- `SECRET_KEY`: Tạo một secret key ngẫu nhiên
- `FLASK_ENV`: `production`
- `MAX_FILE_SIZE`: `524288000` (500MB)

### Bước 4: Deploy
1. Click "Create Web Service"
2. Đợi quá trình build và deploy hoàn tất
3. Truy cập URL được cung cấp để sử dụng ứng dụng

## Cài đặt Local

1. Clone repository
```bash
git clone https://github.com/Nguyenconglytp/LDsub.git
cd LDsub
```

2. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

3. Chạy ứng dụng
```bash
python app.py
```

## Sử dụng
1. Mở trình duyệt và truy cập ứng dụng
2. Đăng ký tài khoản hoặc đăng nhập
3. Upload video và tạo phụ đề

## Cấu trúc dự án
- `app.py` - File chính chứa Flask application
- `templates/` - Thư mục chứa HTML templates
- `uploads/` - Thư mục lưu trữ video và file phụ đề (tạm thời)
- `users.json` - File lưu trữ thông tin người dùng
- `build.sh` - Script build cho Render.com
- `render.yaml` - Cấu hình deployment cho Render.com
- `requirements.txt` - Danh sách dependencies Python

## Lưu ý
- Trên Render.com, files được lưu trữ tạm thời và sẽ bị xóa khi service restart
- Kích thước file upload tối đa: 500MB trên Render.com Free Plan
- Ứng dụng sử dụng faster-whisper để tạo phụ đề nhanh hơn
- FFmpeg được cài đặt tự động trong quá trình build