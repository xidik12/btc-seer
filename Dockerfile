# Stage 1: Build React frontend
FROM node:20.18.1-slim AS frontend-build
WORKDIR /webapp
COPY webapp/package.json webapp/package-lock.json ./
RUN npm ci
COPY webapp/ .
RUN npm run build

# Stage 2: Python backend + serve frontend
FROM python:3.12.8-slim
WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl libgomp1 postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Install torch CPU first so pytorch-forecasting doesn't pull GPU torch + conflicting CUDA deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn==23.0.0

# Copy backend code
COPY backend/ .

# Copy built frontend
COPY --from=frontend-build /webapp/dist /webapp/dist

# Create data directories (Railway volume mounts at /data)
RUN mkdir -p ml/data /data /data/weights /data/backups /data/uploads

# Railway provides PORT env var
ENV PORT=8000
EXPOSE 8000

CMD gunicorn app.main:app -k uvicorn.workers.UvicornWorker --workers ${WEB_CONCURRENCY:-2} --bind 0.0.0.0:${PORT} --timeout 0 --graceful-timeout 30
