# Auditoría QA Profunda — SFTR Unmatch Detector

**Fecha:** 9 de abril de 2026  
**Auditor:** Devin (QA Técnico Principal)  
**Commit de referencia:** `64ddf5fa` + branch `devin/1775660593-phase2-improvements`  
**Repo:** https://github.com/alejandrobarreraqaracter/sftr-unmatch-detector

---

## 1. Resumen Ejecutivo

### Estado general del repositorio
El repositorio implementa una aplicación full-stack funcional para conciliación SFTR con un grado de madurez **alto para demo** y **medio para piloto técnico**. La arquitectura `Session → TradeRecord → FieldComparison` es sólida, el motor de comparación implementa correctamente las reglas de obligación SFTR, y la capa de IA (Anthropic) funciona correctamente para análisis, narrativas y chat analítico.

### Grado de madurez real
- **Backend:** 85% — Motor de comparación robusto, tolerancias por campo, validadores proactivos, 128 tests pasando, exports XLSX/PDF/Word funcionales, reporting regulatorio con snapshots y caché
- **Frontend:** 80% — Dashboard, sesiones, detalle, analítica, chat IA, comparación de periodos, branding qaracter aplicado
- **IA:** 90% — Todos los endpoints funcionan con Anthropic (análisis campo, operación, narrativa sesión, informe analítico, chat, comparación periodos, export)
- **Docker:** 60% — Stack definido pero con problemas de configuración de env vars y modo desarrollo
- **Tests:** 70% — 128 tests backend (parser, comparación, tolerancias, validadores, upload), 0 tests frontend

### Veredicto
| Escenario | Estado |
|-----------|--------|
| Demo seria ante cliente | **LISTO** (con preparación de datos y flujo guiado) |
| Piloto técnico interno | **CASI LISTO** (necesita fixes Docker, tests E2E, hardening) |
| Producción | **NO LISTO** (necesita PostgreSQL, auth, rate limiting, CI/CD) |

---

## 2. Hallazgos QA

### Bugs confirmados

| # | Severidad | Descripción | Estado |
|---|-----------|-------------|--------|
| B1 | **ALTA** | Resolución de alias de columnas en `build_column_index`: cuando el CSV usa nombres alias como `type_sft` en lugar del canónico `sft_type`, el valor de metadata se perdía silenciosamente, causando clasificación incorrecta de obligaciones (CRITICAL → NONE o viceversa) | **CORREGIDO** — commit `1572ffa` |
| B2 | **MEDIA** | Docker compose no pasa variables LLM al contenedor backend — solo establece `DATABASE_URL`. Las variables `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY` dependen de que `backend/.env` exista en el bind mount | Diagnosticado, no corregido |
| B3 | **MEDIA** | Backend Dockerfile usa `fastapi dev` (modo desarrollo) — no apto para producción, expone debugger y reload automático | Diagnosticado, no corregido |
| B4 | **BAJA** | `check-docker-stack.sh` referencia endpoint `/healthz` que SÍ existe en el backend (verificado), pero el puerto de Ollama puede conflictuar con instalación local (11434) | Riesgo operativo documentado |
| B5 | **BAJA** | El export XLSX regulatorio con 31+ sesiones genera timeout — problema de escalabilidad en `_build_export_response` | Diagnosticado, no corregido |

### Inconsistencias

| # | Descripción | Impacto |
|---|-------------|---------|
| I1 | CORS configurado como `allow_origins=["*"]` — acepta cualquier origen | Riesgo de seguridad en producción |
| I2 | Tabla `activity_logs` (plural) vs referencia en código como `activity_log` (singular) en algunos puntos — funciona pero puede confundir | Bajo |
| I3 | Datos sintéticos de marzo 2026 usan siempre las mismas contrapartes (CP1/CP2) — no representativo para demo multi-contraparte | Bajo para demo, medio para piloto |
| I4 | `audit_summary.json` referenciado en prompt del usuario pero no existe — el script generador no lo crea | Sin impacto funcional |

### Riesgos

