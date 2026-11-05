# Nombres por rol

Fuente: guidelines 6.2, 6.3, 6.4. Los sufijos dicen el rol del componente y son los mismos en todos los lenguajes. El casing lo define el lenguaje del repo (PascalCase para tipos y camelCase para funciones en TypeScript, Java o Kotlin; snake_case en Python; las convenciones de exportación en Go).

## Sufijo por rol

| Rol | Nombre | Ejemplo |
|---|---|---|
| Entidad de dominio | sin sufijo | `Payment` |
| Value object | sin sufijo | `Money`, `PaymentId` |
| Evento de dominio | participio pasado, sin sufijo `Event` | `PaymentApproved` |
| Error de dominio | `Error` (o la convención del lenguaje) | `PaymentNotFoundError` |
| Comando (entrada de escritura) | `Command` | `CreatePaymentCommand` |
| Query (entrada de lectura) | `Query` | `GetPaymentQuery` |
| Caso de uso | verbo + sustantivo + `UseCase`, una operación por clase | `CreatePaymentUseCase` |
| Puerto de persistencia | `Repository` | `PaymentsRepository` |
| Otro puerto | `Port` | `PaymentProviderPort` |
| Controller HTTP | `Controller` | `PaymentsController` |
| Handler gRPC | `GrpcHandler` | `PaymentGrpcHandler` |
| Consumidor de eventos | `Consumer`, uno por topic | `OrderCancelledConsumer` |
| Job programado | `Job` | `SettlementReportJob` |
| Implementación de repositorio | tecnología + recurso + `Repository` | `PostgresPaymentsRepository` |
| Implementación de otro puerto | proveedor + `Adapter` | `AcmeProviderAdapter` |
| Cliente de un proveedor | `Client` | `AcmeProviderClient` |
| DTO de request o response | `Request` o `Response` | `CreatePaymentRequest` |
| DTO de un tercero | proveedor + `Dto` | `AcmeAuthorizationDto` |
| Entidad de ORM | `OrmEntity` (o la convención del ORM) | `PaymentOrmEntity` |
| Mapper | qué + `Mapper` | `PaymentHttpMapper` |

Reglas:
- **Un sufijo, no dos.** Sin `Impl`, sin prefijo `I` en interfaces.
- **Sin nombres vagos:** `Manager`, `Helper`, `Util`, `Handler` genérico, `Processor`, `Data`, `Info`.
- Repositorios y controllers en plural, entidades en singular.
- Evento de dominio en pasado. Error de dominio: **una clase por `code`**, con el `code` como constante y la categoría definida por la clase.
- IDs como value objects propios (`PaymentId`), no como string suelto en las firmas del dominio.
- Enums de string con los valores del contrato. Nunca numéricos.

## Archivos y carpetas

- El nombre del archivo es el de la clase principal más el rol, con el casing del lenguaje (kebab-case en TypeScript: `postgres-payments.repository.ts`). Un archivo, una clase principal.
- Tests junto al código que prueban, con sufijo por tipo (unitario, integración, e2e).
- Sin archivos `utils`, `helpers`, `common`. El archivo dice de qué es.
- Sin barrels (`index` que reexporta) en código de aplicación.
- Exports nombrados, nunca default (donde el lenguaje lo distingue).
- Carpetas: máximo cuatro o cinco niveles bajo la raíz de código, sin carpetas vacías.

## Variables y funciones

- Sustantivos específicos. Nada de `data`, `result`, `obj`, `item`, `value`, `temp`, `info`, `flag` como nombre final.
- Sin el tipo en el nombre (`payments`, no `paymentList`). Colecciones en plural.
- Booleanos como predicados en positivo: `isApproved`, `hasRefunds`, `canCancel`.
- Sin abreviaturas, salvo `id`, `url`, `http`, `api`, `sku`, `dto`, `uuid`, `min`, `max`.
- Unidades en el nombre cuando el tipo no las da: `timeoutMs`, `retentionDays`, `sizeBytes`.
- Verbos con significado fijo:

| Verbo | Significa | Devuelve |
|---|---|---|
| `find*` | Busca, puede no encontrar | valor o ausencia |
| `find*OrFail` | Busca, lanza si no encuentra | valor |
| `get*` | Accede a algo que existe, sin efectos | valor |
| `list*` | Colección paginada | página |
| `is*`, `has*`, `can*` | Predicado | booleano |
| `validate*`, `ensure*` | Verifica, lanza si falla | nada |
| `calculate*` | Deriva un valor | valor |
| `execute` | Único método público de un caso de uso | resultado |

- Sin `And` en el nombre de una función (son dos funciones). Máximo tres parámetros posicionales, y sin booleanos posicionales.
- Métodos de entidad en lenguaje de dominio (`payment.approve()`), no setters (`setStatus`).
- Ningún valor mágico inline. Todo número o string con significado tiene nombre (`MAX_RETRY_ATTEMPTS`).
- `switch` o `match` sobre un enum o unión siempre exhaustivo, con el caso por defecto que falla en compilación o lanza.
