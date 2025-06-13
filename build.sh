#!/bin/bash

echo "==> Cập nhật danh sách gói và cài đặt các thư viện hệ thống cần thiết cho WeasyPrint..."
apt-get update -y
apt-get install -y libpango-1.0-0 libcairo2 libgdk-pixbuf2.0-0

echo "==> Cài đặt các gói Python từ requirements.txt..."
pip install -r requirements.txt

echo "==> Hoàn tất Build Script."