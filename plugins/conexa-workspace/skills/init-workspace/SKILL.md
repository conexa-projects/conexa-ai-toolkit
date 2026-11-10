---
name: init-workspace
description: "Crea (o adapta) un repositorio raíz de workspace para trabajar con agentes sobre varios repos a la vez: AGENTS.md como fuente de verdad, CLAUDE.md que lo importa, los repos de trabajo como carpetas hermanas ignoradas por git y clonadas por un bootstrap, subagentes genéricos (code-reviewer, security-reviewer, explorer) más un experto por stack (un solo nest-expert aunque haya varios backends Nest), un mapa de contexto generado que acelera la lectura, y una memoria versionada (knowledge/ + log de decisiones). Usar cuando se pida iniciar, armar, crear, scaffoldear o bootstrapear un workspace, repo raíz, repo de contexto, meta-repo o 'carpeta que agrupe repos' para Claude Code/Codex, con o sin repos existentes; también para sumar esa estructura a un workspace que ya existe, o para actualizar un workspace ya generado a la versión actual de la plantilla. NO crea repos remotos ni pushea."
---

# init-workspace

Generás la raíz de un workspace multi-repo. La raíz **no tiene código de producto**: tiene el contexto que une a los repos (reglas, conocimiento, agentes, scripts). Los repos de trabajo viven como carpetas dentro de la raíz, ignoradas por git:

```
<workspace>/
  AGENTS.md  CLAUDE.md  README.md  CONTRIBUTING.md  MAINTENANCE.md
  bootstrap/  scripts/  knowledge/  drafts/  .claude/  .github/
  repo-a/     ← ignorado, lo clona bootstrap/bootstrap.sh
  repo-b/     ← ignorado
  .context/   ← ignorado, mapa generado por scripts/map.mjs
```

Qué es cada pieza y por qué existe: `references/estructura.md`. Leelo antes de adaptar un workspace existente.

## Reglas duras

- **Nunca pises un archivo existente.** `scaffold.py` saltea lo que existe y lo reporta; la fusión la proponés vos, con diff, y se aplica con aprobación.
- **Nunca escribas dentro de los repos de trabajo.** Solo se leen. Ni commits, ni ramas, ni archivos.
- **No crees repos remotos ni pushees.** Es una skill local. `git init` y el primer commit de la raíz, solo con aprobación explícita.
- **Todo lo que escribas sobre un repo tiene que salir de leerlo.** Lo que no pudiste verificar va marcado `[a confirmar]`. No completes con suposiciones sobre el stack.
- **Nada de secretos ni rutas absolutas de la máquina** en archivos versionados. El validador falla si aparecen.
- Clonar requiere red y credenciales del usuario: mostrá el `--dry-run` y pedí confirmación antes.

## Paso 1 — Destino y modo

1. Resolvé la carpeta destino. Si el usuario no la dio, preguntala.
2. Si no existe o está vacía → **modo nuevo**.
3. Si ya es un workspace generado por esta skill y piden actualizarlo, ponerlo al día o traer la versión nueva de la plantilla → **modo actualizar**: andá directo a la sección "Modo actualizar".
4. Si ya tiene archivos → **modo adaptar**: listá qué hay (`AGENTS.md`, `CLAUDE.md`, `.claude/`, `.gitignore`, carpetas con `.git` adentro). Las carpetas con `.git` son candidatas a repos de trabajo: ofrecé registrarlas en el manifest con su `origin`. Seguí `references/estructura.md` → "Adaptar un workspace existente".

## Paso 2 — Entrevista (una sola tanda)

Preguntá solo lo que no esté en el pedido, todo junto, con defaults:

| Dato | Default |
|---|---|
| Nombre del workspace | nombre de la carpeta |
| Qué es, en una línea | — (obligatorio) |
| Repos de trabajo: URL git, y opcionalmente carpeta y rama | ninguno (se pueden sumar después con `/agregar-repo`) |
| Política de idioma | `es-en`: docs y chat en español; commits, PRs y código en inglés. Alternativas: `es`, `en` |
| CI de GitHub (workflow del validador + PR template) | sí |
| Grafo de código con graphify, además del mapa | no (se puede sumar después con `bash scripts/graphify-setup.sh`) |

Si pasan repos locales en vez de URLs, leé su `origin` con `git -C <ruta> remote get-url origin` y usalo; después el bootstrap los enlaza con `--link` en vez de reclonarlos.

## Paso 3 — Scaffold

```bash
python3 <dir-de-esta-skill>/scripts/scaffold.py \
  --target <destino> --name "<nombre>" --description "<una línea>" \
  --lang es-en \
  --repo "<url>[|carpeta[|rama]]"   # repetible
  # --no-ci  para omitir .github/
```

Corré primero con `--dry-run` en modo adaptar. El script imprime `creado` / `existe (no se tocó)` por archivo. Lo que quedó en "existe" lo fusionás a mano en el Paso 7.

El scaffold deja un sello en `bootstrap/template.lock.json` (versionado): la versión de la plantilla y el hash de cada archivo que generó. Es lo que permite actualizar después sin pisar lo que el equipo modificó.

## Paso 4 — Repos

```bash
cd <destino>
bash bootstrap/bootstrap.sh --dry-run            # mostrale esto al usuario
bash bootstrap/bootstrap.sh [--link <dir>] [--https]
```

