# Diseño técnico: reporte regulatorio por rango de fechas

## Objetivo

Diseñar una capacidad de reporting regulatorio que permita:

- seleccionar un rango de fechas
- generar un anexo auditable en `CSV/XLSX`
- generar un informe ejecutivo en `PDF/Word`
- reflejar qué operaciones fallaron, qué se hizo sobre ellas y qué riesgo permanece abierto
- escalar desde el MVP actual a volúmenes mucho mayores sin obligar al LLM a procesar datos brutos

La premisa principal es esta:

- el dato auditable debe ser determinista y trazable
- la IA solo debe redactar sobre agregados calculados por backend

## Principios de diseño

1. El informe IA nunca sustituye al dato estructurado.
2. La narrativa no se genera sobre millones de filas, sino sobre resúmenes agregados.
3. El anexo debe poder entregarse a auditoría o regulador sin depender del LLM.
4. La generación debe ser reproducible para un mismo rango de fechas.
5. El sistema debe poder evolucionar a ejecución asíncrona y preagregación.

## Entregables del reporte

El reporte regulatorio completo debe componerse de dos piezas.

### 1. Anexo estructurado

Formato:

- `CSV`
- `XLSX`

Contenido:

- una fila por operación
- o una fila por discrepancia de campo, según el nivel de detalle elegido

Casos de uso:

- auditoría interna
- revisión por Compliance
- entrega de evidencia ante Banco Central, CNMV o ESMA

### 2. Informe ejecutivo

Formato:

- `PDF`
- `Word`

Contenido:

- resumen del rango
- evolución temporal
- focos de riesgo
- backlog
- remediación ejecutada
- riesgo residual
- recomendaciones

## Preguntas que debe responder

Un reporte regulatorio útil debe contestar al menos:

- cuántas operaciones se procesaron en el periodo
- cuántas operaciones fallaron
- cuántas fueron `UNPAIR`
- cuántas incidencias eran críticas
- qué campos concentraron más discrepancias
- qué contrapartes concentraron más incidencias
- cuántas incidencias se resolvieron
- cuántas siguen abiertas
- qué se hizo sobre ellas
- qué riesgo sigue pendiente

## Modelo lógico del reporte

El diseño propuesto añade una capa de reporting sobre el modelo actual:

```text
Session
  -> TradeRecord
       -> FieldComparison
  -> ActivityLog

ReportingSnapshot
  -> ReportingKPI
  -> ReportingTopField
  -> ReportingTopCounterparty
  -> ReportingOpenCritical
```

## Componentes nuevos propuestos

### ReportingSnapshot

Representa una fotografía reproducible de un informe generado para un rango concreto.

Campos sugeridos:

- `id`
- `date_from`
- `date_to`
- `created_at`
- `created_by`
- `source_sessions_count`
- `source_trades_count`
- `source_field_comparisons_count`
- `payload_json`
- `narrative_markdown`
- `report_version`

Propósito:

- congelar el contexto del informe
- permitir reexportar el mismo reporte sin recalcular ni volver a llamar al LLM

### ReportingKPI

Opcional si se guarda todo en `payload_json`, pero útil si luego se quiere consultar por SQL.

KPIs sugeridos:

- `sessions`
- `total_trades`
- `trades_with_unmatches`
- `unpair_trades`
- `unmatch_trades`
- `clean_trades`
- `total_unmatches`
- `critical_count`
- `warning_count`
- `pending_fields`
- `resolved_fields`
- `quality_rate`
- `resolution_rate`

### ReportingTopField

Campos sugeridos:

- `snapshot_id`
- `field_name`
- `table_number`
- `count`
- `critical_count`
- `warning_count`

### ReportingTopCounterparty

Campos sugeridos:

- `snapshot_id`
- `emisor_name`
- `receptor_name`
- `sessions`
- `total_trades`
- `total_unmatches`
- `critical_count`

### ReportingOpenCritical

Lista de operaciones o incidencias críticas todavía abiertas en el momento del informe.

Campos sugeridos:

- `snapshot_id`
- `session_id`
- `trade_id`
- `uti`
- `field_name`
- `severity`
- `status`
- `assignee`
- `notes`
- `updated_at`

## Payload agregado para IA

El LLM no debe recibir detalle bruto. Debe recibir un objeto compacto y controlado.

Payload propuesto:

