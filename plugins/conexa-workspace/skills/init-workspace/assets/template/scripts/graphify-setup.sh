#!/usr/bin/env bash
#
# graphify-setup.sh — instala graphify y construye el grafo de código de todos los repos del workspace.
#
# Por qué no alcanza con "graphify install" + "/graphify .": graphify respeta el .gitignore, y en este
# workspace los repos están ignorados en la raíz, así que el grafo saldría vacío. Este script construye
# con --no-gitignore y un .graphifyignore propio (que excluye dependencias, builds y secretos).
#
# La construcción es code-only: AST local con tree-sitter, sin API key ni costo de LLM.
# Todo lo que escribe en archivos versionados es portable. Lo que depende de tu máquina (hooks con la
# ruta del binario, servidor MCP) va solo a configuración local.
#
# Uso:
#   bash scripts/graphify-setup.sh                   # instalación completa + primer grafo
#   bash scripts/graphify-setup.sh --hooks           # además: hooks PreToolUse en .claude/settings.local.json
#   bash scripts/graphify-setup.sh --mcp             # además: servidor MCP del grafo (scope local de Claude Code)
#   bash scripts/graphify-setup.sh --extras pdf,office   # extras de graphify para el paso semántico
#   bash scripts/graphify-setup.sh --install-uv      # si no hay uv ni pipx, instala uv con su instalador oficial
#   bash scripts/graphify-setup.sh --platform codex  # registra la skill en otra plataforma (default: Claude Code)
#   bash scripts/graphify-setup.sh --upgrade         # actualiza graphify a la última versión
#   bash scripts/graphify-setup.sh --refresh         # solo reconstruye el grafo
#   bash scripts/graphify-setup.sh --refresh-if-stale [--background]   # lo usa el hook de inicio
#   bash scripts/graphify-setup.sh --uninstall [--purge]   # saca la integración (y el grafo con --purge)
#   bash scripts/graphify-setup.sh --dry-run         # muestra qué haría
#
# Requisitos: Python >= 3.10, git y Node >= 18 (para editar JSON sin dependencias).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1
OUT="graphify-out"
HEADS_FILE="$OUT/.workspace-heads"
LOCK_DIR="$OUT/.refresh.lock"
BEGIN_MARK="<!-- BEGIN graphify — lo mantiene scripts/graphify-setup.sh; no editar a mano -->"
END_MARK="<!-- END graphify -->"

MODE="install"; HOOKS=0; MCP=0; EXTRAS=""; INSTALL_UV=0; PLATFORM=""; UPGRADE=0; BACKGROUND=0; PURGE=0; DRY=0

usage() { awk 'NR>=3 && /^#/ {sub(/^# ?/,""); print; next} NR>=3 {exit}' "${BASH_SOURCE[0]}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --hooks)            HOOKS=1; shift ;;
    --mcp)              MCP=1; shift ;;
    --extras)           EXTRAS="${2:?--extras necesita una lista, ej. pdf,office}"; shift 2 ;;
    --install-uv)       INSTALL_UV=1; shift ;;
    --platform)         PLATFORM="${2:?--platform necesita un valor}"; shift 2 ;;
    --upgrade)          UPGRADE=1; shift ;;
    --refresh)          MODE="refresh"; shift ;;
    --refresh-if-stale) MODE="stale"; shift ;;
    --background)       BACKGROUND=1; shift ;;
    --uninstall)        MODE="uninstall"; shift ;;
    --purge)            PURGE=1; shift ;;
    --dry-run)          DRY=1; shift ;;
    -h|--help)          usage; exit 0 ;;
    *) echo "Opción desconocida: $1" >&2; usage >&2; exit 2 ;;
  esac
done

say()  { [ "$MODE" = "stale" ] || echo "$@"; }
step() { say ""; say "▸ $*"; }
warn() { echo "  ⚠ $*" >&2; }
die()  { echo "✗ $*" >&2; exit 1; }
run()  { if [ "$DRY" -eq 1 ]; then echo "  (dry-run) $*"; else "$@"; fi; }

