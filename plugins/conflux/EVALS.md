# Evaluaciones de conflux-integration

Corridas con `skill-creator`: cada caso de `skills/conflux-integration/evals/` se ejecutó con la skill y sin ella (línea base), con acceso de solo lectura a los repos de Conflux, y un calificador independiente juzgó cada aserción contra lo que produjo la corrida.

## Iteración 1 (04/11/2026)

| Caso | Con skill | Sin skill |
|---|---|---|
| mercadopago-target-asks-before-designing | 6/6 | 4/6 |
| business-logic-goes-to-processor | 4/4 | 4/4 |
| provider-signature-becomes-generic-mechanism | 5/5 | 4/5 |
| platform-is-not-a-target | 5/5 | 5/5 |
| certification-file-for-target | 9/9 | 7/9 |
| review-flags-third-party-in-dispatcher | 6/6 | 5/6 |
| **Total** | **100 %** | **85 %** |

Tiempo medio por corrida: 409 s con la skill y 271 s sin ella; tokens similares (161 k contra 168 k).

### Qué diferenció a la skill

- Pregunta al proveedor antes de diseñar y escribe el documento del Registry antes que código (sin la skill, arrancó por el package).
- Ante una firma sin timestamp, propone mitigación (re-consulta, aceptación por escrito) en vez de confiar solo en la marca de idempotencia.
- El archivo de certificación sale con tipos B/E/C/S y estado por caso (126 casos para PayU, ninguno en Pasa); sin la skill, sin tipo ni estado por caso.
- La revisión cita archivo y línea de cada hallazgo.

### Límites de la medición

- Las líneas base no partían de cero: heredaban la memoria del usuario (consultar antes de decidir, packages de target, Dispatcher agnóstico), así que la diferencia mide la skill por encima de esa memoria. Un equipo sin esa memoria debería ver una diferencia mayor.
- Dos casos (lógica de negocio y plataforma) no discriminaban. Para la iteración 2 se agregaron aserciones más finas: processor sin estado, reembolso al target original, el `code` de OAuth nunca por el processor, formato de firma no verificado, límites del código actual, 2xx sin estado mapeable.

### Cambios a la skill que salieron de la iteración 1

Las corridas (con y sin skill) encontraron límites reales de `main` que pasaron a `references/sources.md` ("Known capability limits"), a la checklist de target y a la biblioteca de casos:

- el header de idempotencia es fijo (`Idempotency-Key`);
- un 2xx con estado no mapeable se aprueba por el código HTTP;
- `status_mapping` es por target, no por operación;
- `api-key` no soporta credenciales en el cuerpo ni firma de campos;
- `dedup_window_seconds: 0` con un proveedor sin idempotencia permite doble cobro en el reintento;
- webhooks de operaciones distintas con el mismo id de transacción chocan en el mapeo;
- la federación de plataformas del Broker asume la forma de OAuth de Shopify;
- `target-payu` ya no existe en `main`;
- `payu`, `mercadopago`, `tiendanube` y `coppel` se usan como ids de ejemplo en los tests, así que sumarlos a la lista de nombres prohibidos exige renombrar antes;
- las referencias a secretos van sin el prefijo `secretsmanager:` y los documentos `targets` llevan `target_id`.

La iteración 2 (con estos cambios y las aserciones nuevas) no se corrió todavía.
