# SFTR Unmatch Detector

Aplicación full-stack para conciliación de reporting SFTR orientada a equipos de cumplimiento normativo. El sistema carga un fichero tabular de conciliación, donde cada fila representa una operación y contiene los valores de ambas contrapartes, compara los 155 campos SFTR, clasifica discrepancias por severidad, permite su gestión operativa y añade una capa opcional de análisis con IA.

## Estado actual

Este repositorio ya no usa el modelo inicial de "2 ficheros, 1 operación". El núcleo fue reestructurado para el caso real:

- 1 sesión = 1 fichero de conciliación cargado
- 1 fila del CSV = 1 operación
- 1 operación = hasta 155 comparaciones de campo SFTR

La arquitectura actual está alineada con cargas masivas de miles de operaciones por fichero.

## Qué hace el sistema

- Carga un CSV tabular con ambas contrapartes en columnas separadas
- Recorre cada fila como una operación independiente
- Compara 155 campos SFTR usando el catálogo regulatorio
- Detecta:
- coincidencias exactas
- campos espejo válidos como `GIVE/TAKE` o `MRGG/MRGE`
- discrepancias numéricas
- diferencias de fecha
- ausencias en una de las dos contrapartes
- campos no aplicables
- Aplica severidad en función de la obligación regulatoria:
- `CRITICAL` para `M`
- `WARNING` para `C`
- `INFO` para `O`
- Permite gestionar discrepancias con:
- estado
- responsable
- notas
- acciones masivas
- Exporta resultados a XLSX
- Añade una capa opcional de IA para:
- analizar una discrepancia concreta
- resumir una operación
- redactar una narrativa ejecutiva de la sesión

## Arquitectura funcional

### Modelo de datos

El backend trabaja con cuatro entidades principales definidas en [models.py](/home/alejandrobarrera/sftr-unmatch-detector/backend/app/models.py):

- `Session`
  Resume una carga completa: fichero, contrapartes, tipo predominante, número total de operaciones y métricas agregadas.
- `TradeRecord`
  Representa una fila del CSV, es decir, una operación individual.
- `FieldComparison`
  Representa la comparación de un campo SFTR concreto dentro de una operación.
- `ActivityLog`
  Registra cambios y acciones sobre la sesión, la operación o una comparación.

Relación conceptual:

```text
Session
  -> TradeRecord
       -> FieldComparison
  -> ActivityLog
```

### Flujo backend

1. El usuario sube un fichero CSV tabular.
2. El parser transforma cada fila en:
   - metadatos de operación
   - diccionario `emisor`
   - diccionario `receptor`
3. El motor de comparación ejecuta los 155 campos SFTR para esa operación.
4. Se persisten:
   - una `Session`
   - varios `TradeRecord`
   - varios `FieldComparison`
5. El frontend explota esos datos con vistas agregadas y drill-down por operación y campo.

## Estructura del repositorio

```text
backend/
  app/
    data/
      sftr_fields.json
    routers/
      sessions.py
      analytics.py
      ai.py
    services/
      file_parser.py
      comparison.py
      export.py
      field_registry.py
      llm_provider.py
      ai_agents.py
    config.py
    database.py
    main.py
    models.py
    schemas.py
  sample_data/
frontend/
  src/
    components/
    pages/
    lib/
```

## Stack técnico

| Capa | Tecnología |
| --- | --- |
| Frontend | React 18, Vite, TypeScript, Tailwind CSS, shadcn/ui, Recharts |
| Backend | FastAPI, SQLAlchemy, Python 3.12 |
| Base de datos | SQLite |
| Parsing CSV | pandas |
| Export | openpyxl |
| IA opcional | Ollama, Anthropic o OpenAI vía HTTP |

## Branding

Se aplicó la identidad visual de qaracter al frontend:

- naranja principal: `#fc7c34`
- navy principal: `#243444`
- logo disponible en [frontend/public/logo.png](/home/alejandrobarrera/sftr-unmatch-detector/frontend/public/logo.png)

Puntos principales de branding:

- [Sidebar.tsx](/home/alejandrobarrera/sftr-unmatch-detector/frontend/src/components/Sidebar.tsx)
- [button.tsx](/home/alejandrobarrera/sftr-unmatch-detector/frontend/src/components/ui/button.tsx)
- [tailwind.config.js](/home/alejandrobarrera/sftr-unmatch-detector/frontend/tailwind.config.js)
- [index.css](/home/alejandrobarrera/sftr-unmatch-detector/frontend/src/index.css)

## Formato CSV esperado