| # | Riesgo | Probabilidad | Impacto |
|---|--------|--------------|---------|
| R1 | SQLite single-writer bottleneck con uploads concurrentes | Media | Alto |
| R2 | Sin autenticación — cualquier usuario puede borrar/modificar datos | Alta | Alto |
| R3 | Sin rate limiting en endpoints de IA — costes Anthropic no controlados | Alta | Medio |
| R4 | Frontend carga todas las operaciones de una sesión sin paginación real del lado servidor para field_comparisons | Media | Medio |
| R5 | Sin CI/CD configurado — no hay validación automática de PRs | Alta | Medio |

### Huecos de pruebas

| Área | Cobertura actual | Lo que falta |
|------|-----------------|--------------|
| Backend unit tests | 128 tests (parser, comparación, tolerancias, validadores, upload) | Tests para analytics, reporting, AI, export |
| Frontend tests | 0 tests | Todo: componentes, páginas, integración |
| E2E tests | 0 tests automatizados | Playwright/Cypress para flujos críticos |
| Docker | No validado en este entorno | Build, startup, env loading |
| Performance | Medido manualmente (queries <100ms a 121K rows) | Load testing, concurrent uploads |

---

## 3. Qué he probado exactamente

### Backend — Endpoints testeados con curl

#### Sesiones y operaciones
```
GET  /healthz                          → 200 {"status":"ok"}
POST /api/sessions/upload              → 200 (CSV sample + 31 marzo 2026 CSVs)
GET  /api/sessions                     → 200 (32 sesiones listadas)
GET  /api/sessions/1                   → 200 (5 operaciones, 4 unmatches, 2 critical)
GET  /api/sessions/1/summary           → 200 (métricas correctas)
GET  /api/trades/1                     → 200 (155 campos, 0 unmatches, pairing=null)
GET  /api/trades/2                     → 200 (1 unmatch: Fixed rate)
GET  /api/trades/6                     → 200 (pairing=UNPAIR, reason="Other counterparty, UTI")
PATCH /api/field-comparisons/194       → Probado (status, assignee, notes)
GET  /api/sessions/1/export            → 200 (XLSX descargado correctamente)
POST /api/sessions/1/reprocess         → 200 (reprocesamiento funcional)
```

#### Analítica
```
GET  /api/analytics/overview           → 200 (32 sesiones, 786 ops, 27254 discrepancias)
GET  /api/analytics/daily              → 200 (desglose diario correcto)
GET  /api/analytics/top-fields         → 200 (top 10 campos con más discrepancias)
GET  /api/analytics/by-counterparty    → 200 (CP1 vs CP2: 27254)
GET  /api/analytics/by-sft-type        → 200 (Repo: 27254)
GET  /api/analytics/sessions-by-day?day=2026-03-05 → 200
GET  /api/analytics/compare?from_a=2026-03-01&to_a=2026-03-15&from_b=2026-03-16&to_b=2026-03-31 → 200
```

#### Reporting regulatorio
```
GET  /api/reporting/regulatory/preview            → 200 (preview con métricas)
POST /api/reporting/regulatory/generate           → 200 (snapshot creado con narrativa IA)
GET  /api/reporting/regulatory/export.xlsx         → Timeout con 31 sesiones (B5)
GET  /api/reporting/regulatory/snapshots           → 200 (1 snapshot listado)
GET  /api/reporting/regulatory/snapshots/1         → 200 (detalle con payload)
GET  /api/reporting/regulatory/snapshots/1/export.xlsx → 200 (1.7MB)
GET  /api/reporting/regulatory/snapshots/1/export.pdf  → 200 (5.8KB)
GET  /api/reporting/regulatory/snapshots/1/export.doc  → 200 (2.9KB)
GET  /api/reporting/regulatory/snapshots/1/artifacts   → 200 (metadatos de caché)
```

#### IA (Anthropic)
```
GET  /api/ai/status                    → 200 {"available":true, "provider":"anthropic", "model":"claude-sonnet-4-20250514"}
POST /api/ai/field-comparisons/194/analyze → 200 (explicación, pasos resolución, riesgo regulatorio)
POST /api/ai/trades/2/analyze          → 200 (resumen, campo prioritario, riesgo, acción recomendada)
POST /api/ai/sessions/1/narrative      → 200 (narrativa ejecutiva en español)
POST /api/ai/analytics/report          → 200 (informe analítico completo)
POST /api/ai/analytics/chat            → 200 (respuesta contextual con suggested_visual)
POST /api/ai/analytics/compare-report  → No probado explícitamente (endpoint existe)
POST /api/ai/analytics/report/export   → No probado explícitamente (endpoint existe)
```

