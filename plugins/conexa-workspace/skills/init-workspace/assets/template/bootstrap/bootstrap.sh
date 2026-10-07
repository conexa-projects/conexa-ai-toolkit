#!/usr/bin/env bash
#
# bootstrap.sh — pone en su lugar los repos de trabajo listados en bootstrap/repos.tsv.
#
# Idempotente y aditivo: lo que ya está no se toca. Reusa clones existentes (--link, detectados por
# el remote origin) en vez de volver a bajarlos. Tolerante a fallos: si un repo no se puede clonar,
# avisa y sigue con el resto. Mantiene el bloque de repos del .gitignore de la raíz.
#
# Uso:
#   bash bootstrap/bootstrap.sh                          # clona lo que falte (SSH)
#   bash bootstrap/bootstrap.sh --https                  # clona por HTTPS
#   bash bootstrap/bootstrap.sh --link ~/code            # enlaza clones que ya tengas ahí (repetible)
#   bash bootstrap/bootstrap.sh --update                 # fetch + pull --ff-only de los repos limpios
#   bash bootstrap/bootstrap.sh --add <url> [--dir X] [--branch Y]   # suma un repo al manifest
#   bash bootstrap/bootstrap.sh --dry-run                # muestra qué haría, sin tocar nada
#
# Compatible con bash 3.2 (macOS) y Git Bash. Nunca hace reset, clean ni push.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
MANIFEST="$HERE/repos.tsv"
GITIGNORE="$ROOT/.gitignore"
BEGIN_MARK="# >>> repos (bootstrap/bootstrap.sh mantiene este bloque; no editar a mano) >>>"
END_MARK="# <<< repos <<<"

USE_HTTPS=0; DRY=0; UPDATE=0
LINK_DIRS=()
ADD_URL=""; ADD_DIR=""; ADD_BRANCH=""

usage() { awk 'NR>=3 && /^#/ {sub(/^# ?/,""); print; next} NR>=3 {exit}' "${BASH_SOURCE[0]}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --https)   USE_HTTPS=1; shift ;;
    --link)    LINK_DIRS+=("${2:?--link necesita un directorio}"); shift 2 ;;
    --update)  UPDATE=1; shift ;;
    --dry-run) DRY=1; shift ;;
    --add)     ADD_URL="${2:?--add necesita una URL}"; shift 2 ;;
    --dir)     ADD_DIR="${2:?--dir necesita un nombre}"; shift 2 ;;
    --branch)  ADD_BRANCH="${2:?--branch necesita una rama}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Opción desconocida: $1" >&2; usage >&2; exit 2 ;;
  esac
done

command -v git >/dev/null 2>&1 || { echo "✗ git no está instalado" >&2; exit 1; }
[ -f "$MANIFEST" ] || { echo "✗ no encuentro $MANIFEST" >&2; exit 1; }

# URL comparable: sin protocolo, sin usuario, sin .git, en minúsculas. git@host:org/r == https://host/org/r
norm_url() {
  printf '%s' "$1" | sed -E 's#/+$##; s#\.git$##; s#^[a-z+]+://##; s#^[^@/]+@##; s#^([^/:]+):#\1/#' | tr '[:upper:]' '[:lower:]'
}
to_https() { printf '%s' "$1" | sed -E 's#^git@([^:]+):#https://\1/#; s#^ssh://git@([^/]+)/#https://\1/#'; }

# Lista "carpeta<TAB>url<TAB>rama" del manifest, sin comentarios, líneas vacías ni \r.
entries() { tr -d '\r' < "$MANIFEST" | awk -F'\t' '!/^[[:space:]]*#/ && NF>=2 && $1!="" {print $1"\t"$2"\t"$3}'; }

