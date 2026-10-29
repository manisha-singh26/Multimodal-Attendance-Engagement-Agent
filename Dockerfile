# Production Dockerfile for Multimodal Attendance & Engagement Agent
FROM python:3.12-slim

# Set environment variables for offline reproducibility
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    THREADS=6

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition and install
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . /app/

# Expose server port
EXPOSE 5000

# Run with production WSGI server
CMD ["python", "wsgi.py"]