```json
{
  "report_scope": {
    "date_from": "2026-03-01",
    "date_to": "2026-03-31"
  },
  "overview": {
    "sessions": 31,
    "total_trades": 781,
    "trades_with_unmatches": 640,
    "unpair_trades": 94,
    "unmatch_trades": 546,
    "clean_trades": 141,
    "total_unmatches": 27250,
    "critical_count": 18000,
    "warning_count": 9250,
    "pending_fields": 4300,
    "resolved_fields": 12100,
    "quality_rate": 65.2,
    "resolution_rate": 73.8
  },
  "daily_summary": [
    {
      "date": "2026-03-03",
      "total_trades": 30,
      "total_unmatches": 1050,
      "critical_count": 690,
      "unpair_trades": 12
    }
  ],
  "top_fields": [
    {
      "field_name": "Other counterparty",
      "table_number": 1,
      "count": 340
    }
  ],
  "top_counterparties": [
    {
      "emisor_name": "CP1",
      "receptor_name": "CP2",
      "total_unmatches": 4200
    }
  ],
  "open_critical_items": [
    {
      "uti": "UTI-20260303-0042",
      "field_name": "Maturity date",
      "status": "PENDING",
      "assignee": "Equipo SFTR Ops"
    }
  ],
  "remediation_summary": {
    "resolved_fields": 12100,
    "pending_fields": 4300,
    "in_negotiation_fields": 1200,
    "excluded_fields": 600
  },
  "comparison_to_previous_period": {
    "enabled": true,
    "total_unmatches_delta_pct": -8.4,
    "critical_count_delta_pct": -4.1,
    "unpair_trades_delta_pct": 12.2
  }
}
```

## Restricciones del prompt de IA

El prompt del informe regulatorio debe imponer reglas duras:

- no inventar cifras
- no citar métricas ausentes del payload
- no inferir causas no respaldadas por datos agregados
- mencionar explícitamente si un dato no está disponible
- separar hechos observados de recomendaciones

Regla clave:

- la parte cuantitativa del informe debe salir del backend
- la IA solo redacta, resume y prioriza

## Formato del anexo estructurado

### Hoja 1: Executive Summary

Debe incluir:

- rango de fechas
- fecha de generación
- sesiones incluidas
- operaciones procesadas
- operaciones con discrepancias
- `UNPAIR`
- `UNMATCH`
- críticas
- advertencias
- pendientes
- resueltas
- calidad %
- resolución %

### Hoja 2: Trades Summary

Una fila por operación:

- `business_date`
- `session_id`
- `trade_id`
- `row_number`
- `UTI`
- `SFT Type`
- `Action Type`
- `emisor_name`
- `receptor_name`
- `pairing_status`
- `pairing_reason`
- `total_fields`
- `total_unmatches`
- `critical_count`
- `warning_count`
- `has_unmatches`

### Hoja 3: Open Items

Solo incidencias no resueltas:

- `business_date`
- `session_id`
- `trade_id`
- `UTI`
- `field_name`
- `severity`
- `status`
- `assignee`
- `root_cause`
- `notes`
- `updated_at`

### Hoja 4: Critical Open Items

Subconjunto de la hoja anterior para severidad `CRITICAL`.

### Hoja 5: Field Detail

Una fila por discrepancia:

- `business_date`
- `session_id`
- `trade_id`
- `UTI`
- `field_name`
- `table_number`
- `field_number`
- `obligation`
- `emisor_value`
- `receptor_value`
- `result`
- `severity`
- `root_cause`
- `status`
- `assignee`
- `notes`
- `validated`
- `updated_at`

### Hoja 6: Daily Trend

Una fila por día:

- `date`
- `sessions`
- `total_trades`
- `trades_with_unmatches`
- `unpair_trades`
- `total_unmatches`
- `critical_count`
- `warning_count`
- `resolved_fields`
- `pending_fields`

### Hoja 7: Top Fields

Una fila por campo:

- `field_name`
- `table_number`
- `count`
- `critical_count`
- `warning_count`

## Estructura del informe ejecutivo

### Sección 1. Alcance

- periodo cubierto
- sesiones incluidas
- contrapartes incluidas
- universo total de operaciones

### Sección 2. Resultado global

- calidad general del periodo
- volumen total de discrepancias
- severidad agregada
- peso de `UNPAIR`

