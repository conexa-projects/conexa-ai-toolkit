#!/usr/bin/env node
// map.mjs — genera el mapa de contexto de los repos del workspace en .context/.
//
// Determinístico y sin dependencias (Node >= 18, built-ins). No llama a ninguna API.
// Caché por HEAD: un repo cuyo HEAD no cambió no se vuelve a mapear.
//
// Uso:
//   node scripts/map.mjs                 # mapea los repos que cambiaron
//   node scripts/map.mjs --force         # mapea todos
//   node scripts/map.mjs --repo <dir>    # solo uno (forzado)
//   node scripts/map.mjs --quiet         # una sola línea de resumen (para el hook de inicio)

import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { basename, dirname, join, posix } from 'node:path'
import { fileURLToPath } from 'node:url'

const MAP_VERSION = 2
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const MANIFEST = join(ROOT, 'bootstrap', 'repos.tsv')
const OUT = join(ROOT, '.context')
const MAX_READ = 256 * 1024

const args = process.argv.slice(2)
const FORCE = args.includes('--force')
const QUIET = args.includes('--quiet')
const ONLY = args.includes('--repo') ? args[args.indexOf('--repo') + 1] : null

// ── utilidades ───────────────────────────────────────────────

function git(cwd, ...argv) {
  try {
    return execFileSync('git', ['-C', cwd, ...argv], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], maxBuffer: 64 * 1024 * 1024 }).trim()
  } catch {
    return ''
  }
}

function read(path) {
  try {
    if (statSync(path).size > MAX_READ) return ''
    return readFileSync(path, 'utf8')
  } catch {
    return ''
  }
}

function readManifest() {
  if (!existsSync(MANIFEST)) return []
  return readFileSync(MANIFEST, 'utf8')
    .replace(/\r/g, '')
    .split('\n')
    .filter((line) => line.trim() && !line.trim().startsWith('#'))
    .map((line) => {
      const [dir, url, branch = ''] = line.split('\t')
      return { dir: (dir || '').trim(), url: (url || '').trim(), branch: branch.trim() }
    })
    .filter((r) => r.dir && r.url)
}

const truncate = (s, n) => (s.length > n ? s.slice(0, n - 1) + '…' : s)
const cell = (s) => String(s).replace(/\|/g, '\\|').replace(/\n/g, ' ')

// ── detección ────────────────────────────────────────────────

const LANGS = {
  '.ts': 'TypeScript', '.tsx': 'TypeScript', '.js': 'JavaScript', '.jsx': 'JavaScript', '.mjs': 'JavaScript', '.cjs': 'JavaScript',
  '.vue': 'Vue', '.svelte': 'Svelte', '.py': 'Python', '.go': 'Go', '.rs': 'Rust', '.java': 'Java', '.kt': 'Kotlin', '.kts': 'Kotlin',
  '.cs': 'C#', '.fs': 'F#', '.php': 'PHP', '.rb': 'Ruby', '.swift': 'Swift', '.dart': 'Dart', '.scala': 'Scala', '.ex': 'Elixir',
  '.exs': 'Elixir', '.c': 'C', '.h': 'C', '.cpp': 'C++', '.hpp': 'C++', '.sql': 'SQL', '.tf': 'Terraform', '.sh': 'Shell',
  '.ps1': 'PowerShell', '.css': 'CSS', '.scss': 'SCSS', '.html': 'HTML', '.md': 'Markdown', '.mdx': 'Markdown',
}

const MANIFEST_FILES = [
  'package.json', 'pnpm-workspace.yaml', 'nx.json', 'turbo.json', 'lerna.json', 'pyproject.toml', 'requirements.txt', 'setup.py',
  'Pipfile', 'go.mod', 'Cargo.toml', 'pom.xml', 'build.gradle', 'build.gradle.kts', 'settings.gradle', 'settings.gradle.kts',
  'composer.json', 'Gemfile', 'mix.exs', 'pubspec.yaml', 'Makefile', 'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
  'compose.yml', 'compose.yaml', 'serverless.yml', 'template.yaml', 'main.tf', 'Chart.yaml', 'vercel.json', 'netlify.toml',
]