# ── localizar herramientas ───────────────────────────────────

find_python() {
  local c
  for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
      echo "$c"; return 0
    fi
  done
  return 1
}

# Imprime la ruta del binario graphify aunque su carpeta todavía no esté en el PATH.
find_graphify() {
  local d
  if command -v graphify >/dev/null 2>&1; then command -v graphify; return 0; fi
  if command -v uv >/dev/null 2>&1; then
    d="$(uv tool dir --bin 2>/dev/null || true)"
    [ -n "$d" ] && [ -x "$d/graphify" ] && { echo "$d/graphify"; return 0; }
  fi
  for d in "$HOME/.local/bin" "$HOME/Library/Python"/3.*/bin "$HOME/AppData/Roaming/Python"/Python3*/Scripts; do
    [ -x "$d/graphify" ] && { echo "$d/graphify"; return 0; }
    [ -x "$d/graphify.exe" ] && { echo "$d/graphify.exe"; return 0; }
  done
  return 1
}

# Carpetas de repos del manifest que están presentes.
present_repos() {
  [ -f bootstrap/repos.tsv ] || return 0
  tr -d '\r' < bootstrap/repos.tsv | awk -F'\t' '!/^[[:space:]]*#/ && NF>=2 && $1!="" {print $1}' | while read -r d; do
    [ -e "$d" ] && echo "$d"
  done
}

heads_signature() {
  local d
  present_repos | while read -r d; do
    printf '%s %s\n' "$d" "$(git -C "$d" rev-parse HEAD 2>/dev/null || echo none)"
  done
}

# ── archivos del workspace ───────────────────────────────────

write_graphifyignore() {
  local f=".graphifyignore" line added=0
  if [ ! -f "$f" ]; then
    [ "$DRY" -eq 1 ] && { echo "  (dry-run) crearía $f"; return; }
    : > "$f"
    printf '%s\n' "# Qué NO entra al grafo de graphify. Mismo formato que .gitignore." \
      "# El grafo se construye con --no-gitignore (los repos están ignorados en la raíz), así que las" \
      "# exclusiones de dependencias, builds y secretos tienen que estar acá." >> "$f"
  fi
  for line in \
    "# workspace: tooling y generados" "/bootstrap/" "/scripts/" "/.context/" "/drafts/" "/graphify-out/" "/.claude/" "/.github/" \
    "# dependencias y builds" "node_modules/" "vendor/" ".venv/" "venv/" "__pycache__/" "dist/" "build/" "out/" "target/" "bin/" "obj/" \
    ".next/" ".nuxt/" ".turbo/" ".cache/" "coverage/" ".gradle/" "*.min.js" "*.map" "*.lock" "package-lock.json" "pnpm-lock.yaml" \
    "# secretos: nunca" ".env" ".env.*" "!.env.example" "*.pem" "*.key" "*.p12" "*.pfx" "secrets/" "*secret*.json"; do
    grep -qxF -- "$line" "$f" 2>/dev/null && continue
    [ "$DRY" -eq 1 ] && { added=$((added + 1)); continue; }
    printf '%s\n' "$line" >> "$f"; added=$((added + 1))
  done
  say "  · .graphifyignore: $added líneas agregadas"
}

ensure_gitignore() {
  grep -qE '^/?graphify-out/?$' .gitignore 2>/dev/null && { say "  · .gitignore ya ignora graphify-out/"; return; }
  if [ "$DRY" -eq 1 ]; then echo "  (dry-run) agregaría /graphify-out/ al .gitignore"; return; fi
  printf '\n# ── Grafo de graphify: local, se reconstruye con scripts/graphify-setup.sh ──\n/graphify-out/\n' >> .gitignore
  say "  · .gitignore: agregado /graphify-out/"
}

