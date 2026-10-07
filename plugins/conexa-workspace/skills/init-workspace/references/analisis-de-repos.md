# Analizar un repo y escribir su experto

El experto existe para que la sesión principal delegue el trabajo sobre un repo en alguien que ya sabe dónde mirar. Tiene que ser **liviano**: rutea y apunta, no copia. Lo que duplica el código o el README se desincroniza.

## Qué leer, en este orden

Pará cuando tengas lo necesario. No leas el repo entero.

1. `.context/map/<carpeta>.md`: stack, manifests, scripts, entrypoints, tests, CI, hotspots, relaciones.
2. `AGENTS.md` / `CLAUDE.md` del repo, incluidos los anidados que liste el mapa. **Sus reglas mandan dentro del repo.** El experto las referencia, no las repite.
3. `README.md` del repo: propósito, setup, comandos.
4. Manifests (`package.json`, `pyproject.toml`, `go.mod`, `*.csproj`, `pom.xml`, `Makefile`...): scripts reales, versiones, gestor de paquetes.
5. CI (`.github/workflows/`, etc.): qué corre y con qué comandos. Es la mejor fuente de "cómo se testea y se lintea de verdad".
6. Dos o tres entrypoints del mapa, para confirmar el layout. Solo si el layout no quedó claro.
7. `.env.example` o equivalente: nombres de variables, nunca valores.

## Qué va en el experto

Usá `knowledge/templates/repo-expert.md`. Secciones:

| Sección | Contenido | Fuente |
|---|---|---|
| frontmatter `description` | Qué repo es + disparadores concretos: nombre de la carpeta, stack, términos de dominio, síntomas típicos | mapa + README |
| Qué es | 2–4 líneas: propósito, stack, cómo se ejecuta (puerto, CLI, lib) | README + manifests |
| Antes de responder | Punteros a las reglas del repo (`<carpeta>/AGENTS.md`) y a notas de `knowledge/` que apliquen | lo que exista |
| Layout | Directorios principales y qué vive en cada uno, en una línea cada uno | mapa |
| Comandos | Instalar, dev, test (y un solo test), lint, build. **Solo los que existen** en scripts o CI | manifests + CI |
| Convenciones | Las que se ven en el código o están escritas en el repo: naming, capas, estilo de tests | reglas del repo + muestreo |
| Relaciones | Con qué otros repos del workspace habla y cómo | mapa → "Relaciones" |
| Cómo trabajás | Fijo: solo lectura, mapa antes de grepear, no escribís `knowledge/` | plantilla |

**La `description` decide si el experto se usa.** Escribila con las palabras que usaría alguien que tiene un problema en ese repo, no con la jerga formal. Si dos expertos pueden confundirse (ej. dos backends), cada uno dice qué **no** cubre.

Tamaño objetivo: menos de 80 líneas. Si crece, lo que sobra es conocimiento y va a `knowledge/`.

## Frontmatter

```yaml
---
name: <carpeta>-expert          # igual al nombre del archivo, sin .md
description: <una línea, YAML-safe; entrecomillar si tiene ':'>
tools: Read, Grep, Glob, Bash
model: sonnet
---
```

## Fila en AGENTS.md

Entre `<!-- BEGIN repos -->` y `<!-- END repos -->`:

```
| `<carpeta>/` | <qué es, una línea> | <stack corto> | `<carpeta>-expert` |
```

## Verificación

- Cada comando del experto aparece en un manifest o en el CI. Si lo inferiste, marcalo `[a confirmar]`.
- Cada ruta citada existe (`ls` antes de escribirla).
- Ninguna regla del `AGENTS.md` del repo quedó copiada: está referenciada.
- No hay valores de variables de entorno, tokens ni hosts internos que no estén ya en el README público del repo.

## Semillas de conocimiento

No generes notas de `knowledge/` durante el setup salvo que encuentres algo que cumpla el test: **no se deduce leyendo el código**. Por ejemplo, un README que avisa de una trampa de entorno. En ese caso, una nota por trampa, con la fuente citada. Si dudás, no la escribas: el conocimiento bueno sale del trabajo real, no del scaffold.