El parser actual está en [file_parser.py](/home/alejandrobarrera/sftr-unmatch-detector/backend/app/services/file_parser.py) y espera:

- CSV separado por `;`
- una fila de cabecera
- una fila por operación
- columnas de metadatos
- columnas de campos duplicadas por contraparte con sufijos `_cp1` y `_cp2`

### Columnas de metadatos soportadas

- `uti`
- `sft_type`
- `action_type`
- `emisor_name`
- `receptor_name`
- `emisor_lei`
- `receptor_lei`

### Convención para campos

Para cada campo SFTR se esperan dos columnas:

- `{campo_normalizado}_cp1`
- `{campo_normalizado}_cp2`

Ejemplo:

```text
reporting_timestamp_cp1
reporting_timestamp_cp2
fixed_rate_cp1
fixed_rate_cp2
```

La normalización de columnas es:

- minúsculas
- caracteres no alfanuméricos reemplazados por `_`
- colapsado de `_` duplicados

Ejemplo:

```text
"Reporting timestamp" -> "reporting_timestamp"
```

### Ejemplo mínimo

```csv
uti;sft_type;action_type;reporting_timestamp_cp1;reporting_timestamp_cp2;fixed_rate_cp1;fixed_rate_cp2
UTI001;Repo;NEWT;2024-01-01T10:00:00Z;2024-01-01T10:00:00Z;0.0125;0.0125
UTI002;Repo;NEWT;2024-01-01T10:00:00Z;2024-01-01T10:00:00Z;0.0125;0.0150
```

## Catálogo SFTR

El catálogo de 155 campos vive en [sftr_fields.json](/home/alejandrobarrera/sftr-unmatch-detector/backend/app/data/sftr_fields.json) y se accede a través de [field_registry.py](/home/alejandrobarrera/sftr-unmatch-detector/backend/app/services/field_registry.py).

Cobertura:

- Tabla 1: Counterparty Data, 18 campos
- Tabla 2: Loan and Collateral Data, 99 campos
- Tabla 3: Margin Data, 20 campos
- Tabla 4: Re-use Data, 18 campos

Cada campo contiene:

- número de tabla
- número de campo
- nombre
- descripción
- formato esperado
- obligación por tipo SFT y tipo de acción
- indicador de mirror field
- regla de validación descriptiva

## Motor de comparación

El motor principal está en [comparison.py](/home/alejandrobarrera/sftr-unmatch-detector/backend/app/services/comparison.py).

### Lógica actual

- compara cada campo del catálogo para una operación
- resuelve la obligación según `sft_type` y `action_type`
- usa matching flexible de nombre de campo
- detecta mirror match para pares válidos
- aplica tolerancia numérica
- genera `result`, `severity`, `root_cause`, `status`

### Resultados posibles

- `MATCH`
- `UNMATCH`
- `MIRROR`
- `NA`

### Severidades

| Obligación | Severidad |
| --- | --- |
| `M` | `CRITICAL` |
| `C` | `WARNING` |
| `O` | `INFO` |
| `-` | `NONE` |

### Root causes actuales

- `MATCH`
- `BOTH_EMPTY`
- `MISSING_EMISOR`
- `MISSING_RECEPTOR`
- `MIRROR_MATCH`
- `NUMERIC_DELTA`
- `NUMERIC_WITHIN_TOLERANCE`
- `DATE_MISMATCH`
- `FORMAT_DIFFERENCE`
- `VALUE_MISMATCH`
- `NOT_APPLICABLE`

### Tolerancias numéricas actuales

Las tolerancias están implementadas de forma simple por obligación:

- `M` -> `0.0001`
- `C` -> `0.01`
- `O` -> `0.01`

Esto sirve como primera versión, pero no sustituye una parametrización por campo.

## Capa de IA opcional

La capa IA es desacoplable y configurable por proveedor.

### Configuración

Archivo: [backend/.env](/home/alejandrobarrera/sftr-unmatch-detector/backend/.env)

```env
LLM_PROVIDER=ollama
LLM_MODEL=gemma4:e4b
LLM_BASE_URL=http://localhost:11434
LLM_API_KEY=
```

### Proveedores soportados

Implementados en [llm_provider.py](/home/alejandrobarrera/sftr-unmatch-detector/backend/app/services/llm_provider.py):

- `ollama`
- `anthropic`
- `openai`

### Agentes disponibles

Implementados en [ai_agents.py](/home/alejandrobarrera/sftr-unmatch-detector/backend/app/services/ai_agents.py):

- `analyze_field`
  Explica una discrepancia concreta y propone pasos de resolución.
- `analyze_trade`
  Resume y prioriza discrepancias de una operación.
