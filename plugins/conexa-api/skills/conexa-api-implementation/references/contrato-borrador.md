# Proponer un borrador de contrato

Cuando falta el contrato, no se implementa. Se propone un borrador, se explica cada decisión y se espera la aprobación del usuario. Fuente: guidelines 4.1 a 4.3, 5, 8.2.

## Cuándo se puede y cuándo no

Se puede proponer un borrador si el RFC (o el pedido del usuario) define el qué: recursos, operaciones y casos de uso. **No se decide** estilo, plano ni modelado: si eso no está, se frena y se pregunta.

## Qué lleva el borrador

**OpenAPI (REST):**
- `info.version` semántica (`0.1.0` para un borrador), versión mayor en el path (`/v1/...`).
- Por operación: `operationId` único, `x-plane`, `x-audience`, scopes requeridos, `x-idempotent` (`key`, `natural` o ninguno), `x-slo`, `x-degradation` por dependencia, `x-error-codes` (los códigos de error posibles).
- Request y response con schemas estrictos: `additionalProperties: false`, `maxLength`, `maxItems`, `pattern` en IDs, `enum`, rangos. Dinero como `Money`. Fechas ISO 8601 UTC. IDs con prefijo.
- Cada respuesta con headers declarados (`Location`, `ETag`, `RateLimit-*`, `Retry-After`).
- Respuestas de error comunes (400, 401, 403, 404, 422, 429, 503) con el formato estándar.
- **Ejemplos completos** del camino feliz y de cada `4xx`. De ahí salen los tests.
- `x-data-classification` en todo campo no público.
- Colecciones con `PaginatedResponse` común.
- Enums del response que pueden crecer con `x-extensible-enum: true`.

**AsyncAPI (eventos):** un channel por topic con nombre `<dominio>.<recurso>.<hecho en pasado>`, mensaje con el envelope estándar, JSON Schema de `data`, clave de partición (`subject`), `dataVersion`. Campos nuevos siempre opcionales con default.

**Protobuf (gRPC):** paquete con versión (`conexa.<dominio>.v1`), números de campo nunca reutilizados, campos eliminados `reserved`, enums con valor `UNSPECIFIED` en 0.

## Qué se hace con el borrador

1. Guardarlo en el lugar que use el repo para contratos (o `contracts/` si no hay convención) en una rama.
2. Presentarlo al usuario con las decisiones no obvias explicadas y las preguntas abiertas.
3. **Esperar la aprobación.** Solo entonces se escriben los tests y se implementa.
4. Si el repo no tiene verificación de contratos, proponer una mínima: lint (Spectral para OpenAPI), validación de ejemplos contra los schemas y detección de cambios incompatibles contra la versión anterior.

## Qué rompe un contrato (para cambios sobre uno existente)

Compatible: agregar una operación, un campo opcional, un campo de response, un valor de enum extensible, un parámetro opcional. Incompatible: quitar o renombrar, cambiar tipo o formato, cambiar semántica, agregar un campo requerido al request, endurecer una validación, cambiar un status code o un default. Una incompatibilidad es versión mayor nueva, con RFC. Antes de ir a una versión mayor, probar expandir y contraer (agregar lo nuevo junto a lo viejo, deprecar, quitar después). Lo deprecado lleva `deprecated`, `x-deprecated-since`, `x-sunset` y `x-successor`.