# Edita un JSON con Node: $1 archivo, $2 acción (add-perms | remove-perms | add-hooks | remove-hooks), $3 binario.
edit_json() {
  [ "$DRY" -eq 1 ] && { echo "  (dry-run) editaría $1 ($2)"; return; }
  command -v node >/dev/null 2>&1 || { warn "Node no está instalado: no pude editar $1"; return; }
  node - "$1" "$2" "${3:-}" <<'JS'
const fs = require('fs')
const [file, action, bin] = process.argv.slice(2)
let data = {}
try { data = JSON.parse(fs.readFileSync(file, 'utf8')) } catch { data = {} }
const ALLOW = ['Bash(graphify query:*)', 'Bash(graphify path:*)', 'Bash(graphify explain:*)', 'Bash(graphify affected:*)',
  'Bash(graphify god-nodes:*)', 'Bash(bash scripts/graphify-setup.sh --refresh:*)']
const DENY = ['Read(graphify-out/graph.json)', 'Read(graphify-out/cache/**)']
const tag = (cmd) => typeof cmd === 'string' && cmd.includes('graphify hook-guard')
const uniq = (a) => [...new Set(a)]
if (action === 'add-perms' || action === 'remove-perms') {
  data.permissions = data.permissions || {}
  const p = data.permissions
  if (action === 'add-perms') {
    p.allow = uniq([...(p.allow || []), ...ALLOW])
    p.deny = uniq([...(p.deny || []), ...DENY])
  } else {
    p.allow = (p.allow || []).filter((x) => !ALLOW.includes(x))
    p.deny = (p.deny || []).filter((x) => !DENY.includes(x))
  }
}
if (action === 'add-hooks' || action === 'remove-hooks') {
  data.hooks = data.hooks || {}
  const pre = (data.hooks.PreToolUse || []).filter((h) => !(h.hooks || []).some((x) => tag(x.command)))
  if (action === 'add-hooks') {
    const q = bin.includes(' ') ? `"${bin}"` : bin
    pre.push({ matcher: 'Bash|Grep', hooks: [{ type: 'command', command: `${q} hook-guard search`, timeout: 10 }] })
    pre.push({ matcher: 'Read|Glob', hooks: [{ type: 'command', command: `${q} hook-guard read`, timeout: 10 }] })
  }
  if (pre.length) data.hooks.PreToolUse = pre
  else delete data.hooks.PreToolUse
  if (!Object.keys(data.hooks).length) delete data.hooks
}
fs.mkdirSync(require('path').dirname(file), { recursive: true })
fs.writeFileSync(file, JSON.stringify(data, null, 2) + '\n')
JS
}

