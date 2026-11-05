# Observabilidad

Fuente: guidelines 6.8 y 11.1 a 11.4. Tres señales (métricas, trazas, logs) correlacionadas por `traceId`. Se instrumenta con OpenTelemetry **si el cluster tiene colector**. Si no, el servicio arranca igual y loguea a stdout. No falla por eso.

## Qué se construye en `platform/`

Un middleware de entrada, un cliente de salida instrumentado, un logger estructurado y un helper de métricas, todos tomando el contexto de la request (`traceId`, tenant, operación) de un contexto de ejecución, no como parámetro en cada llamada.

## Logs

- JSON, una línea por evento, a `stdout`. Un colector lo recoge, el servicio no tiene credenciales del backend.
- Campos estándar puestos por la librería: `timestamp` (ISO 8601 UTC), `level`, `message` (frase fija en inglés, sin datos interpolados), `service`, `version`, `env`, `plane`, `trace.id`, `span.id`, `operation`, `tenant.id`, `caller.id`, `logger`. Los datos van en campos, no en el mensaje.
- Quién loguea: el middleware de request (inicio y fin), el filtro de errores (`warn` para `4xx`, `error` para `5xx`), los adaptadores de salida (llamadas externas, sin payload). El **dominio no loguea**. El caso de uso casi no: solo anomalías.
- Nunca: body completo, tokens, PAN, secretos, datos `pii-sensitive` sin enmascarar. El enmascarado es automático según `x-data-classification`.
- Sin `console.log` ni equivalente. Sin logs dentro de bucles por item.

## Métricas

- **RED por operación**: tasa (`http_server_requests_total`), errores y duración (histograma `http_server_request_duration_seconds`). Lo mismo por dependencia consumida (`http_client_*`), más estado del breaker, pool de conexiones y outbox pendiente.
- **De negocio** (por ejemplo `payments_created_total{status, provider, currency}`): las emite el caso de uso o un listener de eventos de dominio.
- Nombres `snake_case` con unidad o `_total`. Histogramas con buckets calibrados al SLO de cada operación.
- **Cardinalidad baja** en las dimensiones: `status`, `operation`, `provider`, `currency`. Nunca `payment.id`, `merchant.id` ni `trace.id` (destruyen el almacenamiento). Lo de alta cardinalidad va en trazas y logs.
- Se definen una vez y se usan en otro lugar, nunca dentro de métodos que corren por request.

## Trazas

- Spans de borde e infraestructura los crea la librería (entrante, saliente, base, consumidor, productor). El servicio no los crea a mano; agrega atributos de negocio al span activo con nombres consistentes con los logs (`payment.id`, `tenant.id`, `provider`).
- Propagación del `traceparent` (W3C Trace Context) en headers HTTP, metadata gRPC y envelope de eventos. Los eventos asíncronos enlazan con un link, no como hijo.
- Solo `5xx` y excepciones marcan el span como error. Un `4xx` es `OK`.
- Sin datos sensibles en atributos.

## SLOs

Cada operación declara `x-slo` en el contrato (disponibilidad y umbral de latencia). Las reglas de grabación y las cuatro alertas de burn rate (velocidad a la que se consume el presupuesto de error) se derivan del contrato. Sin generador propio todavía, se documentan en `docs/platform-assumptions.md` como pendiente.

## Tests

Un test e2e de instrumentación con exportadores en memoria: el `traceId` aparece en logs, respuesta de error, evento publicado y mensaje en DLQ. Un test de enmascarado que captura la salida estándar. Que ninguna métrica lleve etiquetas de alta cardinalidad.
