# Harness: lectura rápida y memoria

Tres capas, de la más barata a la más cara de mantener:

| Capa | Dónde | Quién la escribe | Versionada | Responde |
|---|---|---|---|---|
| Mapa | `.context/` | `scripts/map.mjs`, solo | no | ¿Qué hay y dónde? Stack, comandos, estructura, hotspots |
| Memoria | `knowledge/` + `knowledge/decisiones.md` | la sesión principal, por el capture loop | sí | ¿Qué no se deduce del código? ¿Por qué se decidió X? |
| Grafo (opcional) | `graphify-out/` | `scripts/graphify-setup.sh` | no | ¿Quién llama a X? ¿Qué conecta A con B? ¿Qué rompe si cambio Y? |

## El mapa (`scripts/map.mjs`)

Determinístico, sin dependencias ni llamadas a APIs. Lee cada repo del manifest con `git` y el filesystem, y escribe:

- `.context/INDEX.md`: una fila por repo (rama, último commit, stack, archivos), las relaciones entre repos y lo que falta clonar.
- `.context/map/<carpeta>.md`: estructura con conteos, lenguajes, manifests y sus scripts, dependencias principales, entrypoints, tests, CI, Docker/compose, variables de `.env.example` (solo nombres), reglas de agente del repo, últimos commits y hotspots (archivos más tocados en 90 días).
- `.context/map/<carpeta>.json`: la caché. Guarda el `HEAD` con el que se generó.

**Caché por `HEAD`:** si el `HEAD` de un repo no cambió, no se regenera. Por eso es barato correrlo en cada inicio de sesión. `--force` regenera todo; `--repo <carpeta>` uno solo.

**Por qué no se versiona:** se deriva de los repos, cuesta segundos y cambia con cada commit de ellos. Versionarlo generaría ruido en cada PR sin aportar nada que no se regenere solo.

**Límites:** es un índice, no un análisis semántico. Detecta relaciones entre repos por nombre (un repo que menciona el nombre o el paquete de otro en sus manifests o su compose), no por llamadas reales.

## El hook de inicio (`scripts/session-start.sh`)

Registrado en `.claude/settings.json` como `SessionStart`. Lo que imprime entra al contexto de la sesión, así que es corto:

- corre `map.mjs --quiet` (con caché, casi siempre instantáneo);
- avisa qué repos del manifest no están clonados;
- recuerda que el índice está en `.context/INDEX.md`.

**Nunca falla ni bloquea:** sin Node o sin repos, avisa y sale con 0.

## La memoria (`knowledge/`)

- **Notas**: una lección por archivo, con frontmatter `name` + `description`. La `description` se escribe pensando en qué buscaría quien tiene el problema. Todas enlazadas desde `knowledge/README.md`; el validador falla si queda una huérfana.
- **Decisiones**: `knowledge/decisiones.md`, entradas `D-NNN` fechadas. Nunca se reescribe una entrada: se agrega una nueva y la vieja se marca `Reemplazada por D-NNN`.
- **Capture loop**: al cerrar una tarea, ¿descubriste algo que el código no deja obvio? Si sí, se escribe en el mismo movimiento. La skill `/capturar` lo guía.
- **Lo que no es memoria**: la auto-memoria local del agente (vive en la máquina, no se comparte) y `drafts/` (borradores sin validar).

## Graphify (opcional)

Sumalo si el usuario lo pidió, o si los repos son grandes y van a aparecer muchas preguntas de relaciones ("¿quién llama a X?", "¿qué rompe si cambio Y?"). Para repos chicos o medianos, el mapa alcanza.

**Todo lo hace `scripts/graphify-setup.sh`**, que viene en cada workspace. No lo reemplaces por `graphify install` + `/graphify .`: graphify respeta el `.gitignore`, y los repos están ignorados en la raíz, así que el grafo saldría vacío.

```bash
bash scripts/graphify-setup.sh --dry-run     # mostrale al usuario qué va a hacer
bash scripts/graphify-setup.sh               # instalación completa + primer grafo
```

Qué hace, en orden:

1. **Requisitos:** Python ≥ 3.10, git y Node.
2. **CLI** (paquete `graphifyy`, con doble y): con `uv`; si no está, con `pipx`; y como último recurso, `pip --user` con aviso. `--install-uv` instala uv con su instalador oficial si no hay ninguno de los dos. Encuentra el binario aunque su carpeta todavía no esté en el PATH.
3. **Skill `/graphify` a nivel usuario** (`graphify install`; `--platform codex` y otras). No se instala a nivel proyecto a propósito: esa variante registra hooks en el `settings.json` compartido, que fallan en cada llamada para quien no tiene graphify.
4. **Archivos del workspace** (idempotente):
   - `.graphifyignore`: excluye el tooling del workspace, dependencias, builds, lockfiles y secretos. Es necesario porque se construye con `--no-gitignore`.
   - `/graphify-out/` al `.gitignore`: el grafo es local.
   - Permisos en `.claude/settings.json`: consultas al grafo permitidas; leer el `graph.json` crudo, denegado.
   - Una sección entre marcadores en `AGENTS.md`, con cuándo y cómo consultar el grafo.
5. **Construcción code-only:** `graphify extract . --code-only --no-gitignore` + `cluster-only --no-label --no-viz`. Es AST local con tree-sitter: sin API key, sin tokens, en segundos. Verifica que cada repo clonado tenga nodos y avisa si alguno quedó en cero.
6. `--hooks`: hooks `PreToolUse` que empujan a Claude al grafo antes de Grep/Read. Van en `.claude/settings.local.json` (ignorado), porque llevan la ruta absoluta del binario.
7. `--mcp`: agrega el extra `mcp` y registra el grafo como servidor MCP en el scope local de Claude Code. Si el CLI `claude` no está, imprime el comando.

**Refresco:** el hook de inicio corre `--refresh-if-stale --background`. Compara el `HEAD` de cada repo con el de la última construcción y, si cambió alguno, reconstruye en segundo plano con un lock. A mano: `--refresh`.

**Por qué el grafo no se versiona:** code-only cuesta segundos y se deriva de los repos. Versionarlo agregaría megas por PR sin aportar nada que no se regenere solo.

**El paso semántico** (docs, PDFs, imágenes) usa tokens del asistente. Si el usuario lo quiere, que corra `/graphify` sobre una carpeta de docs puntual, nunca sobre la raíz.

**Desinstalar:** `--uninstall` saca la sección de `AGENTS.md`, los permisos, los hooks locales y el MCP local; `--purge` borra además `graphify-out/`. El CLI y la skill de usuario quedan, porque sirven para otros proyectos.
