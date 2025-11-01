# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

# Copy project files
COPY pyproject.toml ./

# Install dependencies using UV
RUN uv pip install --system \
    fastapi>=0.104.0 \
    uvicorn[standard]>=0.24.0 \
    sqlalchemy>=2.0.0 \
    psycopg2-binary>=2.9.9 \
    alembic>=1.12.0 \
    pydantic>=2.5.0 \
    pydantic-settings>=2.1.0 \
    python-multipart>=0.0.6 \
    anthropic>=0.7.0 \
    redis>=5.0.0 \
    celery>=5.3.0 \
    python-jose[cryptography]>=3.3.0 \
    passlib[bcrypt]>=1.7.4 \
    python-dotenv>=1.0.0 \
    httpx>=0.25.0 \
    pypdf>=3.17.0 \
    python-docx>=1.1.0 \
    playwright>=1.40.0

# Copy application code
COPY . .

# Create directories for file storage
RUN mkdir -p /app/storage/cvs /app/storage/temp

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