const ENTRY = /(^|\/)(main|index|app|server|program|manage|wsgi|asgi|cli|handler|lambda)\.(ts|tsx|js|jsx|mjs|cjs|py|go|rs|java|kt|cs|php|rb|swift|dart|scala|ex|exs|vue|svelte)$|(^|\/)Program\.cs$|(^|\/)cmd\/[^/]+\/main\.go$|(^|\/)src\/main\//i
const TEST = /(^|\/)(tests?|__tests__|spec|e2e)(\/|$)|[._-](test|spec)\.[a-z]+$|_test\.go$|Tests?\.cs$/i
const AGENT_RULES = /(^|\/)(AGENTS|CLAUDE)\.md$/
const ENV_EXAMPLE = /(^|\/)(\.env\.(example|sample|template|dist)|example\.env|\.env\.local\.example)$/i

function lockfileManager(files) {
  if (files.has('pnpm-lock.yaml')) return 'pnpm'
  if (files.has('yarn.lock')) return 'yarn'
  if (files.has('bun.lockb') || files.has('bun.lock')) return 'bun'
  if (files.has('package-lock.json')) return 'npm'
  return null
}

function parsePackageJson(text) {
  try {
    const pkg = JSON.parse(text)
    return {
      name: pkg.name || null,
      scripts: pkg.scripts || {},
      deps: Object.keys(pkg.dependencies || {}),
      devDeps: Object.keys(pkg.devDependencies || {}),
      workspaces: pkg.workspaces || null,
      engines: pkg.engines || null,
    }
  } catch {
    return null
  }
}

function makeTargets(text) {
  return [...text.matchAll(/^([A-Za-z0-9][\w.-]*)\s*:(?!=)/gm)].map((m) => m[1]).filter((t) => t !== 'PHONY')
}

function composeServices(text) {
  const lines = text.split('\n')
  const out = []
  let inServices = false
  let indent = null
  for (const line of lines) {
    if (/^services:\s*$/.test(line)) { inServices = true; continue }
    if (!inServices) continue
    if (/^\S/.test(line)) break
    const m = /^(\s+)([A-Za-z0-9_.-]+):\s*$/.exec(line)
    if (!m) continue
    if (indent === null) indent = m[1].length
    if (m[1].length === indent) out.push(m[2])
  }
  return out
}

function envKeys(text) {
  return [...text.matchAll(/^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=/gm)].map((m) => m[1])
}

