# conexa-ai-toolkit

Marketplace interno de Conexa para Claude Code.

## Instalar

```bash
claude plugin marketplace add conexa-projects/conexa-ai-toolkit
claude plugin install conexa-workspace@conexa
claude plugin install conexa-guardrails@conexa
```

## Plugins

| Plugin | Contenido |
|---|---|
| [conexa-workspace](plugins/conexa-workspace) | init-workspace, audit-workspace |
| [conexa-guardrails](plugins/conexa-guardrails) | security-audit (Cloudflare, versión fija) + reglas de Conexa |

Se instalan juntos: el `security-reviewer` que genera init-workspace deriva las auditorías completas a `security-audit`.

## Contribuir

- Cada plugin vive en `plugins/<nombre>/` con su `.claude-plugin/plugin.json`.
- Cada skill vive en `plugins/<plugin>/skills/<skill>/SKILL.md`. Todo lo que use (scripts, referencias, assets) va dentro de ese directorio: un plugin no puede referenciar archivos fuera de sí mismo.
- El `name` de la entrada en `marketplace.json` y el de `plugin.json` tienen que coincidir, y no se cambian una vez publicado.
- Antes de abrir un PR: `claude plugin validate .` y `bash scripts/check.sh` (vendor lock, tests y un workspace de prueba). El CI corre los dos.

## Skills o plugins de terceros

Nada de terceros entra por `npx skills add` ni apuntando al repo de origen: se vendoriza una versión
fija y revisada, como `plugins/conexa-guardrails`.

1. Revisión de seguridad antes de sumarla: código ejecutable (red, `child_process`, escrituras,
   `process.env`), URLs, caracteres invisibles, instrucciones que pidan subir o enviar datos, hooks
   y servidores MCP.
2. Copia del commit revisado, con su licencia, y un `vendor.lock` con los hashes de upstream.
3. Lo propio de Conexa va en archivos aparte (ej. `CONEXA.md`), no editando los de upstream.
4. Un script que verifique la copia contra el lock, corriendo en CI.

El procedimiento de actualización está en [`plugins/conexa-guardrails/README.md`](plugins/conexa-guardrails/README.md).
