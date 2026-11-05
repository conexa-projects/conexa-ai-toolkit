# ADR-<nnn> - Integración de <tercero> en Conflux

| Campo | Valor |
|---|---|
| Estado | Propuesto |
| Fecha | <AAAA-MM-DD> |
| Decisores | <nombres> |
| Contexto técnico | <ADR y documentos en los que se apoya> |
| Tickets | <CFX-…> |

## Contexto

Qué se integra, para qué integrador o merchants, y qué tipo de integración es (target, integrador API, integrador plataforma, operación, mecanismo).

## Decisiones de configuración

Los documentos del Registry que se cargan y las decisiones que no son obvias en ellos: estrategia de auth, un target por ambiente, operaciones síncronas o diferidas, `announce_provisional`, `provider_states`, `reconciliation`, ventanas y TTL.

## Dónde vive cada pieza

| Pieza | Componente / repo | Por qué ahí |
|---|---|---|

## Preguntas al tercero y respuestas

| Pregunta | Respuesta | Fuente (doc oficial, SDK, versión) |
|---|---|---|

## Desvíos aceptados

Lo que se aparta de una regla o de un ADR, con el motivo, quién lo aceptó y hasta cuándo.

## Mecanismos nuevos

Si la integración necesitó una capacidad genérica nueva en el Dispatcher, el Webhook-Handler o el Broker: nombre (por mecanismo), parámetros, revisión de diseño y regresión hecha.

## Certificación

Ruta del archivo de certificación y resumen de su estado.

## Gates pre-producción

Lo que queda abierto antes del primer uso productivo.
