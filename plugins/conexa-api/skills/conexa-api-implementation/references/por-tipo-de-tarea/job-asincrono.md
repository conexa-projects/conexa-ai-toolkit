# Job asíncrono y bulk

Fuente: guidelines 5.8, 10.8. Una operación que tarda más que el presupuesto de latencia de una request, o que procesa un lote, responde `202 Accepted` y se ejecuta aparte.

## El recurso de trabajo

`POST` que encola responde `202` con `Location: /jobs/{id}` y el job en estado `queued`. Es un recurso con identidad propia.

Máquina de estados: `queued` (aceptado, no empezó), `running` (opcionalmente con `progress` de 0 a 1 si la operación puede reportarlo de verdad), `succeeded` (aparece `result`), `failed` (aparece `error` con el formato estándar, incluido `code` y `traceId`), `cancelled` (solo si la operación lo soporta).

Campos: `id`, `type`, `status`, `input` (copia de lo pedido, para que sea autocontenido), `result` (solo si `succeeded`; resultados grandes como URL firmada con expiración), `error` (solo si `failed`), `createdAt`, `startedAt`, `completedAt`, `expiresAt` (retención declarada por tipo, 7 días típico).

El `POST` que crea el job lleva idempotency key como cualquier operación con efectos.

## Workers

- **Idempotentes y reiniciables.** Si un worker muere a mitad, el lock vence y otro lo toma. La ejecución escribe su resultado de forma que repetirla no duplique efectos.
- **Lock con expiración** (`lockedUntil`), más corto que el SLO del job. Sin esto, un worker muerto deja el job `running` para siempre.
- **Timeout por tipo de job.** Si lo supera, `failed` con `code: JOB_TIMEOUT`.
- **Concurrencia acotada por tipo**, para que mil pedidos a la vez no tumben la base. El exceso espera en `queued`.
- **Aislamiento por tenant**: un tenant que pide diez mil exportaciones no bloquea a los demás. Cuota de jobs `queued` más `running` por tenant (excederla es `429`).
- Trabajo dividido en **chunks idempotentes** con el progreso persistido como cursor. Al reintentar, se retoma desde el último chunk completo.
- Los workers corren en un proceso distinto al de las requests HTTP.
- Si falla por una dependencia, mismo ciclo que un consumidor de eventos: reintentos con backoff y una cola de jobs fallidos con los mismos campos que la DLQ.
- Watchdog: si un job esperado no aparece en su ventana, se detecta y se reencola.

## Notificación de finalización

El consumidor puede consultar por polling (`GET /jobs/{id}`, con `Retry-After` sugerido) y/o recibir un evento o webhook al terminar. Publicar el evento por outbox.

## Bulk

- **Bulk asíncrono** es el default para más de decenas de items. Un job con resultado por item.
- `status: succeeded` aunque haya fallos parciales: el job terminó y el resultado dice qué pasó con cada item. `failed` es solo para cuando el job entero no pudo ejecutarse.
- Resultado por item con `index` (posición en el `input`, para correlacionar), estado y error si corresponde. Los fallos van inline hasta un límite (100). Si hay más, todos los resultados van a un archivo (`resultsUrl`, JSON Lines).
- Semántica parcial por default: cada item se procesa de forma independiente. Atómico (todo o nada) solo si hay una invariante que lo exija, y se declara.
- Límite de items en el schema (`maxItems`, 1000 típico).
- El worker procesa en lotes internos (de 50, una transacción por lote) y actualiza `progress` por lote.
- **Idempotencia por item**, además de por job: se registra qué `index` completó.
- Bulk síncrono solo para lotes chicos y operaciones rápidas.

## Tests obligatorios

Encolar y consultar hasta `succeeded`. Worker que muere a mitad: otro retoma y no repite items ya procesados. Job que supera el timeout. Cuota por tenant. Bulk con fallos parciales. Cancelación si aplica.
