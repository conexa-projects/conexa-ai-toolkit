# Agrupar los repos por stack y escribir sus expertos

Hay **un experto por stack, no uno por repo**. Si el workspace tiene cinco backends NestJS, hay un solo `nest-expert` que los cubre a los cinco. El conocimiento de un stack (cómo se arma un módulo, cómo se testea, qué patrones se repiten) es el mismo en todos sus repos: repartirlo en cinco agentes lo duplica, y cinco descriptions casi iguales rutean mal.

El experto existe para que la sesión principal delegue el trabajo en alguien que ya sabe dónde mirar. Tiene que ser **liviano**: rutea y apunta, no copia. Lo que duplica el código o el README se desincroniza.

## 1. Agrupar por stack

Para cada repo clonado, leé la línea **Stack** de `.context/map/<carpeta>.md` y asignale una clave de stack:

| Lo que dice el mapa | Clave | Experto |
|---|---|---|
| NestJS | `nest` | `nest-expert` |
| Next.js | `next` | `next-expert` |
| React (sin Next), React Native / Expo | `react` / `react-native` | `react-expert` / `react-native-expert` |
| Angular, Vue, Nuxt, Svelte, Astro | `angular`, `vue`, `nuxt`, `svelte`, `astro` | `<clave>-expert` |
| Express, Fastify (sin Nest) | `node-api` | `node-api-expert` |
| Sin framework: Python, .NET, Go, Java… | el lenguaje/runtime: `python`, `dotnet`, `go`, `java` | `<clave>-expert` |
| Infra: Terraform, pipelines, Helm | `infra` | `infra-expert` |

Reglas:

- **La clave es el framework principal**, no el lenguaje: un backend Nest y un front React son los dos TypeScript, pero son expertos distintos. Si el mapa no detectó framework, mirá las dependencias del manifest antes de caer al lenguaje.
- **Un repo con dos stacks reales** (monorepo con API Nest y web Next) va en los dos expertos, y en la tabla de AGENTS.md su columna Experto lista los dos.
- **Un stack con un solo repo** igual se llama por el stack (`angular-expert`, no `<carpeta>-expert`): cuando llegue el segundo repo Angular, se suma al mismo experto.
- **No partas un stack por versión** (Nest 8 y Nest 10 van juntos): la diferencia de versión va en "Particularidades". Partilo solo si el usuario lo pide o si son mundos distintos (ej. React web y React Native).
- Si la clave no es obvia, proponé el agrupamiento al usuario antes de escribir: `nest-expert ← pagos-api, usuarios-api · react-expert ← backoffice`.

## 2. Qué leer de cada repo del grupo

Pará cuando tengas lo necesario. No leas los repos enteros; leé primero el más representativo del grupo (el de más hotspots en `.context/INDEX.md`) y de los demás solo lo que **difiere**.

1. `.context/map/<carpeta>.md`: stack, manifests, scripts, entrypoints, tests, CI, hotspots, relaciones.
2. `AGENTS.md` / `CLAUDE.md` del repo, incluidos los anidados que liste el mapa. **Sus reglas mandan dentro del repo.** El experto las referencia, no las repite.
3. `README.md` del repo: propósito, setup, comandos.
4. Manifests (`package.json`, `pyproject.toml`, `go.mod`, `*.csproj`, `pom.xml`, `Makefile`...): scripts reales, versiones, gestor de paquetes.
5. CI (`.github/workflows/`, etc.): qué corre y con qué comandos. Es la mejor fuente de "cómo se testea y se lintea de verdad".
6. Dos o tres entrypoints del mapa, para confirmar el layout. Solo si el layout no quedó claro.
7. `.env.example` o equivalente: nombres de variables, nunca valores.

## 3. Qué va en el experto

Usá `knowledge/templates/stack-expert.md`. Secciones:

| Sección | Contenido | Fuente |
|---|---|---|
| frontmatter `description` | El stack + las carpetas que cubre + disparadores concretos: términos del framework, del dominio, síntomas típicos | mapas + README |
| Intro | 2–3 líneas: versiones del stack, cómo se estructuran los repos en general | manifests |
| Repos que cubrís | Una fila por repo: carpeta, qué es, particularidades (puerto, versión, lo que se aparta de lo común) + punteros a su mapa y su `AGENTS.md` | mapa + README |
| Layout típico | Lo que comparten los repos, una línea por directorio | mapas |
| Comandos | Instalar, dev, test (y un solo test), lint, build. Los comunes una vez; los que difieren, por repo. **Solo los que existen** en scripts o CI | manifests + CI |
| Convenciones | Las que se repiten en los repos, y las divergencias con nombre de carpeta | reglas de los repos + muestreo |
| Relaciones | Con qué otros repos del workspace hablan, y cómo | mapas → "Relaciones" |
| Cómo trabajás | Fijo: identificar el repo, mapa antes de grepear, solo lectura, no escribe `knowledge/` | plantilla |

**La `description` decide si el experto se usa.** Escribila con las palabras que usaría alguien que tiene un problema en ese stack, y nombrá las carpetas: así dispara tanto con "el guard de Nest no deja pasar" como con "en pagos-api falla el login". Si dos expertos pueden confundirse (ej. `next-expert` y `react-expert`), cada uno dice qué **no** cubre.

Tamaño objetivo: menos de 100 líneas aunque cubra muchos repos. Si crece, lo que sobra es conocimiento y va a `knowledge/`; si crece porque los repos divergen mucho, es señal de que son dos stacks.

## Frontmatter

```yaml
---
name: <stack>-expert            # igual al nombre del archivo, sin .md
description: <una línea, YAML-safe; entrecomillar si tiene ':'>
tools: Read, Grep, Glob, Bash
model: sonnet
---
```

## Filas en AGENTS.md

Una fila **por repo** (la tabla es el índice de repos), entre `<!-- BEGIN repos -->` y `<!-- END repos -->`. La columna Experto apunta al experto del stack, así que se repite:

```
| `pagos-api/` | API de cobros | NestJS · pnpm | `nest-expert` |
| `usuarios-api/` | Alta y login de usuarios | NestJS · pnpm | `nest-expert` |
| `backoffice/` | Panel interno | React · Vite | `react-expert` |
```

## Sumar un repo a un experto existente

Cuando entra un repo de un stack que ya tiene experto (`/agregar-repo` o un repo nuevo en el setup):

1. Agregá su fila en "Repos que cubrís" con sus particularidades.
2. Sumá su carpeta (y los términos de dominio nuevos) a la `description`.
3. Si sus comandos o convenciones difieren de lo común, anotalo como divergencia; no reescribas lo común.
4. Su fila en AGENTS.md apunta al experto existente.

## Verificación

- Cada repo clonado está en "Repos que cubrís" de al menos un experto, y su fila de AGENTS.md lo nombra.
- Cada comando del experto aparece en un manifest o en el CI de los repos donde se dice que aplica. Si lo inferiste, marcalo `[a confirmar]`.
- Cada ruta citada existe (`ls` antes de escribirla).
- Ninguna regla del `AGENTS.md` de un repo quedó copiada: está referenciada.
- No hay valores de variables de entorno, tokens ni hosts internos que no estén ya en el README público del repo.

## Semillas de conocimiento

No generes notas de `knowledge/` durante el setup salvo que encuentres algo que cumpla el test: **no se deduce leyendo el código**. Por ejemplo, un README que avisa de una trampa de entorno. En ese caso, una nota por trampa, con la fuente citada. Si dudás, no la escribas: el conocimiento bueno sale del trabajo real, no del scaffold.
