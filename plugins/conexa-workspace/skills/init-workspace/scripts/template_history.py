#!/usr/bin/env python3
"""Mantiene assets/template-history.json: los hashes de cada versión publicada de la plantilla.

`scaffold.py --upgrade` y audit-workspace lo usan para reconocer, en un workspace sin sello, un archivo
que es una versión vieja de la plantilla sin tocar (se puede actualizar) y distinguirlo de uno
modificado a mano. Solo entran los archivos sin placeholders y que no son propios del workspace.

Herramienta de mantenimiento del plugin: correla antes de publicar una versión nueva de la plantilla.
  template_history.py           # suma los hashes del historial de git y del working tree
  template_history.py --check   # falla si la plantilla actual tiene un hash que no está registrado
"""
import hashlib
import json
import os
import subprocess
import sys

import scaffold as sc


def git(cwd, *args):
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True)
    return out.stdout if out.returncode == 0 else b""


def tracked(rel_dst, data):
    return rel_dst not in sc.USER_OWNED and not sc.PLACEHOLDER.search(data.decode("utf-8", errors="replace"))


def main():
    check = "--check" in sys.argv[1:]
    history = {k: set(v) for k, v in sc.load_json(sc.HISTORY).items()}
    before = {k: set(v) for k, v in history.items()}
    template = os.path.realpath(sc.TEMPLATE)

    for src, rel_dst in sc.template_files():
        with open(src, "rb") as fh:
            data = fh.read()
        if tracked(rel_dst, data):
            history.setdefault(rel_dst, set()).add(hashlib.sha256(data).hexdigest())
    if check:
        missing = sorted(k for k, v in history.items() if v - before.get(k, set()))
        if missing:
            sys.exit("✗ template-history.json no tiene la versión actual de: " + ", ".join(missing)
                     + "\n  Corré: python3 plugins/conexa-workspace/skills/init-workspace/scripts/template_history.py")
        print(f"✓ template-history.json al día ({len(history)} archivos)")
        return

    top = git(template, "rev-parse", "--show-toplevel").decode().strip()
    if top:
        prefix = os.path.relpath(template, top).replace(os.sep, "/") + "/"
        for commit in git(top, "log", "--format=%H", "--", prefix).decode().split():
            for path in git(top, "ls-tree", "-r", "--name-only", commit, "--", prefix).decode().splitlines():
                data = git(top, "cat-file", "blob", f"{commit}:{path}")
                rel_dst = sc.dst_of(path[len(prefix):])
                if data and tracked(rel_dst, data):
                    history.setdefault(rel_dst, set()).add(hashlib.sha256(data).hexdigest())
    with open(sc.HISTORY, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({k: sorted(v) for k, v in sorted(history.items())}, fh, indent=2)
        fh.write("\n")
    print(f"template-history.json: {len(history)} archivos, {sum(len(v) for v in history.values())} versiones")


if __name__ == "__main__":
    main()
