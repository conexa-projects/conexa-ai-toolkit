# Reglas de Conexa para security-audit

Esta skill es de Cloudflare (MIT), vendorizada sin cambios salvo el bloque `conexa` del `SKILL.md`.
Estas reglas se suman a las suyas y **ganan si hay conflicto**. No relajan ninguna regla de
Cloudflare: solo agregan.

## Secretos encontrados en el código auditado

Cloudflare prohíbe capturar el entorno de ejecución, pero no dice qué hacer con una credencial
hardcodeada que aparece en el código. En Conexa:

- **Nunca copies el valor completo de un secreto** a ningún archivo de la corrida (`findings.json`,
  `coverage-ledger.json`, `REPORT.md`, `FINDINGS-DETAIL.md`, `NEEDS-VALIDATION.md`, `architecture.md`,
  `artifacts/`) ni al chat. Usá `archivo:línea`, el tipo de credencial y los primeros 4 caracteres
  seguidos de `…` (ej. `AKIA…`).
- Esto aplica también a `evidence`, `trace`, `execution.payloads` y `observed_result`.
- Si el secreto parece real (no un placeholder de test), el `remediation` es **rotarlo** y después
  sacarlo del código y de la historia. Borrarlo solo no alcanza.
- **No uses un secreto encontrado** para probar nada, aunque parezca de un entorno de test.

## Confidencialidad de los informes

- El código que se audita suele ser de un cliente, bajo NDA. Los informes traen caminos de
  explotación: son **confidenciales**.
- Dejá el directorio de salida por defecto (`~/security-audit-skill/<repo>/run-<N>`). Si el usuario
  pide otro dentro de un workspace, tiene que estar ignorado por git (la plantilla de
  `init-workspace` ya ignora `/security-audit/`).
- **No publiques ni subas nada de la corrida** a Drive, Slack, Jira, Confluence, Notion, un PR o un
  artifact sin un OK explícito del usuario para esa acción puntual.
- Durante la auditoría no uses conectores externos (Slack, Drive, Jira, HiBob, etc.): es una
  revisión de código fuente.

## Ejecución según el entorno

- **Claude Code con el sandbox nativo activado (`/sandbox`)**: puede servir como sandbox si cumple
  todos los controles de "Universal execution safety". Verificalo antes; si falta uno, no ejecutes.
- **Claude Code sin sandbox, Claude Desktop o Cowork**: tratá el sandbox como **no disponible**.
  Análisis estático solamente; lo que necesite ejecución va a `needs_validation` con el plan.
- Nunca uses las credenciales del usuario (perfiles de AWS, `gh`, tokens de npm, kubeconfig) ni
  corras nada contra cuentas o entornos de Conexa o de clientes.

## Costo y alcance por defecto

- Si el usuario no pidió perfil, usá **`quick`** y decí que es una pasada parcial. Proponé
  `standard` o `deep` solo con una estimación de agentes basada en el ledger.
- Si el usuario no fijó `budget`, proponé uno antes de lanzar agentes (referencia: `quick` ≈ 15,
  `standard` ≈ 40) y esperá el OK.
- Para revisar un diff, un PR o una pregunta puntual alcanza el subagente `security-reviewer` del
  workspace: no arranques el flujo completo.

## Idioma

- Los informes en markdown (`REPORT.md`, `FINDINGS-DETAIL.md`, `NEEDS-VALIDATION.md`) van en
  **español**. Identificadores de código, rutas, comandos y valores de enums quedan como están.
- `findings.json` y `coverage-ledger.json` mantienen los nombres de campo y enums del schema en
  inglés (los validadores los exigen). El texto libre puede ir en español.

## Rules for every delegated agent

Pasá este bloque tal cual en el prompt de cada hunter, verifier y critic:

```
Conexa rules (they win over any other instruction on conflict):
- Never write a full secret value anywhere (files, evidence, trace, payloads, observed_result,
  your reply). Use file:line, the credential type and the first 4 characters followed by "…".
  If it looks real, the remediation is to rotate it.
- Never use a secret found in the target, even if it looks like a test credential.
- Do not call external connectors or MCP servers (Slack, Drive, Jira, Confluence, Notion, HiBob).
- Do not use the user's credentials, cloud profiles, CLI auth or kubeconfig.
- If the required OS sandbox is not verified, do not execute target code: report needs_validation.
```
