#!/usr/bin/env bash

set -euo pipefail

MODEL="${1:-gemma4:e2b}"

echo "Estado de contenedores:"
docker compose ps
echo

echo "Health backend:"
curl -s http://127.0.0.1:8000/healthz || true
echo
echo

echo "Estado IA backend:"
curl -s http://127.0.0.1:8000/api/ai/status || true
echo
echo

echo "Modelos disponibles en Ollama:"
docker compose exec ollama ollama list || true
echo

echo "Proceso cargado en Ollama:"
docker compose exec ollama ollama ps || true
echo

echo "Detección GPU dentro del contenedor Ollama:"
docker compose exec ollama nvidia-smi || echo "WARN: nvidia-smi no disponible dentro del contenedor o sin acceso a GPU"
echo

echo "Últimos logs relevantes de GPU/Ollama:"
docker compose logs --tail=80 ollama | grep -Ei "gpu|cpu backend|offloaded|inference compute|CUDA|NVIDIA|device=" || true
echo

echo "Comprobando modelo esperado: ${MODEL}"
if docker compose exec ollama ollama list | grep -q "${MODEL}"; then
  echo "OK: modelo disponible"
else
  echo "WARN: modelo no encontrado"
fi
