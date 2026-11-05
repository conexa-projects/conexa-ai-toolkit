# Concurrencia y consistencia

Fuente: guidelines 5.7. Dos escrituras simultáneas al mismo recurso no pueden pisarse en silencio (lost update).

## Control optimista por versión

- El agregado tiene un campo `version` entero que se incrementa en cada mutación. Va en el body como solo lectura y como `ETag` (entre comillas) en las lecturas por ID. **El ETag es la versión, no un hash del body.**
- Las escrituras que editan atributos (`PATCH`, `PUT`, y `DELETE` si el recurso tiene versión) usan `If-Match`. El contrato declara si es obligatorio. En el control plane siempre lo es: sin él, `428 PRECONDITION_REQUIRED`. `If-Match: *` significa "escribí si existe".
- Versión desactualizada: **`412`**, no `409`. El body incluye la versión actual. `409` queda para conflictos de estado de negocio.
- Las acciones (`POST /orders/{id}/cancel`) no requieren `If-Match`: su precondición es el estado, no la versión.

## En el repositorio

```
UPDATE ... SET ..., version = version + 1 WHERE id = ? AND version = ?
```
Si afectó cero filas, se lanza `StaleVersionError` (categoría `precondition`). Nunca `SELECT` y luego `UPDATE` sin condición de versión.

## Lecturas después de escrituras

Dentro de la misma API, una lectura después de una escritura confirmada ve el cambio (lee de la primaria). Entre agregados y a través de eventos hay consistencia eventual, y el contrato lo declara (`x-consistency`). Una lectura que precede a una escritura con `If-Match` no lee de una réplica con lag.

## Creación

La creación concurrente se resuelve con la idempotency key o una restricción de unicidad en la base, nunca con una verificación previa.

## Tests

Dos `PATCH` con la misma versión: uno gana, el otro recibe `412`. `If-Match` ausente en el control plane da `428`. Acción sobre un recurso editado entre medio funciona.
