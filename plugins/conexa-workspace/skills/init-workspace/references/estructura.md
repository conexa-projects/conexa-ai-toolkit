# Estructura del workspace generado

## Principio

La raíz es la **capa de contexto**. Versiona reglas, conocimiento, agentes y scripts. No versiona código de producto: cada repo de trabajo sigue siendo un repo aparte, con su propio remote, y aparece en la raíz como carpeta ignorada. Así una sola sesión de agente ve todos los repos a la vez, y el contexto compartido no queda disperso entre ellos.

## Qué genera y para qué

| Ruta | Versionado | Para qué |
|---|---|---|
| `AGENTS.md` | sí | Fuente de verdad para cualquier agente (Claude, Codex, etc.): qué es el workspace, repos, cómo orientarse, idioma, reglas duras, memoria, roles |
| `CLAUDE.md` | sí | Importa `@AGENTS.md` y agrega solo lo específico de Claude Code (subagentes, skills, hooks). No duplica reglas |
| `README.md` | sí | Para humanos: setup, qué hay, cómo se usa |
| `CONTRIBUTING.md` | sí | Dos velocidades: `knowledge/` directo a la rama base; agentes, reglas y scripts por PR |
| `MAINTENANCE.md` | sí | El capture loop y la tabla "qué disparador actualiza qué" |
| `bootstrap/repos.tsv` | sí | Manifest de repos: `carpeta<TAB>url<TAB>rama` |
| `bootstrap/bootstrap.sh` | sí | Clona o enlaza los repos del manifest; mantiene el bloque de repos del `.gitignore`; `--add`, `--link`, `--update`, `--https`, `--dry-run` |
| `scripts/map.mjs` | sí | Genera el mapa de contexto en `.context/` (sin dependencias, Node ≥ 18) |
| `scripts/session-start.sh` | sí | Hook de inicio: refresca el mapa si un repo cambió y avisa qué falta clonar |
| `scripts/validate.mjs` | sí | Chequeos de CI (ver abajo) |
| `scripts/graphify-setup.sh` | sí | Instalación completa de graphify y construcción del grafo de todos los repos (opcional; ver `harness.md`) |
| `.graphifyignore` | sí | Lo crea `graphify-setup.sh`: qué no entra al grafo |
| `knowledge/README.md` | sí | Índice de notas. Toda nota tiene que estar enlazada acá |
| `knowledge/_template.md` | sí | Plantilla de nota |
| `knowledge/decisiones.md` | sí | Log de decisiones estilo ADR, solo agregar |
| `knowledge/procesos/idioma.md` | sí | La regla de idioma completa |
| `knowledge/templates/repo-expert.md` | sí | Plantilla de agente experto por repo |
| `.claude/settings.json` | sí | Permisos (lectura libre, escrituras riesgosas denegadas) y hook `SessionStart` |
| `.claude/agents/` | sí | `code-reviewer`, `security-reviewer`, `explorer` + un `<repo>-expert` por repo |
| `.claude/skills/agregar-repo/` | sí | Sumar un repo después del setup |
| `.claude/skills/capturar/` | sí | Volcar lo aprendido en una sesión a `knowledge/` |
| `.github/` | sí (opcional) | Workflow del validador y PR template |
| `drafts/` | no | Borradores, análisis, estimaciones. No es conocimiento |
| `.context/` | no | Mapa generado. Se regenera solo |
| `graphify-out/` | no | Grafo de graphify, si se instaló. Se regenera solo |
| `<repo>/` | no | Repos de trabajo |

## Lo que chequea el validador

- Credenciales versionadas (`*.pem`, `*.key`, `.env`, `client_secret*`, etc.).
- Archivos de un repo de trabajo versionados en la raíz.
- Cada carpeta del manifest presente en el bloque de repos del `.gitignore`.
- Links relativos rotos en markdown (ignora los que apuntan a repos o a `.context/`, que no existen en CI).
- Rutas absolutas de una máquina personal.
- Frontmatter de agentes y skills: `name` igual al archivo o carpeta, `description` no vacía.
- Notas de `knowledge/` fuera del índice.
- `CLAUDE.md` que no importa `AGENTS.md`.

## Adaptar un workspace existente

El objetivo es sumar lo que falta sin romper lo que funciona.

1. **Inventario.** Listá lo que hay y clasificalo: igual a la plantilla, equivalente con otro nombre (ej. `docs/lessons/` en vez de `knowledge/`), o ausente.
2. **Equivalentes: respetá el nombre existente.** Si ya hay una carpeta de conocimiento con otro nombre, no crees una segunda. Proponé usar la existente y ajustá las rutas en `AGENTS.md` y en el validador.
3. **`CLAUDE.md` existente sin `AGENTS.md`.** Proponé mover el contenido agnóstico a `AGENTS.md` y dejar en `CLAUDE.md` el `@AGENTS.md` más lo específico de Claude. Mostrá el diff completo antes.
4. **`AGENTS.md` existente.** No lo reemplaces. Proponé agregar solo las secciones faltantes (tabla de repos con marcadores, "Cómo orientarte rápido", "Memoria del proyecto").
5. **`.gitignore` existente.** Agregá solo los bloques que falten: secretos, `/.context/`, `/drafts/*`, estado local de agentes y el bloque de repos con sus marcadores. El bootstrap necesita los marcadores exactos:
   ```
   # >>> repos (bootstrap/bootstrap.sh mantiene este bloque; no editar a mano) >>>
   # <<< repos <<<
   ```
6. **`.claude/settings.json` existente.** Fusioná por clave: sumá los `allow`/`deny` que falten y el hook `SessionStart` si no hay uno. No borres entradas del usuario.
7. **Carpetas con `.git` adentro.** Son repos de trabajo: registralas en `bootstrap/repos.tsv` con su `origin` y su nombre de carpeta actual. Si alguna está **trackeada** por el repo raíz (no ignorada), avisá: sacarla del índice (`git rm -r --cached <carpeta>`) es una decisión del usuario.
8. **Agentes existentes.** No los reescribas. Si hay uno que cumple el rol de un genérico (ej. ya hay un reviewer), no agregues el genérico: mencioná la superposición en el reporte.
