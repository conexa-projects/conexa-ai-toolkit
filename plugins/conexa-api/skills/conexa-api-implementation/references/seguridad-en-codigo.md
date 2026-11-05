# Seguridad en el código

Fuente: guidelines 7.2 a 7.7. Autenticación y autorización están en `modulo-de-plataforma/validacion-de-token.md`. Acá va el resto de lo que el código tiene que cumplir.

## Datos

- Todo campo del contrato lleva `x-data-classification`: `public`, `internal`, `pii`, `pii-sensitive`, `pci`, `secret`. Ante la duda, se clasifica más alto.
- **PCI**: ningún endpoint acepta un número de tarjeta (PAN). El schema solo tiene `token`, `last4`, `bin`, `brand`, `expMonth`, `expYear`. Si llega un PAN en un campo libre (se detecta con el algoritmo de Luhn), `400 SENSITIVE_DATA_IN_FIELD` sin loguear el valor. El filtro de logs también detecta patrones de PAN como defensa adicional.
- **Cifrado en tránsito**: TLS 1.2 como mínimo en toda conexión (externa, interna, base, broker, proveedores). Los clientes salientes verifican certificados siempre. Deshabilitar la verificación es un defecto.
- **Cifrado en reposo**: discos y bases cifrados por infraestructura. Los campos `pii-sensitive` y `secret` se cifran además **a nivel de campo** (cifrado autenticado tipo AES-256-GCM con clave de datos protegida por el KMS, con versión de formato para rotar). Para buscar por igualdad se guarda un hash con clave (HMAC) aparte.
- **Enmascarado automático** según clasificación: `pii` parcial en logs, `pii-sensitive` y `secret` como `[REDACTED]`. En respuestas, `pii-sensitive` va enmascarado salvo scope específico. En eventos nunca viajan `pii-sensitive` ni `pci`.
- **Retención** declarada por tabla con datos personales, y un job que la aplica. Anonimizar, no borrar, cuando hay integridad referencial.
- Ningún dato de producción en ambientes que no sean producción.

## Secretos

- Solo en AWS Secrets Manager. Se cargan al arrancar con la identidad de la carga de trabajo. Si falta un secreto requerido, **el servicio no arranca**.
- Nunca en código, tests, manifiestos, imágenes, logs ni respuestas. Secrets scanning en CI.
- Un usuario de base propio por servicio, con permisos mínimos. Sin superusuario en runtime. Las migraciones usan otro usuario, solo en el deploy.
- Los secretos que se generan para consumidores: aleatoriedad criptográfica, 256 bits o más, con prefijo identificable, generados en el servidor y mostrados una sola vez. Se guardan **hasheados** (client secrets y API keys) o **cifrados** (secretos de webhook, que hay que recuperar para firmar). Comparación en tiempo constante.
- Toda rotación tiene ventana de convivencia (dos secretos activos).

## Input y abuso

- Validación como lista blanca en el borde, contra el schema del contrato: `additionalProperties: false` (evita que un `isAdmin: true` llegue a la entidad), `maxLength` en todo string, `maxItems`, `pattern` en IDs, `enum`, rangos, profundidad máxima de JSON y tamaño máximo de body.
- **Inyección**: queries con parámetros ligados. Los nombres de columnas filtrables salen de una lista blanca. Nada de `exec` con strings (si hay que llamar a un binario, argumentos separados y sin shell). Deserialización solo a estructuras planas validadas, nunca a clases arbitrarias.
- **SSRF**: ver `por-tipo-de-tarea/webhook-saliente.md`.
- **Enumeración**: IDs opacos no secuenciales, `404` uniforme (mismo mensaje y mismo tiempo) para "no existe" y "existe pero no es tuyo", y el mismo mensaje para "no existe el client_id" y "secreto incorrecto".
- **Rate limiting distribuido** (no por instancia): por credencial, por operación crítica, por fallos de autenticación, por `404`, por rechazos de pago. Los límites de seguridad generan alerta y bloqueo temporal.
- **Card testing** (probar tarjetas robadas con pagos chicos): límite específico sobre rechazos por credencial, BIN o tarjeta tokenizada, con métrica y alerta.
- **Replay**: la idempotency key hace que repetir un request devuelva la respuesta original.

## Auditoría

Toda escritura y todo cambio de control plane genera un registro de auditoría de forma automática (quién, qué, cuándo, sobre qué, resultado, `traceId`, valor anterior y nuevo en control plane). Se escribe por outbox en la misma transacción de negocio, en un almacenamiento aparte y de solo agregado. Las denegaciones también se registran. Lecturas de `pii-sensitive` con revelación explícita, con registro propio.

## Dependencias y build

Lockfile obligatorio y usado en CI, versiones fijadas, sin scripts de instalación salvo lista blanca, escaneo de vulnerabilidades y licencias, imagen mínima sin usuario root.

## Tests

Los de `tests.md` más: PAN en campo libre rechazado, enmascarado en la salida estándar de logs, ningún secreto en respuestas, el servicio no arranca sin secretos, rate limit de fallos de autenticación.