agents_block() {
  cat <<EOF
$BEGIN_MARK
## Grafo de código (graphify)

Además del mapa, hay un grafo de símbolos y relaciones de todos los repos en \`graphify-out/\`: local,
ignorado por git, se construye con \`bash scripts/graphify-setup.sh\`. Si \`graphify\` no está instalado
o no hay grafo, seguí con el mapa: el grafo es un acelerador, no un requisito.

Para preguntas de relaciones, **consultá el grafo antes de grepear**:

| Pregunta | Comando |
|---|---|
| Algo en lenguaje natural | \`graphify query "<pregunta>"\` |
| ¿Qué conecta A con B? | \`graphify path "<A>" "<B>"\` |
| Un símbolo y sus vecinos | \`graphify explain "<símbolo>"\` |
| ¿Qué se ve afectado si cambio X? | \`graphify affected "<símbolo>"\` |
| Los hubs de la arquitectura | \`graphify god-nodes\` |

\`graphify-out/GRAPH_REPORT.md\` solo para una revisión amplia de arquitectura.

El grafo se refresca solo al abrir sesión si algún repo cambió. A mano:
\`bash scripts/graphify-setup.sh --refresh\`. **No uses \`/graphify .\` ni \`graphify update .\` sobre esta
raíz**: sin \`--no-gitignore\`, los repos quedan afuera del grafo.
$END_MARK
EOF
}

write_agents_block() {
  [ -f AGENTS.md ] || { warn "no hay AGENTS.md: salteo la sección del grafo"; return; }
  [ "$DRY" -eq 1 ] && { echo "  (dry-run) escribiría la sección del grafo en AGENTS.md"; return; }
  local block tmp
  block="$(agents_block)"; tmp="$(mktemp)"
  if grep -qF "$BEGIN_MARK" AGENTS.md; then
    awk -v b="$BEGIN_MARK" -v e="$END_MARK" -v block="$block" '
      $0==b {print block; skip=1; next} $0==e {skip=0; next} !skip {print}' AGENTS.md > "$tmp"
  elif grep -q '^## Idioma' AGENTS.md; then
    awk -v block="$block" '/^## Idioma/ && !done {print block; print ""; done=1} {print}' AGENTS.md > "$tmp"
  else
    cat AGENTS.md > "$tmp"; printf '\n%s\n' "$block" >> "$tmp"
  fi
  mv "$tmp" AGENTS.md
  say "  · AGENTS.md: sección del grafo escrita"
}

remove_agents_block() {
  [ -f AGENTS.md ] && grep -qF "$BEGIN_MARK" AGENTS.md || return 0
  local tmp; tmp="$(mktemp)"
  awk -v b="$BEGIN_MARK" -v e="$END_MARK" '$0==b {skip=1; next} $0==e {skip=0; getline; if ($0!="") print; next} !skip {print}' AGENTS.md > "$tmp"
  mv "$tmp" AGENTS.md
  say "  · AGENTS.md: sección del grafo quitada"
}

# ── construir el grafo ───────────────────────────────────────

build_graph() {
  local g="$1" repos n d total
  repos="$(present_repos)"
  [ -n "$repos" ] || warn "no hay repos clonados: el grafo va a quedar casi vacío (corré bash bootstrap/bootstrap.sh)"
  [ "$DRY" -eq 1 ] && { echo "  (dry-run) $g extract . --code-only --no-gitignore && $g cluster-only . --no-label --no-viz"; return 0; }
  "$g" extract . --code-only --no-gitignore || { warn "falló la extracción"; return 1; }
  "$g" cluster-only . --no-label --no-viz >/dev/null 2>&1 || warn "no se pudo generar GRAPH_REPORT.md (el grafo igual se puede consultar)"
  heads_signature > "$HEADS_FILE"

  # Verificación: cada repo clonado tiene que tener nodos en el grafo.
  command -v node >/dev/null 2>&1 || return 0
  total=0
  for d in $repos; do
    n="$(node -e 'const g=JSON.parse(require("fs").readFileSync(process.argv[1],"utf8"));const d=process.argv[2]+"/";console.log((g.nodes||[]).filter(n=>(n.source_file||"").startsWith(d)).length)' "$OUT/graph.json" "$d" 2>/dev/null || echo "?")"
    echo "  · $d: $n nodos"
    [ "$n" = "0" ] && warn "$d no tiene nodos: ¿lenguaje sin soporte, o todo excluido por .graphifyignore?"
    case "$n" in ''|*[!0-9]*) ;; *) total=$((total + n)) ;; esac
  done
  echo "  · total en repos: $total nodos"
}

# ── modos ────────────────────────────────────────────────────

if [ "$MODE" = "stale" ]; then
  # Silencioso salvo que haga algo. Nunca falla: lo llama el hook de inicio.
  G="$(find_graphify)" || exit 0
  [ -f "$OUT/graph.json" ] || exit 0
  [ "$(heads_signature)" = "$(cat "$HEADS_FILE" 2>/dev/null)" ] && exit 0
  # Un lock de más de 30 minutos es de un refresco que murió: se descarta.
  [ -d "$LOCK_DIR" ] && [ -n "$(find "$LOCK_DIR" -maxdepth 0 -mmin +30 2>/dev/null)" ] && rmdir "$LOCK_DIR" 2>/dev/null
  mkdir "$LOCK_DIR" 2>/dev/null || { echo "grafo: ya se está refrescando"; exit 0; }
  if [ "$BACKGROUND" -eq 1 ]; then
    ( build_graph "$G" > "$OUT/.refresh.log" 2>&1; rmdir "$LOCK_DIR" 2>/dev/null ) </dev/null >/dev/null 2>&1 &
    echo "grafo: un repo cambió, refrescando en segundo plano (log: $OUT/.refresh.log)"
  else
    build_graph "$G" > "$OUT/.refresh.log" 2>&1; rmdir "$LOCK_DIR" 2>/dev/null
    echo "grafo: refrescado"
  fi
  exit 0
fi

if [ "$MODE" = "refresh" ]; then
  G="$(find_graphify)" || die "graphify no está instalado: bash scripts/graphify-setup.sh"
  step "Reconstruyendo el grafo"
  build_graph "$G"; exit $?
fi

if [ "$MODE" = "uninstall" ]; then
  step "Quitando la integración de graphify del workspace"
  if [ "$DRY" -eq 0 ]; then
    remove_agents_block
    [ -f .claude/settings.json ] && edit_json .claude/settings.json remove-perms && say "  · .claude/settings.json: permisos quitados"
    [ -f .claude/settings.local.json ] && edit_json .claude/settings.local.json remove-hooks && say "  · .claude/settings.local.json: hooks quitados"
    if command -v claude >/dev/null 2>&1; then claude mcp remove -s local graphify >/dev/null 2>&1 && say "  · MCP local quitado"; fi
    [ "$PURGE" -eq 1 ] && rm -rf "$OUT" && say "  · $OUT/ borrado"
  else
    echo "  (dry-run) quitaría la sección de AGENTS.md, los permisos, los hooks locales y el MCP local$([ "$PURGE" -eq 1 ] && echo " y $OUT/")"
  fi
  say ""
  say "La skill de graphify y el CLI siguen instalados en tu usuario (sirven para otros proyectos)."
  say "Para sacarlos: graphify uninstall  y  uv tool uninstall graphifyy (o pipx uninstall graphifyy)."
  exit 0
fi

# ── instalación completa ─────────────────────────────────────

step "1/7 Requisitos"
PY="$(find_python)" || die "falta Python >= 3.10 (macOS: brew install python@3.12 · Ubuntu: sudo apt install python3 · Windows: winget install Python.Python.3.12)"
say "  · $("$PY" --version 2>&1)"
command -v git >/dev/null 2>&1 || die "falta git"
command -v node >/dev/null 2>&1 || warn "sin Node no puedo editar .claude/settings*.json ni verificar el grafo"

PKG="graphifyy"
[ "$MCP" -eq 1 ] && EXTRAS="${EXTRAS:+$EXTRAS,}mcp"
[ -n "$EXTRAS" ] && PKG="graphifyy[$EXTRAS]"

step "2/7 CLI de graphify (paquete: graphifyy, con doble y)"
G="$(find_graphify || true)"
NEED_INSTALL=0
[ -z "$G" ] && NEED_INSTALL=1
[ "$UPGRADE" -eq 1 ] && NEED_INSTALL=1
[ -n "$EXTRAS" ] && NEED_INSTALL=1
if [ "$NEED_INSTALL" -eq 0 ]; then
  say "  · ya instalado: $("$G" --version 2>/dev/null) ($G)"
else
  if ! command -v uv >/dev/null 2>&1 && ! command -v pipx >/dev/null 2>&1 && [ "$INSTALL_UV" -eq 1 ]; then
    say "  · instalando uv con su instalador oficial (astral.sh)…"
    if [ "$DRY" -eq 1 ]; then echo "  (dry-run) curl -LsSf https://astral.sh/uv/install.sh | sh"
    else curl -LsSf https://astral.sh/uv/install.sh | sh || die "no se pudo instalar uv"; export PATH="$HOME/.local/bin:$PATH"; fi
  fi
  if command -v uv >/dev/null 2>&1; then
    say "  · con uv (entorno aislado)"
    run uv tool install --force "$PKG" || die "falló uv tool install"
    [ "$UPGRADE" -eq 1 ] && run uv tool upgrade graphifyy
    command -v graphify >/dev/null 2>&1 || run uv tool update-shell >/dev/null 2>&1 || true
  elif command -v pipx >/dev/null 2>&1; then
    say "  · con pipx (entorno aislado)"
    run pipx install --force "$PKG" || die "falló pipx install"
    command -v graphify >/dev/null 2>&1 || run pipx ensurepath >/dev/null 2>&1 || true
  else
    warn "no hay uv ni pipx: instalo con pip --user (puede mezclarse con otros Python)."
    warn "Recomendado: re-correr con --install-uv, o instalar uv (brew install uv · winget install astral-sh.uv)."
    run "$PY" -m pip install --user --upgrade "$PKG" || die "falló pip install"
  fi
  [ "$DRY" -eq 1 ] && G="graphify" || G="$(find_graphify)" || die "graphify quedó instalado pero no lo encuentro. Abrí una terminal nueva y re-corré el script."
  say "  · listo: $("$G" --version 2>/dev/null)"
fi
command -v graphify >/dev/null 2>&1 || warn "graphify no está en tu PATH todavía: abrí una terminal nueva (los agentes lo llaman como 'graphify')."

step "3/7 Skill /graphify para tu asistente (a nivel usuario: no toca este repo)"
if [ "$DRY" -eq 1 ]; then echo "  (dry-run) $G install${PLATFORM:+ --platform $PLATFORM}"
elif [ -n "$PLATFORM" ]; then "$G" install --platform "$PLATFORM" >/dev/null && say "  · registrada para $PLATFORM"
else "$G" install >/dev/null && say "  · registrada para Claude Code"; fi

step "4/7 Archivos del workspace"
write_graphifyignore
ensure_gitignore
[ -f .claude/settings.json ] && edit_json .claude/settings.json add-perms && [ "$DRY" -eq 0 ] && say "  · .claude/settings.json: permisos de consulta al grafo y lectura del JSON crudo denegada"
write_agents_block

step "5/7 Construyendo el grafo (code-only: local, sin LLM)"
[ "$DRY" -eq 0 ] && mkdir -p "$OUT"
build_graph "$G" || die "no se pudo construir el grafo"

step "6/7 Hooks PreToolUse (opcional, solo tu máquina)"
if [ "$HOOKS" -eq 1 ]; then
  edit_json .claude/settings.local.json add-hooks "$G"
  say "  · .claude/settings.local.json: hooks que empujan al grafo antes de Grep/Read (ignorado por git)"
else
  say "  · salteado (--hooks para activarlos)"
fi

step "7/7 Servidor MCP del grafo (opcional, solo tu máquina)"
if [ "$MCP" -eq 1 ]; then
  GPY="$(head -1 "$G" 2>/dev/null | sed -n 's/^#!//p' | awk '{print $1}')"
  [ -n "$GPY" ] && [ -x "$GPY" ] || GPY="$PY"
  MCP_CMD="$GPY -m graphify.serve $ROOT/$OUT/graph.json"
  if command -v claude >/dev/null 2>&1; then
    run claude mcp remove -s local graphify >/dev/null 2>&1 || true
    run claude mcp add -s local graphify -- $MCP_CMD && say "  · registrado en Claude Code (scope local de este proyecto)"
  else
    say "  · no encontré el CLI de Claude Code. Registralo a mano:"
    say "      claude mcp add -s local graphify -- $MCP_CMD"
  fi
else
  say "  · salteado (--mcp para activarlo)"
fi

say ""
say "Listo. Consultá con: graphify query \"<pregunta>\"  ·  graphify path \"A\" \"B\"  ·  graphify explain \"X\""
say "Se refresca solo al abrir sesión si un repo cambió. A mano: bash scripts/graphify-setup.sh --refresh"
say "Docs, PDFs e imágenes necesitan el paso semántico (usa tokens): pedíselo a tu asistente con /graphify,"
say "pero apuntando a una carpeta de docs, no a la raíz: los repos están en el .gitignore."
[ "$DRY" -eq 0 ] && say "Commiteá lo que cambió en la raíz: .graphifyignore, .gitignore, AGENTS.md, .claude/settings.json"