# ── --add: sumar un repo al manifest ───────────────────────────
if [ -n "$ADD_URL" ]; then
  if [ -z "$ADD_DIR" ]; then
    ADD_DIR="$(basename "${ADD_URL%/}")"; ADD_DIR="${ADD_DIR##*:}"; ADD_DIR="${ADD_DIR%.git}"
  fi
  case "$ADD_DIR" in
    bootstrap|scripts|knowledge|drafts|.claude|.github|.context|node_modules|"")
      echo "✗ '$ADD_DIR' es una carpeta reservada del workspace; usá --dir" >&2; exit 2 ;;
  esac
  printf '%s' "$ADD_DIR" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9._-]*$' || { echo "✗ nombre de carpeta inválido: $ADD_DIR" >&2; exit 2; }
  new_norm="$(norm_url "$ADD_URL")"
  while IFS="$(printf '\t')" read -r d u _b; do
    [ "$d" = "$ADD_DIR" ] && { echo "✗ ya hay un repo con la carpeta '$d' en el manifest" >&2; exit 2; }
    [ "$(norm_url "$u")" = "$new_norm" ] && { echo "✗ ese repo ya está en el manifest como '$d'" >&2; exit 2; }
  done <<EOF
$(entries)
EOF
  if [ "$DRY" -eq 1 ]; then
    echo "· (dry-run) sumaría al manifest: $ADD_DIR  $ADD_URL  ${ADD_BRANCH:-(rama default)}"
  else
    [ -n "$(tail -c1 "$MANIFEST")" ] && printf '\n' >> "$MANIFEST"
    if [ -n "$ADD_BRANCH" ]; then printf '%s\t%s\t%s\n' "$ADD_DIR" "$ADD_URL" "$ADD_BRANCH" >> "$MANIFEST"
    else printf '%s\t%s\n' "$ADD_DIR" "$ADD_URL" >> "$MANIFEST"; fi
    echo "· sumado al manifest: $ADD_DIR"
  fi
fi

