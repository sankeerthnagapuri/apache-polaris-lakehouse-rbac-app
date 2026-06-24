#!/usr/bin/env bash
set -e

# Ensure we are in the project root
cd "$(dirname "$0")/.."

echo "Starting Docker Compose services..."
docker compose down
docker compose up -d

echo "Waiting for services to be ready (10 seconds)..."
sleep 10

# Use the current virtual environment if it exists, else fallback to python
PYTHON_CMD="python"
if [ -f ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
fi

echo "Setting up Keycloak..."
$PYTHON_CMD scripts/setup_keycloak.py

echo "Bootstrapping Iceberg catalog..."
$PYTHON_CMD scripts/setup_catalog.py

echo "Automating RBAC Configuration and Testing Access..."
$PYTHON_CMD scripts/setup_rbac.py

# echo "Fetching Polaris logs..."
# docker compose logs -t polaris > log.txt

echo "Setup and testing complete!"