- `generate_session_narrative`
  Genera una narrativa ejecutiva de una sesión completa.

### Uso esperado

La IA es una capa adicional de interpretación. La lógica determinista de conciliación sigue estando en el motor de comparación y no depende del modelo.

## Frontend

### Páginas principales

- [DashboardPage.tsx](/home/alejandrobarrera/sftr-unmatch-detector/frontend/src/pages/DashboardPage.tsx)
  Resumen global de sesiones, operaciones y discrepancias.
- [UploadPage.tsx](/home/alejandrobarrera/sftr-unmatch-detector/frontend/src/pages/UploadPage.tsx)
  Carga del fichero de conciliación.
- [SessionsPage.tsx](/home/alejandrobarrera/sftr-unmatch-detector/frontend/src/pages/SessionsPage.tsx)
  Histórico de sesiones.
- [SessionDetailPage.tsx](/home/alejandrobarrera/sftr-unmatch-detector/frontend/src/pages/SessionDetailPage.tsx)
  Vista de operaciones de una sesión, export y resumen IA.
- [TradeDetailPage.tsx](/home/alejandrobarrera/sftr-unmatch-detector/frontend/src/pages/TradeDetailPage.tsx)
  Detalle completo de una operación con filtros por campo.

### Componentes principales

- [FieldDetailPanel.tsx](/home/alejandrobarrera/sftr-unmatch-detector/frontend/src/components/FieldDetailPanel.tsx)
  Gestión de una comparación de campo, edición de estado y análisis IA.
- [SeverityBadge.tsx](/home/alejandrobarrera/sftr-unmatch-detector/frontend/src/components/SeverityBadge.tsx)
  Etiquetas traducidas al español para resultado, severidad y estado.
- [Sidebar.tsx](/home/alejandrobarrera/sftr-unmatch-detector/frontend/src/components/Sidebar.tsx)
  Navegación lateral y estado del proveedor IA.

## API

### Sesiones

| Método | Endpoint | Descripción |
| --- | --- | --- |
| `POST` | `/api/sessions/upload` | Carga un CSV y crea la sesión |
| `GET` | `/api/sessions` | Lista sesiones |
| `GET` | `/api/sessions/{id}` | Devuelve sesión y operaciones |
| `GET` | `/api/sessions/{id}/summary` | Resumen agregado |
| `GET` | `/api/sessions/{id}/activity` | Trazabilidad |
| `POST` | `/api/sessions/{id}/bulk-update` | Acción masiva |
| `POST` | `/api/sessions/{id}/export` | Export XLSX |

### Operaciones

| Método | Endpoint | Descripción |
| --- | --- | --- |
| `GET` | `/api/trades/{trade_id}` | Devuelve una operación con sus 155 comparaciones |

### Comparaciones de campo

| Método | Endpoint | Descripción |
| --- | --- | --- |
| `PATCH` | `/api/field-comparisons/{fc_id}` | Actualiza estado, responsable, notas o validación |

### Analítica

| Método | Endpoint | Descripción |
| --- | --- | --- |
| `GET` | `/api/analytics/top-fields` | Campos con más discrepancias |
| `GET` | `/api/analytics/trend` | Tendencia por fecha |
| `GET` | `/api/analytics/by-counterparty` | Resumen por contrapartes |
| `GET` | `/api/analytics/by-sft-type` | Resumen por tipo SFT |

### IA

| Método | Endpoint | Descripción |
| --- | --- | --- |
| `GET` | `/api/ai/status` | Estado del proveedor IA |
| `POST` | `/api/ai/field-comparisons/{fc_id}/analyze` | Análisis IA de una discrepancia |
| `POST` | `/api/ai/trades/{trade_id}/analyze` | Análisis IA de una operación |
| `POST` | `/api/ai/sessions/{session_id}/narrative` | Narrativa ejecutiva de una sesión |

## Setup local

### Backend

```bash
cd backend
poetry install
poetry run fastapi dev app/main.py
```

API disponible en:

- `http://localhost:8000`
- docs automáticas: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend disponible por defecto en:

- `http://localhost:5173`

### Variables de entorno frontend

