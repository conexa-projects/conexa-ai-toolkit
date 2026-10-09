#!/usr/bin/env bash
# Chequeos del marketplace que no cubre `claude plugin validate`. Los corre el CI y se pueden
# correr a mano antes de un PR: bash scripts/check.sh
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WS_SKILLS="$ROOT/plugins/conexa-workspace/skills"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "› conexa-guardrails: copia vendorizada contra vendor.lock"
bash "$ROOT/plugins/conexa-guardrails/scripts/verify-vendor.sh"

echo "› conexa-guardrails: tests de los validadores de security-audit"
(cd "$ROOT/plugins/conexa-guardrails/skills/security-audit" && node --test 2>&1 | tail -n 8)

echo "› conexa-workspace: sintaxis de scripts"
python3 -m py_compile "$WS_SKILLS/init-workspace/scripts/scaffold.py" "$WS_SKILLS/audit-workspace/scripts/audit.py"
for f in "$WS_SKILLS"/init-workspace/assets/template/scripts/*.mjs; do node --check "$f"; done
for f in "$WS_SKILLS"/init-workspace/assets/template/scripts/*.sh "$WS_SKILLS"/init-workspace/assets/template/bootstrap/*.sh; do bash -n "$f"; done

echo "› conexa-workspace: workspace de prueba (scaffold → validate → audit)"
WS="$TMP/ws"
python3 "$WS_SKILLS/init-workspace/scripts/scaffold.py" --target "$WS" --name smoke --description "workspace de prueba del CI" --lang es-en >/dev/null
(
  cd "$WS"
  git init -q
  git add $(git ls-files -o --exclude-standard)
  node scripts/validate.mjs
)
python3 "$WS_SKILLS/audit-workspace/scripts/audit.py" "$WS" --json > "$TMP/audit.json"
python3 - "$TMP/audit.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
bad = [f for f in d["hallazgos"] if f["sev"] in ("critico", "importante")]
for f in bad:
    print(f"  {f['sev']}: {f['title']} — {f['detail']}")
print(f"  audit-workspace: {d['puntaje']}/100 ({d['nivel']})")
sys.exit(1 if bad else 0)
PY

echo "› conexa-workspace: el validador detecta un informe de seguridad versionado"
mkdir -p "$WS/docs" && echo '[]' > "$WS/docs/coverage-ledger.json"
(cd "$WS" && git add docs/coverage-ledger.json && ! node scripts/validate.mjs >/dev/null 2>&1)

echo "✓ todo OK"
