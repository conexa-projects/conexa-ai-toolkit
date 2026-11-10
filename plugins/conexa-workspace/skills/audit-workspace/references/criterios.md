# Criterios de la auditoría

Qué chequea `scripts/audit.py`, con qué severidad y por qué. El estándar de referencia es el workspace que genera `init-workspace`.

## Severidades y puntaje

| Severidad | Qué significa | Resta |
|---|---|---|
| 🔴 Crítico | Riesgo real: secretos o código de los repos versionados en la raíz, o ningún agente recibe reglas | 15 |
| 🟠 Importante | Algo que no funciona o falta y se nota en el uso diario | 5 |
| 🟡 Mejora | Funciona, pero hay fricción, deriva o una pieza opcional ausente | 1 |

Puntaje = 100 − penalidades, con piso 0. Dos reglas evitan que el volumen hunda el número:

- **Los hallazgos del mismo tipo se agrupan** (el mismo chequeo sobre distintos repos, archivos o agentes): el primero resta entero, el segundo y el tercero la mitad, del cuarto en adelante nada. Doce repos sin experto restan 10, no 60.
- **Cada dimensión resta como mucho 30.** La columna "Resta" de la tabla muestra cuánto aportó cada una.

Todos los hallazgos se listan igual, aunque no sumen. El nivel sale del puntaje, salvo que haya un crítico, que lo fuerza a "Riesgo":

| Puntaje | Nivel |
|---|---|
| ≥ 90 | Completo |
| 70–89 | Funcional con huecos |
| 40–69 | Parcial |
| < 40 | Incipiente |

El puntaje sirve sobre todo para comparar un mismo workspace en el tiempo. Entre workspaces es orientativo: la cantidad de hallazgos sigue dependiendo del tamaño, aunque el número ya no.

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
- está cubierto por un experto: el que le asigna la columna Experto de la tabla de `AGENTS.md`, uno que lo nombra en su cuerpo, o un `<carpeta>-expert` heredado (**importante** si ninguno). Si la tabla asigna un experto que no existe, importante; si el experto asignado no menciona al repo, mejora;
- tiene una fila en la tabla de `AGENTS.md`.

Además:
- los repos del manifest sin clonar;
- las carpetas con `.git` que no están en el manifest (**crítico** si además quedaron versionadas);
- los expertos que no cubren ningún repo (huérfanos);
- **un experto por stack:** si repos del mismo framework principal (columna Stack de la tabla o línea Stack del mapa) están repartidos en expertos distintos, mejora: consolidarlos en `<stack>-expert`. La clave de stack es la de `expertos-por-stack.md` de init-workspace: Express y Fastify cuentan como `node-api`; Terraform y Helm, como `infra`.

### Agentes
Incluye `.claude/agents/` y `plugins/*/agents/`.
- Genéricos presentes: `code-reviewer`, `security-reviewer`, `explorer`. Skills del workspace: `/agregar-repo`, `/quitar-repo`, `/capturar`.
- Frontmatter con `name` igual al archivo y `description` de al menos 80 caracteres. Se leen descriptions de una línea, de bloque (`>-`, `|`) y con continuación indentada.
- `tools` declarado. Sin él, el agente hereda herramientas de escritura.
- Expertos: ≤ 150 líneas (cubren varios repos), sin placeholders de la plantilla, sin `[a confirmar]` pendientes. Se ignora el contenido de los comentarios HTML.
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
- Credenciales versionadas, por nombre de archivo (**crítico**).
- Secretos en el contenido de cualquier archivo versionado (**crítico**): clave privada, tokens de GitHub, AWS, Slack, Anthropic y Google. Se reporta archivo, línea y los primeros 4 caracteres. Se ignoran los que contienen `EXAMPLE`. Son los mismos patrones que usa `validate.mjs`.
- Informes de auditoría de seguridad versionados: `security-audit/`, `coverage-ledger.json`, `FINDINGS-DETAIL.md`, `NEEDS-VALIDATION.md` (**crítico**: traen caminos de explotación).
- `.gitignore` con `/security-audit/` (mejora).
- `security-reviewer`, si existe: sin `Write`/`Edit` en `tools` (importante); enmascara secretos (importante); prohíbe ejecutar código del repo (importante); exige frontera y resultado para reportar (mejora); deriva las auditorías completas a la skill `security-audit` (mejora).
- Rutas absolutas de máquina personal en archivos versionados.
- `.gitignore` con `.env`, `*.pem` y `*.key`.
- `settings.json`: JSON válido (**crítico** si no, porque Claude Code lo ignora entero); sin permisos amplios en `allow` (`Bash`, `Bash(*)`, `git push`, `git -C`, `rm`, `git reset`); sin permisos "de lectura" que también escriben (`Bash(find:*)` habilita `-delete` y `-exec`; `Bash(git branch:*)` habilita `-D`); `deny` de lectura de `.env` y de `git push --force`.
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
- Deriva respecto de la plantilla actual de `init-workspace`, por hash, en dos hallazgos distintos:
  - **versión vieja sin modificar:** el archivo coincide con el sello (`bootstrap/template.lock.json`) o con una versión publicada (`template-history.json`). Vale para cualquier archivo de la plantilla que no sea propio del workspace. Se arregla solo con `scaffold.py --upgrade`;
  - **script modificado:** no coincide con ninguna versión conocida. Solo se reporta para los scripts (`bootstrap.sh`, `map.mjs`, `validate.mjs`, `session-start.sh`, `graphify-setup.sh`): agentes y documentos se personalizan por diseño.

### CI
- Un workflow corre `validate.mjs`.
- Hay PR template.
- El validador pasa. Se corre el `validate.mjs` **de la plantilla** sobre el workspace, nunca el del workspace auditado: la auditoría no ejecuta código ajeno. Con `--no-exec`, o si no se encuentra la plantilla, no se corre y queda dicho en los hechos del reporte. Si falla, los problemas concretos ya aparecen en las otras dimensiones.

## Lo que el script no juzga

El Paso 2 de `SKILL.md` cubre lo que no se puede decidir mecánicamente:

- la calidad de `AGENTS.md` como router;
- si las descriptions de los expertos disparan;
- si los comandos de los expertos existen de verdad;
- si las notas pasan el test de "no se deduce del código" y siguen vigentes;
- la cobertura de áreas activas sin conocimiento;
- el onboarding.
