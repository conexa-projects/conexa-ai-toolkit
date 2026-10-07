# conexa-ai-toolkit

Marketplace interno de Conexa para Claude Code.

## Instalar

```bash
claude plugin marketplace add conexa-projects/conexa-ai-toolkit
claude plugin install conexa-workspace@conexa
```

## Plugins

| Plugin | Contenido |
|---|---|
| [conexa-workspace](plugins/conexa-workspace) | init-workspace, audit-workspace |

## Contribuir

- Cada plugin vive en `plugins/<nombre>/` con su `.claude-plugin/plugin.json`.
- Cada skill vive en `plugins/<plugin>/skills/<skill>/SKILL.md`. Todo lo que use (scripts, referencias, assets) va dentro de ese directorio: un plugin no puede referenciar archivos fuera de sí mismo.
- El `name` de la entrada en `marketplace.json` y el de `plugin.json` tienen que coincidir, y no se cambian una vez publicado.
- Antes de abrir un PR: `claude plugin validate .`
