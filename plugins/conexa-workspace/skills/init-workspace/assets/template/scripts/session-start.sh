#!/usr/bin/env bash
# Hook de SessionStart de Claude Code. Lo que imprime entra al contexto de la sesión: corto.
# Nunca falla ni bloquea: sin Node o sin repos, avisa y sale con 0.
cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null || exit 0

missing=""
if [ -f bootstrap/repos.tsv ]; then
  while IFS="$(printf '\t')" read -r dir _url _branch; do
    [ -n "$dir" ] || continue
    [ -e "$dir" ] || missing="$missing $dir"
  done <<LIST
$(tr -d '\r' < bootstrap/repos.tsv | awk -F'\t' '!/^[[:space:]]*#/ && NF>=2 && $1!="" {print}')
LIST
fi

if command -v node >/dev/null 2>&1; then
  summary="$(node scripts/map.mjs --quiet 2>/dev/null || echo 'mapa: no se pudo generar (corré node scripts/map.mjs)')"
else
  summary="mapa: Node no está instalado; el mapa de .context/ no se actualiza"
fi

echo "Workspace: leé .context/INDEX.md antes de explorar los repos. ${summary}"

# Grafo de graphify (opcional): si existe y algún repo cambió, se refresca en segundo plano.
if [ -f graphify-out/graph.json ] && [ -f scripts/graphify-setup.sh ]; then
  bash scripts/graphify-setup.sh --refresh-if-stale --background 2>/dev/null || true
fi
[ -n "$missing" ] && echo "Repos sin clonar:${missing} — bash bootstrap/bootstrap.sh"
exit 0
