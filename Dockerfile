# =============================================================================
# DCLM Payroll Management System - Dockerfile
# Multi-stage build for smaller final image size
# =============================================================================

# ---- Stage 1: Build dependencies (compilation tools) ----
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies for compiling native Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (leverage Docker layer caching)
COPY requirements.txt .

# Install all Python packages into a temporary directory
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Stage 2: Production Image ----
FROM python:3.12-slim AS production

# Install runtime-only system dependencies (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security best practices
RUN groupadd -r payroll && useradd -r -g payroll -d /app -s /bin/false payroll

# Set working directory
WORKDIR /app

# Copy ALL installed packages from builder stage (system-wide install)
COPY --from=builder /install /usr/local

# Copy application source code with correct ownership
COPY --chown=payroll:payroll . .

# Environment configuration
ENV PATH=/usr/local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose the application port
EXPOSE 8000

# Make prestart.sh executable (run as root before switching user)
RUN chmod +x prestart.sh

# Switch to non-root user for running the app
USER payroll

# Health check to verify the application is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/login || exit 1

# Run the prestart script which handles setup then starts uvicorn
CMD ["./prestart.sh"]
