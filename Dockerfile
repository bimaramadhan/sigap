# ==========================================
# Backend FastAPI - SIGAP
# ==========================================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Install system dependencies untuk geospatial library (GDAL, GEOS, PROJ)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgdal-dev \
    gdal-bin \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code dan data pendukung
COPY api/ ./api/
COPY engine/ ./engine/
COPY pipeline/ ./pipeline/
COPY knowledge/ ./knowledge/
COPY data/ ./data/
COPY db/ ./db/

# Pastikan direktori cache ada
RUN mkdir -p data/cache

# Expose port (Cloud Run memakai PORT env var, default 8080)
EXPOSE 8080

# Jalankan Uvicorn FastAPI
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
