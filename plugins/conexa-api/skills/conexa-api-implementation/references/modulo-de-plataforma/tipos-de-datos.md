# Tipos de datos

Fuente: guidelines 5.3. Se construye una vez como tipos comunes en `platform/` o `shared/` y se usan en todos los contratos.

- **Instantes**: ISO 8601 / RFC 3339 en **UTC con `Z` y milisegundos** (`2026-09-24T14:32:11.204Z`). En entrada se aceptan offsets y se normalizan a UTC. Se rechazan los instantes sin zona. Nunca epoch. Almacenamiento con zona (`timestamptz`).
- **Fechas civiles** (`2026-09-24`, sin hora): no se convierten a instante. Se guardan como `date`.
- **Dinero**: objeto `Money` con monto **entero en la menor unidad** y `currency` ISO 4217 alfabético en mayúsculas. Indivisible: no existe `amount` sin `currency`. Sumar monedas distintas es un error de dominio (el tipo lo impide). Almacenamiento `bigint` más `char(3)`. Nunca float ni double.
- **IDs**: string opaco con prefijo de tipo (`pay_...`), generado en el servidor, al menos 96 bits de entropía, longitud fija por tipo, minúsculas, nunca enteros. Valor de ID inválido o con prefijo de otro tipo es `400 INVALID_ID_FORMAT` antes de tocar la base. Como value object propio en el código.
- **Strings**: UTF-8, `maxLength` en todo string de request, recorte de espacios en el borde, normalización Unicode NFC, sin HTML en campos de datos.
- **Números**: enteros con `minimum` y `maximum`. Flotantes solo para magnitudes donde la imprecisión es aceptable, nunca para dinero ni para comparar por igualdad. Nunca `NaN` ni `Infinity`.
- **Enums**: strings en snake_case con los valores del contrato, sensibles a mayúsculas. En entrada, un valor desconocido es `400 INVALID_ENUM`. En salida, el consumidor tolera desconocidos.
- **Nulos, ausentes y vacíos**: en responses todo campo del schema está presente (`null` si no tiene valor), los objetos condicionales se omiten, los arrays nunca son `null` (`[]`). En `PATCH` (Merge Patch), ausente es "no tocar", `null` es "borrar", presente es "reemplazar". El deserializador tiene que distinguir ausente de `null`.
- **Arrays**: `maxItems` siempre en requests, `minItems: 1` si el vacío viola una invariante.

Validación en el borde contra el schema del contrato, con todas las violaciones juntas.
