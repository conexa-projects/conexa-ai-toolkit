# Endpoint (REST o gRPC)

Fuente: guidelines 3.a, 3.a.1, 5, 6.5 a 6.7. Hacelo de adentro hacia afuera, con los tests escritos primero.

## Orden de trabajo

1. Tests desde el contrato (`../tests.md`): camino feliz, cada `4xx` declarado, los seis de autorización.
2. Dominio: entidad, value objects, errores, evento de dominio si corresponde. Las reglas de negocio viven acá.
3. Aplicación: comando o query inmutable, caso de uso con un solo método público, puertos nuevos.
4. Adaptador de salida: repositorio (y proveedor si hay) que implementa el puerto.
5. Adaptador de entrada: controller o handler, mapper, registro de guards y decoradores de plataforma.
6. Correr lint y tests.

## El adaptador de entrada hace cinco cosas, en orden

1. Recibir la entrada ya validada en forma (la validación contra el schema del contrato corre antes, en el borde).
2. Extraer el contexto del llamador (`Caller`: identidad, tenant, scopes, `traceId`) **del token**, nunca del body.
3. Traducir entrada más contexto a un comando o query de la aplicación (mapper).
4. Invocar el caso de uso.
5. Traducir el resultado a la respuesta del protocolo (mapper).

No decide negocio, no consulta repositorios, no atrapa errores de dominio.

Lo que **no** tiene un controller: `try/catch` que arme status, validación de campos, `if` de negocio, repositorios inyectados, `merchantId` tomado del body.

Lo que sí tiene: decoradores o middleware declarativos (autenticación, scopes, audiencia, idempotencia), conversión de parámetros de path a value objects (un ID con formato inválido es `400 INVALID_ID_FORMAT` antes de tocar la base), y headers que dependen del resultado (`Location` en `201` y `202`, `ETag` en lecturas por ID).

## Mapper del protocolo

Una clase por par (protocolo, agregado). Convierte primitivos del protocolo a value objects (`string` a `PaymentId`, `{amount, currency}` a `Money`) y de vuelta. Aplica las reglas de representación: fechas ISO 8601 UTC con `Z` y milisegundos, `null` para opcionales sin valor en responses, objetos condicionales omitidos, arrays nunca `null`. Sin lógica de negocio. Se testea solo: el shape tiene que coincidir con el schema del contrato.

## Caso de uso

- Un método público, `execute`. Si hace falta otro, es otro caso de uso.
- Orquesta, no decide reglas. Un `if (monto > limite)` en el caso de uso es una regla que se escapó de la entidad.
- Tiempo e IDs se inyectan (`Clock`, generador de IDs). Sin `now()` directo, para que los tests sean deterministas.
- La transacción abarca solo persistencia y outbox. La llamada al proveedor queda **fuera**.
- Devuelve una entidad o tipo de la aplicación, nunca un DTO de response.
- Autorización a nivel de recurso acá: `404` si el recurso es de otro tenant, y las referencias a otros recursos también se verifican (`422 <RECURSO>_NOT_FOUND`).

## Operaciones de escritura

- `POST` con `x-idempotent: key`: interceptor de idempotencia, header obligatorio (`modulo-de-plataforma/idempotencia.md`).
- `PATCH` o `PUT` sobre recursos con versión: `If-Match` con control optimista (`modulo-de-plataforma/concurrencia.md`). Versión desactualizada es `412`, no `409`.
- Acciones (`POST /orders/{id}/cancel`): su precondición es el estado, no la versión. Sin `If-Match`.
- Las transiciones de estado se hacen por acciones con nombre de dominio, nunca por `PATCH` del campo `status`.

## Lecturas

- Toda colección pagina (`modulo-de-plataforma/paginacion.md`). Filtros implícitos (tenant, archivados) en el repositorio antes que los del consumidor.
- Un `GET` nunca tiene efectos secundarios.
- Campos filtrables y ordenables salen de una lista blanca, con índice que respalde cada `sort` permitido.

## gRPC

Misma estructura, otro protocolo: mismo caso de uso, otro mapper, y un filtro de errores que mapea a códigos gRPC. Identidad y tenant llegan en metadata. Los deadlines se propagan. Paginación con `page_token` opaco.

## Errores

Los errores de dominio suben hasta el filtro único de plataforma (`modulo-de-plataforma/errores.md`). Cada `code` del contrato tiene su clase de error, y cada clase tiene su `code` en el contrato.
