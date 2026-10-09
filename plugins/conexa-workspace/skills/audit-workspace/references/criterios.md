# Criterios de la auditoría

Qué chequea `scripts/audit.py`, con qué severidad y por qué. El estándar de referencia es el workspace que genera `init-workspace`.

## Severidades y puntaje

| Severidad | Qué significa | Resta |
|---|---|---|
| 🔴 Crítico | Riesgo real: secretos o código de los repos versionados en la raíz, o ningún agente recibe reglas | 15 |
| 🟠 Importante | Algo que no funciona o falta y se nota en el uso diario | 5 |
| 🟡 Mejora | Funciona, pero hay fricción, deriva o una pieza opcional ausente | 1 |

Puntaje = 100 − penalidades, con piso 0. El nivel sale del puntaje, salvo que haya un crítico, que lo fuerza a "Riesgo":

| Puntaje | Nivel |
|---|---|
| ≥ 90 | Completo |
| 70–89 | Funcional con huecos |
| 40–69 | Parcial |
| < 40 | Incipiente |

El puntaje sirve para comparar un mismo workspace en el tiempo, no workspaces entre sí: uno con 100 repos acumula más hallazgos por volumen.

## Dimensiones

### Estructura
- La raíz es un repo git.
- `AGENTS.md` existe. Si falta pero hay `CLAUDE.md` es importante; si no hay ninguno de los dos, crítico.
- `CLAUDE.md` importa `@AGENTS.md` y agrega poco más (≤ 45 líneas).
- `AGENTS.md` no pasa de 250 líneas, tiene la tabla de repos con marcadores, la sección de orientación rápida y la de memoria.
- Existen las piezas del estándar: README, CONTRIBUTING, MAINTENANCE, `.gitignore`, bootstrap, `map.mjs`, `validate.mjs`, `session-start.sh`, `settings.json`, índice y plantillas de `knowledge/`.
- Manifest: `bootstrap/repos.tsv`. Se aceptan y se reportan como no estándar: `bootstrap/manifest.tsv`, `repos.txt`, `fuentes.txt` o una lista `REPOS=(…)` embebida en `bootstrap.sh`.

### Repos
Por cada repo del manifest que está presente:
- es un repo git, y su `origin` coincide con el manifest (comparación normalizada: SSH == HTTPS);
- está en la rama del manifest, si el manifest fija una;
- está en el bloque de repos del `.gitignore` (**crítico** si no) y no está versionado en la raíz (**crítico**);
- tiene un experto `<carpeta>-expert` (se acepta otro nombre que contenga la carpeta, como mejora) y una fila en la tabla de `AGENTS.md`.

Además:
- los repos del manifest sin clonar;
- las carpetas con `.git` que no están en el manifest (**crítico** si además quedaron versionadas);
- los expertos sin repo del mismo nombre, que requieren confirmación en la revisión de juicio.

### Agentes
Incluye `.claude/agents/` y `plugins/*/agents/`.
- Genéricos presentes: `code-reviewer`, `security-reviewer`, `explorer`. Skills del workspace: `/agregar-repo`, `/capturar`.
- Frontmatter con `name` igual al archivo y `description` de al menos 80 caracteres.
- `tools` declarado. Sin él, el agente hereda herramientas de escritura.
- Expertos: ≤ 120 líneas, sin placeholders de la plantilla, sin `[a confirmar]` pendientes. Se ignora el contenido de los comentarios HTML.
- Pares de expertos con descriptions casi iguales (> 70 % de palabras en común), que rutean mal.

### Memoria
- Existe `knowledge/`. Si no, se buscan candidatas: `docs/knowledge`, `docs`, `kb`.
- Notas en el índice (importante) y con `description` (mejora).
- Log de decisiones presente.
- Memoria vacía: mejora; importante si el workspace tiene más de 30 días.
- `knowledge/` sin commits hace más de 45 días en un workspace de más de 30: el capture loop no está pasando.
- Borradores versionados en `drafts/`.
- **Referencias a código rotas:** menciones entre backticks a `repo/ruta` en notas y agentes que ya no existen en el repo clonado. Es la señal más directa de conocimiento desactualizado.

### Seguridad
- Credenciales versionadas (**crítico**).
- Informes de auditoría de seguridad versionados: `security-audit/`, `coverage-ledger.json`, `FINDINGS-DETAIL.md`, `NEEDS-VALIDATION.md` (**crítico**: traen caminos de explotación).
- `.gitignore` con `/security-audit/` (mejora).
- `security-reviewer`, si existe: sin `Write`/`Edit` en `tools` (importante); enmascara secretos (importante); prohíbe ejecutar código del repo (importante); exige frontera y resultado para reportar (mejora); deriva las auditorías completas a la skill `security-audit` (mejora).
- Rutas absolutas de máquina personal en archivos versionados.
- `.gitignore` con `.env`, `*.pem` y `*.key`.
- `settings.json`: JSON válido (**crítico** si no, porque Claude Code lo ignora entero); sin permisos amplios en `allow` (`Bash`, `Bash(*)`, `git push`, `git -C`, `rm`, `git reset`); `deny` de lectura de `.env` y de `git push --force`.
- Hooks con rutas absolutas en el `settings.json` compartido, que fallan en otras máquinas.

### Harness
- Hook de inicio registrado.
- Mapa de `.context/` generado y al día. Se compara el `HEAD` cacheado de cada repo con el actual.
- `.context/` ignorado; nada generado (`.context/`, `graphify-out/`) versionado.
- Si hay grafo de graphify:
  - existe `.graphifyignore`;
  - `AGENTS.md` dice cómo usarlo;
  - cada repo presente tiene nodos (si no, se construyó respetando el `.gitignore` de la raíz);
  - está al día;
  - no hay hooks de graphify en el settings compartido.
- Scripts distintos a la plantilla actual de `init-workspace` (hash). Es una mejora, porque puede ser una personalización intencional.

### CI
- Un workflow corre `validate.mjs`.
- Hay PR template.
- El validador del workspace pasa localmente. Si falla, los problemas concretos ya aparecen en las otras dimensiones.

## Lo que el script no juzga

El Paso 2 de `SKILL.md` cubre lo que no se puede decidir mecánicamente:

- la calidad de `AGENTS.md` como router;
- si las descriptions de los expertos disparan;
- si los comandos de los expertos existen de verdad;
- si las notas pasan el test de "no se deduce del código" y siguen vigentes;
- la cobertura de áreas activas sin conocimiento;
- el onboarding.
