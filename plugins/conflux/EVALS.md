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

## Iteración 2 (04/11/2026)

Misma metodología, con los cambios de arriba aplicados a la skill y 6 aserciones nuevas (41 en total, antes 35).

| Caso | Con skill | Sin skill |
|---|---|---|
| mercadopago-target-asks-before-designing | 7/7 | 5/7 |
| business-logic-goes-to-processor | 6/6 | 5/6 |
| provider-signature-becomes-generic-mechanism | 6/6 | 4/6 |
| platform-is-not-a-target | 6/6 | 5/6 |
| certification-file-for-target | 10/10 | 8/10 |
| review-flags-third-party-in-dispatcher | 6/6 | 5/6 |
| **Total** | **100 %** | **78 %** |

Tiempo medio por corrida: 397 s con la skill y 277 s sin ella; tokens iguales (166 k en ambos).

### Qué cambió respecto de la iteración 1

- Ahora todos los casos discriminan. Los dos que en la iteración 1 empataban se separan por las aserciones nuevas: sin la skill, el processor guarda estado (lógica de negocio) y no se pregunta quién llama a quién (plataforma).
- Sin la skill, en el caso de Mercado Pago no se le pregunta al proveedor antes de diseñar y el documento del Registry queda después del código. En el caso de Getnet no se marca el formato como no verificado ni se propone mitigar la falta de anti-replay.
- Con la skill aparecieron hallazgos que ninguna aserción mide todavía:
  - separa los datos del proveedor verificados en documentación oficial de los supuestos;
  - si un reintento con la misma `idempotency_key` cruza el umbral de ruteo, se cobra dos veces, porque la clave de dedup incluye el target;
  - cargar Getnet como `hmac-sha256` haría que todo webhook auténtico reciba 401;
  - las credenciales de PayU van en el cuerpo, lo que no encaja con `api-key`.

### Aserciones flojas, según los calificadores

- Revisión: "cita archivo y línea" no aclara si cuentan las líneas de contexto en `main`.
- Plataforma: "pregunta o determina" deja pasar cualquier diseño que ponga `type: platform`.
- Certificación: "casos de PayU o preguntas A definir" deja pasar cualquier caso con sabor a PayU. "Ningún caso en Pasa" no aclara si cuentan los resultados heredados de la corrida de plataforma.
- Mercado Pago: "menciona certificación" y "señala un límite del código" pasan en las dos corridas con una sola mención.
- Getnet: "estrategia genérica con parámetros en el Registry" no exige que el algoritmo sea un parámetro.

Endurecer estas aserciones y sumar las que miden los hallazgos de arriba queda para una iteración 3, si se decide hacerla.
