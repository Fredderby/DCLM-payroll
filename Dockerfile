# =============================================================================
# DCLM Payroll Management System - Dockerfile
# Multi-stage build: Python dependencies → Production image
# =============================================================================

# ---- Stage 1: Install Dependencies ----
FROM python:3.12-slim AS builder

# Set working directory inside build stage
WORKDIR /app

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy ONLY requirements first (leverage Docker layer caching)
COPY requirements.txt .

# Install Python dependencies into a local directory (not system-wide)
# This keeps the final image slim by only copying the installed packages
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Stage 2: Production Image ----
FROM python:3.12-slim AS production

# Install runtime-only system dependencies (no build tools needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security best practices
RUN groupadd -r payroll && useradd -r -g payroll -d /app -s /bin/false payroll

# Set working directory
WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /root/.local /home/payroll/.local

# Copy application source code
COPY --chown=payroll:payroll . .

# Make sure scripts in .local are usable
ENV PATH=/home/payroll/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose the application port (dynamically set via env)
EXPOSE 8000

# Make prestart.sh executable (run as root before switching user)
RUN chmod +x prestart.sh

# Switch to non-root user
USER payroll

# Health check to verify the application is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/login || exit 1

# Run the prestart script to set up tables, then start uvicorn
# The prestart.sh ensures database tables exist before the app starts
CMD ["./prestart.sh"]
