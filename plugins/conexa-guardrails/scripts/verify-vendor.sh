#!/usr/bin/env bash
# Verifica que skills/security-audit sea exactamente la versión de upstream registrada en
# vendor.lock, más los agregados de Conexa (CONEXA.md, LICENSE-cloudflare y el bloque conexa del
# SKILL.md). Falla si cambió un archivo de upstream o si apareció uno que no está en el lock.
#
# Uso: bash scripts/verify-vendor.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILL="$ROOT/skills/security-audit"
LOCK="$ROOT/vendor.lock"
ALLOWED_EXTRA=("./CONEXA.md" "./LICENSE-cloudflare")

if command -v sha256sum >/dev/null 2>&1; then
  hash() { sha256sum | cut -d' ' -f1; }
else
  hash() { shasum -a 256 | cut -d' ' -f1; }
fi

fail=0
cd "$SKILL"

# 1. El bloque conexa tiene que existir exactamente una vez
if [ "$(grep -c '^<!-- conexa:begin -->$' SKILL.md)" != "1" ] || [ "$(grep -c '^<!-- conexa:end -->$' SKILL.md)" != "1" ]; then
  echo "FALLA  SKILL.md: falta el bloque conexa o está duplicado"; fail=1
fi

# 2. Cada archivo del lock coincide con upstream
while read -r expected file; do
  case "$expected" in "#"*|"") continue ;; esac
  if [ ! -f "$file" ]; then echo "FALLA  falta $file"; fail=1; continue; fi
  if [ "$file" = "./SKILL.md" ]; then
    # Saca el bloque conexa (y la línea en blanco que le sigue) para comparar contra upstream
    actual="$(python3 -I -c 'import re,sys
s=open("SKILL.md",encoding="utf-8").read()
sys.stdout.write(re.sub(r"<!-- conexa:begin -->\n.*?<!-- conexa:end -->\n\n","",s,count=1,flags=re.S))' | hash)"
  else
    actual="$(hash < "$file")"
  fi
  if [ "$actual" != "$expected" ]; then echo "FALLA  $file cambió respecto de upstream"; fail=1; fi
done < "$LOCK"

# 3. No hay archivos nuevos fuera del lock
while IFS= read -r f; do
  grep -q "  $f\$" "$LOCK" && continue
  for a in "${ALLOWED_EXTRA[@]}"; do [ "$f" = "$a" ] && continue 2; done
  echo "FALLA  archivo no registrado: $f"; fail=1
done < <(find . -type f | sort)

if [ "$fail" = 0 ]; then
  echo "OK  security-audit coincide con $(grep '^# commit:' "$LOCK" | cut -d' ' -f3) + agregados de Conexa"
fi
exit "$fail"
