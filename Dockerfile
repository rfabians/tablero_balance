FROM python:3.12-slim

# Dependencias de sistema para geopandas (GDAL, PROJ, GEOS)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgdal-dev \
        gdal-bin \
        libgeos-dev \
        libproj-dev \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONPATH="/app:/app/src"

# Instalar dependencias Python primero (aprovechar capa de cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copiar código fuente y assets
COPY main.py .
COPY src/ ./src/
COPY assets/ ./assets/

EXPOSE 8050

CMD ["gunicorn", "main:server", \
     "--bind", "0.0.0.0:8050", \
     "--workers", "2", \
     "--timeout", "120", \
     "--log-level", "info"]