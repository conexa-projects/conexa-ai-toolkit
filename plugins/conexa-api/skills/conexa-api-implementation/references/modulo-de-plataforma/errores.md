# Errores

Fuente: guidelines 5.5 y 6.8. Del dominio a la respuesta, con un único punto de traducción.

## Jerarquía

- Una clase de error de dominio por `code`. No una clase genérica con el `code` como parámetro: permite typos y no se sabe qué errores lanza un caso de uso.
- El `code` es una constante de la clase y coincide letra por letra con `x-error-codes` del contrato. Un test verifica que cada `code` del contrato tiene su clase y viceversa.
- La `category` la define la clase, no quien la lanza.
- Categorías y su status HTTP:

| Categoría | HTTP | gRPC |
|---|---|---|
| `validation` | 400 | INVALID_ARGUMENT |
| `unauthenticated` | 401 | UNAUTHENTICATED |
| `forbidden` | 403 | PERMISSION_DENIED |
| `not_found` | 404 | NOT_FOUND |
| `conflict` | 409 | ABORTED o ALREADY_EXISTS |
| `precondition` | 412 | FAILED_PRECONDITION |
| `unprocessable` | 422 | FAILED_PRECONDITION |
| `rate_limited` | 429 | RESOURCE_EXHAUSTED |
| `unavailable` | 503 | UNAVAILABLE |
| `internal` | 500 | INTERNAL |

- `metadata` son datos estructurados para logs y mensajes, nunca sensibles.
- El `message` de la excepción es técnico, en inglés, para logs. No es el `message` de la respuesta.
- Los errores de infraestructura (conexión, timeout, excepciones del driver) no son errores de dominio. Se atrapan en el adaptador de salida y se relanzan como error de categoría `unavailable` o `internal`.
- Los desenlaces esperables del negocio (pago rechazado, timeout del proveedor) son resultados tipados, no excepciones.

## Punto de traducción único

Un filtro global por protocolo convierte todo a la respuesta. **Es el único lugar donde aparecen status codes.**

```
{ "error": { "code": "...", "message": "...", "traceId": "...", "details": [...], "docs": "..." } }
```

- Error de dominio: status por categoría, log con nivel `warn` para `4xx` y `error` para `5xx`, una sola vez.
- Error de validación de schema: `400 VALIDATION_FAILED` con **todas** las violaciones juntas en `details`, no solo la primera.
- Límite excedido: `429` con `Retry-After`.
- Cualquier otra cosa es un bug: `500 INTERNAL_ERROR` con `traceId`, log `error`, y se incrementa la métrica `http_unhandled_errors_total` (su objetivo es cero).
- Headers por categoría: `Retry-After` en `429` y `503`, `WWW-Authenticate` en `401`.
- gRPC: un interceptor equivalente. Consumidores de eventos: la categoría decide entre reintentar y DLQ.

## Mensajes

Dicen qué pasó y qué hacer, con los identificadores relevantes y sin datos sensibles. Un idioma, el de la documentación de la API. Se construyen en el filtro desde una plantilla por `code`, no se escriben en cada `throw`. **Nunca** contienen stack traces, nombres de clases o archivos, SQL, mensajes de drivers, hosts, versiones ni URLs internas.

## Tests

Cada `code` del contrato tiene su clase y viceversa. Un test de patrones prohibidos recorre las respuestas de error buscando stack, SQL, nombres de clase y hosts. Cada categoría produce su status. La validación devuelve todas las violaciones. Un `500` lleva `traceId` y no lleva stack.
