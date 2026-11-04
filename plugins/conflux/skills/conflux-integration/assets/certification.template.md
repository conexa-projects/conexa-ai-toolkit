# Certificación de <integración> — <PREFIJO>

| Campo | Valor |
|---|---|
| Integración | <qué se integra: target, integrador API, integrador plataforma, operación, mecanismo> |
| Componentes y repos | <repos tocados, con rama o PR> |
| Documentos del Registry | <targets / integrators / integrator_platforms, con versión o PR> |
| Contrato del tercero verificado contra | <documentación oficial, SDK y versión, sandbox> |
| Fecha | <AAAA-MM-DD> |
| Responsable | <quién ejecuta y firma> |

> Este archivo lista todos los casos que tienen que cumplirse para declarar la integración lista para producción. Es un documento, no una suite: cada caso dice cómo se verifica y dónde queda la evidencia. Un caso nunca se ablanda para que pase; un comportamiento sin decidir queda «A definir» con su pregunta.

## Criterio de pase a producción

- Todos los casos `B` y `E` en `Pasa`.
- Los `C` y `S` en `Pasa`, o aceptados por escrito como riesgo conocido por el EM (quién y cuándo, en la tabla de riesgos aceptados).
- Ningún `A definir` en un caso `B` o `E`.
- Cada `Bloqueado` resuelto o aceptado por escrito con su ticket.
- Los gates pre-producción de abajo cerrados o aceptados por escrito.

## Casos

Tipo: `B` básico · `E` borde · `C` caos · `S` seguridad. Estado: `Pendiente` · `Pasa` · `Falla` · `Bloqueado` · `A definir` · `Retirado`.

### <ÁREA> — <nombre del área>

| ID | Caso | Tipo | Alcance | Verificación | Referencia | Evidencia | Estado |
|---|---|---|---|---|---|---|---|
| <PREFIJO>-<ÁREA>-01 | Dado …, cuando …, entonces … | B | General | <cómo> | <ADR / doc / ID del catálogo> | | Pendiente |

<!-- Repetir una sección por área: ARCH, CFG, PKG, PRC, ENV, IDM, SYNC, DEL, DLQ, AUTH, ASYNC, WHK, REC, NTF, CONN, MAN, TOK, CUST, PLT, MET, OBS, SEC, CHS, LOAD, OPS, INF, CMP, BIZ. Omitir las que no aplican y decir por qué en «Áreas que no aplican». -->

## Áreas que no aplican

| Área | Por qué |
|---|---|

## Preguntas abiertas («A definir»)

| ID del caso | Pregunta | Quién decide | Desde |
|---|---|---|---|

## Gates pre-producción

| Gate | Origen | Estado |
|---|---|---|

## Riesgos aceptados

| ID del caso | Riesgo | Aceptado por | Fecha |
|---|---|---|---|

## Resumen

| Estado | B | E | C | S | Total |
|---|---|---|---|---|---|
| Pasa | | | | | |
| Falla | | | | | |
| Bloqueado | | | | | |
| A definir | | | | | |
| Pendiente | | | | | |

Qué bloquea el pase a producción hoy: <lista>.
