#!/usr/bin/env python3
"""Tests de conexa-workspace: scaffold, upgrade, audit, validador y bootstrap. Sin red ni dependencias.

    python3 -m unittest discover -s plugins/conexa-workspace/tests -v
"""
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INIT = os.path.join(PLUGIN, "skills", "init-workspace")
AUDIT_DIR = os.path.join(PLUGIN, "skills", "audit-workspace")
SCAFFOLD = os.path.join(INIT, "scripts", "scaffold.py")
AUDIT = os.path.join(AUDIT_DIR, "scripts", "audit.py")
TEMPLATE = os.path.join(INIT, "assets", "template")
HAS_NODE = shutil.which("node") is not None


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


fixture = load("make_fixture", os.path.join(AUDIT_DIR, "evals", "files", "make_fixture.py"))
scaffold = load("scaffold", SCAFFOLD)
audit_mod = load("audit", AUDIT)


def run(cwd, *args, check=True):
    return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, check=check)


def audit(root, *extra):
    return json.loads(run(root, sys.executable, AUDIT, root, "--json", *extra).stdout)


def titles(report, sev=None):
    return [f["title"] for f in report["hallazgos"] if sev is None or f["sev"] == sev]


def text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="conexa-ws-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def scaffold(self, name="ws", *extra):
        ws = os.path.join(self.tmp, name)
        run(self.tmp, sys.executable, SCAFFOLD, "--target", ws, "--name", "demo", "--description", "workspace de prueba", *extra)
        return ws


class FixtureAudit(Base):
    def test_clean_workspace_has_no_serious_findings(self):
        ws = fixture.build(os.path.join(self.tmp, "good"), clean=True)
        report = audit(ws)
        self.assertEqual(titles(report, "critico") + titles(report, "importante"), [])
        self.assertGreaterEqual(report["puntaje"], 95)
        if HAS_NODE:
            self.assertEqual(run(ws, "node", "scripts/validate.mjs", check=False).returncode, 0)

    def test_every_seeded_defect_is_reported(self):
        ws = fixture.build(os.path.join(self.tmp, "bad"))
        report = audit(ws)
        for key, (sev, expected, _) in fixture.DEFECTS.items():
            with self.subTest(defecto=key):
                self.assertTrue(any(expected in t for t in titles(report, sev)), f"falta el hallazgo «{expected}» ({sev})")
        self.assertTrue(report["nivel"].startswith("Riesgo"))

    def test_secret_is_never_printed_in_full(self):
        ws = fixture.build(os.path.join(self.tmp, "bad"))
        out = run(ws, sys.executable, AUDIT, ws).stdout
        self.assertNotIn(fixture.FAKE_GH_TOKEN, out)
        if HAS_NODE:
            res = run(ws, "node", "scripts/validate.mjs", check=False)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("secreto en el contenido", res.stderr)
            self.assertNotIn(fixture.FAKE_GH_TOKEN, res.stderr)

    def test_audit_does_not_execute_workspace_code(self):
        ws = fixture.build(os.path.join(self.tmp, "good"), clean=True)
        marker = os.path.join(self.tmp, "ejecutado")
        with open(os.path.join(ws, "scripts", "validate.mjs"), "w", encoding="utf-8") as fh:
            fh.write(f"import {{ writeFileSync }} from 'node:fs'\nwriteFileSync({json.dumps(marker)}, 'x')\n")
        audit(ws)
        self.assertFalse(os.path.exists(marker), "audit.py ejecutó el validate.mjs del workspace auditado")
        self.assertIn("no ejecutado", audit(ws, "--no-exec")["hechos"]["validador"])

    def test_multiline_description_is_read(self):
        ws = fixture.build(os.path.join(self.tmp, "good"), clean=True)
        self.assertFalse([t for t in titles(audit(ws)) if "description" in t and "corta" in t])


