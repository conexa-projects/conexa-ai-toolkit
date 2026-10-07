---
name: audit-workspace
description: "Audita un workspace multi-repo para agentes (raíz con AGENTS.md/CLAUDE.md, repos como carpetas ignoradas, subagentes, knowledge/, mapa y grafo de contexto) y reporta qué está completo, qué falta y qué se puede mejorar, con puntaje, hallazgos por severidad y un plan de acción. Combina chequeos mecánicos (estructura, manifest vs clones, .gitignore, agentes, memoria, seguridad, harness, CI) con una revisión de juicio (calidad del router, de los expertos y de las notas). Usar cuando se pida auditar, validar, revisar, diagnosticar, chequear la salud o la madurez de un workspace, repo raíz o repo de contexto, o preguntar si está completo, qué le falta o cómo mejorarlo; también antes de sumar gente nueva o después de un tiempo sin mantenerlo. Solo lee: no corrige nada sin aprobación."
---

# audit-workspace

Auditás una raíz de workspace contra el estándar de `init-workspace` y devolvés un diagnóstico accionable. Funciona también con workspaces que no generó esa skill: donde hay una pieza equivalente con otro formato, la reconocés y lo decís, en vez de marcarla como faltante.

## Reglas duras

- **Solo lectura.** No edites, no commitees, no corras `bootstrap.sh`, `map.mjs` ni `graphify-setup.sh` durante la auditoría. El script de auditoría no escribe nada salvo que le pases `--out`.
- **No entres a modificar los repos de trabajo.** Leerlos para verificar referencias está bien.
- **Cada hallazgo con evidencia:** archivo, línea o comando que lo muestra. Sin "podría mejorarse" sin decir qué y cómo.
- **Separá lo mecánico de lo de juicio.** El puntaje sale solo del script; tu revisión agrega hallazgos marcados como `[juicio]`, sin tocar el número.
- **No repitas un secreto** que encuentres: archivo y primeros 4 caracteres, como mucho.

## Paso 1 — Chequeo mecánico

```bash
python3 <dir-de-esta-skill>/scripts/audit.py <raíz> [--json] [--template <dir>]
```

- Si el usuario no dio la raíz, usá el directorio actual si tiene `AGENTS.md`, `CLAUDE.md` o `bootstrap/`; si no, preguntá.
- `--template` apunta a `init-workspace/assets/template` para detectar scripts desactualizados. Si la skill `init-workspace` está instalada como hermana, se encuentra sola.
- Usá `--json` si vas a procesar los hallazgos; markdown si solo los vas a mostrar.

Qué chequea cada dimensión y con qué severidad: `references/criterios.md`.

## Paso 2 — Revisión de juicio

Lo que un script no puede decidir. Leé solo lo necesario para cada punto:

1. **AGENTS.md como router.** ¿Se entiende en un minuto qué es el workspace y a quién delegar? ¿Las reglas duras son pocas y concretas? ¿Hay contenido que se deduce del código o que debería ser una nota de `knowledge/`?
2. **Expertos.** Para cada `<repo>-expert` (hasta 5; si hay más, los de repos con más hotspots en `.context/INDEX.md`):
   - ¿La `description` usa las palabras de alguien con un problema en ese repo?
   - Verificá **dos comandos** contra el `package.json`, `Makefile` o CI del repo. ¿Existen?
   - ¿Copia reglas del `AGENTS.md` del repo en vez de referenciarlas?
   - Los que el script marcó como "sin repo del mismo nombre": ¿cubren un repo con otro nombre?
3. **Notas de knowledge.** Muestreá hasta 5 (las más viejas primero: `git log --format=%cs -1 -- <nota>`). ¿Pasan el test "no se deduce del código"? ¿Siguen siendo ciertas? ¿Hay dos que dicen lo mismo?
4. **Decisiones.** ¿Tienen su porqué? ¿Hay decisiones evidentes en el código o en AGENTS.md que no están registradas?
5. **Cobertura.** Repos con mucha actividad (hotspots) y cero notas; stacks presentes (Terraform, pipelines, base de datos) sin experto que los cubra.
6. **Onboarding.** ¿Con el README alguien nuevo llega a una sesión útil en 10 minutos?

Si el workspace no sigue el estándar, sumá un punto 7: **qué partes del estándar conviene adoptar y cuáles no**, según cómo trabaja ese workspace. No todo hueco es un defecto: un workspace de un solo repo no necesita manifest.

## Paso 3 — Reporte

```
# Auditoría — <workspace> · <fecha>

**<puntaje>/100 · <nivel>**   (del script)
<la tabla de dimensiones del script>

## Resumen
<3–4 líneas: en qué estado está, qué es lo más urgente, qué está bien>

## Plan de acción
| # | Acción | Resuelve | Esfuerzo | Cómo |
|---|---|---|---|---|
| 1 | ... | 🔴 ... | 5 min | `comando` o skill |
<máximo 7 filas, ordenadas por severidad y después por esfuerzo>

## Hallazgos
<los del script, agrupados por severidad, más los tuyos marcados [juicio]>

## Lo que está bien
<2–4 puntos concretos: sirve para no romperlo al corregir>
```

Esfuerzo: `5 min` (un comando), `30 min` (editar unos archivos), `sesión` (escribir expertos o notas).

Mostralo en el chat. Si el usuario lo quiere guardar, va a `drafts/auditoria-<fecha>.md` (ignorado por git): `audit.py --out drafts/auditoria-<fecha>.md` para la parte mecánica, y sumá tu revisión.

## Paso 4 — Ofrecer correcciones

Nunca apliques nada sin OK explícito, ítem por ítem o por grupo. Ruteá cada corrección:

| Tipo | Con qué |
|---|---|
| Piezas faltantes de la estructura | `init-workspace` en modo adaptar |
| Repo sin clonar, bloque de `.gitignore` desincronizado | `bash bootstrap/bootstrap.sh` |
| Repo sin experto o sin fila en la tabla | `/agregar-repo` del workspace |
| Memoria vacía o capture loop inactivo | `/capturar` en las próximas tareas: no se inventa conocimiento para llenar el hueco |
| Mapa o grafo desactualizados | `node scripts/map.mjs` · `bash scripts/graphify-setup.sh --refresh` |
| Credencial versionada | Sacarla del índice **y rotarla**. Rotar es del usuario: decilo explícitamente |
| Repo versionado en la raíz | `git rm -r --cached <carpeta>`, con aprobación |
| Script distinto a la plantilla | Mostrá el `diff` primero: puede ser una personalización intencional |

Después de corregir, volvé a correr el script y mostrá el antes y el después del puntaje.
