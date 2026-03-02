FROM python:3.11-slim

WORKDIR /app

# gcc is needed by some Python packages (e.g. grpcio) during install
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata first (layer-caching: dependencies change less often than code)
COPY pyproject.toml .

# Copy source and config
COPY src/ src/
COPY dagster.yaml .
COPY workspace.yaml .

# Install the package and all runtime dependencies
RUN pip install --no-cache-dir -e "."

# Dagster looks for dagster.yaml in DAGSTER_HOME
ENV DAGSTER_HOME=/app

EXPOSE 4000
