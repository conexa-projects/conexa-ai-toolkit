# Cómo contribuir

## Dos velocidades

| Qué tocás | Cómo | Por qué |
|---|---|---|
| `knowledge/` | Directo a la rama base | Si hay que abrir un PR para dejar una lección, nadie la deja |
| `.claude/agents/`, `.claude/skills/` | PR con review | Un agente roto lo sufre todo el equipo |
| `AGENTS.md`, `CLAUDE.md` | PR | Son las reglas duras: cambiarlas es una decisión de equipo |
| `bootstrap/`, `scripts/`, `.github/` | PR | Si se rompen, se rompe el onboarding o el CI |

## Agregar una nota a `knowledge/`

1. Copiá [`knowledge/_template.md`](knowledge/_template.md).
2. Guardala en la carpeta del área, con nombre en kebab-case. Si el área no existe, creala.
3. Sumala al índice de [`knowledge/README.md`](knowledge/README.md). **No es opcional:** el CI falla
   si una nota queda fuera del índice.

**La `description` del frontmatter es lo más importante de la nota.** Es lo que hace que se encuentre
después. Escribila pensando en qué buscaría alguien que tiene el problema.

**El test:** ¿se deduce leyendo el código o corriendo un comando? Si sí, no la escribas.

## Registrar una decisión

Agregá una entrada al final de [`knowledge/decisiones.md`](knowledge/decisiones.md). Nunca reescribas
una entrada: si la decisión cambia, agregá una nueva y marcá la vieja como reemplazada.

## Agregar o cambiar un agente

- Van en `.claude/agents/<nombre>.md`, con frontmatter `name` (igual al archivo sin `.md`) y
  `description`; opcionales `tools` y `model`.
- **Livianos.** Un agente rutea y apunta al conocimiento; no lo copia. Una regla copiada adentro de un
  agente ahora vive en dos lados, y mañana van a decir cosas distintas.
- **La `description` decide si el agente se dispara.** Nombrá los síntomas y las palabras concretas
  ante las que tiene que aparecer, no el área en abstracto.
- Para un repo nuevo, usá `/agregar-repo`: arma el experto desde
  [`knowledge/templates/repo-expert.md`](knowledge/templates/repo-expert.md).

## Qué corre CI

```bash
node scripts/validate.mjs
```

Correlo local antes de abrir el PR.