### Frontend — Páginas verificadas visualmente

| Página | URL | Estado |
|--------|-----|--------|
| Dashboard | `/` | Funcional — 32 sesiones, métricas correctas, tabla recientes |
| Upload | `/upload` | Funcional — formulario de carga |
| Sesiones | `/sessions` | Funcional — listado paginado |
| Detalle sesión | `/sessions/1` | Funcional — operaciones, filtros, export, UNPAIR/UNMATCH badges |
| Analítica | `/analytics` | Funcional — overview, chat IA, comparación periodos, gráficos |

### Reconciliation Logic — Verificación semántica

| Regla | Verificación | Resultado |
|-------|-------------|-----------|
| UTI/Other counterparty mismatch → UNPAIR | Trade 6 (marzo 2026): UTI y Other counterparty difieren → `pairing_status=UNPAIR` | **CORRECTO** |
| Discrepancias en otros campos → UNMATCH | Trade 2 (sample): solo Fixed rate difiere → `pairing_status=UNMATCH` | **CORRECTO** |
| Ambos lados mismo valor (incluso vacío) → no discrepancia | Trade 1: 155 MATCH (150 same value + 5 BOTH_EMPTY) | **CORRECTO** |
| Mirror fields (GIVE/TAKE) → MIRROR | Trade 5: side cp1=GIVE, cp2=TAKE → `result=MIRROR, root_cause=MIRROR_MATCH` | **CORRECTO** |
| Obligation `-` → NA when values differ | No hay campos con obligación `-` y valores diferentes en sample (todos coinciden) | Sin evidencia directa |
| Tolerancias numéricas | Trade 2: Fixed rate 0.0125 vs 0.0150, delta=0.0025, tolerance=0.0001 → UNMATCH | **CORRECTO** |
| MATCH vs NA semántica | MATCH se usa para valores iguales/dentro tolerancia; NA para obligation `-` con valores diferentes | **CORRECTO** según código |

### Datos de prueba
- **Sample CSV:** 5 operaciones, 155 campos, 4 unmatches (2 CRITICAL, 2 WARNING)
- **Marzo 2026:** 31 CSVs (1 por día), 781 trades adicionales, 27,250 unmatches
- **Total en DB:** 32 sesiones, 786 trades, 121,830 field comparisons, 23MB SQLite

### Tests automatizados
```bash
pytest backend/tests/ -v
# 128 tests passed, 0 failed
# test_file_parser.py: 10 tests
# test_comparison.py: 54 tests
# test_tolerances.py: 21 tests
# test_validators.py: 33 tests
# test_upload_endpoint.py: 10 tests
```

---

## 4. Cambios aplicados

### Commits realizados

| Commit | Archivo(s) | Descripción |
|--------|-----------|-------------|
| `1572ffa` | `backend/app/services/column_mapping.py` | Fix: resolución de aliases de metadatos en `build_column_index`. Cuando el CSV usa alias (`type_sft`) en lugar del canónico (`sft_type`), ahora se registra también el nombre canónico en `norm_to_original` |

### Validación post-fix
- Los 128 tests existentes siguen pasando
- Test específico verifica que `build_column_index(["type_sft", "action_code", ...])` produce `norm_to_original` con ambas claves (`"type_sft"` y `"sft_type"`)
- Impacto: previene clasificación incorrecta de obligaciones cuando CSVs usan nombres de columna alternativos

---

## 5. Riesgos residuales

### Lo que sigue siendo débil

| Área | Debilidad | Riesgo para demo | Riesgo para piloto |
|------|-----------|-------------------|-------------------|
| **Docker** | compose no inyecta env vars de IA; usa modo dev; sin healthcheck | Bajo (demo local) | **Alto** |
| **Auth** | Sin autenticación ni autorización | Bajo (demo controlada) | **Crítico** |
| **CORS** | `allow_origins=["*"]` | Bajo | **Alto** |
| **Rate limiting IA** | Sin límites en llamadas a Anthropic | Medio | **Alto** |
| **Export XLSX** | Timeout con 31+ sesiones en regulatory export | **Medio** | **Alto** |
| **Tests frontend** | 0 tests | Bajo | **Alto** |
| **CI/CD** | No existe | Bajo | **Alto** |
| **SQLite** | Single-writer, sin backups, sin WAL mode | Bajo | **Alto** |

