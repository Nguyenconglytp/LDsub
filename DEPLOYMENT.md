# Hướng dẫn deploy lên Render.com

## Cách deploy

1. **Đẩy code lên GitHub** (đã hoàn thành)
2. **Tạo Web Service trên Render.com:**
   - Đăng nhập vào [render.com](https://render.com)
   - Click "New" → "Web Service"
   - Kết nối GitHub repository: `Nguyenconglytp/LDsub`
   - Chọn branch: `copilot/fix-2fed5771-9d9f-4c69-8289-91cdb5f4915d`

3. **Render sẽ tự động:**
   - Phát hiện file `render.yaml`
   - Chạy `build.sh` để cài đặt FFmpeg và dependencies
   - Khởi động với `gunicorn app:app`

## Các vấn đề đã được khắc phục

### ✅ Cấu hình Production
- App không còn chạy ở debug mode
- Bind đúng host và port cho Render.com
- Secret key được tạo tự động
- Logging được bật cho production

### ✅ Xử lý File
- File không bị xóa trước khi download
- Cleanup được delay 5 phút
- Upload folder được tạo tự động

### ✅ Dependencies
- FFmpeg được cài đặt qua build.sh
- Gunicorn cho production server
- Tất cả Python packages cần thiết

### ✅ Health Check
- Endpoint `/health` cho monitoring
- Root path `/` hoạt động bình thường

## Lưu ý quan trọng

1. **Free plan của Render.com:**
   - Service sẽ sleep sau 15 phút không hoạt động
   - Storage không persistent (file upload sẽ mất khi restart)
   - RAM và CPU giới hạn

2. **Tối ưu hóa:**
   - Sử dụng model "tiny" cho Whisper (nhanh nhất)
   - File cleanup tự động sau 5 phút
   - Logging để debug vấn đề

3. **Monitoring:**
   - Check logs trong Render dashboard
   - Sử dụng `/health` endpoint để kiểm tra

## URL sau khi deploy
- Ứng dụng sẽ có URL dạng: `https://ldsub.onrender.com`
- Đăng nhập với tài khoản có sẵn: `nguyenconglytp`