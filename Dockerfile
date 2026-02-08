# Stage 1: Build React frontend
FROM node:20-slim AS frontend-build
WORKDIR /webapp
COPY webapp/package.json webapp/package-lock.json ./
RUN npm ci
COPY webapp/ .
RUN npm run build

# Stage 2: Python backend + serve frontend
FROM python:3.12-slim
WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy backend code
COPY backend/ .

# Copy trained model weights
COPY backend/app/models/weights/ app/models/weights/

# Copy built frontend
COPY --from=frontend-build /webapp/dist /webapp/dist

# Create data directories (Railway volume mounts at /data)
RUN mkdir -p ml/data /data /data/weights

# Railway provides PORT env var
ENV PORT=8000
EXPOSE 8000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
