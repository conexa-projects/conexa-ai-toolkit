# Mantenimiento

Cómo este workspace se mantiene útil con el tiempo. La convención está en
[`CONTRIBUTING.md`](CONTRIBUTING.md); acá va el proceso.

## El capture loop

Lo que descubrís en una sesión **no se queda en el chat ni en la memoria local del agente**: esa
memoria vive en tu máquina y no la ve nadie más.

**Si algo es durable y compartible, va versionado a esta raíz.**

Al cerrar una tarea, preguntate: *¿descubrí algo que el código no dejaba obvio?* Si la respuesta es
sí, escribilo en el mismo movimiento — media hora después ya no te vas a acordar de por qué era
no-obvio, que es justo lo que hace valiosa a la nota. En Claude Code, `/capturar` te guía.

Los subagentes **no escriben** en `knowledge/`: es una norma de su prompt. El volcado lo hace la sesión
principal, así que el capture loop es una acción consciente, no un automatismo.

## Qué disparador actualiza qué

| Disparador | Acción | Dónde |
|---|---|---|
| Resolviste un bug que costó encontrar | Escribir la lección | `knowledge/<área>/` |
| Descubriste una trampa de entorno o tooling | Escribir la lección | `knowledge/<área>/` |
| Se tomó o se descartó una decisión de diseño | Agregar una entrada | `knowledge/decisiones.md` |
| Cambió una regla dura del workspace | Editar y abrir PR | `AGENTS.md` |
| Un agente ruteó mal o le faltó contexto | Ajustar su prompt, que siga liviano | `.claude/agents/` |
| Se suma un repo al workspace | `/agregar-repo <url>` | `bootstrap/repos.tsv` + experto + `AGENTS.md` |
| Se da de baja o se renombra un repo | Editar el manifest, el experto y la tabla | `bootstrap/repos.tsv`, `.claude/agents/`, `AGENTS.md` |
| Una nota quedó desactualizada | Editarla o borrarla | `knowledge/` |
| Hiciste `git pull` en un repo y usás el grafo | Nada: se refresca al abrir sesión. Para ya: `bash scripts/graphify-setup.sh --refresh` | `graphify-out/` (local) |

## Sin dueños fijos

Quien toca algo, lo actualiza. Funciona si todos respetan el capture loop.

## Borrar es mantener

Una nota que dejó de ser cierta es peor que ninguna: se lee con la misma confianza que una correcta.
Si encontrás una desactualizada, arreglala o borrala del índice y del disco.
