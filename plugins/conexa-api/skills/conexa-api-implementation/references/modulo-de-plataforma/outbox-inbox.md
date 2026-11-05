# Outbox e inbox

Fuente: guidelines 3.d y 10.8. Resuelven dos problemas del mundo de eventos. Por qué existen: escribir en la base y publicar al broker son dos operaciones que no pueden ser atómicas entre sí. Si el proceso muere entre una y otra, se pierde el evento o queda uno sin cambio de estado.

## Outbox (publicar sin perder eventos)

**Qué es:** una tabla `outbox` en la misma base del servicio. El caso de uso escribe el estado nuevo **y** el evento en esa tabla **en la misma transacción**. Un proceso aparte (el relay) lee las filas pendientes y las publica al broker.

```
outbox
  id, topic, partition_key, payload (envelope completo), headers,
  created_at, published_at (nulo si pendiente), attempts
```

- El publicador (adaptador de salida del puerto de eventos) **exige estar dentro de una transacción**. Publicar fuera de una es un bug y lanza.
- El relay publica en orden por `partition_key` (por agregado), marca `published_at` solo tras la confirmación del broker, y reintenta con backoff. Si el broker está caído, la outbox acumula y publica todo al volver.
- Entrega **al menos una vez**: puede haber duplicados. Por eso el consumidor es idempotente.
- Métricas con alerta: `outbox_pending_rows` y `outbox_oldest_pending_seconds`.
- Limpieza de filas publicadas tras un período de retención.
- Un broker distinto por proyecto: el relay habla con una interfaz `EventBroker` y hay un adaptador por broker.

## Inbox (consumir sin duplicar efectos)

**Qué es:** una tabla `processed_events` con el `id` del evento como clave única. Antes de aplicar el efecto, el consumidor inserta el `id` **en la misma transacción que el efecto**. Si la inserción falla por clave duplicada, el evento ya se procesó: se confirma y se ignora.

```
processed_events
  consumer, event_id, processed_at     PRIMARY KEY (consumer, event_id)
```

- Hace falta cuando el efecto no es idempotente por naturaleza (un incremento). No hace falta si el efecto lo es (un `upsert` por clave, fijar un estado).
- Durante una convivencia de topics `.v1` y `.v2` con doble publicación, se deduplica además por `subject` más `time`.
- Retención acotada con limpieza periódica.

## Envelope

`id`, `type`, `source`, `subject`, `time`, `dataVersion`, `traceparent`, `data`. El `traceparent` permite continuar la traza distribuida en el consumidor.

## Tests

Falla del broker: la outbox acumula, el relay publica todo al volver, sin pérdida ni desorden por agregado. Publicar fuera de transacción falla. El mismo evento entregado dos veces produce un solo efecto. El proceso muere tras procesar y antes de confirmar: al reiniciar no duplica.