- `--link <dir>` reutiliza clones que ya existen en otra carpeta (los detecta por `origin` y los enlaza con symlink).
- Si un clon falla (acceso, red), seguí con los demás y dejalo anotado en el reporte final. No lo reintentes en loop.

## Paso 5 — Mapa

```bash
node scripts/map.mjs
```

Genera `.context/INDEX.md` y `.context/map/<repo>.md`: stack, comandos, estructura, entrypoints, hotspots, relaciones entre repos. Es la base factual del paso siguiente.

Si el usuario quiere el grafo de graphify: `bash scripts/graphify-setup.sh --dry-run`, mostrá el plan y, con el OK, correlo sin `--dry-run` (sumá `--hooks` o `--mcp` solo si los pidió). Instala todo y construye el grafo code-only, sin costo de LLM. **No uses `graphify install` ni `/graphify .` directo**: con los repos ignorados en la raíz, el grafo sale vacío. Detalle: `references/harness.md`.

## Paso 6 — Un experto por stack

No es un experto por repo: los repos se agrupan por stack (framework principal) y cada grupo tiene **un** experto. Varios backends Nest → un `nest-expert`. Seguí `references/expertos-por-stack.md`:

1. Agrupá los repos clonados por stack con la línea **Stack** de `.context/INDEX.md`. Si el agrupamiento no es obvio (monorepo mixto, repo sin framework), proponelo al usuario antes de escribir.
2. Por cada grupo, leé el repo más representativo a fondo y de los demás solo lo que difiere: mapa, README, `AGENTS.md`/`CLAUDE.md`, manifests y CI.
3. Creá `.claude/agents/<stack>-expert.md` a partir de `knowledge/templates/stack-expert.md`, con todos los repos del grupo en "Repos que cubrís".
4. Completá la fila de cada repo en la tabla de `AGENTS.md` (entre los marcadores `BEGIN repos` / `END repos`): la columna Experto apunta al experto de su stack.

Los repos que no se pudieron clonar quedan en la tabla con `[no clonado]` y fuera de los expertos.

## Paso 7 — Cierre

1. Modo adaptar: proponé la fusión de cada archivo que quedó en "existe", con diff, y aplicá lo aprobado.
2. `git init` si hace falta. Corré `node scripts/validate.mjs` (necesita que los archivos estén en el índice: `git add` por nombre de lo generado, sin commitear todavía) y corregí lo que marque.
3. Fijate si la skill `security-audit` aparece entre las skills disponibles de la sesión. Si no, anotá en el reporte que falta instalar el plugin `conexa-guardrails`: sin él, `security-reviewer` recomienda una skill que no existe.
4. Preguntá antes del primer commit. Nunca `git add -A`: agregá por nombre, y verificá con `git status` que ninguna carpeta de repo quedó adentro.

## Modo actualizar

Para un workspace que ya existe y quedó con una versión vieja de la plantilla (lo marca `audit-workspace`, o lo pide el usuario).

```bash
python3 <dir-de-esta-skill>/scripts/scaffold.py --target <destino> --upgrade --dry-run   # mostrale esto
python3 <dir-de-esta-skill>/scripts/scaffold.py --target <destino> --upgrade
```

Por cada archivo de la plantilla:

| Salida | Qué pasó |
|---|---|
| `creado` | No existía (ej. una skill nueva del workspace) |
| `actualizado` | Era una versión vieja **sin modificar**: se pisó con la actual. Lo sabe por el sello o, si el workspace no tiene sello, porque coincide con una versión publicada |
| `modificado a mano (no se tocó)` | Alguien lo editó. Mostrá el `diff` contra la plantilla y proponé la fusión; se aplica con aprobación |
| `omitido` | Falta un dato para generarlo: pasá `--name` y `--description` |

`AGENTS.md`, `README.md`, `.gitignore`, el manifest y `knowledge/` son del equipo: `--upgrade` nunca los toca. Si la versión nueva les suma algo (un bloque del `.gitignore`, una sección de `AGENTS.md`), lo detecta `audit-workspace` y se fusiona como en "Adaptar un workspace existente".

Después: `node scripts/validate.mjs`, y commit con aprobación, agregando por nombre los archivos actualizados y `bootstrap/template.lock.json`. Reportá creados, actualizados y los modificados que quedaron pendientes de fusión.

## Formato del reporte final

```
Workspace listo en <destino>

Creado: <n> archivos · Fusionados: <lista> · Sin tocar: <lista>
Repos: <carpeta> — clonado | enlazado | falló (<motivo>)
Expertos: <stack>-expert ← <carpetas que cubre> (uno por línea)
Seguridad: security-reviewer (revisión acotada) · security-audit disponible | falta el plugin conexa-guardrails
Grafo: construido (<n> nodos por repo) | no instalado
Validador: OK | <problemas pendientes>
[a confirmar]: <lo que no se pudo verificar, por repo>

Siguiente paso: abrir Claude Code en <destino>. Para sumar un repo: /agregar-repo <url> · para darlo de baja o renombrarlo: /quitar-repo <carpeta>
```

## Referencias

- `references/estructura.md` — cada archivo generado, su propósito, y cómo adaptar un workspace existente.
- `references/expertos-por-stack.md` — cómo agrupar los repos por stack, qué leer y cómo escribir cada experto.
- `references/harness.md` — el mapa de contexto, el hook de inicio, la memoria y graphify opcional.
