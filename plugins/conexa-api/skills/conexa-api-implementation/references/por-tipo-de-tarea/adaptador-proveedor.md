# Adaptador de proveedor externo

Fuente: guidelines 6.7, 7.7, 10.1 a 10.4, 10.7. Un adaptador de proveedor implementa un puerto de la aplicación y traduce entre el lenguaje del dominio y el del proveedor. **Nada del proveedor sale de él.**

## Estructura en tres piezas

1. **Puerto** (en aplicación): habla el lenguaje del dominio. Recibe entidades y value objects, devuelve un resultado tipado. Un puerto por capacidad (autorizar, reembolsar), no por proveedor.
2. **Adaptador**: implementa el puerto, orquesta mapper y cliente, traduce errores.
3. **Cliente**: habla el protocolo del proveedor. No conoce el dominio. Mapper: convierte dominio a request del proveedor y response a resultado del dominio, e incluye la tabla que traduce los códigos de rechazo del proveedor al enum del dominio.

## Resultado tipado para lo esperable

Los desenlaces normales del negocio son un tipo, no excepciones:

```
AuthorizationResult = Approved(providerReference)
                    | Rejected(reason, providerCode)
                    | Timeout
```

Rechazo y timeout son resultados esperables. La entidad decide qué hacer con cada uno (un timeout deja el pago en `pending`). Las fallas de infraestructura (proveedor caído, breaker abierto, respuesta inválida) sí son excepciones de infraestructura que el filtro único traduce a `503`.

## Reglas

- **Timeouts** de conexión, lectura y total en configuración validada. Derivados del presupuesto de latencia de la operación (`../modulo-de-plataforma/resiliencia.md`).
- **Idempotency key hacia el proveedor**: derivada de forma determinista (por ejemplo desde el ID del recurso, la operación y el proveedor). No se reenvía la del consumidor.
- **Sin reintentos automáticos en el cliente** para operaciones con efectos. El reintento lo decide el adaptador, y solo si el proveedor soporta idempotencia. Si el proveedor no la soporta, no se reintenta: se deja `pending` y se consulta el estado.
- **Un timeout es ambiguo**: no se sabe si el proveedor procesó. Nunca se hace failover a otro proveedor ante timeout. Se deja `pending` y un job consulta el estado.
- **Validar toda respuesta antes de usarla**: contra el schema del proveedor y por coherencia con lo enviado (el monto aprobado es el solicitado, la moneda coincide, la respuesta corresponde a nuestra referencia). Una incoherencia es respuesta inválida, no éxito: el pago queda en revisión y se alerta. Un código desconocido del proveedor significa "desconocido" (`pending`), nunca éxito.
- **Circuit breaker** por (proveedor, operación). Con el breaker abierto: `503` si no hay alternativa, `pending` si el contrato admite resultado diferido, failover solo si el rechazo es seguro.
- **Credenciales** de AWS Secrets Manager, una por proveedor y ambiente, con permisos mínimos. Sandbox y producción en rutas separadas.
- **Egress**: el tráfico saliente a proveedores va por destinos conocidos. Documentarlo en `docs/platform-assumptions.md`.
- **SDK del proveedor**: si se usa, se envuelve en el adaptador y nada fuera lo importa. Se desactivan su telemetría, reintentos y logging propios. Se prefiere un cliente generado desde su OpenAPI sobre un SDK opaco.
- **Datos enviados**: lo mínimo que la operación requiere, con referencia propia (`ref_...`) en lugar de nuestros IDs internos.
- **Nunca** se loguea el body completo del proveedor.

## Webhooks entrantes del proveedor

Es una entrada anónima desde internet. En orden: endpoint dedicado fuera del contrato público, verificación de firma del proveedor (sin firma válida, `401` y descarte), verificación de timestamp (ventana de 5 minutos), validación de payload, idempotencia por el ID de evento del proveedor, respuesta `2xx` rápida con procesamiento asíncrono, correlación por nuestra referencia, y **confirmación por consulta** al proveedor antes de transiciones críticas (el webhook es un aviso, la fuente de verdad es la consulta autenticada). Si el proveedor no firma, combinar allowlist de IP, token secreto en header y tratamiento solo como disparador de consulta.

## Tests obligatorios

Con mocks grabados del proveedor (un mapping por caso del contrato): aprobación, cada código de rechazo, timeout forzado, respuesta malformada, respuesta con monto distinto, `503` repetido hasta abrir el breaker, y breaker abierto con y sin fallback. Verificar que el request enviado al proveedor es el esperado (monto, referencia, idempotency key derivada).