### Sección 3. Evolución temporal

- días más problemáticos
- tendencia general
- cambios frente al periodo anterior, si aplica

### Sección 4. Focos de riesgo

- top campos
- top contrapartes
- operaciones críticas abiertas

### Sección 5. Remediación ejecutada

- incidencias resueltas
- backlog abierto
- casos en negociación
- responsables asignados

### Sección 6. Riesgo residual y recomendaciones

- qué sigue abierto
- impacto potencial
- acciones recomendadas

## Endpoints propuestos

### Backend analítico

- `GET /api/reporting/regulatory/preview?date_from=...&date_to=...`
  - devuelve solo agregados y preview estructurado

- `POST /api/reporting/regulatory/generate`
  - crea un `ReportingSnapshot`
  - opcionalmente genera narrativa IA

- `GET /api/reporting/regulatory/{snapshot_id}`
  - devuelve el snapshot ya congelado

- `GET /api/reporting/regulatory/{snapshot_id}/export.xlsx`
  - export estructurado

- `GET /api/reporting/regulatory/{snapshot_id}/export.pdf`
  - informe ejecutivo PDF

- `GET /api/reporting/regulatory/{snapshot_id}/export.doc`
  - informe ejecutivo Word

### Backend IA

- `POST /api/ai/reporting/regulatory/narrative`
  - recibe payload agregado
  - devuelve narrativa markdown

## Flujo recomendado

1. El usuario selecciona `date_from` y `date_to`.
2. El backend calcula agregados.
3. El usuario ve un preview determinista.
4. El usuario pulsa `Generar reporte regulatorio`.
5. El backend guarda un `ReportingSnapshot`.
6. Si se solicita IA, el LLM redacta sobre el payload agregado.
7. El usuario descarga:
   - `XLSX` auditable
   - `PDF/Word` ejecutivo

## Estrategia de escalabilidad

## Fase 1. MVP avanzado

Mantener:

- SQLite
- cálculo on-demand
- narrativa sobre agregados

Límite razonable:

- miles o decenas de miles de operaciones por periodo

## Fase 2. Operación real

Mover a:

- PostgreSQL
- índices por fecha, estado, severidad, campo y pairing
- jobs de agregación diaria
- snapshots persistidos
- generación de informes asíncrona

Índices recomendados:

- `sessions(created_at)`
- `sessions(filename)`
- `trade_records(session_id, uti)`
- `field_comparisons(session_id, trade_id)`
- `field_comparisons(field_name, severity, status)`
- `field_comparisons(updated_at)`

## Fase 3. Escala alta

Para cientos de miles o millones:

- particionado por fecha
- tablas agregadas diarias
- colas de trabajo para generación de reportes
- caché por rango de fechas
- almacenamiento desacoplado de exportaciones generadas

## Cómo evitar alucinaciones del LLM

1. No enviar filas brutas.
2. No enviar todo el periodo a texto libre.
3. Enviar solo agregados cerrados.
4. Hacer que la numeralia del informe se pinte desde código cuando sea posible.
5. Congelar el payload en `ReportingSnapshot`.
6. Versionar prompts y snapshots.

## Qué partes deben ser deterministas

Deterministas:

- KPIs
- tablas
- anexos
- ratios
- contadores
- listas de pendientes

Narrativas IA:

- resumen ejecutivo
- lectura de tendencias
- priorización
- recomendaciones

## Orden de implementación recomendado

### P0

- añadir preview regulatorio por rango
- export estructurado `XLSX`
- incluir backlog abierto, assignee y notas

### P1

- añadir `ReportingSnapshot`
- congelar payload y narrativa
- export `PDF/Word` desde snapshot

### P2

- añadir informe IA regulatorio
- añadir comparación con periodo anterior
- destacar riesgo residual

### P3

- pasar a generación asíncrona
- añadir cache y preagregación
- preparar migración a PostgreSQL

## Recomendación final

Para este proyecto, la forma correcta de escalar no es aumentar el contexto del LLM.

La arquitectura correcta es:

- detalle completo en base de datos
- agregación fuerte en backend
- snapshot reproducible del informe
- IA solo como capa de redacción sobre payload agregado

Eso permite:

- auditoría fiable
- menor coste
- menor latencia
- menor riesgo de alucinación
- evolución razonable hacia cargas masivas