function firstParagraph(markdown) {
  const lines = markdown.replace(/\r/g, '').split('\n')
  const title = (lines.find((l) => /^#\s+/.test(l)) || '').replace(/^#\s+/, '').trim()
  const para = []
  let started = false
  for (const l of lines) {
    if (/^\s*(#|<|!\[|\[!\[|```|---|\|)/.test(l)) { if (started) break; continue }
    if (!l.trim()) { if (started) break; continue }
    started = true
    para.push(l.trim())
  }
  return { title, summary: truncate(para.join(' '), 400) }
}

// ── mapeo de un repo ─────────────────────────────────────────

function mapRepo(repo, allRepos) {
  const path = join(ROOT, repo.dir)
  const head = git(path, 'rev-parse', 'HEAD')
  const tracked = git(path, 'ls-files').split('\n').filter(Boolean)
  const files = new Set(tracked)

  // estructura
  const top = new Map()
  const sub = new Map()
  for (const f of tracked) {
    const parts = f.split('/')
    const key = parts.length > 1 ? parts[0] + '/' : parts[0]
    top.set(key, (top.get(key) || 0) + 1)
    if (parts.length > 2) {
      const k2 = parts[0] + '/' + parts[1] + '/'
      sub.set(k2, (sub.get(k2) || 0) + 1)
    }
  }
  const topDirs = [...top.entries()].filter(([k]) => k.endsWith('/')).sort((a, b) => b[1] - a[1])
  const rootFiles = [...top.keys()].filter((k) => !k.endsWith('/')).sort()

  // lenguajes
  const langCount = new Map()
  for (const f of tracked) {
    const m = /\.[^./]+$/.exec(f)
    const lang = m && LANGS[m[0].toLowerCase()]
    if (lang) langCount.set(lang, (langCount.get(lang) || 0) + 1)
  }
  const langs = [...langCount.entries()].sort((a, b) => b[1] - a[1])

  // manifests hasta profundidad 2 (cubre monorepos con apps/*, packages/*)
  const manifests = tracked.filter((f) => f.split('/').length <= 3 && MANIFEST_FILES.includes(basename(f)) && !f.includes('node_modules/'))
  const csproj = tracked.filter((f) => /\.(csproj|fsproj|sln)$/.test(f)).slice(0, 20)

  const details = []
  let pkgName = null
  const packageNames = []
  for (const mf of manifests.slice(0, 25)) {
    const text = read(join(path, mf))
    const name = basename(mf)
    if (name === 'package.json') {
      const pkg = parsePackageJson(text)
      if (!pkg) continue
      if (pkg.name) packageNames.push(pkg.name)
      if (mf === 'package.json') pkgName = pkg.name
      details.push({ file: mf, kind: 'package.json', pkg })
    } else if (name === 'Makefile') {
      details.push({ file: mf, kind: 'make', targets: makeTargets(text).slice(0, 25) })
    } else if (/^(docker-)?compose\.ya?ml$/.test(name) || /^docker-compose\.ya?ml$/.test(name)) {
      details.push({ file: mf, kind: 'compose', services: composeServices(text) })
    } else if (name === 'go.mod') {
      const mod = (/^module\s+(\S+)/m.exec(text) || [])[1]
      const goV = (/^go\s+(\S+)/m.exec(text) || [])[1]
      if (mod) packageNames.push(mod)
      details.push({ file: mf, kind: 'go', text: [mod && `module ${mod}`, goV && `go ${goV}`].filter(Boolean).join(' · ') })
    } else if (name === 'pyproject.toml') {
      const pname = (/^\s*name\s*=\s*"([^"]+)"/m.exec(text) || [])[1]
      const pyV = (/requires-python\s*=\s*"([^"]+)"/.exec(text) || [])[1]
      const tools = [...new Set([...text.matchAll(/^\[tool\.([\w-]+)/gm)].map((m) => m[1]))]
      if (pname) packageNames.push(pname)
      details.push({ file: mf, kind: 'py', text: [pname, pyV && `python ${pyV}`, tools.length && `tools: ${tools.join(', ')}`].filter(Boolean).join(' · ') })
    } else if (name === 'Cargo.toml') {
      const cname = (/^\s*name\s*=\s*"([^"]+)"/m.exec(text) || [])[1]
      if (cname) packageNames.push(cname)
      details.push({ file: mf, kind: 'other', text: cname || '' })
    } else if (name === 'pom.xml') {
      const art = (/<artifactId>([^<]+)<\/artifactId>/.exec(text) || [])[1]
      const jv = (/<(?:java\.version|maven\.compiler\.release)>([^<]+)</.exec(text) || [])[1]
      if (art) packageNames.push(art)
      details.push({ file: mf, kind: 'other', text: [art, jv && `java ${jv}`].filter(Boolean).join(' · ') })
    } else if (name === 'composer.json') {
      try {
        const c = JSON.parse(text)
        if (c.name) packageNames.push(c.name)
        details.push({ file: mf, kind: 'other', text: [c.name, c.scripts && `scripts: ${Object.keys(c.scripts).join(', ')}`].filter(Boolean).join(' · ') })
      } catch { /* ignorar */ }
    } else {
      details.push({ file: mf, kind: 'other', text: '' })
    }
  }
  for (const f of csproj) {
    const text = read(join(path, f))
    const tf = (/<TargetFrameworks?>([^<]+)</.exec(text) || [])[1]
    details.push({ file: f, kind: 'other', text: tf ? `target ${tf}` : '' })
  }

  const manager = lockfileManager(files)
  const workflows = tracked.filter((f) => /^\.github\/workflows\/.+\.ya?ml$/.test(f) || /^\.gitlab-ci\.yml$|^azure-pipelines\.ya?ml$|^Jenkinsfile$|^\.circleci\/config\.yml$|^bitbucket-pipelines\.yml$/.test(f))
  const entrypoints = tracked.filter((f) => ENTRY.test(f) && !TEST.test(f) && !/node_modules|dist\/|build\//.test(f)).slice(0, 15)
  const testFiles = tracked.filter((f) => TEST.test(f))
  const agentRules = tracked.filter((f) => AGENT_RULES.test(f))
  const envFiles = tracked.filter((f) => ENV_EXAMPLE.test(f)).slice(0, 5)
  const envVars = [...new Set(envFiles.flatMap((f) => envKeys(read(join(path, f)))))].slice(0, 60)
  const readmePath = tracked.find((f) => /^readme(\.md)?$/i.test(f))
  const readme = readmePath ? firstParagraph(read(join(path, readmePath))) : { title: '', summary: '' }

  // git
  const branch = git(path, 'rev-parse', '--abbrev-ref', 'HEAD')
  const defaultBranch = git(path, 'rev-parse', '--abbrev-ref', 'origin/HEAD').replace(/^origin\//, '')
  const lastDate = git(path, 'log', '-1', '--format=%cs')
  const commits = git(path, 'log', '-8', '--format=%h %cs %s').split('\n').filter(Boolean)
  const churn = new Map()
  for (const f of git(path, 'log', '--since=90.days', '--name-only', '--format=').split('\n')) {
    if (f && files.has(f)) churn.set(f, (churn.get(f) || 0) + 1)
  }
  const hotspots = [...churn.entries()].sort((a, b) => b[1] - a[1]).slice(0, 12)

  // stack corto
  const stack = []
  if (langs[0]) stack.push(langs[0][0])
  if (langs[1] && langs[1][1] > langs[0][1] * 0.2) stack.push(langs[1][0])
  const allDeps = details.filter((d) => d.kind === 'package.json').flatMap((d) => [...d.pkg.deps, ...d.pkg.devDeps])
  const FRAMEWORKS = [['next', 'Next.js'], ['@nestjs/core', 'NestJS'], ['react', 'React'], ['vue', 'Vue'], ['@angular/core', 'Angular'], ['svelte', 'Svelte'], ['express', 'Express'], ['fastify', 'Fastify'], ['nuxt', 'Nuxt'], ['astro', 'Astro'], ['electron', 'Electron'], ['react-native', 'React Native'], ['expo', 'Expo']]
  const fw = FRAMEWORKS.filter(([d]) => allDeps.includes(d)).map(([, n]) => n)
  if (fw.includes('Next.js') && fw.includes('React')) fw.splice(fw.indexOf('React'), 1)
  stack.push(...fw.slice(0, 2))
  if (manager) stack.push(manager)
  if (details.some((d) => d.kind === 'py') || files.has('requirements.txt')) stack.includes('Python') || stack.push('Python')
  if (csproj.length && !stack.includes('C#')) stack.push('.NET')
  if (details.some((d) => d.kind === 'compose') || files.has('Dockerfile')) stack.push('Docker')

  return {
    version: MAP_VERSION, dir: repo.dir, url: repo.url, head, branch, defaultBranch, lastDate, commits, fileCount: tracked.length,
    topDirs, sub: [...sub.entries()], rootFiles, langs, details, manager, workflows, entrypoints, testCount: testFiles.length,
    testDirs: [...new Set(testFiles.map((f) => f.split('/').slice(0, -1).slice(0, 2).join('/') || '.'))].slice(0, 8), agentRules, envFiles, envVars,
    readme, hotspots, stack: [...new Set(stack)].join(' · '), pkgName, packageNames: [...new Set(packageNames)],
    manifestText: truncate(manifests.concat(csproj).map((m) => read(join(path, m))).join('\n'), 200 * 1024),
    relations: [],
  }
}

// ── render ───────────────────────────────────────────────────

function renderRepo(m) {
  const L = []
  L.push(`# ${m.dir}`, '')
  L.push(`> Generado por \`scripts/map.mjs\` el ${new Date().toISOString().slice(0, 10)} sobre \`${m.head.slice(0, 10)}\`. No editar: se regenera.`, '')
  L.push(`- **Remote:** \`${m.url}\``)
  L.push(`- **Rama:** \`${m.branch}\`${m.defaultBranch ? ` (default del remote: \`${m.defaultBranch}\`)` : ''} · último commit ${m.lastDate}`)
  L.push(`- **Stack:** ${m.stack || '[no detectado]'} · ${m.fileCount} archivos versionados`)
  if (m.langs.length) L.push(`- **Lenguajes:** ${m.langs.slice(0, 6).map(([l, n]) => `${l} (${n})`).join(', ')}`)
  L.push('')
  if (m.readme.title || m.readme.summary) {
    L.push('## Qué dice el README', '')
    if (m.readme.title) L.push(`**${m.readme.title}**`, '')
    if (m.readme.summary) L.push(m.readme.summary, '')
  }
  if (m.agentRules.length) {
    L.push('## Reglas de agente del repo', '', 'Mandan dentro del repo. Leelas antes de trabajar:', '')
    for (const f of m.agentRules) L.push(`- \`${m.dir}/${f}\``)
    L.push('')
  }
  L.push('## Estructura', '')
  for (const [d, n] of m.topDirs.slice(0, 20)) {
    const children = m.sub.filter(([k]) => k.startsWith(d)).sort((a, b) => b[1] - a[1]).slice(0, 8)
    L.push(`- \`${d}\` (${n})${children.length ? ' — ' + children.map(([k, c]) => `\`${k.slice(d.length)}\` ${c}`).join(', ') : ''}`)
  }
  if (m.rootFiles.length) L.push(`- raíz: ${m.rootFiles.slice(0, 25).map((f) => `\`${f}\``).join(', ')}`)
  L.push('')
  if (m.details.length) {
    L.push('## Manifests y comandos', '')
    for (const d of m.details) {
      if (d.kind === 'package.json') {
        const p = d.pkg
        L.push(`### \`${d.file}\`${p.name ? ` — ${p.name}` : ''}`, '')
        if (m.manager && d.file === 'package.json') L.push(`Gestor: **${m.manager}**`)
        if (p.engines) L.push(`Engines: ${Object.entries(p.engines).map(([k, v]) => `${k} ${v}`).join(', ')}`)
        if (p.workspaces) L.push(`Workspaces: ${JSON.stringify(p.workspaces)}`)
        const scripts = Object.entries(p.scripts)
        if (scripts.length) {
          L.push('', '| script | comando |', '|---|---|')
          for (const [k, v] of scripts.slice(0, 30)) L.push(`| \`${cell(k)}\` | \`${cell(truncate(v, 90))}\` |`)
        }
        if (p.deps.length) L.push('', `Dependencias (${p.deps.length}): ${p.deps.slice(0, 30).join(', ')}${p.deps.length > 30 ? ', …' : ''}`)
        L.push('')
      } else if (d.kind === 'make') {
        L.push(`- \`${d.file}\` — targets: ${d.targets.map((t) => `\`${t}\``).join(', ') || '—'}`)
      } else if (d.kind === 'compose') {
        L.push(`- \`${d.file}\` — servicios: ${d.services.map((s) => `\`${s}\``).join(', ') || '—'}`)
      } else {
        L.push(`- \`${d.file}\`${d.text ? ` — ${d.text}` : ''}`)
      }
    }
    L.push('')
  }
  if (m.entrypoints.length) L.push('## Entrypoints probables', '', ...m.entrypoints.map((f) => `- \`${f}\``), '')
  L.push('## Tests', '', m.testCount ? `${m.testCount} archivo${m.testCount === 1 ? '' : 's'} de test. Dónde: ${m.testDirs.map((d) => `\`${d}\``).join(', ')}` : 'No se detectaron archivos de test.', '')
  if (m.workflows.length) L.push('## CI', '', ...m.workflows.map((f) => `- \`${f}\``), '')
  if (m.envVars.length) L.push('## Variables de entorno (solo nombres)', '', `De ${m.envFiles.map((f) => `\`${f}\``).join(', ')}: ${m.envVars.map((v) => `\`${v}\``).join(', ')}`, '')
  if (m.relations.length) L.push('## Relaciones con otros repos del workspace', '', ...m.relations.map((r) => `- menciona a \`${r}\` en sus manifests`), '')
  if (m.hotspots.length) L.push('## Hotspots (más tocados en 90 días)', '', ...m.hotspots.map(([f, n]) => `- \`${f}\` (${n})`), '')
  if (m.commits.length) L.push('## Últimos commits', '', ...m.commits.map((c) => `- ${cell(c)}`), '')
  return L.join('\n')
}