class Scoring(Base):
    def test_volume_does_not_sink_the_score(self):
        ws = self.scaffold()
        run(ws, "git", "init", "-q")
        lines = []
        for i in range(12):
            repo = os.path.join(ws, f"svc-{i}")
            os.makedirs(repo)
            run(repo, "git", "init", "-q")
            run(repo, "git", "remote", "add", "origin", f"git@github.com:acme/svc-{i}.git")
            lines.append(f"svc-{i}\tgit@github.com:acme/svc-{i}.git")
        with open(os.path.join(ws, "bootstrap", "repos.tsv"), "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        with open(os.path.join(ws, ".gitignore"), encoding="utf-8") as fh:
            gi = fh.read()
        with open(os.path.join(ws, ".gitignore"), "w", encoding="utf-8") as fh:
            fh.write(gi.replace("# <<< repos <<<", "\n".join(f"/svc-{i}" for i in range(12)) + "\n# <<< repos <<<"))
        run(ws, "git", "add", "AGENTS.md", "CLAUDE.md", ".gitignore", "bootstrap", "scripts", "knowledge", ".claude", ".github", "README.md")
        report = audit(ws)
        # 12 repos sin experto y sin fila: mismo tipo de hallazgo, se agrupa y la dimensión tiene tope.
        self.assertGreaterEqual(len(titles(report, "importante")), 12)
        self.assertLessEqual(report["dimensiones"]["repos"]["resta"], audit_mod.DIM_CAP)
        self.assertGreaterEqual(report["puntaje"], 60)

    def test_empty_folder_is_flagged_as_risk(self):
        report = audit(self.tmp)
        self.assertTrue(report["nivel"].startswith("Riesgo"))
        self.assertLess(report["puntaje"], 70)


class Upgrade(Base):
    def upgrade(self, ws, *extra):
        return run(ws, sys.executable, SCAFFOLD, "--target", ws, "--upgrade", *extra).stdout

    def test_scaffold_writes_lock(self):
        ws = self.scaffold()
        lock = json.loads(text(os.path.join(ws, "bootstrap", "template.lock.json")))
        self.assertEqual(lock["files"]["scripts/map.mjs"], sha(os.path.join(ws, "scripts", "map.mjs")))
        self.assertNotIn("AGENTS.md", lock["files"])
        self.assertEqual(lock["values"]["name"], "demo")

    def test_untouched_old_file_is_updated_and_custom_is_kept(self):
        ws = self.scaffold()
        lock_path = os.path.join(ws, "bootstrap", "template.lock.json")
        old, custom, agents = (os.path.join(ws, *p.split("/")) for p in ("scripts/session-start.sh", "scripts/map.mjs", "AGENTS.md"))
        # versión vieja sin tocar: archivo y sello coinciden entre sí, no con la plantilla
        with open(old, "a", encoding="utf-8") as fh:
            fh.write("# vieja\n")
        lock = json.loads(text(lock_path))
        lock["files"]["scripts/session-start.sh"] = sha(old)
        with open(lock_path, "w", encoding="utf-8") as fh:
            json.dump(lock, fh)
        for path in (custom, agents):
            with open(path, "a", encoding="utf-8") as fh:
                fh.write("\n// del equipo\n")
        os.remove(os.path.join(ws, "MAINTENANCE.md"))
        before = {p: sha(p) for p in (old, custom, agents)}

        dry = self.upgrade(ws, "--dry-run")
        self.assertEqual(before, {p: sha(p) for p in before}, "--dry-run escribió")
        self.assertRegex(dry, r"actualizado\s+scripts/session-start\.sh")

        out = self.upgrade(ws)
        self.assertRegex(out, r"modificado a mano \(no se tocó\)\s+scripts/map\.mjs")
        self.assertRegex(out, r"creado\s+MAINTENANCE\.md")
        self.assertEqual(sha(old), sha(os.path.join(TEMPLATE, "scripts", "session-start.sh")))
        self.assertEqual(sha(custom), before[custom])
        self.assertEqual(sha(agents), before[agents], "--upgrade tocó un archivo propio del workspace")
        self.assertNotIn("AGENTS.md", out.split("Plantilla:")[1].split("\n\n")[0])
        self.assertIn("0 actualizados", self.upgrade(ws))  # idempotente

    def test_legacy_workspace_without_lock_uses_history(self):
        ws = self.scaffold()
        os.remove(os.path.join(ws, "bootstrap", "template.lock.json"))
        known, unknown = os.path.join(ws, "scripts", "session-start.sh"), os.path.join(ws, "scripts", "map.mjs")
        for path in (known, unknown):
            with open(path, "a", encoding="utf-8") as fh:
                fh.write("# otra versión\n")
        history = os.path.join(self.tmp, "history.json")
        with open(history, "w", encoding="utf-8") as fh:
            json.dump({"scripts/session-start.sh": [sha(known)]}, fh)
        argv, hist = sys.argv, scaffold.HISTORY
        try:
            scaffold.HISTORY, sys.argv = history, ["scaffold.py", "--target", ws, "--upgrade"]
            with open(os.devnull, "w") as devnull:
                stdout, sys.stdout = sys.stdout, devnull
                try:
                    scaffold.main()
                finally:
                    sys.stdout = stdout
        finally:
            scaffold.HISTORY, sys.argv = hist, argv
        self.assertEqual(sha(known), sha(os.path.join(TEMPLATE, "scripts", "session-start.sh")))
        self.assertNotEqual(sha(unknown), sha(os.path.join(TEMPLATE, "scripts", "map.mjs")))
        self.assertTrue(os.path.exists(os.path.join(ws, "bootstrap", "template.lock.json")))

    def test_history_covers_current_template(self):
        res = run(PLUGIN, sys.executable, os.path.join(INIT, "scripts", "template_history.py"), "--check", check=False)
        self.assertEqual(res.returncode, 0, res.stderr or res.stdout)

    def test_scaffold_never_overwrites(self):
        ws = os.path.join(self.tmp, "ws")
        os.makedirs(ws)
        with open(os.path.join(ws, "CLAUDE.md"), "w", encoding="utf-8") as fh:
            fh.write("mío\n")
        self.scaffold()
        self.assertEqual(text(os.path.join(ws, "CLAUDE.md")), "mío\n")
        self.assertNotIn("CLAUDE.md", json.loads(text(os.path.join(ws, "bootstrap", "template.lock.json")))["files"])


class Bootstrap(Base):
    def setUp(self):
        super().setUp()
        self.remote = os.path.join(self.tmp, "remote")
        os.makedirs(self.remote)
        run(self.remote, "git", "init", "-q")
        with open(os.path.join(self.remote, "f"), "w") as fh:
            fh.write("x\n")
        run(self.remote, "git", "add", "f")
        run(self.remote, "git", "-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-qm", "init")
        self.ws = self.scaffold()

    def bootstrap(self, *args, check=True):
        return run(self.ws, "bash", "bootstrap/bootstrap.sh", *args, check=check)

    def block(self):
        gi = text(os.path.join(self.ws, ".gitignore"))
        return gi[gi.index("# >>> repos"):gi.index("# <<< repos <<<")].splitlines()[1:]

    def manifest(self):
        return [l.split("\t")[0] for l in text(os.path.join(self.ws, "bootstrap", "repos.tsv")).splitlines() if l.strip() and not l.startswith("#")]

    def test_add_rename_remove(self):
        self.bootstrap("--add", self.remote, "--dir", "api")
        self.assertTrue(os.path.isdir(os.path.join(self.ws, "api", ".git")))
        self.assertEqual((self.manifest(), self.block()), (["api"], ["/api"]))

        self.bootstrap("--rename", "api", "pagos-api", "--dry-run")
        self.assertEqual(self.manifest(), ["api"])
        self.bootstrap("--rename", "api", "pagos-api")
        self.assertTrue(os.path.isdir(os.path.join(self.ws, "pagos-api", ".git")))
        self.assertFalse(os.path.exists(os.path.join(self.ws, "api")))
        self.assertEqual((self.manifest(), self.block()), (["pagos-api"], ["/pagos-api"]))

        out = self.bootstrap("--remove", "pagos-api").stdout
        self.assertEqual((self.manifest(), self.block()), ([], []))
        self.assertTrue(os.path.isdir(os.path.join(self.ws, "pagos-api")), "--remove borró un clon")
        self.assertIn("ya no está ignorada", out)

    def test_remove_unlinks_a_linked_repo(self):
        clones = os.path.join(self.tmp, "clones")
        os.makedirs(clones)
        run(clones, "git", "clone", "-q", self.remote, "api")
        self.bootstrap("--add", self.remote, "--dir", "api", "--link", clones)
        link = os.path.join(self.ws, "api")
        self.assertTrue(os.path.islink(link))
        self.bootstrap("--remove", "api")
        self.assertFalse(os.path.lexists(link))
        self.assertTrue(os.path.isdir(os.path.join(clones, "api", ".git")), "--remove borró el clon original")

    def test_rejects_bad_input(self):
        self.assertEqual(self.bootstrap("--remove", "nope", check=False).returncode, 2)
        self.bootstrap("--add", self.remote, "--dir", "api")
        self.assertEqual(self.bootstrap("--rename", "api", "scripts", check=False).returncode, 2)
        self.assertEqual(self.manifest(), ["api"])


class Parity(unittest.TestCase):
    """Las constantes que viven en más de un script tienen que decir lo mismo."""

    def setUp(self):
        self.validate = text(os.path.join(TEMPLATE, "scripts", "validate.mjs"))
        self.bootstrap = text(os.path.join(TEMPLATE, "bootstrap", "bootstrap.sh"))

    def js_regexes(self, const):
        """Las fuentes de las regex de una constante de validate.mjs, evaluada por Node."""
        decl = re.search(rf"const {const} = \[.*?\]\n", self.validate, re.S).group(0)
        js = decl + f"console.log(JSON.stringify({const}.map((r) => (Array.isArray(r) ? r[1] : r).source)))"
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout
        return [src.replace("\\/", "/") for src in json.loads(out)]

    @unittest.skipUnless(HAS_NODE, "necesita Node")
    def test_secret_content_patterns(self):
        self.assertEqual([p.pattern for _, p in audit_mod.SECRET_CONTENT], self.js_regexes("SECRET_CONTENT"))

    @unittest.skipUnless(HAS_NODE, "necesita Node")
    def test_secret_path_patterns(self):
        self.assertEqual(audit_mod.SECRET_PATH, self.js_regexes("SECRET_PATH"))

    @unittest.skipUnless(HAS_NODE, "necesita Node")
    def test_audit_output_patterns(self):
        self.assertEqual(audit_mod.AUDIT_OUTPUT, self.js_regexes("AUDIT_OUTPUT"))

    def test_gitignore_markers(self):
        for marker in (audit_mod.BEGIN_REPOS_GI, audit_mod.END_REPOS_GI):
            self.assertIn(marker, self.validate)
            self.assertIn(marker, self.bootstrap)
            self.assertIn(marker, text(os.path.join(TEMPLATE, "dot-gitignore.tmpl")))

    def test_shared_sets(self):
        self.assertEqual(audit_mod.USER_OWNED, scaffold.USER_OWNED)
        self.assertEqual(audit_mod.RENAMES, scaffold.RENAMES)
        self.assertEqual(audit_mod.TEMPLATE_SCRIPTS, scaffold.EXECUTABLE)

    def test_workspace_skills_exist_in_template(self):
        for skill in audit_mod.WS_SKILLS:
            self.assertTrue(os.path.exists(os.path.join(TEMPLATE, "dot-claude", "skills", skill, "SKILL.md.tmpl")), skill)

    def test_stack_keys_match_reference(self):
        ref = text(os.path.join(INIT, "references", "expertos-por-stack.md"))
        for framework in ("Express", "Fastify", "Terraform", "NestJS", "Next.js"):
            self.assertIn(f"`{audit_mod.slug(framework)}-expert`", ref, framework)


if __name__ == "__main__":
    unittest.main()