# Imprime la ruta de un clon existente bajo los --link cuyo origin sea la URL dada.
find_existing_clone() {
  local want candidate origin
  want="$(norm_url "$1")"
  for dir in ${LINK_DIRS[@]+"${LINK_DIRS[@]}"}; do
    [ -d "$dir" ] || continue
    for candidate in "$dir"/*/; do
      [ -e "${candidate}.git" ] || continue
      origin="$(git -C "$candidate" remote get-url origin 2>/dev/null || true)"
      [ -n "$origin" ] || continue
      if [ "$(norm_url "$origin")" = "$want" ]; then
        (cd "$candidate" && pwd -P)
        return 0
      fi
    done
  done
  return 1
}

# Reescribe el bloque de repos del .gitignore con las carpetas del manifest.
sync_gitignore() {
  local block tmp
  block="$(entries | awk -F'\t' '{print "/"$1}')"
  [ -f "$GITIGNORE" ] || : > "$GITIGNORE"
  if ! grep -qF "$BEGIN_MARK" "$GITIGNORE"; then
    printf '\n%s\n%s\n' "$BEGIN_MARK" "$END_MARK" >> "$GITIGNORE"
  fi
  tmp="$(mktemp)"
  awk -v b="$BEGIN_MARK" -v e="$END_MARK" -v block="$block" '
    $0==b {print; if (block!="") print block; skip=1; next}
    $0==e {skip=0}
    !skip {print}
  ' "$GITIGNORE" > "$tmp"
  if cmp -s "$tmp" "$GITIGNORE"; then rm -f "$tmp"; else mv "$tmp" "$GITIGNORE"; echo "· .gitignore: bloque de repos actualizado"; fi
}

cloned=0; linked=0; present=0; updated=0; failed=0; failed_list=""

# El manifest entra por el descriptor 3 para que git (prompts de credenciales) no consuma el stdin del loop.
while IFS="$(printf '\t')" read -r dir url branch <&3; do
  [ -n "$dir" ] || continue
  target="$ROOT/$dir"
  [ "$USE_HTTPS" -eq 1 ] && url="$(to_https "$url")"

  if [ -e "$target" ] || [ -L "$target" ]; then
    present=$((present + 1))
    if [ "$UPDATE" -eq 1 ] && [ -e "$target/.git" ]; then
      if [ -n "$(git -C "$target" status --porcelain 2>/dev/null)" ]; then
        echo "· $dir — tiene cambios sin commitear, no se actualiza"
      elif ! git -C "$target" rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1; then
        echo "· $dir — la rama actual no sigue a ninguna remota, no se actualiza"
      elif [ "$DRY" -eq 1 ]; then
        echo "· $dir — (dry-run) haría fetch + pull --ff-only"
      else
        before="$(git -C "$target" rev-parse HEAD)"
        if git -C "$target" fetch --prune -q && git -C "$target" merge --ff-only -q '@{u}' 2>/dev/null; then
          if [ "$(git -C "$target" rev-parse HEAD)" = "$before" ]; then echo "· $dir — al día"
          else
            echo "· $dir — actualizado a $(git -C "$target" log -1 --format='%h %s' | cut -c1-70)"
            updated=$((updated + 1))
          fi
        else
          echo "· $dir — no se pudo actualizar con fast-forward (¿divergió?), se deja como está"
        fi
      fi
    else
      echo "· $dir — ya estaba, no se toca"
    fi
    continue
  fi

  if existing="$(find_existing_clone "$url")"; then
    if [ "$DRY" -eq 1 ]; then echo "· $dir — (dry-run) enlazaría a $existing"
    else ln -s "$existing" "$target" && echo "· $dir — enlazado a $existing"; fi
    linked=$((linked + 1))
    continue
  fi

  if [ "$DRY" -eq 1 ]; then
    echo "· $dir — (dry-run) clonaría $url${branch:+ @ $branch}"
    cloned=$((cloned + 1))
    continue
  fi

  echo "· $dir — clonando $url${branch:+ @ $branch}…"
  ok=0
  if [ -n "$branch" ]; then
    if git clone -q --branch "$branch" "$url" "$target"; then ok=1
    elif [ ! -e "$target" ] && git clone -q "$url" "$target"; then
      ok=1; echo "  ⚠ la rama '$branch' no existe en el remote: quedó en la default. Corregí bootstrap/repos.tsv"
    fi
  elif git clone -q "$url" "$target"; then ok=1; fi

  if [ "$ok" -eq 1 ]; then cloned=$((cloned + 1))
  else
    failed=$((failed + 1)); failed_list="$failed_list $dir"
    echo "  ✗ no se pudo clonar $dir (¿acceso, red, SSH? probá --https). Sigo con el resto."
    # Un repo recién sumado con --add que no se pudo clonar no queda en el manifest.
    if [ -n "$ADD_URL" ] && [ "$dir" = "$ADD_DIR" ]; then
      tmp="$(mktemp)"
      awk -F'\t' -v d="$dir" '$1!=d' "$MANIFEST" > "$tmp" && mv "$tmp" "$MANIFEST"
      echo "  · se sacó $dir del manifest: corregí la URL o el acceso y volvé a correr --add"
    fi
  fi
done 3<<EOF
$(entries)
EOF

[ "$DRY" -eq 1 ] || sync_gitignore

echo
verb="Listo"; [ "$DRY" -eq 1 ] && verb="Dry-run"
echo "$verb: clonados $cloned · enlazados $linked · ya estaban $present · actualizados $updated · fallaron $failed"
[ "$failed" -gt 0 ] && echo "Fallaron:$failed_list"
if [ "$DRY" -eq 0 ]; then
  echo
  echo "Siguiente:"
  echo "  1. En cada repo, su setup propio (.env.example, dependencias): está en su README."
  echo "  2. node scripts/map.mjs   # regenera el mapa de contexto (.context/)"
fi
[ "$failed" -eq 0 ]
