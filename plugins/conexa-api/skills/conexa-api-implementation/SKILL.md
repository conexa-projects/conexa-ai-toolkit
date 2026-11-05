---
name: conexa-api-implementation
description: Implementa código de APIs de Conexa siguiendo los API Design Guidelines, en cualquier lenguaje. Cubre endpoints (REST, gRPC), productores y consumidores de eventos, adaptadores de proveedores externos, webhooks salientes y jobs asíncronos, además del bootstrap de un repo de servicio. Usar siempre que se pida implementar, agregar, modificar o crear la base de una operación de API, un consumidor de eventos, un adaptador de proveedor, un webhook o un job en un repo de servicio de Conexa, aunque el pedido no mencione los guidelines. No usar para decidir estilo de API, plano (data plane o control plane) ni modelado de recursos (eso es diseño y va en el RFC), ni para revisar código ya escrito.
---

# Implementación de APIs Conexa

Esta skill convierte un diseño aprobado (RFC y contrato) en código que cumple los API Design Guidelines de Conexa. Los guidelines son agnósticos al lenguaje, así que la skill también lo es: detecta el stack del repo y aplica sus convenciones idiomáticas (casing, herramientas de lint, framework de tests).

## Lo primero que tenés que saber

**No existe una librería de plataforma compartida.** Los guidelines hablan de `api-core`, de plantillas de servicio y de plugins de lint propios, pero hoy no existen. Cada servicio construye lo transversal (idempotencia, paginación, errores, validación de token, outbox, timeouts, reintentos, observabilidad) dentro de un **módulo de plataforma local**, una carpeta `platform/` con interfaces estables, pensada para poder extraerse a una librería compartida más adelante. Cuando un guideline diga "usá la librería de plataforma", leelo como "usá el módulo de plataforma del servicio, y si no existe esa pieza, construila siguiendo `references/modulo-de-plataforma/`".

Tampoco hay schema registry de eventos. Ver `references/entorno.md`.

## Entradas obligatorias

Antes de escribir código, verificá que existen:

1. **RFC aprobado** de la API u operación. Si el cambio es chico y el estándar no exige RFC (campo opcional, filtro, valor de enum extensible, código de error), alcanza con el PR de contrato. Si falta un RFC que sí corresponde, frená y avisá. No lo inventes.
2. **Contrato** (OpenAPI para REST, AsyncAPI para eventos, Protobuf para gRPC). Si falta, **proponé un borrador** siguiendo `references/contrato-borrador.md` y esperá la aprobación del usuario antes de implementar.

Si la operación toca estilo, plano o modelado y el RFC no lo resuelve, es una decisión de diseño: frená y preguntá.

## Modos de trabajo

**Bootstrap**: el repo no tiene la base. Hacé esto, en orden:
1. Inventariá qué existe (estructura de capas, lint, tests, módulo `platform/`).
2. Preguntá lo que no se pueda deducir: broker de mensajes, formato de eventos, si el cluster tiene colector de OpenTelemetry.
3. Creá la estructura de capas (`references/capas-y-dependencias.md`).
4. Construí en `platform/` **solo las piezas que el contrato necesita** (ver paso 3 del flujo).
5. Configurá la verificación de límites entre capas y la estructura de tests.
6. Generá `docs/platform-assumptions.md` desde `assets/platform-assumptions.template.md`, con lo que asumiste.

**Feature**: el repo ya tiene la base. Agregá la operación usando lo que existe. Si falta una pieza que la operación necesita, construila en `platform/` y mencionalo.

## Flujo

1. **Detectar el stack.** Lenguaje, framework, gestor de dependencias, herramientas de lint y de tests. Si hay convenciones del repo, tienen prioridad sobre las de esta skill en estilo de código (casing, formato). Nunca sobre las reglas de comportamiento de abajo.
2. **Verificar entradas** (RFC y contrato).
3. **Leer las extensiones del contrato** y decidir qué piezas hacen falta: `x-idempotent` (idempotencia), `x-slo` y `x-degradation` (resiliencia y observabilidad), `x-plane` (data o control plane, afecta qué servicio recibe la operación), `x-error-codes` (catálogo de errores), `x-data-classification` (enmascarado y cifrado). Si ningún `POST` es idempotente, no construyas idempotencia. Construí lo necesario y nada más.
4. **Tests primero**, desde los ejemplos del contrato (`references/tests.md`). Deben fallar antes de implementar.
5. **Implementar por capas**, de adentro hacia afuera: dominio, aplicación, adaptadores de salida, adaptadores de entrada.
6. **Correr lint y tests del repo** y corregir hasta que pasen. Si el repo no tiene lint de capas, configurá el de su lenguaje.
7. **Devolver el checklist de bloqueo** (`references/checklist-bloqueo.md`) con cada punto marcado como cumple, no cumple o no aplica, y una línea de evidencia por cada uno.

