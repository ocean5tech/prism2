FROM python:3.12-slim

WORKDIR /app

# ‰ÅûßV
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 6requirements‡öv‰ÅPythonV
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6”(ã
COPY app/ ./app/

# ´2ïã
EXPOSE 8000

# /¨}ä
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]