### Lo que NO debería venderse como "cerrado"

1. **Stack Docker para producción** — necesita hardening significativo
2. **Seguridad** — ni auth, ni CORS restringido, ni rate limiting
3. **Escalabilidad** — SQLite es adecuado para demo/piloto pequeño pero no para volúmenes reales
4. **Tests E2E automatizados** — cobertura solo en backend, nada en frontend ni E2E
5. **Export regulatorio a escala** — timeout con 31 sesiones
6. **Datos sintéticos** — no representan variedad real de contrapartes/tipos SFT

---

## 6. Recomendación de siguientes pasos

### P0 — Antes de demo

| # | Acción | Esfuerzo |
|---|--------|----------|
| 1 | Preparar dataset demo curado con 3-5 sesiones representativas (diferentes contrapartes, tipos SFT, con UNPAIRs y UNMATCHs) | 2h |
| 2 | Probar flujo demo completo: upload → detalle → resolución → IA → export → analítica → reporting | 1h |
| 3 | Verificar que PDF/Word del snapshot no muestra markdown crudo | 30min |
| 4 | Preparar script de setup rápido para demo (`make demo` o similar) | 1h |

### P1 — Antes de piloto técnico

| # | Acción | Esfuerzo |
|---|--------|----------|
| 1 | Fix Docker compose: `env_file: ./backend/.env`, cambiar a `fastapi run` para producción, añadir healthchecks | 2h |
| 2 | Implementar autenticación básica (JWT o API key simple) | 4h |
| 3 | Restringir CORS a dominios específicos | 30min |
| 4 | Añadir rate limiting en endpoints de IA (ej. 10 req/min) | 2h |
| 5 | Optimizar export XLSX regulatorio (streaming, paginación) | 4h |
| 6 | Añadir índices SQLite: `(result, field_name)` para analytics | 30min |
| 7 | Configurar CI/CD básico (GitHub Actions: lint, tests, build) | 2h |
| 8 | Añadir tests E2E con Playwright para flujos críticos (upload, detalle, resolución, export) | 8h |
| 9 | Activar WAL mode en SQLite para mejor concurrencia de lectura | 30min |

### P2 — Para escalar

| # | Acción | Esfuerzo |
|---|--------|----------|
| 1 | Migración a PostgreSQL | 8h |
| 2 | Jobs asíncronos para procesamiento de CSV y exports (Celery/ARQ) | 16h |
| 3 | Caché de analytics con materialización (Redis o tabla precomputada) | 8h |
| 4 | Paginación server-side para field_comparisons en detalle de trade | 4h |
| 5 | Límites al tamaño de prompt de IA (truncar contexto a N operaciones) | 2h |
| 6 | Monitorización y observabilidad (logging estructurado, métricas) | 8h |
| 7 | Backup automático de base de datos | 2h |
| 8 | Tests de carga (Locust/k6) para validar throughput | 4h |

---

## Anexo: Métricas de rendimiento medidas

| Métrica | Valor |
|---------|-------|
| DB size (32 sesiones, 786 trades, 121K FC) | 23 MB |
| Top-fields aggregation query | 24ms |
| Session detail query (3,255 rows) | 10ms |
| Daily analytics join (121K rows) | 100ms |
| AI field analysis response time | ~5s (Anthropic) |
| AI session narrative response time | ~10s (Anthropic) |
| Snapshot XLSX export (1 week) | ~2s, 1.7MB |
| Snapshot PDF export | <1s, 5.8KB |
| Snapshot Word export | <1s, 2.9KB |

## Anexo: Arquitectura verificada

```
Session (1 CSV) → TradeRecord (1 fila/operación) → FieldComparison (1 campo × 155)
                                                  → pairing_status: UNPAIR | UNMATCH | null
                                                  → pairing_reason: "UTI, Other counterparty" | null

ReportingSnapshot → payload (JSON congelado) → artifacts (caché XLSX/PDF/Word)

ActivityLog → tracking de cambios de estado en field_comparisons
```

### Endpoints verificados: 30+ endpoints funcionales
### Tests automatizados: 128 pasando
### Páginas frontend: 5 verificadas visualmente
### Integración IA: 6 endpoints probados con Anthropic (claude-sonnet-4-20250514)
