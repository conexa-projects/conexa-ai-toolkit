# Resiliencia

Fuente: guidelines 10.1 a 10.8. Se construye una vez en `platform/` como un cliente de dependencias con timeouts, reintentos, circuit breaker y límites de concurrencia, y todas las llamadas externas pasan por él. Ninguna llamada externa usa un cliente HTTP "crudo".

## Clasificar cada dependencia primero

| Clase | Ejemplo | Ante falla |
|---|---|---|
| Crítica síncrona | Base de datos, proveedor sin `pending` posible | Timeout corto, reintento acotado, breaker. Al abrirse: `503`. |
| Crítica con resultado diferido | Proveedor, cuando el contrato admite `pending` | Timeout, sin reintento en línea, resultado `pending` y job de consulta. |
| Opcional | Enriquecimiento (`expand=customer`) | Timeout muy corto, sin reintento. Al fallar se omite y se marca la degradación. |
| Asíncrona | Broker vía outbox | La outbox absorbe. Nunca afecta la respuesta. |
| Configuración | Control plane | No es dependencia en línea. Su falla es datos desactualizados. |

Una dependencia mal clasificada (un enriquecimiento tratado como crítico) es la causa más frecuente de una caída en cascada. Infraestructura compartida: rate limiting en **fail open** (si Redis cae, se deja pasar con alerta), idempotencia en **fail closed** (`503` si no se puede deduplicar), JWKS con caché largo.

## Timeouts

Toda llamada que espera algo fuera del proceso tiene **tres** timeouts definidos: de conexión, de lectura y total. También el pool al adquirir una conexión (200 ms interno), los locks y las consultas a base. Los defaults de las librerías suelen ser infinitos o de minutos. El total sale de `min(presupuesto del salto, 2 a 3 veces el p99 de la dependencia)`. La operación entera tiene un timeout propio en el middleware, con cancelación de llamadas en vuelo y rollback. Se propaga el **deadline** restante a las llamadas internas y se rechaza si ya venció.

## Reintentos

Solo si se cumplen las tres: la operación es segura de repetir (idempotente o con key), la falla es transitoria (timeout de conexión, `503`, `429`) y hay presupuesto de latencia. Backoff exponencial con jitter (variación aleatoria que dispersa los reintentos): `min(base * 2^n, máximo) * aleatorio(0.5, 1.5)`. En línea, máximo 2 reintentos, y cero hacia proveedores con `pending` disponible. Presupuesto de reintentos: no más del 10% del tráfico hacia una dependencia son reintentos. `Retry-After` gana al backoff calculado. Nunca `4xx` (salvo `429`). Se reintenta en un solo nivel de la cadena.

## Circuit breaker

Un breaker abre cuando una dependencia falla de forma sostenida, para fallar rápido en lugar de gastar un timeout por llamada. Tres estados: cerrado, abierto, semiabierto (deja pasar pocas llamadas de prueba). Umbral **por tasa** con ventana deslizante y volumen mínimo (por ejemplo 20 llamadas), no por conteo absoluto. Cuentan como falla: timeouts, errores de conexión, `5xx`, respuestas inválidas y latencia por encima del 80% del timeout. No cuentan los `4xx`. Uno por (dependencia, operación). Tiempo de apertura con backoff en reaperturas. Con el breaker abierto: `503`, `pending`, omitir o failover según la clase.

## Bulkheads (compartimentos)

Pool de conexiones **por dependencia**, nunca uno global. Tamaño por concurrencia esperada. Límite de operaciones en vuelo por tipo, con rechazo inmediato (`503 SERVICE_OVERLOADED` con `Retry-After`) en lugar de encolar. Cuota por tenant para operaciones caras.

## Degradación

Decisión por operación y dependencia, declarada en el contrato (`x-degradation`): `fail`, `pending`, `omit`, `default`, `stale`, `failover`. Respuesta degradada: header `Degraded`, el campo omitido como `null`, status `200`, métrica `degraded_responses_total`. Una lectura declarada `strong` nunca degrada a datos viejos. Los fallbacks salen de configuración de negocio, no se inventan en código.

## Backpressure

Admisión antes de cualquier trabajo: rate limit, límite de concurrencia, deadline vencido, load shedding (rechazar una fracción del tráfico cuando el servicio está saturado, con prioridad `critical`, `high`, `normal`, `low`).

## Tests de Nivel 1 (en CI)

Proveedor responde después del timeout. `503` repetido hasta abrir el breaker. Breaker semiabierto cierra o reabre. Base que no responde. Redis de idempotencia caído (`503`) y de rate limit caído (pasa). Pool agotado. Un test de coherencia de configuración que verifica que los timeouts suman menos que el presupuesto total.
