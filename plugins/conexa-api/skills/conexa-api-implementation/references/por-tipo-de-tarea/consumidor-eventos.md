# Consumidor y productor de eventos

Fuente: guidelines 3.d, 8.6, 8.7, 10.8. Contrato en AsyncAPI, schemas como archivos (ver `../entorno.md`: no hay schema registry).

## Productor

- Se publica **siempre por outbox**, en la misma transacción que el cambio de estado (`../modulo-de-plataforma/outbox-inbox.md`). Publicar directo después del commit pierde eventos cuando el proceso muere entre un paso y otro.
- El evento de dominio lo emite la entidad (se acumula en ella y el caso de uso lo extrae). La entidad no conoce el broker.
- Envelope estándar: `id`, `type`, `source`, `subject` (clave de partición, normalmente el ID del agregado), `time`, `dataVersion`, `traceparent`, y `data`.
- El orden se garantiza por agregado: misma clave de partición, mismo orden.
- Nunca viajan datos `pii-sensitive` ni `pci` en `data`. Si un consumidor los necesita, recibe el ID y consulta la API.
- Un campo nuevo es opcional con default. Un cambio incompatible es un topic nuevo con sufijo `.v2` y doble publicación durante la convivencia (8.7).

## Consumidor

- **Un consumidor por topic.** Nada de un consumidor con `switch` por tipo de evento.
- Recibe el envelope completo.
- **Idempotente**: inbox por `id` de evento, o un efecto naturalmente idempotente. Ver `../modulo-de-plataforma/outbox-inbox.md`. Un consumidor que muere después de procesar y antes de confirmar la lectura recibe el mismo mensaje al reiniciar. Es el caso normal de un deploy.
- **Lector tolerante**: ignora campos desconocidos, tolera valores nuevos de enums extensibles, lee campos opcionales nuevos con default, no asume orden global. Deserializa con el schema de la `dataVersion` del mensaje, no con "el schema actual".
- No publica al topic que consume, y llama a un solo caso de uso.

## Fallas: transitorias y permanentes

| Tipo | Ejemplos | Qué hacer |
|---|---|---|
| Transitoria | Dependencia caída, timeout, circuit breaker abierto | Reintentar sin confirmar, con backoff corto y límite (100 ms a 30 s, 5 a 10 intentos). Si sigue fallando, **pausar la partición**, no mandar a DLQ. Reanudar cuando la dependencia vuelve. |
| Permanente | Error de dominio, validación, mensaje que no deserializa | Mandar a la DLQ (dead letter queue, la cola donde quedan los mensajes que no se pueden procesar) de inmediato, confirmar y seguir. |
| Error interno inesperado | Bug | Tratar como transitorio con límite bajo (3 intentos) y luego DLQ. |

Mandar a DLQ mil mensajes válidos porque una base estuvo caída dos minutos crea trabajo de reproceso innecesario.

## DLQ

- Un topic de DLQ por topic y por consumer group.
- El mensaje va con headers que explican: razón, categoría, intentos, primer fallo, `traceId`, consumidor, topic, partición y offset originales. Sin datos sensibles.
- Un mensaje en DLQ es una alerta, no un log (métrica `dlq_messages_total`). Retención larga (30 días o más).
- Reprocesar desde la DLQ es una operación manual, con dry-run y límite, después de corregir la causa. Nunca se reinyecta de forma automática.
- **Protección contra mensaje venenoso**: contador de intentos por offset persistido. Si un mensaje que mata el proceso se intentó más de N veces a través de reinicios, va a DLQ antes de procesarse.

## Tests obligatorios

Mensaje con error de dominio va a DLQ y la partición sigue. Mensaje con dependencia caída reintenta y pausa sin ir a DLQ. El mismo mensaje entregado dos veces produce un solo efecto. Mensaje con campo extra y con valor de enum nuevo se procesa. Un mensaje que mata el proceso termina en DLQ tras reiniciar.