function renderIndex(repos, maps) {
  const L = []
  L.push('# Mapa del workspace', '')
  L.push(`> Generado por \`scripts/map.mjs\` el ${new Date().toISOString().slice(0, 16).replace('T', ' ')}. No editar: se regenera.`, '')
  L.push('| Repo | Rama | Último commit | Stack | Archivos | Detalle |', '|---|---|---|---|---|---|')
  for (const r of repos) {
    const m = maps.get(r.dir)
    if (!m) { L.push(`| \`${r.dir}\` | — | — | **no clonado** | — | \`bash bootstrap/bootstrap.sh\` |`); continue }
    L.push(`| \`${r.dir}\` | \`${m.branch}\` | ${m.lastDate} | ${cell(m.stack || '—')} | ${m.fileCount} | [map/${r.dir}.md](map/${r.dir}.md) |`)
  }
  const rel = [...maps.values()].filter((m) => m.relations.length)
  if (rel.length) {
    L.push('', '## Relaciones detectadas', '', 'Por nombre de repo o de paquete mencionado en manifests y compose — es una pista, no un grafo de llamadas.', '')
    for (const m of rel) L.push(`- \`${m.dir}\` → ${m.relations.map((r) => `\`${r}\``).join(', ')}`)
  }
  L.push('', '## Cómo usarlo', '', '1. Ubicá el repo acá; abrí su detalle en `map/<repo>.md`.', '2. Después `knowledge/README.md` para lo que no se deduce del código.', '3. Recién ahí, grep sobre el repo puntual.')
  return L.join('\n') + '\n'
}

// ── main ─────────────────────────────────────────────────────

function main() {
  const repos = readManifest()
  mkdirSync(join(OUT, 'map'), { recursive: true })
  const maps = new Map()
  let regenerated = 0
  const missing = []

  for (const repo of repos) {
    const path = join(ROOT, repo.dir)
    if (!existsSync(path) || !git(path, 'rev-parse', 'HEAD')) { missing.push(repo.dir); continue }
    const cacheFile = join(OUT, 'map', `${repo.dir}.json`)
    const head = git(path, 'rev-parse', 'HEAD')
    const forced = FORCE || ONLY === repo.dir
    if (!forced && existsSync(cacheFile)) {
      try {
        const cached = JSON.parse(readFileSync(cacheFile, 'utf8'))
        if (cached.head === head && cached.version === MAP_VERSION) { maps.set(repo.dir, cached); continue }
      } catch { /* caché rota: se regenera */ }
    }
    if (ONLY && ONLY !== repo.dir && existsSync(cacheFile)) {
      try { maps.set(repo.dir, JSON.parse(readFileSync(cacheFile, 'utf8'))); continue } catch { /* regenerar */ }
    }
    maps.set(repo.dir, { ...mapRepo(repo, repos), fresh: true })
    regenerated++
  }

  // relaciones: un repo menciona el nombre de carpeta o de paquete de otro en sus manifests
  if (regenerated) {
    for (const m of maps.values()) {
      if (!m.manifestText) continue
      const text = m.manifestText.toLowerCase()
      m.relations = [...maps.values()]
        .filter((o) => o.dir !== m.dir)
        .filter((o) => [o.dir, ...(o.packageNames || [])].some((n) => n && n.length > 3 && text.includes(n.toLowerCase())))
        .map((o) => o.dir)
    }
  }

  for (const m of maps.values()) {
    if (!m.fresh && !regenerated) continue
    const { fresh, ...data } = m
    writeFileSync(join(OUT, 'map', `${m.dir}.json`), JSON.stringify(data))
    writeFileSync(join(OUT, 'map', `${m.dir}.md`), renderRepo(data))
  }
  // El índice se reescribe cuando cambia su contenido: qué repos hay, cuáles faltan y en qué HEAD está cada uno.
  const signature = JSON.stringify(repos.map((r) => [r.dir, maps.get(r.dir)?.head || null, maps.get(r.dir)?.relations || []]))
  const sigFile = join(OUT, 'index.sig')
  const previous = existsSync(sigFile) ? readFileSync(sigFile, 'utf8') : ''
  if (signature !== previous || !existsSync(join(OUT, 'INDEX.md'))) {
    writeFileSync(join(OUT, 'INDEX.md'), renderIndex(repos, maps))
    writeFileSync(sigFile, signature)
  }

  const summary = `mapa: ${maps.size}/${repos.length} repos · ${regenerated} regenerados${missing.length ? ` · sin clonar: ${missing.join(', ')}` : ''}`
  if (QUIET) console.log(summary)
  else {
    console.log(summary)
    console.log(`índice: ${posix.join('.context', 'INDEX.md')}`)
  }
}

main()
