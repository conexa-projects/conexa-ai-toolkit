<!--
PR de la raíz del workspace: contexto, reglas, agentes y scripts.
El código de producto va en el PR de su propio repo.
-->

## Qué cambia
<!-- 1–2 líneas: qué y para qué. -->


## Tipo
- [ ] **Reglas** — `AGENTS.md`, `CLAUDE.md`
- [ ] **Agente o skill** — `.claude/`
- [ ] **Repos** — `bootstrap/repos.tsv`
- [ ] **Tooling** — `bootstrap/`, `scripts/`, `.github/`
- [ ] **Conocimiento** — `knowledge/`

## Checklist
- [ ] No agrego credenciales ni rutas absolutas de mi máquina
- [ ] `node scripts/validate.mjs` pasa en local
- [ ] Si agregué una nota, está en el índice de `knowledge/README.md`
- [ ] Si toqué un agente, sigue liviano: apunta al conocimiento en vez de repetirlo
- [ ] Si sumé un repo, tiene su experto y su fila en la tabla de `AGENTS.md`
