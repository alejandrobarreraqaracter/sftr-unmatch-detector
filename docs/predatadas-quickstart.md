# Predatadas Quickstart

`predatadas` vive en este mismo repo, con `backend` compartido y un frontend separado en [frontend-predatadas](/home/alejandrobarrera/sftr-unmatch-detector/frontend-predatadas).

## Qué compara

El producto `predatadas` usa solo estos 7 campos:

- `Reporting timestamp`
- `Other counterparty`
- `UTI`
- `Event date`
- `Type of SFT`
- `Execution timestamp`
- `Method used to provide collateral`

Además, calcula una columna `Diferencia` para los campos temporales:

- `Reporting timestamp`: diferencia en segundos
- `Execution timestamp`: diferencia en segundos
- `Event date`: diferencia en días

## Arranque con Docker

Desde la raíz del repo:

```bash
./start-docker-stack.sh
```

URLs:

- Frontend SFTR: `http://localhost:5173`
- Frontend Predatadas: `http://localhost:5174`
- Backend API: `http://localhost:8000`
- Docs API: `http://localhost:8000/docs`

Si quieres validar si `Ollama` está usando GPU:

```bash
./check-docker-stack.sh gemma4:e2b
```

Si los logs muestran `loaded CPU backend` u `offloaded 0/... layers to GPU`, entonces sigue corriendo en CPU.

## Arranque local

Backend:

```bash
cd backend
poetry run fastapi dev app/main.py
```

Frontend predatadas:

```bash
cd frontend-predatadas
npm run dev -- --host 127.0.0.1 --port 5174
```

## Datos demo

Hay un lote sintético listo en:

- [backend/sample_data/predatadas_april_2026](/home/alejandrobarrera/sftr-unmatch-detector/backend/sample_data/predatadas_april_2026)

Generador:

- [backend/sample_data/generate_predatadas_csvs.py](/home/alejandrobarrera/sftr-unmatch-detector/backend/sample_data/generate_predatadas_csvs.py)

Auditoría:

- [backend/sample_data/predatadas_april_2026/audit_summary.json](/home/alejandrobarrera/sftr-unmatch-detector/backend/sample_data/predatadas_april_2026/audit_summary.json)

## Cómo probar

1. Abre `http://localhost:5174`
2. Ve a `Cargar fichero`
3. Selecciona varios CSV de `predatadas_april_2026`
4. Ejecuta la carga en lote
5. Revisa:
   - sesiones
   - detalle de operación
   - columna `Diferencia`
   - analítica
   - snapshot / reporting

## Nota sobre SQLite

Como el modelo añade `product_type` y columnas de `difference_*`, si venías de una base local antigua conviene recrearla antes de probar:

```bash
rm -f backend/sftr_unmatch.db
```

Al arrancar el backend, SQLite se recreará con el esquema nuevo.
