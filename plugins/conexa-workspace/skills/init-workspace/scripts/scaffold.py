#!/usr/bin/env python3
"""Renderiza la plantilla de workspace en una carpeta destino.

Nunca pisa archivos existentes: los saltea y los reporta como "existe (no se tocó)".
Sin dependencias: solo la librería estándar de Python 3.8+.

Uso:
  scaffold.py --target DIR --name NOMBRE --description "una línea"
              [--lang es-en|es|en] [--repo "url[|carpeta[|rama]]"]... [--no-ci] [--dry-run]
"""
import argparse
import datetime
import os
import re
import stat
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "template")

# Nombres guardados sin punto en la plantilla, para que ninguna herramienta de empaquetado los omita.
RENAMES = {"dot-claude": ".claude", "dot-github": ".github", "dot-gitignore": ".gitignore"}
EXECUTABLE = {"bootstrap/bootstrap.sh", "scripts/session-start.sh", "scripts/map.mjs", "scripts/validate.mjs", "scripts/graphify-setup.sh"}
SAFE_DIR = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
RESERVED = {"bootstrap", "scripts", "knowledge", "drafts", ".claude", ".github", ".context", "node_modules"}

LANG = {
    "es-en": {
        "summary": "**Español** para el chat y la documentación del workspace. **Inglés, sin excepción**, "
                   "para commits, PRs, issues, código, identificadores y comentarios en el código.",
        "table": "| Chat con el usuario: explicaciones, planes, preguntas | Español |\n"
                 "| Documentación del workspace: README, AGENTS.md, `knowledge/` | Español |\n"
                 "| Mensajes de commit, títulos y descripciones de PR, issues | **Inglés** |\n"
                 "| Código, identificadores, comentarios en el código | **Inglés** |",
        "why": "El historial y los artefactos de ingeniería los lee gente de afuera del equipo; "
               "la documentación la escribe y la lee el equipo.",
    },
    "es": {
        "summary": "**Todo en español**: chat, documentación, commits y PRs. El código sigue la convención "
                   "de cada repo (identificadores y comentarios en el idioma que ya usa).",
        "table": "| Chat, documentación, `knowledge/` | Español |\n"
                 "| Mensajes de commit, PRs, issues | Español |\n"
                 "| Identificadores y comentarios en el código | El que ya usa el repo |",
        "why": "El equipo y el cliente trabajan en español; el código conserva la convención existente "
               "para no mezclar idiomas dentro de un mismo archivo.",
    },
    "en": {
        "summary": "**English** for everything versioned: docs, commits, PRs, code and comments. "
                   "Chat follows the user's language.",
        "table": "| Chat con el usuario | El idioma del usuario |\n"
                 "| Documentación, `knowledge/`, commits, PRs, issues | **Inglés** |\n"
                 "| Código, identificadores, comentarios | **Inglés** |",
        "why": "Todo lo versionado lo lee un equipo distribuido que no comparte un idioma.",
    },
}


def parse_repo(spec):
    parts = [p.strip() for p in spec.split("|")]
    url = parts[0]
    if not url:
        raise ValueError(f"repo sin URL: {spec!r}")
    folder = parts[1] if len(parts) > 1 and parts[1] else re.sub(r"\.git$", "", url.rstrip("/").split("/")[-1].split(":")[-1])
    branch = parts[2] if len(parts) > 2 else ""
    if not SAFE_DIR.match(folder) or folder in RESERVED:
        raise ValueError(f"nombre de carpeta inválido o reservado: {folder!r} (usá url|carpeta)")
    return folder, url, branch


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--description", required=True)
    ap.add_argument("--lang", choices=sorted(LANG), default="es-en")
    ap.add_argument("--repo", action="append", default=[])
    ap.add_argument("--no-ci", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    try:
        repos = [parse_repo(r) for r in args.repo]
    except ValueError as e:
        sys.exit(f"✗ {e}")
    folders = [r[0] for r in repos]
    if len(set(folders)) != len(folders):
        sys.exit("✗ hay dos repos con la misma carpeta; usá url|carpeta para diferenciarlos")

    lang = LANG[args.lang]
    tsv = "\n".join(f"{f}\t{u}\t{b}".rstrip("\t") for f, u, b in repos)
    ignore = "\n".join(f"/{f}" for f in folders)
    rows = "\n".join(f"| `{f}/` | [a completar] | [a completar] | `{f}-expert` |" for f in folders) \
        or "| _(sin repos todavía — sumalos con `/agregar-repo`)_ | | | |"
    values = {
        "NAME": args.name,
        "DESCRIPTION": args.description,
        "DATE": datetime.date.today().isoformat(),
        "LANG_SUMMARY": lang["summary"],
        "LANG_TABLE": lang["table"],
        "LANG_WHY": lang["why"],
        "REPOS_TSV": tsv,
        "REPOS_GITIGNORE": ignore,
        "REPOS_TABLE": rows,
    }

    target = os.path.abspath(args.target)
    created, skipped = [], []
    for base, dirs, files in os.walk(TEMPLATE):
        dirs.sort()
        rel_base = os.path.relpath(base, TEMPLATE)
        if args.no_ci and rel_base.split(os.sep)[0] == "dot-github":
            continue
        for name in sorted(files):
            rel_src = os.path.normpath(os.path.join(rel_base, name))
            parts = rel_src.split(os.sep)
            if parts[-1].endswith(".tmpl"):
                parts[-1] = parts[-1][: -len(".tmpl")]
            parts = [RENAMES.get(p, p) for p in parts]
            rel_dst = "/".join(parts)
            dst = os.path.join(target, *parts)
            if os.path.lexists(dst):
                skipped.append(rel_dst)
                continue
            with open(os.path.join(base, name), encoding="utf-8") as fh:
                text = fh.read()
            for key, val in values.items():
                text = text.replace("{{" + key + "}}", val)
            leftover = re.findall(r"\{\{[A-Z_]+\}\}", text)
            if leftover:
                sys.exit(f"✗ placeholder sin valor en {rel_dst}: {leftover}")
            created.append(rel_dst)
            if args.dry_run:
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            if rel_dst in EXECUTABLE:
                os.chmod(dst, os.stat(dst).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    tag = " (dry-run: no se escribió nada)" if args.dry_run else ""
    print(f"Destino: {target}{tag}")
    for p in created:
        print(f"  creado               {p}")
    for p in skipped:
        print(f"  existe (no se tocó)  {p}")
    print(f"\n{len(created)} creados · {len(skipped)} existentes sin tocar · {len(repos)} repos en el manifest")
    if skipped:
        print("Los existentes se fusionan a mano: ver references/estructura.md → 'Adaptar un workspace existente'.")


if __name__ == "__main__":
    main()
