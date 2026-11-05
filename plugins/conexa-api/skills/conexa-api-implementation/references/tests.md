# Tests

Fuente: guidelines 6.10, 10.9, 12.1 a 12.7. **Tests primero**, desde los ejemplos del contrato. Usá el framework de tests del repo.

## Qué se escribe, por nivel

| Nivel | Qué prueba | Contra qué |
|---|---|---|
| Unitario | Entidades, value objects, mappers, casos de uso con fakes | Nada externo |
| Contrato (productor) | Cada operación contra el contrato: status, schema, headers, errores | El servicio levantado con fakes |
| Integración | Cada adaptador de salida contra su tecnología real | Contenedores efímeros (testcontainers o equivalente) |
| Resiliencia | Comportamiento ante fallas de dependencias | Mocks configurados para fallar |
| Seguridad funcional | Autorización, validación, enmascarado | El servicio levantado |
| End to end | Flujo de negocio completo entre servicios | Pre-producción (lo define el RFC) |

## Contrato (productor)

Por cada camino declarado:
1. Construir el request desde el **ejemplo del contrato**, no a mano. Así el ejemplo también se valida.
2. Verificar el status declarado.
3. Validar el body contra el schema de respuesta, con `additionalProperties: false` **en el test** para detectar campos que se filtran fuera del contrato.
4. Verificar headers (`Location`, `ETag`, `Retry-After`, `RateLimit-*`).
5. Por cada `4xx` declarado: provocar la condición y verificar status, `error.code` (uno de `x-error-codes`), `traceId` y el shape de `details`.

El 100% de las operaciones y de los `4xx` declarados tiene test.

## Los seis tests de autorización, por operación

| Test | Esperado |
|---|---|
| Sin token | `401 AUTHENTICATION_REQUIRED` |
| Token inválido (firma, `aud` de otra API, `env` equivocado, expirado) | `401 TOKEN_INVALID` o `TOKEN_EXPIRED` |
| Token sin el scope requerido | `403 INSUFFICIENT_SCOPE` |
| Audiencia incorrecta | `403 AUDIENCE_NOT_ALLOWED` |
| Recurso de otro tenant | `404`, no `403`, mismo tiempo que un inexistente |
| Referencia a un recurso de otro tenant en el request | `422 <RECURSO>_NOT_FOUND` |

Más: en listados, con datos de dos tenants cada uno ve solo lo suyo; con `merchantId` en el body, `400`. Se corren contra un emisor de test con JWKS real, **sin mockear el guard**.

## Integración

Repositorios contra la base real (misma versión mayor que producción, con las migraciones reales): ida y vuelta, concurrencia optimista, paginación sin duplicados ni faltantes, filtros implícitos por tenant, tipos de columna (`bigint`, con zona horaria). Proveedores contra mocks grabados, un caso por escenario del contrato. Productor y consumidor contra el broker.

## Reglas de escritura

- Nombre del test: una oración en presente que describe el comportamiento. Un comportamiento por test.
- Arrange, Act, Assert, separados.
- Sin lógica en los tests (`if`, bucles que repliquen el código). Valores esperados literales.
- Builders para los datos de prueba (`aPayment().approved().build()`), con valores por defecto válidos y estables. Sin datos aleatorios que afecten el comportamiento.
- **Fakes** (implementaciones simples en memoria) en lugar de mocks para los puertos. Reloj y generador de IDs fijos.
- Todo dato de prueba es sintético.
- Sin reintento automático de tests. Un test que falla a veces se arregla o se pone en cuarentena con plazo.
- Tests junto al código que prueban.

## Cobertura

Ramas mayores al 80% en dominio y aplicación (bloquea bajo 60%). El 100% de operaciones y `4xx` del contrato. No se testean getters triviales ni código generado.

## Dónde se escribe el resto

Idempotencia, eventos, resiliencia y proveedores tienen sus tests obligatorios al final de su guía respectiva.
