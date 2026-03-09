# Multi-stage build for CS Pulse Load Driver
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ================================================================
# Final stage
# ================================================================
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy load driver code
COPY . .

# Create results directory
RUN mkdir -p /app/results

# Environment variables (override at run time; no secrets in image)
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO
# CS_PULSE_BASE_URL must be set when running (e.g. docker run -e CS_PULSE_BASE_URL=https://your-app.example.com)
ENV CS_PULSE_BASE_URL=https://platform.example.com

# Entry point: run driver
ENTRYPOINT ["python", "-u", "driver.py"]
CMD ["--scenarios", "1,2a,2b,2c,2d,2e,3,4,5,6,7", "--customers", "1,2,3"]