Crear `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

También hay un ejemplo en [frontend/.env.example](/home/alejandrobarrera/sftr-unmatch-detector/frontend/.env.example).

### Base de datos

Por defecto se usa:

```text
backend/sftr_unmatch.db
```

Puede sobrescribirse con `DATABASE_URL`.

### Configuración recomendada para Devin + Anthropic

Si vas a probar el repositorio dentro de `app.devin.ai`, lo recomendable es usar `Anthropic` u `OpenAI` con API key. Un `Ollama` local en tu máquina no será accesible desde Devin salvo que lo expongas como servicio remoto.

Se incluye una plantilla segura en [backend/.env.example](/home/alejandrobarrera/sftr-unmatch-detector/backend/.env.example).

Ejemplo para `Anthropic`:

```env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-20250514
LLM_API_KEY=your_anthropic_api_key_here
LLM_BASE_URL=
```

Flujo recomendado:

1. Copiar `backend/.env.example` a `backend/.env`.
2. Sustituir `LLM_API_KEY` por la clave real.
3. Mantener `frontend/.env` apuntando al backend correcto.
4. En Devin, pasar esos valores como secrets o variables de entorno, no hardcodearlos en el repo.

## Ficheros de muestra

Directorio: [backend/sample_data](/home/alejandrobarrera/sftr-unmatch-detector/backend/sample_data)

Ficheros relevantes:

- [sftr_reconciliation_sample.csv](/home/alejandrobarrera/sftr-unmatch-detector/backend/sample_data/sftr_reconciliation_sample.csv)
  Fichero tabular de ejemplo con 5 operaciones y 313 columnas.
- [sftr_reconciliation_demo.csv](/home/alejandrobarrera/sftr-unmatch-detector/backend/sample_data/sftr_reconciliation_demo.csv)
- [emisor_report.csv](/home/alejandrobarrera/sftr-unmatch-detector/backend/sample_data/emisor_report.csv)
- [receptor_report.csv](/home/alejandrobarrera/sftr-unmatch-detector/backend/sample_data/receptor_report.csv)
  Artefactos del modelo anterior, mantenidos como referencia.

## Estado de desarrollo y limitaciones conocidas

El proyecto está funcional, pero no cerrado. Puntos importantes:

- el parser depende de una convención de columnas concreta
- todavía no existe un motor formal de mapping configurable de columnas
- las tolerancias numéricas son globales por obligación, no específicas por campo
- las reglas `validation_rule` del catálogo aún no se aplican como validación proactiva estricta
- no hay suite de tests automatizados
- no hay migraciones versionadas, se sigue usando `Base.metadata.create_all()`
- la vista de sesión todavía no implementa paginación frontend real para cargas muy grandes
- el export XLSX sigue siendo funcional, pero su formato aún puede adaptarse mejor al nuevo modelo por operación
- la UI no está completamente unificada en español en todas las pantallas

## Qué se ha hecho en esta iteración

- reestructuración completa del modelo de datos del caso "una operación" al caso "miles de operaciones por fichero"
- parser CSV tabular con columnas por contraparte
- nuevo motor de comparación por fila
- introducción de `root_cause`
- tolerancias numéricas básicas
- nueva vista de sesión por operaciones
- nueva vista de detalle de operación
- edición de discrepancias por campo
- capa IA desacoplable por proveedor
- branding qaracter aplicado al frontend

## Siguientes mejoras naturales

- mapping configurable de columnas de entrada
- validación proactiva de LEI, ISIN, fechas y divisas
- tolerancias por campo
- trazabilidad y reporting auditable más formal
- paginación y búsqueda server-side para sesiones grandes
- tests de parser, comparación y API

## Referencias de implementación

- backend principal: [main.py](/home/alejandrobarrera/sftr-unmatch-detector/backend/app/main.py)
- modelos: [models.py](/home/alejandrobarrera/sftr-unmatch-detector/backend/app/models.py)
- schemas: [schemas.py](/home/alejandrobarrera/sftr-unmatch-detector/backend/app/schemas.py)
- parser: [file_parser.py](/home/alejandrobarrera/sftr-unmatch-detector/backend/app/services/file_parser.py)
- comparación: [comparison.py](/home/alejandrobarrera/sftr-unmatch-detector/backend/app/services/comparison.py)
- export: [export.py](/home/alejandrobarrera/sftr-unmatch-detector/backend/app/services/export.py)
- IA: [llm_provider.py](/home/alejandrobarrera/sftr-unmatch-detector/backend/app/services/llm_provider.py)
- IA: [ai_agents.py](/home/alejandrobarrera/sftr-unmatch-detector/backend/app/services/ai_agents.py)
- router sesiones: [sessions.py](/home/alejandrobarrera/sftr-unmatch-detector/backend/app/routers/sessions.py)
- router analítica: [analytics.py](/home/alejandrobarrera/sftr-unmatch-detector/backend/app/routers/analytics.py)
- router IA: [ai.py](/home/alejandrobarrera/sftr-unmatch-detector/backend/app/routers/ai.py)
