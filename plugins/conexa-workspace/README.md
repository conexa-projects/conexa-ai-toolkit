# conexa-workspace

Skills para crear y auditar la raíz de un workspace multi-repo pensado para agentes.

| Skill | Invocación | Qué hace |
|---|---|---|
| init-workspace | `/conexa-workspace:init-workspace` | Crea o adapta la raíz del workspace: AGENTS.md, CLAUDE.md, bootstrap, subagentes, knowledge/ y mapa de contexto. También actualiza un workspace ya generado a la plantilla actual, sin pisar lo modificado a mano. No crea repos remotos ni pushea. |
| audit-workspace | `/conexa-workspace:audit-workspace` | Audita un workspace contra el estándar de init-workspace y devuelve puntaje, hallazgos y plan de acción. Solo lectura. |

El `security-reviewer` que genera init-workspace hace la revisión acotada (un diff, un PR, "¿esto es seguro?") y deriva las auditorías completas a la skill `security-audit` del plugin [conexa-guardrails](../conexa-guardrails). audit-workspace chequea que tenga las reglas actuales y que ningún informe de auditoría quede versionado.

Las dos skills tienen que vivir en el mismo plugin: `audit-workspace/scripts/audit.py` busca la plantilla en `../../init-workspace/assets/template`.

## Desarrollo

```bash
python3 -m unittest discover -s plugins/conexa-workspace/tests -v    # scaffold, upgrade, audit, validador, bootstrap
python3 plugins/conexa-workspace/skills/audit-workspace/evals/files/make_fixture.py /tmp/ws   # workspace con defectos sembrados
```

**Al cambiar la plantilla** (`init-workspace/assets/template/`):

1. Subí la versión en `.claude-plugin/plugin.json`: queda en el sello de cada workspace.
2. Corré `python3 plugins/conexa-workspace/skills/init-workspace/scripts/template_history.py`. Registra los hashes de la versión nueva en `assets/template-history.json`, que es lo que deja que `--upgrade` reconozca un archivo viejo sin tocar en workspaces sin sello. El CI falla si falta.
3. Si tocás una constante que vive en más de un script (patrones de secretos, marcadores del `.gitignore`, archivos propios del workspace), cambiala en todos: los tests de paridad lo verifican.
