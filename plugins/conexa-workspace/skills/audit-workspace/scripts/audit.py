#!/usr/bin/env python3
"""Audita un workspace multi-repo para agentes y reporta qué falta o se puede mejorar.

Solo lee: no modifica nada del workspace ni de sus repos. Sin dependencias (Python 3.8+ y git).
Funciona con workspaces generados por init-workspace y también con estructuras parecidas que no
siguen el estándar: en ese caso reporta qué pieza equivalente encontró o no encontró.

Uso:
  audit.py [RAIZ] [--json] [--template DIR] [--out ARCHIVO]
    RAIZ         raíz del workspace (default: directorio actual)
    --json       salida JSON en vez de markdown
    --template   plantilla de init-workspace para detectar scripts desactualizados
                 (default: se busca una skill init-workspace hermana de esta)
    --out        además de imprimir, escribe el reporte en ese archivo
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

DIMS = [
    ("estructura", "Estructura"),
    ("repos", "Repos"),
    ("agentes", "Agentes"),
    ("memoria", "Memoria"),
    ("seguridad", "Seguridad"),
    ("harness", "Harness"),
    ("ci", "CI"),
]
SEV = {"critico": ("🔴", 15), "importante": ("🟠", 5), "mejora": ("🟡", 1)}
BEGIN_REPOS_GI = "# >>> repos (bootstrap/bootstrap.sh mantiene este bloque; no editar a mano) >>>"
END_REPOS_GI = "# <<< repos <<<"
GENERIC_AGENTS = ["code-reviewer", "security-reviewer", "explorer"]
WS_SKILLS = ["agregar-repo", "capturar"]
SECRET_PATH = [r"\.pem$", r"\.key$", r"\.p12$", r"\.pfx$", r"(^|/)client_secret[^/]*\.json$",
               r"(^|/)\.env(\.(?!example$)[^/]+)?$", r"(^|/)secrets\.json$", r"(^|/)id_(rsa|ed25519|ecdsa)$"]
MACHINE_PATH = re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/|[A-Za-z]:\\Users\\[A-Za-z0-9._-]+")
TEXT_EXT = re.compile(r"\.(md|mjs|js|ts|json|ya?ml|sh|ps1|txt|tsv|toml|py)$|(^|/)\.gitignore$", re.I)
PLACEHOLDER = re.compile(r"<carpeta>|\[a completar\]|<qué [^>]*>|<dir>|<instalar>|<convención[^>]*>")
TO_CONFIRM = re.compile(r"\[a confirmar\]", re.I)
MD_LINK = re.compile(r"\[[^\]]*\]\(([^()\s]+)\)")
CODE_REF = re.compile(r"`([A-Za-z0-9._-]+/[A-Za-z0-9._/@-]+?)(?::L?\d+(?:-\d+)?)?`")
FRONTMATTER = re.compile(r"^---\r?\n(.*?)\r?\n---", re.S)


# ── utilidades ───────────────────────────────────────────────

def sh(cwd, *args):
    try:
        return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception:
        return ""


def git(cwd, *args):
    return sh(cwd, "git", *args)


def read(path, limit=512 * 1024):
    try:
        if os.path.getsize(path) > limit:
            return ""
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def frontmatter(text):
    m = FRONTMATTER.match(text)
    if not m:
        return None
    fields = {}
    for line in m.group(1).splitlines():
        pm = re.match(r"^([\w-]+):\s*(.*)$", line)
        if pm:
            fields[pm.group(1)] = pm.group(2).strip().strip("'\"")
    return fields


def norm_url(url):
    u = url.strip().rstrip("/")
    u = re.sub(r"\.git$", "", u)
    u = re.sub(r"^[a-z+]+://", "", u)
    u = re.sub(r"^[^@/]+@", "", u)
    u = re.sub(r"^([^/:]+):", r"\1/", u)
    return u.lower()


def strip_code(md):
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    out, fence = [], None
    for line in md.split("\n"):
        m = re.match(r"^\s*(`{3,}|~{3,})", line)
        if fence is None:
            if m:
                fence = m.group(1)
                continue
            out.append(line)
        elif m and line.strip().startswith(fence[0] * len(fence)):
            fence = None
    return "\n".join(out)


def sha(path):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


# ── auditoría ────────────────────────────────────────────────

class Audit:
    def __init__(self, root, template):
        self.root = os.path.abspath(root)
        self.template = template
        self.findings = []
        self.passed = {d: 0 for d, _ in DIMS}
        self.facts = {}

    def p(self, *parts):
        return os.path.join(self.root, *parts)

    def exists(self, *parts):
        return os.path.lexists(self.p(*parts))

    def ok(self, dim):
        self.passed[dim] += 1

    def add(self, dim, sev, title, detail="", fix=""):
        self.findings.append({"dim": dim, "sev": sev, "title": title, "detail": detail, "fix": fix})

    def check(self, dim, cond, sev, title, detail="", fix=""):
        if cond:
            self.ok(dim)
        else:
            self.add(dim, sev, title, detail, fix)
        return cond

    # ── contexto base ──

    def load(self):
        self.is_git = bool(git(self.root, "rev-parse", "--git-dir"))
        self.tracked = git(self.root, "ls-files").splitlines() if self.is_git else []
        self.repos = self.read_manifest()
        self.repo_dirs = [r["dir"] for r in self.repos]
        # carpetas con .git adentro, a profundidad 1, que no están en el manifest
        self.unlisted = sorted(
            d for d in os.listdir(self.root)
            if d not in self.repo_dirs and not d.startswith(".") and os.path.isdir(self.p(d)) and os.path.exists(self.p(d, ".git"))
        )
        self.agent_paths = {}
        roots = [os.path.join(".claude", "agents")]
        plugins = self.p("plugins")
        if os.path.isdir(plugins):
            roots += [os.path.join("plugins", pl, "agents") for pl in sorted(os.listdir(plugins))]
        for r in roots:
            if os.path.isdir(self.p(r)):
                for f in sorted(os.listdir(self.p(r))):
                    if f.endswith(".md") and f[:-3] not in self.agent_paths:
                        self.agent_paths[f[:-3]] = os.path.join(r, f).replace(os.sep, "/")
        self.agents = sorted(self.agent_paths)

        self.agents_md = read(self.p("AGENTS.md"))
        self.claude_md = read(self.p("CLAUDE.md"))
        self.facts.update({
            "raiz": self.root, "git": self.is_git, "repos_manifest": len(self.repos),
            "repos_presentes": sum(1 for r in self.repos if self.exists(r["dir"])), "agentes": len(self.agents),
            "agentes_en_plugins": sum(1 for v in self.agent_paths.values() if v.startswith("plugins/")) or None,
        })

    def read_manifest(self):
        path = self.p("bootstrap", "repos.tsv")
        self.manifest_kind = "estandar" if os.path.exists(path) else None
        if not self.manifest_kind:
            for cand in ("bootstrap/manifest.tsv", "bootstrap/repos.txt", "repos.tsv", "repos.txt", "bootstrap/fuentes.txt"):
                if os.path.exists(self.p(cand)):
                    self.manifest_kind = cand
                    path = self.p(cand)
                    break
        if not self.manifest_kind:
            return self.manifest_from_script()
        repos = []
        for line in read(path).replace("\r", "").split("\n"):
            if not line.strip() or line.strip().startswith("#"):
                continue
            parts = re.split(r"\t|\s*\|\s*", line.strip())
            if len(parts) < 2:
                continue
            # tolera "url carpeta" o "carpeta url": la URL es el campo con ':' o '/'
            a, b = parts[0].strip(), parts[1].strip()
            if re.search(r"[:/]", a) and not re.search(r"[:/]", b):
                a, b = b, a
            repos.append({"dir": a.rstrip("/"), "url": b, "branch": parts[2].strip() if len(parts) > 2 else ""})
        return repos

    def manifest_from_script(self):
        """Lista de repos embebida en bootstrap.sh, como REPOS=( "carpeta:repo" ... )."""
        text = read(self.p("bootstrap", "bootstrap.sh"))
        m = re.search(r"^\s*REPOS=\((.*?)^\s*\)", text, re.S | re.M)
        if not m:
            return []
        repos = []
        for entry in re.findall(r"[\"']([^\"']+)[\"']", m.group(1)):
            a, _, b = entry.partition(":")
            if a and b:
                repos.append({"dir": a.strip().rstrip("/"), "url": b.strip(), "branch": ""})
        if repos:
            self.manifest_kind = "lista embebida en bootstrap/bootstrap.sh"
        return repos

    # ── dimensiones ──

    def estructura(self):
        d = "estructura"
        self.check(d, self.is_git, "importante", "La raíz no es un repositorio git",
                   "Sin git no hay historia del contexto, ni validador, ni forma de compartirlo.", "`git init` en la raíz.")
        if self.claude_md:
            self.check(d, bool(self.agents_md), "importante", "Falta AGENTS.md",
                       "Hay CLAUDE.md, pero otros agentes (Codex, Cursor…) no ven las reglas.", "Mover lo agnóstico de CLAUDE.md a AGENTS.md e importarlo con `@AGENTS.md`.")
        else:
            self.check(d, bool(self.agents_md), "critico", "No hay AGENTS.md ni CLAUDE.md",
                       "Ningún agente recibe las reglas ni el contexto del workspace.", "init-workspace en modo adaptar.")
        if self.claude_md:
            imports = re.search(r"^@AGENTS\.md\s*$", self.claude_md, re.M)
            self.check(d, bool(imports) or not self.agents_md, "importante", "CLAUDE.md no importa AGENTS.md",
                       "Las reglas quedan duplicadas o divergen entre agentes.", "Agregar la línea `@AGENTS.md` y dejar en CLAUDE.md solo lo propio de Claude Code.")
            extra = [l for l in self.claude_md.splitlines() if l.strip() and not l.startswith("@")]
            self.check(d, len(extra) <= 45, "mejora", f"CLAUDE.md tiene {len(extra)} líneas además del import",
                       "Lo que no es específico de Claude Code debería vivir en AGENTS.md.", "Mover lo agnóstico a AGENTS.md.")
        else:
            self.add(d, "importante", "Falta CLAUDE.md", "Claude Code no carga AGENTS.md por sí solo.", "Crear CLAUDE.md con `@AGENTS.md`.")
        if self.agents_md:
            n = len(self.agents_md.splitlines())
            self.check(d, n <= 250, "mejora", f"AGENTS.md tiene {n} líneas",
                       "Un router largo se lee entero en cada sesión y diluye las reglas duras.", "Mover detalle a knowledge/ y dejar punteros.")
            self.check(d, "BEGIN repos" in self.agents_md, "mejora", "AGENTS.md no tiene la tabla de repos con marcadores",
                       "Sin marcadores, /agregar-repo no puede mantenerla.", "Agregar `<!-- BEGIN repos -->` / `<!-- END repos -->` alrededor de la tabla.")
            self.check(d, re.search(r"orientarte|\.context/INDEX\.md", self.agents_md) is not None, "mejora",
                       "AGENTS.md no dice cómo orientarse rápido", "Los agentes exploran a ciegas en vez de leer el mapa.",
                       "Agregar la sección 'Cómo orientarte rápido' (mapa → knowledge → código).")
            self.check(d, re.search(r"(?i)memoria|capture|knowledge/", self.agents_md) is not None, "mejora",
                       "AGENTS.md no explica dónde va lo aprendido", "Sin esa regla, el capture loop no pasa.", "Agregar la sección 'Memoria del proyecto'.")
        for f, sev, why in [
            ("README.md", "mejora", "onboarding humano"),
            ("CONTRIBUTING.md", "mejora", "la convención de dos velocidades"),
            ("MAINTENANCE.md", "mejora", "el capture loop y qué disparador actualiza qué"),
            (".gitignore", "critico", "sin él, los repos y los secretos se pueden versionar"),
            ("bootstrap/bootstrap.sh", "importante", "sin script de clonado, el onboarding es manual"),
            ("scripts/map.mjs", "mejora", "el mapa de contexto que acelera la lectura"),
            ("scripts/validate.mjs", "importante", "los chequeos de CI"),
            ("scripts/session-start.sh", "mejora", "el hook de inicio"),
            (".claude/settings.json", "importante", "permisos y hook de inicio"),
            ("knowledge/README.md", "importante", "el índice de la memoria"),
            ("knowledge/_template.md", "mejora", "la plantilla de nota"),
            ("knowledge/templates/repo-expert.md", "mejora", "la plantilla de experto por repo"),
        ]:
            self.check(d, self.exists(*f.split("/")), sev, f"Falta `{f}`", f"Cubre {why}.", "init-workspace en modo adaptar.")
        if self.manifest_kind and self.manifest_kind != "estandar":
            self.add(d, "mejora", f"Manifest en formato no estándar: `{self.manifest_kind}`",
                     "Se leyó igual, pero bootstrap.sh, map.mjs y el validador esperan `bootstrap/repos.tsv`.",
                     "Migrar a `carpeta<TAB>url<TAB>rama` en bootstrap/repos.tsv.")
        elif not self.manifest_kind:
            self.add(d, "importante", "No hay manifest de repos", "No hay lista autoritativa de qué repos componen el workspace.",
                     "Crear bootstrap/repos.tsv (init-workspace en modo adaptar lo arma desde las carpetas con .git).")

    def repos_dim(self):
        d = "repos"
        gi = read(self.p(".gitignore"))
        b, e = gi.find(BEGIN_REPOS_GI), gi.find(END_REPOS_GI)
        block = [l.strip() for l in gi[b + len(BEGIN_REPOS_GI):e].splitlines()] if b != -1 and e > b else None
        if self.repos:
            self.check(d, block is not None, "importante", "El .gitignore no tiene el bloque de repos con marcadores",
                       "bootstrap.sh no puede mantenerlo y un repo nuevo puede terminar versionado.", "Agregar los marcadores y correr `bash bootstrap/bootstrap.sh`.")
        table = self.agents_md
        tb, te = table.find("BEGIN repos"), table.find("END repos")
        table = table[tb:te] if tb != -1 and te > tb else table
        missing = []
        for r in self.repos:
            rd, path = r["dir"], self.p(r["dir"])
            if not os.path.lexists(path):
                missing.append(rd)
                continue
            self.ok(d)
            if not os.path.exists(os.path.join(path, ".git")):
                self.add(d, "importante", f"`{rd}/` no es un repo git", "Está en el manifest pero no tiene .git.", "Revisar si es una copia; reclonar con bootstrap.")
                continue
            origin = git(path, "remote", "get-url", "origin")
            self.check(d, not origin or norm_url(origin) == norm_url(r["url"]), "importante",
                       f"`{rd}/`: el origin no coincide con el manifest", f"origin `{origin}` · manifest `{r['url']}`",
                       "Corregir la URL en el manifest o el remote del clon.")
            if r["branch"]:
                cur = git(path, "rev-parse", "--abbrev-ref", "HEAD")
                self.check(d, cur == r["branch"], "mejora", f"`{rd}/` está en `{cur}` y el manifest dice `{r['branch']}`",
                           "Puede ser trabajo en curso; si no, el manifest quedó viejo.", "Confirmar cuál es la rama de trabajo.")
            if block is not None:
                self.check(d, f"/{rd}" in block or f"/{rd}/" in block, "critico", f"`{rd}/` no está en el bloque de repos del .gitignore",
                           "El código del repo se puede versionar en la raíz.", "`bash bootstrap/bootstrap.sh` lo resincroniza.")
            inside = [f for f in self.tracked if f == rd or f.startswith(rd + "/")]
            self.check(d, not inside, "critico", f"`{rd}/` está versionado en la raíz ({len(inside)} entradas)",
                       "La raíz no tiene que versionar código de los repos.", f"`git rm -r --cached {rd}` (decisión del usuario).")
            expert = f"{rd.split('/')[-1]}-expert"
            keys = [re.sub(r"[^a-z0-9]", "", seg.lower()) for seg in rd.split("/") if len(seg) > 2]
            alt = [a for a in self.agents if any(k and k in re.sub(r"[^a-z0-9]", "", a.lower()) for k in keys)]
            if expert in self.agents:
                self.ok(d)
            elif alt:
                self.add(d, "mejora", f"El experto de `{rd}/` tiene nombre no estándar: `{alt[0]}`", "", f"Renombrar a `{expert}` si no rompe nada.")
            else:
                self.add(d, "importante", f"`{rd}/` no tiene agente experto", "El trabajo sobre ese repo no tiene a quién delegarse.",
                         f"`/agregar-repo` o crear `.claude/agents/{expert}.md` desde la plantilla.")
            self.check(d, f"`{rd}/`" in table or f"| {rd}" in table, "mejora", f"`{rd}/` no aparece en la tabla de repos de AGENTS.md",
                       "", "Agregar la fila entre los marcadores.")
        if missing:
            self.add(d, "mejora", f"Repos del manifest sin clonar: {', '.join(missing)}",
                     "Los agentes no los pueden leer en esta máquina.", "`bash bootstrap/bootstrap.sh` (con `--link` si ya están clonados en otro lado).")
        for u in self.unlisted:
            if any(f == u or f.startswith(u + "/") for f in self.tracked):
                self.add(d, "critico", f"`{u}/` está versionado en la raíz y no está en el manifest",
                         "Quedó como gitlink o con su código adentro de la raíz.", f"`git rm -r --cached {u}`, registrarlo en el manifest y correr bootstrap.")
                continue
            self.add(d, "importante", f"`{u}/` tiene .git pero no está en el manifest",
                     "Otro miembro del equipo no lo va a tener, y puede no estar ignorado.", f"`bash bootstrap/bootstrap.sh --add $(git -C {u} remote get-url origin) --dir {u}`.")
        for a in self.agents:
            if a.endswith("-expert"):
                base = a[:-7]
                segments = {seg for r in self.repo_dirs for seg in r.split("/")}
                self.check(d, base in segments or not self.repos, "mejora", f"Experto sin repo del mismo nombre: `{a}`",
                           f"Ningún repo del manifest se llama `{base}`. Puede cubrir uno con otro nombre (confirmalo) o haber quedado huérfano.",
                           "Si cubre un repo, nombrarlo `<carpeta>-expert`; si no, borrarlo.")

    def agentes(self):
        d = "agentes"
        for g in GENERIC_AGENTS:
            self.check(d, g in self.agents, "mejora", f"Falta el agente genérico `{g}`", "", "Copiarlo de la plantilla de init-workspace.")
        for s in WS_SKILLS:
            self.check(d, self.exists(".claude", "skills", s, "SKILL.md"), "mejora", f"Falta la skill del workspace `/{s}`", "", "Copiarla de la plantilla de init-workspace.")
        descs = {}
        for a in self.agents:
            text = read(self.p(*self.agent_paths[a].split("/")))
            fm = frontmatter(text)
            if not fm:
                self.add(d, "importante", f"`{a}`: sin frontmatter", "Claude Code no lo reconoce como subagente.", "Agregar `name` y `description`.")
                continue
            self.check(d, fm.get("name") == a, "importante", f"`{a}`: name `{fm.get('name')}` no coincide con el archivo", "", f"Usar `name: {a}`.")
            desc = fm.get("description", "")
            self.check(d, len(desc) >= 80, "importante" if not desc else "mejora", f"`{a}`: description {'vacía' if not desc else 'muy corta'} ({len(desc)} caracteres)",
                       "La description decide si el agente se dispara.", "Nombrar disparadores concretos: síntomas, términos, módulos.")
            descs[a] = desc
            body_lines = len(text.splitlines())
            visible = re.sub(r"<!--.*?-->", "", text, flags=re.S)
            if a.endswith("-expert"):
                self.check(d, body_lines <= 120, "mejora", f"`{a}`: {body_lines} líneas", "Un experto largo duplica conocimiento que se desincroniza.",
                           "Mover lo que sobra a knowledge/ y dejar el puntero.")
                ph = PLACEHOLDER.findall(visible)
                self.check(d, not ph, "importante", f"`{a}`: quedaron {len(ph)} placeholders de la plantilla", ", ".join(sorted(set(ph)))[:120], "Completarlos leyendo el repo.")
                tc = TO_CONFIRM.findall(visible)
                self.check(d, not tc, "mejora", f"`{a}`: {len(tc)} datos marcados [a confirmar]", "", "Verificarlos en el repo y quitar la marca.")
            if "tools" not in fm:
                self.add(d, "mejora", f"`{a}`: no declara `tools`", "Hereda todas las herramientas, incluidas las de escritura.", "Declarar `tools: Read, Grep, Glob, Bash` si es de solo lectura.")
            else:
                self.ok(d)
        # expertos con descriptions casi iguales se pisan al rutear
        experts = [a for a in descs if a.endswith("-expert")]
        for i, a in enumerate(experts):
            for b2 in experts[i + 1:]:
                wa, wb = set(re.findall(r"\w{5,}", descs[a].lower())), set(re.findall(r"\w{5,}", descs[b2].lower()))
                if wa and wb and len(wa & wb) / max(1, min(len(wa), len(wb))) > 0.7:
                    self.add(d, "mejora", f"`{a}` y `{b2}` tienen descriptions muy parecidas", "El ruteo entre los dos va a ser errático.",
                             "Que cada uno diga qué no cubre.")

    def memoria(self):
        d = "memoria"
        kdir = self.p("knowledge")
        if not os.path.isdir(kdir):
            alt = [c for c in ("docs/knowledge", "docs", "knowledge-base", "kb") if os.path.isdir(self.p(*c.split("/")))]
            self.add(d, "importante", "No hay carpeta knowledge/", f"Candidata encontrada: `{alt[0]}/`." if alt else "No hay memoria versionada.",
                     "Crear knowledge/ o declarar la carpeta existente en AGENTS.md.")
            return
        self.ok(d)
        notes = []
        for base, _, files in os.walk(kdir):
            for f in files:
                if f.endswith(".md"):
                    rel = os.path.relpath(os.path.join(base, f), self.root).replace(os.sep, "/")
                    if rel not in ("knowledge/README.md", "knowledge/_template.md") and not rel.startswith("knowledge/templates/"):
                        notes.append(rel)
        seeds = {"knowledge/decisiones.md", "knowledge/procesos/idioma.md"}
        real = [n for n in notes if n not in seeds]
        self.facts["notas"] = len(real)
        index = read(self.p("knowledge", "README.md"))
        linked = set()
        for link in MD_LINK.findall(strip_code(index)):
            linked.add(os.path.normpath(os.path.join("knowledge", link.split("#")[0])).replace(os.sep, "/"))
        orphans = [n for n in notes if n not in linked]
        self.check(d, not orphans, "importante", f"{len(orphans)} notas fuera del índice", ", ".join(orphans[:6]), "Sumarlas a knowledge/README.md.")
        bad_fm = [n for n in notes if not (frontmatter(read(self.p(*n.split("/")))) or {}).get("description")]
        self.check(d, not bad_fm, "mejora", f"{len(bad_fm)} notas sin description en el frontmatter", ", ".join(bad_fm[:6]),
                   "La description es lo que hace que la nota se encuentre.")
        dec = read(self.p("knowledge", "decisiones.md"))
        entries = len(re.findall(r"^###\s+D-\d+", dec, re.M))
        self.facts["decisiones"] = entries
        self.check(d, bool(dec), "mejora", "No hay log de decisiones", "", "Crear knowledge/decisiones.md.")
        age_days = None
        if self.is_git:
            first = git(self.root, "log", "--reverse", "--format=%ct")
            first = first.splitlines()[0] if first else ""
            last_k = git(self.root, "log", "-1", "--format=%ct", "--", "knowledge/")
            if first:
                age_days = (datetime.datetime.now().timestamp() - int(first)) / 86400
            if last_k and age_days and age_days > 30:
                idle = (datetime.datetime.now().timestamp() - int(last_k)) / 86400
                self.facts["dias_sin_capturar"] = int(idle)
                self.check(d, idle <= 45, "mejora", f"knowledge/ sin cambios hace {int(idle)} días",
                           "Si se siguió trabajando en los repos, el capture loop no está pasando.", "Correr `/capturar` al cerrar tareas.")
        if not real:
            sev = "importante" if age_days and age_days > 30 else "mejora"
            self.add(d, sev, "La memoria está vacía (solo las notas semilla)",
                     "Todavía no se capturó ninguna lección." + (f" El workspace tiene {int(age_days)} días." if age_days else ""), "Usar `/capturar` al cerrar tareas.")
        else:
            self.ok(d)
        drafts = [f for f in self.tracked if f.startswith("drafts/") and not f.endswith(".gitkeep")]
        self.check(d, not drafts, "importante", f"{len(drafts)} borradores versionados en drafts/", ", ".join(drafts[:5]),
                   "drafts/ es local: si algo es conocimiento, pasalo a knowledge/.")
        self.code_refs(d, notes)

    def code_refs(self, d, notes):
        """Referencias a archivos de los repos (`repo/ruta`) en notas y agentes que ya no existen."""
        present = [r for r in self.repo_dirs if os.path.isdir(self.p(r))]
        if not present:
            return
        files = notes + [self.agent_paths[a] for a in self.agents]
        broken = []
        for f in files:
            text = strip_code(read(self.p(*f.split("/"))))
            for ref in CODE_REF.findall(text):
                top = ref.split("/")[0]
                if top in present and "<" not in ref and "*" not in ref and not os.path.lexists(self.p(*ref.rstrip("/").split("/"))):
                    broken.append(f"{f} → {ref}")
        self.check(d, not broken, "importante", f"{len(broken)} referencias a código que ya no existe", "; ".join(broken[:6]),
                   "El código se movió o se borró: actualizar la nota o el agente.")

    def seguridad(self):
        d = "seguridad"
        secrets = [f for f in self.tracked if any(re.search(p, f, re.I) for p in SECRET_PATH)]
        self.check(d, not secrets, "critico", "Credenciales versionadas", ", ".join(secrets[:6]), "Sacarlas del índice y **rotarlas**: siguen en la historia.")
        paths = []
        for f in self.tracked:
            if TEXT_EXT.search(f) and not f.endswith("validate.mjs"):
                for m in MACHINE_PATH.findall(read(self.p(*f.split("/")))):
                    paths.append(f"{f} → {m}")
        self.check(d, not paths, "importante", f"{len(paths)} rutas absolutas de una máquina personal", "; ".join(paths[:5]), "Usar rutas relativas o `$CLAUDE_PROJECT_DIR`.")
        gi = read(self.p(".gitignore"))
        for pat in (".env", "*.pem", "*.key"):
            self.check(d, re.search(r"^" + re.escape(pat) + r"\s*$", gi, re.M) is not None, "importante", f"El .gitignore no ignora `{pat}`", "", "Agregar el bloque de secretos.")
        settings = self.p(".claude", "settings.json")
        if not os.path.exists(settings):
            return
        try:
            data = json.loads(read(settings))
        except ValueError:
            self.add(d, "critico", ".claude/settings.json no es JSON válido", "Claude Code lo ignora entero.", "Corregir la sintaxis.")
            return
        perms = data.get("permissions", {})
        allow, deny = perms.get("allow", []), perms.get("deny", [])
        risky = [a for a in allow if a in ("Bash", "Bash(*)", "Bash(git -C:*)", "Bash(git push:*)", "Bash(rm:*)", "Bash(git reset:*)") or a.startswith("Bash(git push")]
        self.check(d, not risky, "importante", "Permisos amplios en allow", ", ".join(risky),
                   "Habilitan escrituras o pushes sin confirmación. Moverlos a `ask`.")
        self.check(d, any(".env" in x for x in deny), "importante", "No se deniega leer `.env`", "", "Agregar `Read(**/.env)` y similares a deny.")
        self.check(d, any("push --force" in x or "push -f" in x for x in deny), "mejora", "No se deniega `git push --force`", "", "Agregarlo a deny.")
        abs_hooks = []
        for event, entries in (data.get("hooks") or {}).items():
            for entry in entries or []:
                for h in entry.get("hooks", []):
                    cmd = h.get("command", "")
                    if MACHINE_PATH.search(cmd) or re.match(r"^/(?!\$)", cmd.strip()):
                        abs_hooks.append(f"{event}: {cmd[:60]}")
        self.check(d, not abs_hooks, "importante", "Hooks con rutas absolutas en el settings.json compartido", "; ".join(abs_hooks),
                   "Fallan en otras máquinas. Llevarlos a `.claude/settings.local.json`.")

    def harness(self):
        d = "harness"
        settings = read(self.p(".claude", "settings.json"))
        self.check(d, "session-start" in settings, "mejora", "No hay hook de inicio de sesión", "El mapa no se refresca solo y no se avisa qué falta clonar.",
                   "Registrar `scripts/session-start.sh` en SessionStart.")
        present = [r for r in self.repo_dirs if os.path.isdir(self.p(r)) and os.path.exists(self.p(r, ".git"))]
        if os.path.exists(self.p(".context", "INDEX.md")):
            self.ok(d)
            stale = []
            for r in present:
                try:
                    cached = json.loads(read(self.p(".context", "map", r + ".json"))).get("head")
                except ValueError:
                    cached = None
                if cached != git(self.p(r), "rev-parse", "HEAD"):
                    stale.append(r)
            self.check(d, not stale, "mejora", f"Mapa desactualizado para: {', '.join(stale)}", "Se regenera al abrir sesión.", "`node scripts/map.mjs`.")
        elif present:
            self.add(d, "mejora", "No hay mapa de contexto generado", "Los agentes van a explorar a ciegas.", "`node scripts/map.mjs`.")
        self.check(d, "/.context/" in read(self.p(".gitignore")) or not os.path.exists(self.p(".context")), "importante",
                   ".context/ no está ignorado", "Es generado: versionarlo mete ruido en cada PR.", "Agregar `/.context/` al .gitignore.")
        tracked_generated = [f for f in self.tracked if f.startswith(".context/") or f.startswith("graphify-out/")]
        self.check(d, not tracked_generated, "importante", f"{len(tracked_generated)} archivos generados versionados",
                   ", ".join(tracked_generated[:4]), "Sacarlos del índice: se regeneran solos.")
        # graphify
        g_out = self.p("graphify-out", "graph.json")
        has_setup = self.exists("scripts", "graphify-setup.sh")
        installed = bool(sh(self.root, "sh", "-c", "command -v graphify"))
        self.facts["graphify"] = "grafo construido" if os.path.exists(g_out) else ("instalado sin grafo" if installed else "no instalado")
        if os.path.exists(g_out):
            self.check(d, self.exists(".graphifyignore"), "importante", "Hay grafo pero no `.graphifyignore`",
                       "Construido sobre la raíz, el grafo puede incluir dependencias o dejar afuera los repos.", "`bash scripts/graphify-setup.sh --refresh`.")
            self.check(d, "BEGIN graphify" in self.agents_md, "mejora", "AGENTS.md no dice cómo usar el grafo", "", "`bash scripts/graphify-setup.sh` escribe la sección.")
            try:
                g = json.loads(read(g_out, limit=600 * 1024 * 1024))
                sources = {(n.get("source_file") or "").split("/")[0] for n in g.get("nodes", [])}
                empty = [r for r in present if r not in sources]
                self.check(d, not empty, "importante", f"Repos sin nodos en el grafo: {', '.join(empty)}",
                           "Probablemente se construyó respetando el .gitignore de la raíz.", "`bash scripts/graphify-setup.sh --refresh`.")
            except ValueError:
                self.add(d, "mejora", "No se pudo leer graphify-out/graph.json", "", "Reconstruir el grafo.")
            heads = read(self.p("graphify-out", ".workspace-heads")).strip()
            now = "\n".join(f"{r} {git(self.p(r), 'rev-parse', 'HEAD')}" for r in present)
            if heads:
                self.check(d, heads == now, "mejora", "El grafo está desactualizado", "Se refresca al abrir sesión si está el hook.", "`bash scripts/graphify-setup.sh --refresh`.")
            gshared = "hook-guard" in settings
            self.check(d, not gshared, "importante", "Hooks de graphify en el settings.json compartido",
                       "Fallan en cada llamada para quien no tenga graphify.", "Moverlos a `.claude/settings.local.json` (`graphify-setup.sh --hooks`).")
        elif installed and has_setup and len(present) >= 2:
            self.add(d, "mejora", "graphify está instalado pero no hay grafo", "", "`bash scripts/graphify-setup.sh`.")
        # scripts desactualizados respecto de la plantilla
        if self.template:
            drift = []
            for rel in ("bootstrap/bootstrap.sh", "scripts/map.mjs", "scripts/validate.mjs", "scripts/session-start.sh", "scripts/graphify-setup.sh"):
                mine, theirs = sha(self.p(*rel.split("/"))), sha(os.path.join(self.template, *rel.split("/")))
                if mine and theirs and mine != theirs:
                    drift.append(rel)
                elif theirs and not mine and rel.endswith("graphify-setup.sh"):
                    drift.append(rel + " (falta)")
            self.facts["plantilla"] = self.template
            self.check(d, not drift, "mejora", f"{len(drift)} scripts distintos a la plantilla actual", ", ".join(drift),
                       "Puede ser una personalización o una versión vieja. Comparar con diff antes de actualizar.")

    def ci(self):
        d = "ci"
        wf_dir = self.p(".github", "workflows")
        wfs = [f for f in os.listdir(wf_dir) if f.endswith((".yml", ".yaml"))] if os.path.isdir(wf_dir) else []
        runs = any("validate.mjs" in read(os.path.join(wf_dir, f)) for f in wfs)
        self.check(d, runs, "importante" if self.exists("scripts", "validate.mjs") else "mejora", "El CI no corre el validador",
                   "Un secreto o un repo versionado llega a main sin que nadie lo vea.", "Agregar el workflow de validate de la plantilla.")
        self.check(d, self.exists(".github", "pull_request_template.md"), "mejora", "No hay PR template", "", "Copiarlo de la plantilla.")
        if self.exists("scripts", "validate.mjs") and self.is_git and sh(self.root, "sh", "-c", "command -v node"):
            out = subprocess.run(["node", "scripts/validate.mjs"], cwd=self.root, capture_output=True, text=True)
            n = len([l for l in out.stderr.splitlines() if l.strip().startswith("·")])
            self.facts["validador"] = "OK" if out.returncode == 0 else f"{n} problemas"
            self.check(d, out.returncode == 0, "importante", f"El validador del workspace falla ({n} problemas)",
                       "Los problemas concretos aparecen en las otras dimensiones de este reporte.", "`node scripts/validate.mjs` y corregir.")

    def run(self):
        self.load()
        self.estructura()
        self.repos_dim()
        self.agentes()
        self.memoria()
        self.seguridad()
        self.harness()
        self.ci()
        return self

    # ── puntaje y salida ──

    def score(self):
        penalty = sum(SEV[f["sev"]][1] for f in self.findings)
        return max(0, 100 - penalty)

    def level(self, s):
        if any(f["sev"] == "critico" for f in self.findings):
            return "Riesgo: hay problemas críticos"
        if s >= 90:
            return "Completo"
        if s >= 70:
            return "Funcional con huecos"
        if s >= 40:
            return "Parcial"
        return "Incipiente"

    def dim_status(self, dim):
        fs = [f for f in self.findings if f["dim"] == dim]
        if any(f["sev"] == "critico" for f in fs):
            return "🔴"
        if any(f["sev"] == "importante" for f in fs):
            return "🟠"
        if fs:
            return "🟡"
        return "✅"

    def to_json(self):
        s = self.score()
        return {"fecha": datetime.date.today().isoformat(), "puntaje": s, "nivel": self.level(s), "hechos": self.facts,
                "dimensiones": {d: {"estado": self.dim_status(d), "ok": self.passed[d],
                                    "hallazgos": len([f for f in self.findings if f["dim"] == d])} for d, _ in DIMS},
                "hallazgos": self.findings}

    def to_markdown(self):
        s = self.score()
        L = [f"# Auditoría del workspace — {os.path.basename(self.root)}", "",
             f"**{s}/100 · {self.level(s)}** · {datetime.date.today().isoformat()}", ""]
        facts = [f"{k.replace('_', ' ')}: {v}" for k, v in self.facts.items() if k not in ("raiz", "plantilla") and v is not None]
        L += ["> " + " · ".join(facts), ""]
        L += ["| Dimensión | Estado | Chequeos OK | Hallazgos |", "|---|---|---|---|"]
        for d, name in DIMS:
            n = len([f for f in self.findings if f["dim"] == d])
            L.append(f"| {name} | {self.dim_status(d)} | {self.passed[d]} | {n} |")
        for sev, label in (("critico", "Críticos"), ("importante", "Importantes"), ("mejora", "Mejoras")):
            fs = [f for f in self.findings if f["sev"] == sev]
            if not fs:
                continue
            L += ["", f"## {SEV[sev][0]} {label} ({len(fs)})", ""]
            for f in fs:
                dim = dict(DIMS)[f["dim"]]
                line = f"- **[{dim}] {f['title']}**"
                if f["detail"]:
                    line += f" — {f['detail']}"
                if f["fix"]:
                    line += f"  \n  → {f['fix']}"
                L.append(line)
        if not self.findings:
            L += ["", "Sin hallazgos mecánicos. Queda la revisión de juicio (calidad de AGENTS.md, expertos y notas)."]
        return "\n".join(L) + "\n"


def find_template(explicit):
    if explicit:
        return os.path.abspath(explicit) if os.path.isdir(explicit) else None
    for cand in (os.path.join(HERE, "..", "..", "init-workspace", "assets", "template"),
                 os.path.expanduser("~/.claude/skills/init-workspace/assets/template")):
        if os.path.isdir(cand):
            return os.path.abspath(cand)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--template")
    ap.add_argument("--out")
    args = ap.parse_args()
    if not os.path.isdir(args.root):
        sys.exit(f"✗ no existe {args.root}")
    audit = Audit(args.root, find_template(args.template)).run()
    out = json.dumps(audit.to_json(), ensure_ascii=False, indent=2) if args.json else audit.to_markdown()
    print(out)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out)


if __name__ == "__main__":
    main()
