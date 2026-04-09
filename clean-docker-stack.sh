#!/usr/bin/env bash

set -euo pipefail

echo "Parando stack Docker y eliminando volúmenes..."
docker compose down -v

echo "Limpiando imágenes locales del proyecto..."
docker image rm -f sftr-unmatch-detector-backend sftr-unmatch-detector-frontend >/dev/null 2>&1 || true

echo "Stack limpio."
echo "Tendrás que volver a descargar modelos y reconstruir imágenes en el próximo arranque."