## Reglas innegociables

Son los puntos de bloqueo de código de los guidelines. Se cumplen siempre, sin importar el lenguaje. Si una no se puede cumplir, no la saltees: explicá por qué y proponé una excepción registrada.

1. El dominio no importa infraestructura (framework, ORM, cliente HTTP, broker).
2. El tenant (el cliente o comercio dueño de los datos) sale **solo del token**. Nunca del body, de un header custom ni de la IP. Un recurso de otro tenant devuelve `404`, no `403`.
3. Ningún número de tarjeta (PAN) ni dato PCI fuera del tokenizador. Los campos solo admiten `token`, `last4`, `bin`, `brand`, `expMonth`, `expYear`.
4. El dinero es un entero en la menor unidad más el código de moneda ISO 4217. Nunca float.
5. Toda llamada externa tiene timeout de conexión, de lectura y total, definidos explícitamente.
6. Solo se reintenta lo idempotente y transitorio, con la misma idempotency key, y nunca un `4xx` (salvo `429`).
7. La transacción de base de datos abarca solo persistencia y outbox. Ninguna llamada externa adentro.
8. Un único punto traduce excepciones a respuestas de error. Los controllers no tienen `try/catch` que arme status.
9. Los errores nunca exponen stack traces, SQL, clases, hosts ni versiones.
10. Logs estructurados, con `traceId`, sin datos sensibles sin enmascarar y sin bodies completos.
11. La inserción de la idempotency key es atómica (una sola operación que falla si ya existe).
12. Los consumidores de eventos son idempotentes y tienen test de doble procesamiento.
13. Las queries usan parámetros ligados. Nunca interpolación de strings.
14. Ningún secreto en código, tests, manifiestos ni imágenes.
15. Los eventos se publican por outbox en la misma transacción que el cambio de estado.
16. Los tests se escriben antes de la implementación, desde los ejemplos del contrato.

## Cuándo frenar y preguntar

- Falta el RFC que corresponde o el contrato (para el contrato, proponé borrador).
- El contrato pide algo que el entorno no garantiza: claims del token que Keycloak no emite, broker sin definir.
- Una regla de esta skill choca con una convención del repo, o con lo que pide el usuario.
- Hay que decidir estilo, plano o modelado.
- El usuario pide saltear un punto de bloqueo.

Al preguntar, proponé una opción concreta con tu recomendación. No devuelvas una lista abierta.

## Entorno que se asume

Detalle y supuestos en `references/entorno.md`. En resumen: Keycloak como proveedor de identidad, AWS Secrets Manager para secretos, broker de mensajes variable (se pregunta en el bootstrap), OpenTelemetry solo si el cluster tiene colector, y sin schema registry (los schemas viven como archivos en el repo de contratos con verificación de compatibilidad en CI).

## Dónde leer según la tarea

Leé solo lo que la tarea necesita.

| Tarea | Leer |
|---|---|
| Cualquier tarea | `references/capas-y-dependencias.md`, `references/nombres-por-rol.md` |
| Endpoint REST o gRPC | `por-tipo-de-tarea/endpoint.md` |
| Consumidor o productor de eventos | `por-tipo-de-tarea/consumidor-eventos.md`, `modulo-de-plataforma/outbox-inbox.md` |
| Llamar a un proveedor externo | `por-tipo-de-tarea/adaptador-proveedor.md`, `modulo-de-plataforma/resiliencia.md` |
| Webhook saliente | `por-tipo-de-tarea/webhook-saliente.md` |
| Job asíncrono o bulk | `por-tipo-de-tarea/job-asincrono.md` |
| Armar una pieza transversal | el archivo que corresponda en `modulo-de-plataforma/` |
| Auth, datos sensibles, input, secretos | `seguridad-en-codigo.md` |
| Escribir tests | `tests.md` |
| Falta el contrato | `contrato-borrador.md` |
| Cierre de la tarea | `checklist-bloqueo.md` |

Piezas en `modulo-de-plataforma/`: `idempotencia`, `paginacion`, `errores`, `validacion-de-token`, `outbox-inbox`, `resiliencia`, `observabilidad`, `tipos-de-datos`, `concurrencia`.

## Cómo reportar al terminar

Resumí en pocas líneas: qué se implementó, qué piezas de plataforma se construyeron, qué se asumió del entorno, y el checklist de bloqueo. Definí la primera vez los términos que el usuario pueda no conocer. Si algo del estándar quedó inconsistente con el repo o con la realidad, señalalo y esperá su decisión. No modifiques los guidelines ni documentos ya entregados por tu cuenta.
