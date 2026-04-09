#!/usr/bin/env bash

set -euo pipefail

echo "Parando stack Docker..."
docker compose down

echo "Stack detenido."
