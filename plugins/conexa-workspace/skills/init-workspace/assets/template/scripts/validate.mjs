#!/usr/bin/env node
// validate.mjs — chequeos del workspace que corre CI. Sin dependencias: built-ins de Node >= 18.
// Trabaja sobre los archivos versionados (git ls-files), así que corré `git add` antes de validar
// archivos nuevos.

import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { posix } from 'node:path'

const SECRET_PATH = [/\.pem$/i, /\.key$/i, /\.p12$/i, /\.pfx$/i, /(^|\/)client_secret[^/]*\.json$/i, /(^|\/)\.env(\.(?!example$)[^/]+)?$/i, /(^|\/)secrets\.json$/i, /(^|\/)id_(rsa|ed25519|ecdsa)$/]
const MACHINE_PATH = [/\/(?:Users|home)\/[A-Za-z0-9._-]+\//g, /[A-Za-z]:\\Users\\[A-Za-z0-9._-]+/g]
const TEXT_EXT = /\.(md|mjs|js|ts|json|ya?ml|sh|ps1|txt|tsv|toml|py)$|(^|\/)\.gitignore$/i
const MARKDOWN_LINK = /\[[^\]]*\]\(([^()\s]*(?:\([^()]*\)[^()\s]*)*)\)/g
const EXTERNAL = /^(https?:|mailto:|tel:|#)/i
const FRONTMATTER = /^---\r?\n([\s\S]*?)\r?\n---/
const BEGIN_MARK = '# >>> repos (bootstrap/bootstrap.sh mantiene este bloque; no editar a mano) >>>'
const END_MARK = '# <<< repos <<<'
const SELF = 'scripts/validate.mjs'

const problems = []
const fail = (section, msg) => problems.push(`${section}: ${msg}`)

function tracked() {
  try {
    return execFileSync('git', ['ls-files'], { encoding: 'utf8' }).split('\n').filter(Boolean)
  } catch {
    console.error('✗ no es un repositorio git (o git no está instalado). Corré `git init` y `git add` primero.')
    process.exit(2)
  }
}

function readSafe(path) {
  try { return readFileSync(path, 'utf8') } catch { return null }
}

function stripCode(markdown) {
  const out = []
  let fence = null
  for (const line of markdown.split('\n')) {
    const m = /^\s*(`{3,}|~{3,})/.exec(line)
    if (fence === null) {
      if (m) { fence = m[1]; continue }
      out.push(line.replace(/`[^`]*`/g, ''))
    } else if (m && m[1][0] === fence[0] && m[1].length >= fence.length && /^\s*(`{3,}|~{3,})\s*$/.test(line)) {
      fence = null
    }
  }
  return out.join('\n')
}

function localLinks(markdown) {
  return [...stripCode(markdown.replace(/<!--[\s\S]*?-->/g, '')).matchAll(MARKDOWN_LINK)].map((m) => m[1]).filter((t) => t && !EXTERNAL.test(t))
}

function resolve(from, link) {
  const target = decodeURIComponent(link.split('#')[0])
  return target ? posix.normalize(posix.join(posix.dirname(from), target)) : null
}

function frontmatter(content) {
  const m = FRONTMATTER.exec(content)
  if (!m) return null
  const fields = {}
  for (const line of m[1].split('\n')) {
    const pair = /^([\w-]+):\s*(.*)$/.exec(line)
    if (pair) fields[pair[1]] = pair[2].trim().replace(/^["']|["']$/g, '')
  }
  return fields
}

function repoDirs() {
  const text = readSafe('bootstrap/repos.tsv')
  if (text === null) return []
  return text.replace(/\r/g, '').split('\n')
    .filter((l) => l.trim() && !l.trim().startsWith('#'))
    .map((l) => l.split('\t')[0].trim())
    .filter(Boolean)
}

const files = tracked()
const repos = repoDirs()

// 1. Credenciales versionadas
for (const f of files) if (SECRET_PATH.some((p) => p.test(f))) fail('credencial versionada', f)

// 2. Repos de trabajo versionados en la raíz, y bloque del .gitignore
for (const dir of repos) {
  const inside = files.filter((f) => f === dir || f.startsWith(dir + '/'))
  if (inside.length) fail('repo de trabajo versionado en la raíz', `${dir}/ (${inside.length} archivos) — git rm -r --cached ${dir}`)
}
const gitignore = readSafe('.gitignore') || ''
const b = gitignore.indexOf(BEGIN_MARK)
const e = gitignore.indexOf(END_MARK)
if (b === -1 || e === -1 || e < b) {
  fail('.gitignore', 'falta el bloque de repos con sus marcadores (lo mantiene bootstrap/bootstrap.sh)')
} else {
  const block = gitignore.slice(b + BEGIN_MARK.length, e).split('\n').map((l) => l.trim())
  for (const dir of repos) if (!block.includes(`/${dir}`)) fail('.gitignore', `/${dir} no está en el bloque de repos — corré bash bootstrap/bootstrap.sh`)
}

// 3. Links relativos rotos (se ignoran los que apuntan a repos o a .context/, que no existen en CI)
const skipPrefixes = ['.context/', ...repos.map((d) => d + '/')]
for (const f of files.filter((p) => p.endsWith('.md'))) {
  const content = readSafe(f)
  if (content === null) continue
  for (const link of localLinks(content)) {
    const target = resolve(f, link)
    if (target === null || target.startsWith('..')) continue
    if (skipPrefixes.some((p) => (target + '/').startsWith(p)) || repos.includes(target)) continue
    if (!existsSync(target)) fail('link roto', `${f} → ${link}`)
  }
}

// 4. Rutas absolutas de una máquina personal
for (const f of files.filter((p) => TEXT_EXT.test(p) && p !== SELF)) {
  const content = readSafe(f)
  if (content === null) continue
  for (const re of MACHINE_PATH) for (const m of content.matchAll(re)) fail('ruta de máquina personal', `${f} → ${m[0]}`)
}

// 5. Frontmatter de agentes y skills
for (const f of files.filter((p) => /^\.claude\/agents\/[^/]+\.md$/.test(p))) {
  const fm = frontmatter(readSafe(f) || '')
  const expected = posix.basename(f, '.md')
  if (!fm) { fail('agente', `${f}: no abre con frontmatter`); continue }
  if (fm.name !== expected) fail('agente', `${f}: name "${fm.name || ''}" debería ser "${expected}"`)
  if (!fm.description) fail('agente', `${f}: description vacía`)
}
for (const f of files.filter((p) => /^\.claude\/skills\/[^/]+\/SKILL\.md$/.test(p))) {
  const fm = frontmatter(readSafe(f) || '')
  const expected = f.split('/')[2]
  if (!fm) { fail('skill', `${f}: no abre con frontmatter`); continue }
  if (fm.name !== expected) fail('skill', `${f}: name "${fm.name || ''}" debería ser "${expected}"`)
  if (!fm.description) fail('skill', `${f}: description vacía`)
}

// 6. Notas de knowledge/ fuera del índice
const INDEX = 'knowledge/README.md'
const notes = files.filter((p) => p.startsWith('knowledge/') && p.endsWith('.md') && p !== INDEX && p !== 'knowledge/_template.md' && !p.startsWith('knowledge/templates/'))
if (notes.length && !files.includes(INDEX)) {
  fail('knowledge', `hay notas pero ${INDEX} no está versionado`)
} else if (files.includes(INDEX)) {
  const linked = new Set(localLinks(readSafe(INDEX) || '').map((l) => resolve(INDEX, l)).filter(Boolean))
  for (const n of notes) if (!linked.has(n)) fail('nota fuera del índice', `${n} — sumala a ${INDEX}`)
}

// 7. CLAUDE.md importa AGENTS.md
if (files.includes('CLAUDE.md') && !/^@AGENTS\.md\s*$/m.test(readSafe('CLAUDE.md') || '')) {
  fail('CLAUDE.md', 'no importa AGENTS.md (falta una línea "@AGENTS.md")')
}
if (!files.includes('AGENTS.md')) fail('AGENTS.md', 'no está versionado')

if (problems.length) {
  console.error(`✗ ${problems.length} problema(s):`)
  for (const p of problems) console.error(`  · ${p}`)
  process.exit(1)
}
console.log(`✓ workspace válido (${files.length} archivos versionados, ${repos.length} repos en el manifest)`)
