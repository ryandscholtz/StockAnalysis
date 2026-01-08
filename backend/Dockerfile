# Multi-stage Docker build for Stock Analysis API
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r app && useradd -r -g app app

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt requirements-test.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-test.txt

# Development stage
FROM base as development

# Install development tools
RUN pip install --no-cache-dir \
    black \
    isort \
    flake8 \
    mypy \
    pre-commit

# Copy source code
COPY . .

# Change ownership to app user
RUN chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Development command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production

# Copy only necessary files
COPY app/ ./app/
COPY requirements.txt ./

# Change ownership to app user
RUN chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Production command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]