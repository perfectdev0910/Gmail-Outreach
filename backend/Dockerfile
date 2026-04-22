# Backend Dockerfile for Render deployment

FROM python:3.11-slim

WORKDIR /app

# System dependencies (add curl + build essentials for stability)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Prevent Python buffering logs (VERY important on Render)
ENV PYTHONUNBUFFERED=1

# Copy requirements first (better caching)
COPY requirements.txt .

# Upgrade pip tools (important for dependency resolution)
RUN pip install --upgrade pip setuptools wheel

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# IMPORTANT: Render uses dynamic ports
ENV PORT=8000

EXPOSE 8000

# Run with proper port binding
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]