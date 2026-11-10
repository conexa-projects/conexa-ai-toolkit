#!/usr/bin/env python3
"""Renderiza la plantilla de workspace en una carpeta destino, o la actualiza.

Crear/adaptar: nunca pisa archivos existentes; los saltea y los reporta como "existe (no se tocó)".
Actualizar (--upgrade): pisa solo los archivos que nadie modificó desde que se generaron. Lo sabe por
el sello bootstrap/template.lock.json (hash de cada archivo generado) y, en workspaces sin sello, por
assets/template-history.json (hashes de las versiones publicadas). Lo modificado a mano no se toca.
Sin dependencias: solo la librería estándar de Python 3.8+.

Uso:
  scaffold.py --target DIR --name NOMBRE --description "una línea"
              [--lang es-en|es|en] [--repo "url[|carpeta[|rama]]"]... [--no-ci] [--dry-run]
  scaffold.py --target DIR --upgrade [--dry-run]
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import stat
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "template")
HISTORY = os.path.join(HERE, "..", "assets", "template-history.json")
PLUGIN_JSON = os.path.join(HERE, "..", "..", "..", ".claude-plugin", "plugin.json")
LOCK = "bootstrap/template.lock.json"

# Nombres guardados sin punto en la plantilla, para que ninguna herramienta de empaquetado los omita.
RENAMES = {"dot-claude": ".claude", "dot-github": ".github", "dot-gitignore": ".gitignore"}
EXECUTABLE = {"bootstrap/bootstrap.sh", "scripts/session-start.sh", "scripts/map.mjs", "scripts/validate.mjs", "scripts/graphify-setup.sh"}
SAFE_DIR = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
RESERVED = {"bootstrap", "scripts", "knowledge", "drafts", ".claude", ".github", ".context", "node_modules"}
PLACEHOLDER = re.compile(r"\{\{[A-Z_]+\}\}")
# Archivos que el equipo edita por diseño: se crean si faltan, pero --upgrade nunca los pisa ni los
# reporta como modificados. Mantener igual que USER_OWNED de audit-workspace/scripts/audit.py.
USER_OWNED = {"AGENTS.md", "README.md", ".gitignore", "bootstrap/repos.tsv", "knowledge/README.md",
              "knowledge/decisiones.md", "knowledge/procesos/idioma.md", "drafts/.gitkeep"}

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


def template_version():
    try:
        with open(PLUGIN_JSON, encoding="utf-8") as fh:
            return json.load(fh).get("version") or "desconocida"
    except (OSError, ValueError):
        return "desconocida"


def dst_of(rel_src):
    """Ruta destino de un archivo de la plantilla: sin .tmpl y con los dot-* renombrados."""
    parts = rel_src.replace(os.sep, "/").split("/")
    if parts[-1].endswith(".tmpl"):
        parts[-1] = parts[-1][: -len(".tmpl")]
    return "/".join(RENAMES.get(p, p) for p in parts)


def template_files(ci=True):
    """(ruta absoluta en la plantilla, ruta destino relativa), en orden estable."""
    out = []
    for base, dirs, files in os.walk(TEMPLATE):
        dirs.sort()
        rel_base = os.path.relpath(base, TEMPLATE)
        if not ci and rel_base.split(os.sep)[0] == "dot-github":
            continue
        for name in sorted(files):
            out.append((os.path.join(base, name), dst_of(os.path.normpath(os.path.join(rel_base, name)))))
    return out


def build_values(name, description, lang_key, repos):
    lang = LANG[lang_key]
    folders = [r[0] for r in repos]
    values = {
        "DATE": datetime.date.today().isoformat(),
        "LANG_SUMMARY": lang["summary"],
        "LANG_TABLE": lang["table"],
        "LANG_WHY": lang["why"],
        "REPOS_TSV": "\n".join(f"{f}\t{u}\t{b}".rstrip("\t") for f, u, b in repos),
        "REPOS_GITIGNORE": "\n".join(f"/{f}" for f in folders),
        "REPOS_TABLE": "\n".join(f"| `{f}/` | [a completar] | [a completar] | [a completar] |" for f in folders)
        or "| _(sin repos todavía — sumalos con `/agregar-repo`)_ | | | |",
    }
    if name:
        values["NAME"] = name
    if description:
        values["DESCRIPTION"] = description
    return values


def render(src, values):
    """Devuelve (texto, placeholders que quedaron sin valor)."""
    with open(src, encoding="utf-8") as fh:
        text = fh.read()
    for key, val in values.items():
        text = text.replace("{{" + key + "}}", val)
    return text, PLACEHOLDER.findall(text)


def sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha_file(path):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


def write_file(dst, rel_dst, text):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    if rel_dst in EXECUTABLE:
        os.chmod(dst, os.stat(dst).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_lock(target, lock):
    lock["files"] = dict(sorted(lock.get("files", {}).items()))
    path = os.path.join(target, *LOCK.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(lock, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def read_manifest(target):
    """Repos del manifest existente, para no perderlos si --upgrade tiene que recrear un archivo."""
    repos = []
    try:
        with open(os.path.join(target, "bootstrap", "repos.tsv"), encoding="utf-8") as fh:
            for line in fh.read().replace("\r", "").split("\n"):
                if not line.strip() or line.strip().startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 2 and parts[0].strip():
                    repos.append((parts[0].strip(), parts[1].strip(), parts[2].strip() if len(parts) > 2 else ""))
    except OSError:
        pass
    return repos


def upgrade(args, target):
    lock = load_json(os.path.join(target, *LOCK.split("/")))
    had_lock = bool(lock)
    vals = lock.get("values", {})
    name, description = args.name or vals.get("name"), args.description or vals.get("description")
    lang_key = args.lang or vals.get("lang") or "es-en"
    ci = False if args.no_ci else vals.get("ci", os.path.isdir(os.path.join(target, ".github")))
    values = build_values(name, description, lang_key, read_manifest(target))
    history = load_json(HISTORY)
    locked = lock.get("files", {})
    files = dict(locked)
    created, updated, modified, omitted, current, own = [], [], [], [], 0, 0
    for src, rel_dst in template_files(ci):
        dst = os.path.join(target, *rel_dst.split("/"))
        exists = os.path.lexists(dst)
        if rel_dst in USER_OWNED and exists:
            own += 1
            continue
        text, missing = render(src, values)
        if missing:
            omitted.append(f"{rel_dst} (falta {', '.join(sorted(set(missing)))}: pasá --name y --description)")
            continue
        new = sha_text(text)
        if not exists:
            created.append(rel_dst)
        else:
            cur = sha_file(dst)
            if cur == new:
                current += 1
                if rel_dst not in USER_OWNED:
                    files[rel_dst] = new
                continue
            if cur is not None and (cur == locked.get(rel_dst) or cur in history.get(rel_dst, [])):
                updated.append(rel_dst)
            else:
                modified.append(rel_dst)
                continue
        if not args.dry_run:
            write_file(dst, rel_dst, text)
        if rel_dst not in USER_OWNED:
            files[rel_dst] = new

    old_version = lock.get("template_version", "sin sello")
    if not args.dry_run:
        write_lock(target, {"template_version": template_version(),
                            "values": {"name": name, "description": description, "lang": lang_key, "ci": bool(ci)},
                            "files": files})
    tag = " (dry-run: no se escribió nada)" if args.dry_run else ""
    print(f"Destino: {target}{tag}")
    print(f"Plantilla: {old_version} → {template_version()}")
    for label, items in (("creado", created), ("actualizado", updated), ("modificado a mano (no se tocó)", modified), ("omitido", omitted)):
        for p in items:
            print(f"  {label:<31}{p}")
    print(f"\n{len(created)} creados · {len(updated)} actualizados · {len(modified)} modificados a mano · "
          f"{current} al día · {own} propios del workspace sin tocar")
    if not had_lock:
        print("El workspace no tenía sello: se actualizó solo lo que coincide con una versión publicada de la plantilla.")
    if modified:
        print(f"Los modificados a mano se fusionan con diff contra la plantilla: {os.path.normpath(TEMPLATE)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", required=True)
    ap.add_argument("--name")
    ap.add_argument("--description")
    ap.add_argument("--lang", choices=sorted(LANG))
    ap.add_argument("--repo", action="append", default=[])
    ap.add_argument("--no-ci", action="store_true")
    ap.add_argument("--upgrade", action="store_true", help="actualiza los archivos de la plantilla que nadie modificó")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    target = os.path.abspath(args.target)
    if args.upgrade:
        if args.repo:
            ap.error("--upgrade no suma repos: usá bootstrap/bootstrap.sh --add")
        if not os.path.isdir(target):
            sys.exit(f"✗ no existe {target}")
        return upgrade(args, target)
    if not args.name or not args.description:
        ap.error("--name y --description son obligatorios (salvo con --upgrade)")

    try:
        repos = [parse_repo(r) for r in args.repo]
    except ValueError as e:
        sys.exit(f"✗ {e}")
    folders = [r[0] for r in repos]
    if len(set(folders)) != len(folders):
        sys.exit("✗ hay dos repos con la misma carpeta; usá url|carpeta para diferenciarlos")

    lang_key = args.lang or "es-en"
    values = build_values(args.name, args.description, lang_key, repos)
    lock_path = os.path.join(target, *LOCK.split("/"))
    lock = load_json(lock_path)
    files = dict(lock.get("files", {}))
    created, skipped = [], []
    for src, rel_dst in template_files(ci=not args.no_ci):
        dst = os.path.join(target, *rel_dst.split("/"))
        if os.path.lexists(dst):
            skipped.append(rel_dst)
            continue
        text, leftover = render(src, values)
        if leftover:
            sys.exit(f"✗ placeholder sin valor en {rel_dst}: {leftover}")
        created.append(rel_dst)
        if rel_dst not in USER_OWNED:
            files[rel_dst] = sha_text(text)
        if not args.dry_run:
            write_file(dst, rel_dst, text)
    # El sello: qué versión de la plantilla generó cada archivo. Lo usan --upgrade y audit-workspace.
    if not args.dry_run and created:
        write_lock(target, {"template_version": template_version(),
                            "values": lock.get("values") or {"name": args.name, "description": args.description, "lang": lang_key, "ci": not args.no_ci},
                            "files": files})
    if created and not lock:
        created.append(LOCK)

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
