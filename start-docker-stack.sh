#!/usr/bin/env bash

set -euo pipefail

MODEL="${1:-gemma4:e2b}"

echo "Levantando stack Docker..."
docker compose up -d --build

echo "Esperando a que el servicio Ollama responda..."
for _ in $(seq 1 60); do
  if docker compose exec ollama ollama list >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "Descargando modelo en Ollama: ${MODEL}"
docker compose exec ollama ollama pull "${MODEL}"

echo
echo "Stack listo."
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:8000"
echo "Docs:     http://localhost:8000/docs"
echo "Ollama:   http://localhost:11434"
echo "Modelo:   ${MODEL}"
