# Sử dụng hình ảnh cơ sở của Python 3.11 trên Debian Bookworm (phù hợp với Render)
FROM python:3.11-slim-bookworm

# Thiết lập biến môi trường để Python không tạo file .pyc
ENV PYTHONUNBUFFERED 1

# Cài đặt các gói hệ thống cần thiết cho WeasyPrint
# RUN apt-get update -y && apt-get install -y libpango-1.0-0 libcairo2 libgdk-pixbuf2.0-0
# LƯU Ý QUAN TRỌNG: Thay vì lệnh trên, chúng ta sử dụng gói font thay thế hỗ trợ tiếng Việt tốt hơn và cài đặt các phụ thuộc cần thiết cho WeasyPrint
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    fontconfig \
    fonts-dejavu \
    libpango-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    zlib1g-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Tạo thư mục cho ứng dụng
WORKDIR /app

# Sao chép các file yêu cầu (requirements.txt) và cài đặt các gói Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép tất cả các file còn lại của ứng dụng vào trong Docker image
COPY . .

# Khai báo cổng mà ứng dụng sẽ lắng nghe (cổng mặc định của Render là 10000)
EXPOSE 10000

# Lệnh để chạy ứng dụng khi container khởi động
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]
