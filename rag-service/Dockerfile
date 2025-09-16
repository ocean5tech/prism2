FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/
COPY .env .

# 创建日志目录
RUN mkdir -p logs

# 创建数据目录
RUN mkdir -p data/models data/collections

# 设置权限
RUN chmod -R 755 app/ && chmod 600 .env

# 暴露端口
EXPOSE 8001

# 启动命令
CMD ["python", "-m", "app.main"]