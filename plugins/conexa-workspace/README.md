# conexa-workspace

Skills para crear y auditar la raíz de un workspace multi-repo pensado para agentes.

| Skill | Invocación | Qué hace |
|---|---|---|
| init-workspace | `/conexa-workspace:init-workspace` | Crea o adapta la raíz del workspace: AGENTS.md, CLAUDE.md, bootstrap, subagentes, knowledge/ y mapa de contexto. No crea repos remotos ni pushea. |
| audit-workspace | `/conexa-workspace:audit-workspace` | Audita un workspace contra el estándar de init-workspace y devuelve puntaje, hallazgos y plan de acción. Solo lectura. |

Las dos skills tienen que vivir en el mismo plugin: `audit-workspace/scripts/audit.py` busca la plantilla en `../../init-workspace/assets/template`.
