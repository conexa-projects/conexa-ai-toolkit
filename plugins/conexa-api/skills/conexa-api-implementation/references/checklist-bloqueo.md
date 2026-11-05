# Checklist de bloqueo de código

Fuente: sección C de 14.1, adaptada a un entorno sin librería de plataforma compartida. Se recorre al cerrar la tarea. Cada punto se reporta como **cumple**, **no cumple** o **no aplica**, con una línea de evidencia (archivo, test o comando). Un punto que no cumple frena: se corrige o se propone una excepción registrada. Nunca se marca "cumple" sin evidencia.

Formato de reporte:

```
[cumple]    Dominio sin imports de infraestructura (6.1). Evidencia: regla de límites en CI, pasa.
[no cumple] Timeout de lectura sin definir en AcmeProviderClient (10.2). Corregido en <archivo>.
[no aplica] Idempotencia: el contrato no tiene operaciones x-idempotent.
```

## Arquitectura

- [ ] El dominio no importa aplicación, adaptadores, framework, ORM ni HTTP. (6.1)
- [ ] Ninguna feature importa clases internas de otra. (6.1)
- [ ] Controllers sin `try/catch` que arme status, sin `if` de negocio, sin repositorios. (6.5)
- [ ] Identidad y tenant salen del `Caller` construido desde el token, nunca del body ni de headers custom. (6.5, 7.3)
- [ ] Las reglas de negocio viven en entidades o servicios de dominio. (6.6)
- [ ] La transacción abarca solo persistencia y outbox, sin llamadas externas. (6.6)
- [ ] La entidad de dominio y la de ORM están separadas. (6.1)

## Implementación

- [ ] Lo transversal está en el módulo de plataforma del servicio, sin reimplementarlo por endpoint. (5)
- [ ] Toda colección pagina. (5.1)
- [ ] Queries con parámetros ligados, sin interpolación de strings. (5.2, 7.6)
- [ ] Filtros implícitos (tenant, archivados) en el repositorio antes de los del consumidor. (5.2)
- [ ] Dinero como `Money` (entero más moneda), ningún float. (5.3)
- [ ] Ningún PAN ni dato PCI fuera del tokenizador. (5.3, 7.4)
- [ ] Operaciones `x-idempotent: key` con header obligatorio e inserción atómica con clave `(scope, key)`. (5.4)
- [ ] Un único filtro global de errores, y cada `code` del contrato tiene su clase. (5.5)
- [ ] Ningún error expone stack, SQL, clases, hosts ni versiones, y existe el test de patrones prohibidos. (5.5)
- [ ] El token no aparece en ningún log. Los headers de tenant o IP del cliente no se honran. (5.6)
- [ ] Escrituras sobre recursos con versión usan `If-Match` y devuelven `412` si está desactualizada. (5.7)

## Seguridad

- [ ] El middleware valida firma, algoritmo (lista fija), `iss`, `aud`, `exp` y `env`, aunque haya gateway. (7.2)
- [ ] Guards de scope y audiencia aplicados. Pertenencia al tenant verificada en el caso de uso. Tenant del body rechazado. (7.3)
- [ ] TLS en toda conexión, sin deshabilitar la verificación de certificados. (7.4)
- [ ] Ningún secreto en código, tests, manifiestos ni imágenes. El servicio no arranca si falta un secreto requerido. (7.5)
- [ ] Sin ejecución de comandos con strings, sin deserialización a clases arbitrarias, campos filtrables de lista blanca. (7.6)
- [ ] Ninguna excepción de la tecnología (driver, cliente HTTP) sale del adaptador sin traducir. (6.7)
- [ ] Ningún `catch` vacío ni que loguee y siga. (6.8)
- [ ] Ningún body completo ni dato sensible sin enmascarar en logs. (6.8, 11.2)
- [ ] Si hay URLs de consumidores: controles anti-SSRF completos. (7.6)

## Resiliencia

- [ ] Toda llamada externa tiene timeout de conexión, lectura y total definidos. (10.2)
- [ ] Solo se reintentan fallas transitorias, en operaciones idempotentes, con la misma clave, nunca `4xx` salvo `429`. (10.3)
- [ ] Toda dependencia externa tiene circuit breaker por (dependencia, operación). (10.4)
- [ ] Pool de conexiones por dependencia, con timeout de adquisición. Ningún pool global. (10.5)
- [ ] Consumidores de eventos idempotentes, con test de doble procesamiento. (10.8)
- [ ] Eventos publicados por outbox en la misma transacción. (3.d)

## Observabilidad

- [ ] Instrumentación de entrada, salida, base y consumidores. `traceId` en logs, errores, eventos y DLQ. (11.1)
- [ ] Sin dimensiones de alta cardinalidad en métricas. (11.3)
- [ ] Cada operación del contrato tiene `x-slo` declarado. (11.5)

## Tests

- [ ] Unitarios de toda la lógica de dominio y del caso de uso. (12.1)
- [ ] Tests de contrato por camino feliz y por cada `4xx` declarado, desde los ejemplos del contrato. (12.2)
- [ ] Los seis tests de autorización por operación, contra un emisor de test, sin mockear el guard. (12.6)
- [ ] Resiliencia inyectada (Nivel 1) por cada dependencia nueva. (10.9)
- [ ] Todo dato de prueba es sintético. (12.7)
- [ ] Sin reintento automático de tests. (12.8)
- [ ] Lint, formato, verificación de límites entre capas y tests pasan. (6.11)

## Cierre

- [ ] `docs/platform-assumptions.md` actualizado con lo asumido y lo construido.
- [ ] Todo lo que no cumple tiene una excepción propuesta (motivo, mitigación, plan, vencimiento) y quedó a decisión del usuario.
- [ ] Lo que no se pudo verificar con herramienta (nombres vagos, archivo igual a su clase, barrels) está declarado como revisión manual.
