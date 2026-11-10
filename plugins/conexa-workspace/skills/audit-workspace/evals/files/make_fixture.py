#!/usr/bin/env python3
"""Arma un workspace de prueba con defectos sembrados, para los evals y los tests de audit-workspace.

Genera un workspace con init-workspace (3 repos locales, sin red) y le siembra los defectos de DEFECTS.
Cada defecto declara el texto que tiene que aparecer en el título de un hallazgo de audit.py.

Uso:
  make_fixture.py DESTINO            # workspace con todos los defectos
  make_fixture.py DESTINO --clean    # el mismo workspace, sin defectos
  make_fixture.py --list             # lista los defectos y el hallazgo esperado

Necesita el scaffold.py de init-workspace. Lo busca como skill hermana y subiendo desde este archivo y
desde el directorio actual; si no lo encuentra, pasá su ruta en INIT_WORKSPACE_SCAFFOLD.
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def find_scaffold():
    """scaffold.py de init-workspace: hermana de esta skill, o más arriba si este archivo se copió a otro lado."""
    if os.environ.get("INIT_WORKSPACE_SCAFFOLD"):
        return os.environ["INIT_WORKSPACE_SCAFFOLD"]
    tail = os.path.join("init-workspace", "scripts", "scaffold.py")
    for start in (HERE, os.getcwd()):
        d = start
        while True:
            for cand in (os.path.join(d, tail), os.path.join(d, "skills", tail), os.path.join(d, ".claude", "skills", tail)):
                if os.path.exists(cand):
                    return cand
            if os.path.dirname(d) == d:
                break
            d = os.path.dirname(d)
    cand = os.path.join(os.path.expanduser("~"), ".claude", "skills", tail)
    if os.path.exists(cand):
        return cand
    sys.exit("✗ no encuentro init-workspace/scripts/scaffold.py: pasá su ruta en INIT_WORKSPACE_SCAFFOLD")


REPOS = {  # carpeta -> (qué es, celda de stack, dependencia principal)
    "pagos-api": ("API de cobros", "TypeScript · NestJS · pnpm", "@nestjs/core"),
    "usuarios-api": ("Alta y login de usuarios", "TypeScript · NestJS · pnpm", "@nestjs/core"),
    "backoffice": ("Panel interno", "TypeScript · React · Vite", "react"),
}
# Los secretos de prueba se arman en ejecución para que este archivo no dispare ningún escáner.
FAKE_GH_TOKEN = "gh" + "p_" + "0123456789abcdefghijklmnopqrstuvwxyzAB"

# id -> (severidad, texto esperado en el título del hallazgo, qué se sembró)
DEFECTS = {
    "secreto-contenido": ("critico", "secretos en el contenido", "token de GitHub en knowledge/integraciones/github.md"),
    "credencial": ("critico", "Credenciales versionadas", "config/.env versionado"),
    "repo-sin-ignorar": ("critico", "no está en el bloque de repos del .gitignore", "backoffice fuera del bloque de repos"),
    "informe-seguridad": ("critico", "Informes de auditoría de seguridad versionados", "docs/FINDINGS-DETAIL.md versionado"),
    "permiso-escritura": ("importante", "Permisos de lectura en allow que también habilitan escrituras", "Bash(find:*) en allow"),
    "nota-huerfana": ("importante", "notas fuera del índice", "knowledge/integraciones/github.md sin enlazar"),
    "repo-sin-experto": ("importante", "no está cubierto por ningún experto", "backoffice sin experto"),
    "ruta-maquina": ("importante", "rutas absolutas de una máquina personal", "ruta de home en una nota"),
    "expertos-por-repo": ("mejora", "expertos para el stack nest", "pagos-api-expert y usuarios-api-expert en vez de nest-expert"),
    "plantilla-vieja": ("mejora", "de una versión vieja de la plantilla", "scripts/session-start.sh viejo y sin tocar"),
    "script-modificado": ("mejora", "scripts modificados respecto de la plantilla", "bootstrap/bootstrap.sh editado a mano"),
}
# Lo que solo detecta la revisión de juicio (no audit.py): sirve para los evals.
JUDGMENT = {
    "comando-inexistente": "pagos-api-expert lista `pnpm test:e2e`, que no existe en pagos-api/package.json",
}


def run(cwd, *args):
    subprocess.run(list(args), cwd=cwd, check=True, capture_output=True)


def write(root, rel, text):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def read(root, rel):
    with open(os.path.join(root, *rel.split("/")), encoding="utf-8") as fh:
        return fh.read()


def expert(name, folders, commands):
    rows = "\n".join(f"| `{f}/` | {REPOS[f][0]} | — |" for f in folders)
    return f"""---
name: {name}
description: >-
  Usar para cualquier trabajo sobre {', '.join(f + '/' for f in folders)}: módulos, guards, DTOs, providers,
  errores de inyección de dependencias y endpoints de {' y '.join(REPOS[f][0].lower() for f in folders)}.
tools: Read, Grep, Glob, Bash
model: sonnet
---

Sos el experto en NestJS de este workspace.

## Repos que cubrís

| Carpeta | Qué es | Particularidades |
|---|---|---|
{rows}

## Comandos

