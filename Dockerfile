# Build stage
FROM python:3.14-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ src/

# Install the package
RUN pip install --no-cache-dir build && \
    python -m build --wheel && \
    pip install --no-cache-dir dist/*.whl

# Runtime stage
FROM python:3.14-slim AS runtime

WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash tomt

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/tomt /usr/local/bin/tomt
COPY --from=builder /usr/local/bin/tomt-web /usr/local/bin/tomt-web

# Create data directory for the database
RUN mkdir -p /app/data && chown -R tomt:tomt /app

USER tomt

# Set the data directory as the working directory
WORKDIR /app/data

# Environment variables (to be provided at runtime)
ENV REDDIT_CLIENT_ID=""
ENV REDDIT_CLIENT_SECRET=""
ENV ANTHROPIC_API_KEY=""

# Web service configuration
ENV TOMT_HOST="0.0.0.0"
ENV TOMT_PORT="8000"
ENV TOMT_DB_PATH="/app/data/tomt.db"

# Expose web service port
EXPOSE 8000

# Default command shows help (use "tomt-web" for web service)
ENTRYPOINT []
CMD ["tomt", "--help"]
