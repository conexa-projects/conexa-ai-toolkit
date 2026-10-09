# conexa-guardrails

Plugin de seguridad de Conexa. Hoy trae una skill:

| Skill | Qué hace | Origen |
|---|---|---|
| `security-audit` | Auditoría de seguridad de código fuente: modo guía para preguntas y revisiones puntuales; flujo completo de 6 fases (reconocimiento, hunting, validación, JSON validado, verificación independiente, informe) solo cuando se pide explícitamente | [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill), MIT, versión fija en `vendor.lock` |

Las reglas propias de Conexa están en [`skills/security-audit/CONEXA.md`](skills/security-audit/CONEXA.md):
enmascarar secretos encontrados, confidencialidad de los informes, nada de ejecución fuera de un
sandbox verificado, perfil `quick` y presupuesto por defecto, informes en español.

## Cómo se reparte con el workspace

| Pedido | Quién |
|---|---|
| "¿Esto es seguro?", revisar un diff o un PR, antes de mergear algo de auth/pagos/CI | subagente `security-reviewer` del workspace (`init-workspace`) |
| Auditoría completa, pen-test, revisión de punta a punta, informe para entregar | skill `security-audit` de este plugin |

`audit-workspace` chequea que el `security-reviewer` tenga las reglas actuales y que ningún informe
quede versionado.

## Instalación

**Claude Code**:

```bash
claude plugin marketplace add <org>/conexa-ai-toolkit
claude plugin install conexa-guardrails@conexa
```

**Claude Desktop / Cowork / claude.ai**: subir `skills/security-audit/` comprimida como skill de la
organización (Settings → Skills). Es la misma carpeta, con `CONEXA.md` adentro.

Recomendado en Claude Code: activar el sandbox nativo (`/sandbox`). Sin él, la skill hace solo
análisis estático y marca como `needs_validation` lo que requiera ejecutar.

## Actualizar la versión de Cloudflare

No uses `npx skills add`: baja la última versión sin fijarla y ejecuta un CLI de npm.

1. Cloná upstream en una carpeta aparte y mirá el diff desde el commit de `vendor.lock`:
   `git diff <commit-del-lock>..HEAD -- skills/security-audit`.
2. Revisalo con el mismo criterio de la primera vez: código nuevo en los `.cjs` (red, `child_process`,
   escrituras, `process.env`), URLs nuevas, caracteres invisibles, instrucciones que pidan subir o
   enviar datos, cambios en las reglas de ejecución y sandbox.
3. Corré los tests de upstream: `node --test` dentro de `skills/security-audit`.
4. Copiá los archivos nuevos, volvé a insertar el bloque `conexa` en el `SKILL.md` (debajo del
   título) y regenerá `vendor.lock` con los hashes de upstream.
5. `bash scripts/verify-vendor.sh` tiene que dar OK. Subí la versión en `plugin.json`.
6. Registrá la actualización en el log de decisiones del marketplace: commit, qué cambió, quién revisó.

## Verificación

```bash
bash scripts/verify-vendor.sh   # la copia coincide con upstream + agregados de Conexa
cd skills/security-audit && node --test   # tests de los validadores (65)
```

## Revisión de seguridad inicial (2026-10-09, commit c1c8a8c)

- Sin red, telemetría, hooks, servidores MCP ni dependencias. Los dos validadores solo leen el archivo
  que se les pasa: sin seguir symlinks, solo archivos regulares, con tope de tamaño y exigiendo
  UTF-8. No escriben nada. `child_process` aparece solo en los tests.
- Sin caracteres invisibles, comentarios HTML, base64 ni instrucciones ocultas. Las únicas URLs son
  las de Cloudflare.
- Hueco cubierto por `CONEXA.md`: no había regla para no copiar a los informes los secretos
  encontrados en el código.