```bash
{commands}
```
"""


def build(target, clean=False):
    target = os.path.abspath(target)
    args = [sys.executable, find_scaffold(), "--target", target, "--name", "pagos-ws", "--description", "Workspace del proyecto de pagos"]
    for folder in REPOS:
        args += ["--repo", f"git@github.com:acme/{folder}.git"]
    subprocess.run(args, check=True, capture_output=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    run(target, "git", "init", "-q")

    # Repos de trabajo: locales, con el origin que dice el manifest (no se clona nada).
    for folder, (_, _, dep) in REPOS.items():
        repo = os.path.join(target, folder)
        write(target, f"{folder}/package.json", json.dumps(
            {"name": folder, "scripts": {"start:dev": "run dev", "test": "jest", "lint": "eslint ."}, "dependencies": {dep: "^10.0.0"}}, indent=2) + "\n")
        write(target, f"{folder}/src/main.ts", "export const main = () => 'ok'\n")
        run(repo, "git", "init", "-q")
        run(repo, "git", "remote", "add", "origin", f"git@github.com:acme/{folder}.git")
        run(repo, "git", "add", ".")
        run(repo, "git", "-c", "user.email=fixture@example.com", "-c", "user.name=fixture", "commit", "-qm", "init")

    agents = read(target, "AGENTS.md")
    for folder, (what, stack, _) in REPOS.items():
        if clean:
            exp = "`nest-expert`" if "Nest" in stack else "`react-expert`"
        else:
            exp = f"`{folder}-expert`" if "Nest" in stack else "[a completar]"
        agents = agents.replace(f"| `{folder}/` | [a completar] | [a completar] | [a completar] |", f"| `{folder}/` | {what} | {stack} | {exp} |")
    write(target, "AGENTS.md", agents)

    cmds = "pnpm install\npnpm start:dev\npnpm test\npnpm lint"
    if clean:
        write(target, ".claude/agents/nest-expert.md", expert("nest-expert", ["pagos-api", "usuarios-api"], cmds))
        write(target, ".claude/agents/react-expert.md",
              expert("react-expert", ["backoffice"], cmds).replace("NestJS", "React").replace("módulos, guards, DTOs, providers", "componentes, hooks, rutas, formularios"))
    else:
        write(target, ".claude/agents/pagos-api-expert.md", expert("pagos-api-expert", ["pagos-api"], cmds + "\npnpm test:e2e"))
        write(target, ".claude/agents/usuarios-api-expert.md", expert("usuarios-api-expert", ["usuarios-api"], cmds))
        seed(target)

    # Todo lo de la raíz al índice, menos los repos de trabajo.
    out = subprocess.run(["git", "ls-files", "-o", "--exclude-standard", "-z"], cwd=target, check=True, capture_output=True).stdout
    files = [f for f in out.decode("utf-8").split("\0") if f and f.split("/")[0] not in REPOS]
    run(target, "git", "add", "--", *files)
    return target


def seed(target):
    write(target, "knowledge/integraciones/github.md",
          f"---\nname: github\ndescription: Cómo se conecta el bot de releases con GitHub\n---\n\n"
          f"El bot usa este token: {FAKE_GH_TOKEN}\n\nEl script vive en /Users/" + "maria/code/pagos-ws/scripts.\n")
    write(target, "config/.env", "DATABASE_URL=postgres://localhost/pagos\n")
    write(target, "docs/FINDINGS-DETAIL.md", "# Hallazgos\n")
    gitignore = read(target, ".gitignore").replace("/backoffice\n", "")
    write(target, ".gitignore", gitignore.replace("\n.env\n", "\n").replace("\n.env.*\n", "\n"))
    settings = json.loads(read(target, ".claude/settings.json"))
    settings["permissions"]["allow"].append("Bash(find:*)")
    write(target, ".claude/settings.json", json.dumps(settings, indent=2) + "\n")
    # Versión vieja sin tocar: el archivo y el sello coinciden entre sí, pero no con la plantilla actual.
    old = read(target, "scripts/session-start.sh") + "# versión anterior de la plantilla\n"
    write(target, "scripts/session-start.sh", old)
    lock = json.loads(read(target, "bootstrap/template.lock.json"))
    lock["files"]["scripts/session-start.sh"] = hashlib.sha256(old.encode("utf-8")).hexdigest()
    lock["template_version"] = "0.1.0"
    write(target, "bootstrap/template.lock.json", json.dumps(lock, indent=2) + "\n")
    # Personalización a mano: el sello no cambia.
    write(target, "bootstrap/bootstrap.sh", read(target, "bootstrap/bootstrap.sh") + "# ajuste local del equipo\n")


def main():
    argv = sys.argv[1:]
    if "--list" in argv:
        for key, (sev, title, what) in DEFECTS.items():
            print(f"{sev:<11} {key:<20} {what}  →  hallazgo: «{title}»")
        for key, what in JUDGMENT.items():
            print(f"{'juicio':<11} {key:<20} {what}")
        return
    paths = [a for a in argv if not a.startswith("--")]
    if len(paths) != 1:
        sys.exit(__doc__)
    if os.path.exists(paths[0]) and os.listdir(paths[0]):
        sys.exit(f"✗ {paths[0]} ya existe y no está vacío")
    print(build(paths[0], clean="--clean" in argv))


if __name__ == "__main__":
    main()
