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
//    node tools/gate.mjs                    # run until two consecutive passes
//    node tools/gate.mjs --once             # a single audit, then report
//    node tools/gate.mjs --max 6            # give up after 6 attempts
//    node tools/gate.mjs --on-fail "<cmd>"  # run <cmd> between failed attempts
//    node tools/gate.mjs --on-pass "<cmd>"  # run <cmd> when the bar IS met
//
//  Without --on-fail the loop measures repeatedly and nothing changes between
//  iterations, which is only useful for checking stability. With it, the loop
//  is closed: measure, repair, measure again.
//
//  --on-pass closes the other half, and it matters more than it looks. This
//  project has declared completion four times and been wrong four times
//  (docs/FALSIFY.md): every pass meant "the criteria do not look at this
//  defect". So clearing the bar runs --on-pass — whose job is to find what the
//  criteria are not measuring — and the loop continues. A pass is a reason to
//  distrust the test, not a reason to stop.
// ============================================================================

import { spawn } from 'node:child_process';
import { readFileSync, writeFileSync, existsSync, appendFileSync } from 'node:fs';

const ROOT = new URL('..', import.meta.url).pathname;
const STATE = `${ROOT}docs/GATE.md`;
const REQUIRED_STREAK = process.argv.includes('--once') ? 1 : 2;
const MAX_ATTEMPTS = (() => {
  const i = process.argv.indexOf('--max');
  return i >= 0 ? Number(process.argv[i + 1]) : 12;
})();

/**
 * The command that repairs whatever the last audit found, run between attempts.
 *
 * The gate can measure but it cannot code, so closing the loop needs something
 * that can. Passing it in rather than hard-wiring it keeps this file a
 * measurement harness: `--on-fail "<shell command>"` is enough of an interface
 * for a human, a script, or an agent runner.
 */
const ON_FAIL = (() => {
  const i = process.argv.indexOf('--on-fail');
  return i >= 0 ? process.argv[i + 1] : null;
})();

/**
 * What to run when the bar IS met.
 *
 * This project has declared completion four times and been wrong four times —
 * see docs/FALSIFY.md. Every one of those passes turned out to mean "the
 * criteria do not look at this defect", not "the defect is gone". The first
 * pass scored 100/100 on a frame that was untextured flat-shaded boxes, because
 * nothing in the rubric looked at the image at all.
 *
 * Verifying every pattern of events reachable from here is not something that
 * finishes in any practical span of time, so "proved it all" is not a state
 * this loop can arrive at. Feeling close to it is better explained by not being
 * able to see the unmeasured region than by actually being close.
 *
 * So a pass is not an exit. With --on-pass, clearing the bar runs that command
 * — whose job is to find what the criteria are not measuring and add it — and
 * then measures again. The loop's normal state is running.
 */
const ON_PASS = (() => {
  const i = process.argv.indexOf('--on-pass');
  return i >= 0 ? process.argv[i + 1] : null;
})();

const runFixer = (cmd) => new Promise((resolve) => {
  const child = spawn(cmd, { cwd: ROOT, shell: true, stdio: 'inherit' });
  child.on('close', (code) => resolve(code));
});

