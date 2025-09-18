#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Bắt đầu cài đặt thư viện hệ thống..."

# Cập nhật và cài đặt các thư viện cần thiết cho audio/video
apt-get update && apt-get install -y --no-install-recommends \
  ffmpeg \
  libsndfile1 \
  libavformat-dev \
  libavcodec-dev \
  libavdevice-dev \
  libavutil-dev \
  libavfilter-dev \
  libswscale-dev \
  libswresample-dev \
  pkg-config

echo "Đã cài xong thư viện hệ thống."
echo "Bắt đầu cài đặt các package Python..."

# Nâng cấp pip và cài đặt từ requirements.txt
pip install --upgrade pip
pip install -r requirements.txt

# Tạo thư mục uploads nếu chưa có
mkdir -p uploads

echo "Đã cài xong các package Python. Build hoàn tất."