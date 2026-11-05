# Idempotencia (idempotency keys)

Fuente: guidelines 1.2 y 5.4. Se construye **solo si el contrato tiene operaciones con `x-idempotent: key`**: `POST` que crean recursos o ejecutan acciones con efectos externos no reversibles (cobrar, enviar). No aplica a `GET`, `PUT`, `DELETE`, ni a transiciones cuya repetición devuelve el estado actual (`x-idempotent: natural`).

Una operación idempotente produce el mismo efecto aunque se ejecute varias veces. La idempotency key es un identificador que manda el consumidor para que un reintento no duplique un cobro.

## Qué se construye

Un **interceptor** (middleware) que corre antes del controller en toda operación marcada, y una tabla de almacenamiento.

## El header

`Idempotency-Key: <UUID>`. **Obligatorio** en las operaciones que lo declaran: ausente es `400 IDEMPOTENCY_KEY_REQUIRED`. Si fuera opcional, el consumidor lo olvida justo en el reintento automático de su SDK. UUID validado, comparación sin distinguir mayúsculas (se normaliza a minúsculas).

## Almacenamiento

Motor por defecto: **la base relacional del servicio**, porque la fila de idempotencia y el recurso se escriben en la misma transacción (nunca queda un recurso sin registro ni un registro completado sin recurso). Redis (`SET NX EX`) solo para operaciones de alto volumen sin efectos externos, con manejo explícito de la ventana de inconsistencia. Nunca memoria del proceso.

```
idempotency_keys
  scope             identidad del llamador, tomada del token (nunca del body)
  key               UUID
  operation         operationId del contrato
  request_hash      SHA-256 del body canónico + path params que identifican el recurso
  status            in_progress | completed
  response_status, response_headers, response_body
  resource_id       opcional, para diagnóstico
  created_at, completed_at, expires_at, locked_until
  PRIMARY KEY (scope, key)
```

- Clave primaria `(scope, key)`: dos consumidores con la misma clave no colisionan.
- `operation` en la fila, no en la clave: reusar la clave para otra operación se detecta y es `422 IDEMPOTENCY_KEY_REUSED`.
- `request_hash` usa el body canonicalizado (claves ordenadas, sin espacios). No entran query params ni headers que varían entre reintentos.
- `response_headers` guarda solo los que deben reproducirse (`Location`, `ETag`). Nunca `Set-Cookie`, rate limit ni trace.
- Retención 24 horas (`expires_at`), con un job de limpieza.

## Algoritmo

```
1. Leer Idempotency-Key. Ausente o inválida: 400.
2. scope = identidad del token; operation = operationId de la ruta.
3. request_hash = hash del request canónico.
4. INSERT (scope, key, operation, request_hash, status='in_progress',
          expires_at = ahora + 24h, locked_until = ahora + 30s)
   ON CONFLICT (scope, key) DO NOTHING
   Esta es una sola operación atómica. Un SELECT seguido de un INSERT NO sirve:
   dos requests concurrentes pasarían las dos.
5. Si insertó: es la primera vez. Ejecutar (paso 8).
6. Si no insertó, leer la fila existente:
   a. operation o request_hash distintos: 422 IDEMPOTENCY_KEY_REUSED.
   b. completed: responder lo guardado, sin ejecutar. Agregar header Idempotent-Replayed: true.
   c. in_progress con locked_until vigente: 409 REQUEST_IN_PROGRESS con Retry-After.
   d. in_progress con locked_until vencido: abandonado (ver abajo).
8. Ejecutar controller, caso de uso y efectos dentro de una transacción.
9. En la MISMA transacción, marcar completed con la respuesta guardada.
10. COMMIT y responder.
11. Error de dominio (4xx): guardarlo también como completed. Un reintento devuelve el mismo 4xx.
12. Error 5xx: ROLLBACK, no se guarda. Queda in_progress hasta locked_until. El reintento vuelve a ejecutar.
```

## Qué se guarda y qué no

| Primera ejecución | ¿Completed? | El reintento devuelve |
|---|---|---|
| `2xx` | Sí | La misma respuesta |
| `4xx` de dominio | Sí | El mismo `4xx` (si no, un límite que cambió podría aprobar lo que el consumidor cree rechazado) |
| `400` de validación, `401`, `403`, `429` | No | Se revalida normalmente |
| `5xx` | No (rollback) | Se vuelve a ejecutar (son fallas nuestras) |

## In-progress abandonado

El proceso murió entre el paso 4 y el 10. Con `locked_until` vencido: intentar `UPDATE ... SET locked_until = ahora + 30s WHERE scope=? AND key=? AND locked_until < ahora`. Si actualizó una fila, este request toma el lock y ejecuta. Si no, otro ya lo tomó: `409`. Antes de ejecutar, verificar si el efecto ya ocurrió (recurso con el mismo `idempotency_key` o `resource_id`) para no duplicarlo. Con motor relacional y una sola transacción, esto es raro por construcción.

## Hacia proveedores

La clave que se manda a un proveedor es **derivada** de forma determinista (ID del recurso, operación, proveedor), no la del consumidor.

## Tests obligatorios (los diez)

Falta la clave. Primera ejecución. Reintento con respuesta idéntica y `Idempotent-Replayed`. Mismo key con body distinto (`422`). Mismo key con otra operación (`422`). Dos requests concurrentes con la misma clave (exactamente una ejecuta, la otra recibe `409` o la respuesta guardada). Error de dominio guardado y repetido. `5xx` no guardado y reejecutado. In-progress abandonado retomado sin duplicar. Dos consumidores con la misma clave sin colisión.
