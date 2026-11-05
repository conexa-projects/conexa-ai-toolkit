# Supuestos de plataforma

Generado en el bootstrap. Lista lo que el servicio asume del entorno y lo que construyó localmente, para que sea visible y revisable. Actualizalo cuando cambie.

| Campo | Valor |
|---|---|
| Servicio | |
| Fecha | |
| Lenguaje y framework | |
| RFC y contrato de referencia | |

## Entorno asumido

| Pieza | Qué se asumió | Confirmado por | Fecha |
|---|---|---|---|
| Keycloak: emite `iss`, `aud`, `exp`, `env`, `tenant_id`, `tenant_kind`, `scope`, `jti` | | | |
| Keycloak: JWKS accesible desde el servicio | | | |
| Broker de mensajes | (cuál) | | |
| Formato de eventos | JSON con JSON Schema | | |
| AWS Secrets Manager con rol por service account | | | |
| Colector de OpenTelemetry en el cluster | (sí, no, no verificado) | | |
| Base de datos y versión | | | |

## Construido localmente en `platform/`

| Pieza | Estado | Notas |
|---|---|---|
| Validación de token y guards | | |
| Idempotencia | (construida, no aplica) | |
| Paginación | | |
| Errores y filtro único | | |
| Outbox e inbox | | |
| Resiliencia (timeouts, reintentos, breaker, pools) | | |
| Observabilidad | | |
| Tipos comunes (Money, instantes, IDs) | | |

## Reglas verificadas por herramienta

| Regla | Herramienta | Corre en CI |
|---|---|---|
| Límites entre capas | | |
| Lint y formato | | |
| Verificación de contrato | | |
| Secrets scanning | | |

## Lo que no se pudo verificar con herramienta (revisión manual)

Nombres vagos, archivo igual a su clase, barrels.

## Desvíos del estándar

Cada punto del estándar que no se cumple, con su excepción registrada o su motivo.

## Decisiones pendientes

Lo que quedó abierto y espera una definición del equipo.
