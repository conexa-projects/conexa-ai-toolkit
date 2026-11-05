# Paginación

Fuente: guidelines 5.1 y 5.2. **Toda colección pagina**, aunque sea chica hoy.

## Cursor por defecto

Cursor (un puntero opaco a la posición, no a un número de página) para toda colección de negocio. Es consistente ante inserciones y borrados (no duplica ni saltea) y cuesta lo mismo en la página 1 que en la 5000. Offset solo si la colección es chica y acotada por diseño, el consumidor realmente necesita saltar a una página, y un lag de consistencia es aceptable.

## Parámetros y respuesta

```
GET /payments?limit=20&cursor=...&sort=-createdAt

{
  "data": [ ... ],
  "pagination": { "limit": 20, "hasMore": true, "nextCursor": "..." }
}
```

- `limit`: entero, default 20, mínimo 1, máximo 100 (declarado por operación). Si excede el máximo se aplica el máximo.
- `cursor`: string opaco. Inválido (no decodifica, firma o hash de filtros no coincide) es `400 INVALID_CURSOR`.
- `data` siempre es un array, nunca `null`. `nextCursor` está presente si y solo si `hasMore` es `true`.
- `hasMore` se calcula pidiendo `limit + 1` a la base y devolviendo `limit`.
- Sin `page`, `pageSize` ni `offset` en operaciones con cursor.
- Sin conteo total por defecto (`COUNT(*)` en cada página es caro). Si se necesita, es opt-in y aproximado.

## Cómo se construye el cursor

- Codifica los valores de las columnas del orden de la última fila (por ejemplo `createdAt` y `id`), un hash de los filtros y el sort de la consulta, y una versión de formato.
- **Ordenamiento estable**: el orden siempre termina con `id` como desempate. Sin desempate, filas con el mismo `createdAt` se saltean o duplican.
- El cursor es **opaco** (codificado y firmado). Los consumidores no lo decodifican. Un cursor que se usa con filtros distintos a los de la consulta original se rechaza.
- No lleva datos sensibles.
- Consulta tipo keyset: `WHERE (created_at, id) < (:c, :i) ORDER BY created_at DESC, id DESC LIMIT :limit + 1`.

## Índices

Cada `sort` permitido tiene un índice que lo respalda, con el tenant como primera columna. Los campos ordenables salen de una lista blanca. Sin índice no se permite ordenar por ese campo.

## Filtros

Lista blanca de campos filtrables, tipos y operadores declarados en el contrato. Los filtros implícitos (tenant, archivados) se aplican en el repositorio **antes** de los del consumidor. Un intento de filtrar por tenant ajeno se rechaza o ignora según el contrato.

## Se construye una vez

Un helper de plataforma que recibe la consulta, el orden y el límite y devuelve la página. Los endpoints no implementan paginación cada uno por su cuenta.

## Tests

Veinticinco filas con `limit: 10`: tres páginas sin duplicados ni faltantes y la última con `hasMore: false`. Inserción entre páginas sin duplicados. Cursor inválido y cursor con filtros distintos. `limit` sobre el máximo. Dos filas con el mismo instante. Un tenant no ve filas de otro.
