# LDsub - Video Subtitle Generator

## Mô tả
Ứng dụng web hỗ trợ tạo phụ đề tự động cho video bằng Python Flask.

## Tính năng
- Upload video và tạo phụ đề tự động
- Hỗ trợ nhiều định dạng video
- Giao diện web đơn giản, dễ sử dụng
- Quản lý người dùng với đăng nhập/đăng ký

## Cài đặt
1. Clone repository
```bash
git clone https://github.com/Nguyenconglytp/LDsub.git
cd LDsub
```

2. Cài đặt dependencies
```bash
pip install flask
```

3. Chạy ứng dụng
```bash
python app.py
```

## Sử dụng
1. Mở trình duyệt và truy cập `http://localhost:5000`
2. Đăng ký tài khoản hoặc đăng nhập
3. Upload video và tạo phụ đề

## Cấu trúc dự án
- `app.py` - File chính chứa Flask application
- `templates/` - Thư mục chứa HTML templates
- `uploads/` - Thư mục lưu trữ video và file phụ đề
- `users.json` - File lưu trữ thông tin người dùng