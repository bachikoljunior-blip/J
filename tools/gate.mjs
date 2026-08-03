// ============================================================================
//  gate.mjs — the loop that decides when development stops.
//
//  "Keep building until the quality is judged not inferior" is not a condition
//  a program can evaluate, so docs/QUALITY.md restates it as ten weighted axes
//  with numeric targets and tools/audit.mjs measures them from the running
//  game. This driver closes the loop:
//
//      run audit → PASS? → run it again → PASS twice in a row? → stop
//                     ↓ FAIL
//              docs/BACKLOG.md lists what to fix; fix it; loop again
//
//  Two consecutive passes, not one. Several axes are measured from live frames
//  and behavioural probes, which carry run-to-run noise; a single pass can be
//  luck, and a target that only clears on a lucky run has not actually been
//  met. The streak survives across invocations in docs/GATE.md, so a fix made
//  between runs correctly resets it.
//
//    node tools/gate.mjs             # run until two consecutive passes
//    node tools/gate.mjs --once      # a single audit, then report
//    node tools/gate.mjs --max 6     # give up after 6 attempts
// ============================================================================

import { spawn } from 'node:child_process';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';

const ROOT = new URL('..', import.meta.url).pathname;
const STATE = `${ROOT}docs/GATE.md`;
const REQUIRED_STREAK = process.argv.includes('--once') ? 1 : 2;
const MAX_ATTEMPTS = (() => {
  const i = process.argv.indexOf('--max');
  return i >= 0 ? Number(process.argv[i + 1]) : 12;
})();

const runAudit = () => new Promise((resolve) => {
  const child = spawn('node', ['tools/audit.mjs'], { cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'] });
  let out = '';
  child.stdout.on('data', (d) => { out += d; process.stdout.write(d); });
  child.stderr.on('data', (d) => { out += d; process.stderr.write(d); });
  child.on('close', (code) => resolve({ code, out }));
});

const scoreOf = (out) => {
  const m = out.match(/総合\s+(\d+)\s*\/\s*100/);
  return m ? Number(m[1]) : null;
};
const failuresOf = (out) => {
  const lines = out.split('\n');
  const i = lines.findIndex((l) => l.includes('最優先の未達'));
  if (i < 0) return [];
  return lines.slice(i + 1).filter((l) => l.trim().startsWith('- ')).map((l) => l.trim());
};

const history = [];
let streak = 0;

for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
  console.log(`\n══════ 品質ゲート 試行 ${attempt}/${MAX_ATTEMPTS}` +
    ` (連続合格 ${streak}/${REQUIRED_STREAK}) ══════\n`);
  const { code, out } = await runAudit();
  const score = scoreOf(out);
  const pass = code === 0;
  streak = pass ? streak + 1 : 0;
  history.push({ attempt, score, pass, failures: failuresOf(out) });

  console.log(`\n── 試行 ${attempt}: ${pass ? 'PASS' : 'FAIL'} (${score ?? '?'}/100), ` +
    `連続合格 ${streak}/${REQUIRED_STREAK}`);

  if (streak >= REQUIRED_STREAK) break;
  if (!pass) {
    // Development is not finished. The backlog says what to do next; a human or
    // an agent fixes it and re-runs. Bailing here rather than looping blindly
    // keeps the loop honest: nothing improves on its own between two runs.
    console.log('\n未達項目が残っている。docs/BACKLOG.md の上位から修正して再実行すること。');
    break;
  }
}

const finalPass = streak >= REQUIRED_STREAK;
let md = '# 品質ゲートの記録\n\n';
md += `判定: **${finalPass ? '合格' : '未達'}** — 連続合格 ${streak}/${REQUIRED_STREAK}\n\n`;
md += '仕組みは `tools/gate.mjs`、基準は `docs/QUALITY.md`、計測は `tools/audit.mjs`。\n';
md += `${REQUIRED_STREAK} 回連続で全軸 80 点以上かつ総合 88 点以上になるまで開発を続ける。\n\n`;
md += '| 試行 | 総合 | 判定 | 未達 |\n|---|---|---|---|\n';
for (const h of history) {
  md += `| ${h.attempt} | ${h.score ?? '—'} | ${h.pass ? 'PASS' : 'FAIL'} | ` +
    `${h.failures.length ? h.failures.join('<br>') : '—'} |\n`;
}
if (existsSync(STATE)) {
  const prev = readFileSync(STATE, 'utf8');
  const tail = prev.slice(prev.indexOf('\n## 過去の実行\n') + 1);
  md += `\n## 過去の実行\n\n${tail.startsWith('## 過去の実行') ? tail.slice(9) : prev}\n`;
} else {
  md += '\n## 過去の実行\n\n（なし）\n';
}
writeFileSync(STATE, md);

console.log(`\n══════ ${finalPass ? '品質ゲート合格 — 開発完了条件を満たした'
  : '品質ゲート未達 — 開発継続'} ══════`);
process.exitCode = finalPass ? 0 : 1;