const runAudit = () => new Promise((resolve) => {
  const child = spawn('node', ['tools/audit.mjs'], { cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'] });
  let out = '';
  child.stdout.on('data', (d) => { out += d; process.stdout.write(d); });
  child.stderr.on('data', (d) => { out += d; process.stderr.write(d); });
  child.on('close', (code) => resolve({ code, out }));
});

/**
 * Unit checks, run before the browser audit on every attempt.
 *
 * The audit costs about twelve minutes and needs a GL context to say anything
 * at all. These run the same engine code directly in node in a couple of
 * seconds. When one of them fails, the audit that follows would have spent
 * twelve minutes to reach a worse-explained version of the same verdict.
 *
 * They do not gate the attempt — a unit failure is printed and the audit still
 * runs, because the audit measures thirteen axes and this covers one of them.
 * The point is that the cheap signal arrives first.
 */
const UNIT_CHECKS = [
  ['継続性', 'tools/unit-continuity.mjs'],
  ['カメラ', 'tools/unit-camera.mjs'],
  ['接地IK', 'tools/unit-footik.mjs'],
  ['動きの層', 'tools/unit-motion.mjs'],
  // Not a unit check of the game — a check of the measurement. It reads the
  // criterion snapshots the audit leaves in docs/audit-runs.json and reports any
  // criterion that changed its verdict without the code changing.
  ['計測の安定性', 'tools/stability.mjs'],
];

const runUnits = async () => {
  const failed = [];
  // Parse every file first. A syntax error in a module the unit checks do not
  // import is invisible to them and costs a full audit to find, twelve minutes
  // in, as a blank page.
  const parseCode = await new Promise((resolve) => {
    const child = spawn('sh', ['tools/parsecheck.sh'], { cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'] });
    let buf = '';
    child.stdout.on('data', (d) => { buf += d; });
    child.stderr.on('data', (d) => { buf += d; });
    child.on('close', (c) => { if (c !== 0) process.stdout.write(buf); resolve(c); });
    child.on('error', () => resolve(0));
  });
  if (parseCode !== 0) failed.push('構文');
  for (const [name, script] of UNIT_CHECKS) {
    const code = await new Promise((resolve) => {
      const child = spawn('node', [script], { cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'] });
      let buf = '';
      child.stdout.on('data', (d) => { buf += d; });
      child.stderr.on('data', (d) => { buf += d; });
      child.on('close', (c) => {
        if (c !== 0) process.stdout.write(buf);
        resolve(c);
      });
      child.on('error', () => resolve(0));   // a missing check must not block
    });
    if (code !== 0) failed.push(name);
  }
  console.log(failed.length
    ? `単体検査: ${failed.join('・')} が不合格 — 監査の前にここで直る`
    : `単体検査: ${UNIT_CHECKS.length} 件すべて合格`);
  return failed;
};

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

/**
 * A fingerprint of one attempt: which targets are unmet and at what values.
 *
 * Two attempts with the same fingerprint mean the loop learned nothing between
 * them. That is the signature of a loop burning wall-clock and producing
 * nothing, and it is invisible from inside a single attempt — which is exactly
 * why it has to be detected here rather than left to whoever is watching.
 */
const signatureOf = (failures) => failures.slice().sort().join('|');

/**
 * The same fingerprint with the numbers stripped out.
 *
 * Stall detection compares full signatures, which fails in the direction that
 * hides the problem: a criterion that measures the machine rather than the game
 * reports a different number every run, so every attempt looks different and the
 * loop reads noise as progress. Two audits of one commit have already reported
 * 229,045 and 409,347 triangles.
 *
 * Comparing the *set of unmet criteria* instead catches that. The same targets
 * unmet twice running is a stall whatever the digits did, and `node
 * tools/stability.mjs` will name which criteria are the noisy ones.
 */
const labelsOf = (failures) => failures
  .map((l) => l.replace(/:.*$/, '').trim())
  .sort()
  .join('|');

/** Append one line per attempt as it finishes, so a killed run still tells you why. */
const journal = (line) => {
  try {
    appendFileSync(`${ROOT}docs/GATE-LOG.md`, `${line}\n`);
  } catch { /* the log is a convenience; never let it stop the loop */ }
};

if (!ON_FAIL && MAX_ATTEMPTS > REQUIRED_STREAK) {
  console.log('注意: --on-fail が無い。未達が出ても何も変わらないので、'
    + `試行は ${REQUIRED_STREAK} 回で打ち切る。`);
  console.log('  修正まで回すなら: node tools/gate.mjs --on-fail "<修正コマンド>"');
}

const history = [];
let streak = 0;
let lastSignature = null;
let lastLabels = null;
let stalled = 0;
let stalledOut = false;

for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
  console.log(`\n══════ 品質ゲート 試行 ${attempt}/${MAX_ATTEMPTS}` +
    ` (連続合格 ${streak}/${REQUIRED_STREAK}) ══════\n`);
  const unitFailed = await runUnits();
  const { code, out } = await runAudit();
  const score = scoreOf(out);
  // A unit failure counts as a failure of the attempt even when the audit is
  // happy, because it means the audit is not looking at something the engine
  // itself can already prove is broken. Folding it into the failure list also
  // keeps the stall signature honest: a run where only the unit result changed
  // has still learned something.
  const pass = code === 0 && unitFailed.length === 0;
  streak = pass ? streak + 1 : 0;
  const failures = failuresOf(out).concat(unitFailed.map((n) => `- [単体] ${n}`));
  history.push({ attempt, score, pass, failures });

  console.log(`\n── 試行 ${attempt}: ${pass ? 'PASS' : 'FAIL'} (${score ?? '?'}/100), ` +
    `連続合格 ${streak}/${REQUIRED_STREAK}`);
  const sig = signatureOf(failures);
  const labels = labelsOf(failures);
  journal(`- 試行 ${attempt} — ${pass ? 'PASS' : 'FAIL'} ${score ?? '?'}/100, `
    + `未達 ${failures.length} 件`
    + `${sig === lastSignature ? '  ← 前回と同一' : ''}`);

  // Stall detection. An attempt that reproduces the previous one exactly means
  // nothing moved, and continuing costs another full measurement to learn the
  // same thing again.
  // Compare on the criteria, not the digits: see labelsOf().
  if (!pass && (sig === lastSignature || labels === lastLabels)) {
    stalled++;
    if (sig !== lastSignature) {
      console.log('\n未達の項目は前回と同じで、数値だけが動いている。'
        + 'その数値は計測のぶれであってコードの変化ではない可能性が高い。');
      console.log('  node tools/stability.mjs で、どの項目が機械の速度を測っているか確認すること。');
    }
    if (!ON_FAIL) {
      console.log('\n同じ未達が2回続いた。--on-fail が無いので、'
        + 'この先は同じ計測を繰り返すだけになる。ここで止める。');
      stalledOut = true;
      break;
    }
    if (stalled >= 2) {
      console.log(`\n修正コマンドを ${stalled} 回実行したが、未達の内容も値も動いていない。`);
      console.log('同じ計測を繰り返しても学べることはないので止める。');
      console.log('原因を切り分けること——修正が対象に届いていないか、'
        + '計測側が実際とは別のものを見ている可能性が高い。');
      stalledOut = true;
      break;
    }
  } else if (!pass) {
    stalled = 0;
  }
  lastSignature = sig;
  lastLabels = labels;

  if (streak >= REQUIRED_STREAK) {
    if (!ON_PASS) break;
    // Clearing the bar is evidence about the bar, not about the game. Go look
    // for what it does not measure, then measure again.
    console.log(`\n${REQUIRED_STREAK} 回連続で合格した。`
      + 'これは基準がその欠陥を見ていない可能性の合図なので、終了しない。');
    console.log(`基準を疑うコマンドを実行: ${ON_PASS}`);
    const r = await runFixer(ON_PASS);
    if (r !== 0) console.log(`非ゼロ終了 (${r})。それでも計測は続ける。`);
    streak = 0;
    continue;
  }
  if (!pass) {
    // Not finished. docs/BACKLOG.md now holds the ranked work list; whoever
    // drives this loop — a person or an agent — fixes the top of it and the
    // next iteration measures again.
    //
    // This used to `break` here, on the reasoning that nothing improves on its
    // own between two runs. That was true and it was still the wrong call: a
    // gate whose job is "do not stop until the bar is met" must not be the
    // thing that stops. Now it reports and keeps going, so the only ways out
    // are the bar being met or the attempt budget running out — and the
    // attempt budget exists solely so an unattended run cannot spin forever.
    console.log(`\n未達 ${failures.length} 件。`
      + 'docs/BACKLOG.md の上位から修正すること。次の試行まで待機する。');
    if (!ON_FAIL) {
      console.log('（--on-fail が指定されていないため、修正は自動では行われない）');
    } else {
      console.log(`修正コマンドを実行: ${ON_FAIL}`);
      const r = await runFixer(ON_FAIL);
      if (r !== 0) console.log(`修正コマンドが非ゼロ終了 (${r})。それでも計測は続ける。`);
    }
  }
}

const finalPass = streak >= REQUIRED_STREAK;
let md = '# 品質ゲートの記録\n\n';
md += `判定: **${finalPass ? '合格' : '未達'}** — 連続合格 ${streak}/${REQUIRED_STREAK}\n\n`;
md += '仕組みは `tools/gate.mjs`、基準は `docs/QUALITY.md`、計測は `tools/audit.mjs`。\n';
md += `${REQUIRED_STREAK} 回連続で全軸 80 点以上かつ総合 88 点以上になるまで開発を続ける。\n`;
md += '合格は終了条件ではない。過去4回の合格は全て「基準がその欠陥を見ていない」'
  + 'ことの現れだった（`docs/FALSIFY.md`）。\n\n';
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

// "合格" and not "完成": the bar was cleared, which is a statement about the
// bar. docs/FALSIFY.md keeps the record of the four times that was mistaken for
// the other thing.
console.log(`\n══════ ${finalPass ? '品質ゲート合格（暫定） — 基準が測っていない領域を疑うこと'
  : stalledOut ? '品質ゲート停滞 — 同じ結果が繰り返された。原因の切り分けが要る'
    : '品質ゲート未達 — 開発継続'} ══════`);
if (finalPass && !ON_PASS) {
  console.log('--on-pass が無いのでここで止まるが、これは「完成した」という意味ではない。');
  console.log('docs/FALSIFY.md の「今わかっている測っていないもの」を見ること。');
}
// 0 pass, 1 unmet, 2 stalled. A driver that cannot tell "still working" from
// "going in circles" will happily go in circles for hours.
process.exitCode = finalPass ? 0 : stalledOut ? 2 : 1;
