#!/usr/bin/env bash
set -o errexit
set -o nounset

# Cập nhật danh sách package
apt-get update

# Cài đặt các thư viện hệ thống cần thiết cho audio/video và librosa
apt-get install -y ffmpeg libsndfile1 libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev libavfilter-dev libswscale-dev libswresample-dev

# Cài đặt các package Python
pip install --upgrade pip
pip install -r requirements.txt