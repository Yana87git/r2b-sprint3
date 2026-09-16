#!/usr/bin/env node
// spec-sync: エージェントのツール一覧が、設計書（agent.md）と実装（tools.py）で
// 一致しているかだけを機械検出する。**どちらが正しいかは判定しない。**
// ルールの根拠: .claude/rules/agent-development.md §1「設計が正」/ §5「ガードレールは仕組みで強制する」
//
// 使い方:
//   node .claude/scripts/spec-sync.mjs          # 全体検査（品質ゲート用）
//   node .claude/scripts/spec-sync.mjs --hook   # PostToolUse フック用（stdin の file_path のみ）
//
// 終了コード: 0=一致 / 1=不一致・取り出し失敗（全体） / 2=同（フック。stderr が Claude に返る）

import { readFileSync, existsSync } from 'node:fs'

const HOOK_MODE = process.argv.includes('--hook')

const IMPL_FILE = 'backend/app/agent/tools.py'
const SPEC_FILE = 'docs/requirements/agent.md'
const SPEC_HEADING = '#### ツール一覧'
// フックで走らせる対象。これ以外のファイルの編集では何もしない
const WATCHED = [IMPL_FILE, SPEC_FILE]

// 取り出しに失敗したことを、差分（＝一致）と区別して扱うための例外
class ExtractError extends Error {}

/** 実装側: ALLOWED_TOOL_NAMES の "mcp__app__<name>" から <name> を取り出す。 */
function implTools() {
  if (!existsSync(IMPL_FILE)) throw new ExtractError(`${IMPL_FILE} が見つからない`)
  const text = readFileSync(IMPL_FILE, 'utf8')
  const block = text.match(/ALLOWED_TOOL_NAMES\s*=\s*\[([\s\S]*?)\]/)
  if (!block) throw new ExtractError(`${IMPL_FILE} に ALLOWED_TOOL_NAMES が見つからない`)
  const names = [...block[1].matchAll(/["']mcp__app__([A-Za-z0-9_]+)["']/g)].map((m) => m[1])
  if (names.length === 0) {
    throw new ExtractError(`${IMPL_FILE} の ALLOWED_TOOL_NAMES からツール名を取り出せない`)
  }
  return new Set(names)
}

/** 設計側: 「#### ツール一覧」直後の表の1列目から、バッククォートのツール名を取り出す。 */
function specTools() {
  if (!existsSync(SPEC_FILE)) throw new ExtractError(`${SPEC_FILE} が見つからない`)
  const lines = readFileSync(SPEC_FILE, 'utf8').split('\n')
  const head = lines.findIndex((l) => l.trim() === SPEC_HEADING)
  if (head < 0) throw new ExtractError(`${SPEC_FILE} に見出し「${SPEC_HEADING}」が見つからない`)

  const names = []
  let inTable = false
  for (const line of lines.slice(head + 1)) {
    const trimmed = line.trim()
    if (trimmed.startsWith('#')) break // 次の見出しまで
    if (!trimmed.startsWith('|')) {
      if (inTable) break // 表が終わった
      continue
    }
    inTable = true
    const first = trimmed.split('|')[1] ?? ''
    const name = first.match(/`([A-Za-z0-9_]+)`/)
    if (name) names.push(name[1])
  }
  if (!inTable) throw new ExtractError(`${SPEC_FILE} の「${SPEC_HEADING}」直後に表が無い`)
  if (names.length === 0) {
    throw new ExtractError(`${SPEC_FILE} の「${SPEC_HEADING}」の表からツール名を取り出せない`)
  }
  return new Set(names)
}

/** 検査の本体。フックでも全体検査でもここだけを通す（経路で規則を分けない）。 */
function check() {
  const impl = implTools()
  const spec = specTools()
  const onlyImpl = [...impl].filter((n) => !spec.has(n)).sort()
  const onlySpec = [...spec].filter((n) => !impl.has(n)).sort()
  const messages = []
  if (onlyImpl.length > 0) {
    messages.push(`実装にあるが ${SPEC_FILE} に無い: ${onlyImpl.join(', ')}`)
  }
  if (onlySpec.length > 0) {
    messages.push(`${SPEC_FILE} にあるが実装に無い: ${onlySpec.join(', ')}`)
  }
  return { messages, implCount: impl.size, specCount: spec.size }
}

const HANDOFF =
  'どちらが正しいかは /design-check で判定すること。判定せずに片方を書き換えないこと。'

function run(emit) {
  try {
    const { messages, implCount, specCount } = check()
    if (messages.length === 0) return { code: 0, ok: `ツール一覧は一致（${implCount}個）` }
    emit(`spec-sync: ツール一覧が食い違っている（実装 ${implCount}個 / 設計 ${specCount}個）`)
    for (const m of messages) emit(`  ✗ ${m}`)
    emit(`  → ${HANDOFF}`)
    return { code: 1 }
  } catch (e) {
    if (e instanceof ExtractError) {
      // 取り出せなかったときは、差分なし（＝一致）と扱わずに止める
      emit(`spec-sync: 取り出せなかった。${e.message}`)
      emit('  → 検査が素通りしている状態なので、先にこれを直すこと。')
      return { code: 1 }
    }
    throw e
  }
}

if (HOOK_MODE) {
  // PostToolUse フック: stdin の JSON から編集ファイルを特定し、対象のときだけ検査する
  let input = ''
  process.stdin.on('data', (d) => (input += d))
  process.stdin.on('end', () => {
    let filePath
    try {
      filePath = JSON.parse(input)?.tool_input?.file_path
    } catch {
      process.exit(0)
    }
    if (!filePath) process.exit(0)
    const normalized = filePath.replace(/\\/g, '/')
    if (!WATCHED.some((w) => normalized.endsWith(w))) process.exit(0)
    const { code } = run((line) => console.error(line))
    process.exit(code === 0 ? 0 : 2)
  })
} else {
  const { code, ok } = run((line) => console.log(line))
  if (code === 0) console.log(`✓ spec-sync: ${ok}`)
  process.exit(code)
}
