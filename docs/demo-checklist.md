# Demo Checklist

## Antes de empezar

- Confirmar que backend y frontend están arriba.
- Confirmar `LLM_PROVIDER=anthropic`.
- Abrir:
  - `http://localhost:5173`
  - `http://localhost:8000/docs`

## 1. Carga

- Ir a `Cargar fichero`.
- Subir uno o varios CSV de marzo 2026.
- Comprobar que crea sesión sin error.

Validar:

- nombre de contrapartes
- total de operaciones
- total de discrepancias
- sesión visible en listado

## 2. Vista de sesiones

- Ir a `Sesiones`.
- Abrir una sesión cargada.

Validar:

- métricas generales coherentes
- sesión con operaciones visibles

## 3. Detalle de sesión

- Revisar tabla de operaciones.
- Probar filtros:
  - `Unpair`
  - `Unmatch`
- Comprobar columna de tipo y motivo.

Validar:

- `UNPAIR` cuando falle `UTI` o `Other counterparty`
- `UNMATCH` para el resto

## 4. Detalle de operación

- Abrir una operación con discrepancias.
- Comprobar:
  - tabla de 155 campos
  - filtros de severidad
  - columna `Responsable`
  - estado
  - panel lateral de detalle

Validar:

- `root_cause` visible
- edición de estado / responsable / notas
- guardar cambios sin error

## 5. Export operativo

- En sesión, probar:
  - `Exportar todo`
  - `Exportar discrepancias`

Validar:

- descarga correcta
- hojas presentes
- columnas de contexto:
  - `Trade ID`
  - `UTI`
  - `Pairing Status`
  - `Pairing Reason`

## 6. Reprocesado

- Pulsar `Reprocesar sesión`.

Validar:

- termina sin error
- la sesión sigue consistente
- export sigue funcionando después

## 7. Analítica

- Ir a `Analítica`.
- Poner rango:
  - `2026-03-01` a `2026-03-31`
- Pulsar `Aplicar`.

Validar:

- KPIs cargan
- gráficas cargan
- top fields / counterparties cargan

## 8. Drill-down

- Hacer clic en:
  - un punto de evolución diaria
  - una barra
  - un día con incidencias

Validar:

- scroll automático
- resaltado temporal
- bloque `Sesiones del día` visible
- apertura correcta de sesión desde ahí

## 9. Comparación entre periodos

- Comparar:
  - `2026-03-01` a `2026-03-15`
  - `2026-03-16` a `2026-03-31`

Validar:

- deltas visibles
- tabla comparativa de campos
- coherencia general del resultado

## 10. IA

- Generar:
  - `Informe IA`
  - `Informe comparativo IA`
- Probar `Chat analítico guiado`

Preguntas recomendadas:

- `¿Qué campos parecen ser la principal fuente de discrepancias?`
- `¿Qué contrapartes requieren más atención?`
- `Compara la primera y segunda quincena de marzo`

Validar:

- respuesta generada
- efecto de escritura
- `Visual sugerido` clicable
- salto manual al gráfico correcto

## 11. Reporting regulatorio

- En analítica, usar `Preview regulatorio`.
- Luego:
  - `Guardar snapshot`
  - `Snapshot + IA`
  - descargar `XLSX`, `PDF`, `Word`

Validar:

- snapshot creado
- narrativa congelada visible
- descargas correctas
- histórico de snapshots visible

## 12. Cierre

- Comprobar que no hay errores en consola del navegador.
- Comprobar que el backend no devuelve `500`.

## Diagnóstico rápido si algo falla

1. Revisar `http://localhost:8000/api/ai/status`
2. Revisar logs del backend
3. Revisar `.env`
4. Confirmar que el frontend está pegando al backend correcto
