// ============================================================================
//  unit-voice.mjs — is axis M thirteen voices, or one voice thirteen times?
//
//  The audit establishes the voice axis like this:
//
//    timbres        = Object.keys(VOICE_TIMBRES).length
//    combatVocals   = Object.keys(VOCALS).length
//    creatureVoices = Object.keys(CREATURE_VOICES).length
//    synthesis      = typeof audio.speak === 'function'
//
//  Counting keys establishes that thirteen entries exist. Thirteen identical
//  entries satisfy it exactly as well and give the player one voice — the same
//  failure as counting FLINCH_TIERS without checking the poses differ.
//
//  audio.js imports in node (it only touches AudioContext inside AudioEngine),
//  so the tables can be compared directly: how far apart the timbres actually
//  sit, whether the phoneme set spans a real vowel space, and whether text
//  turns into different utterances for different speakers.
// ============================================================================

import {
  VOICE_TIMBRES, VOCALS, CREATURE_VOICES, PHONEMES, ARTICULATIONS,
  MUSIC_MODES, utteranceFromText,
} from '../src/core/audio.js';

let failures = 0;
const check = (name, ok, detail) => {
  if (!ok) failures++;
  console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${name.padEnd(34)} ${detail}`);
};

/** Numeric fields of an object, flattened, so two entries can be compared. */
function numbersOf(o, prefix = '', out = {}) {
  for (const [k, v] of Object.entries(o || {})) {
    if (typeof v === 'number') out[prefix + k] = v;
    else if (Array.isArray(v)) v.forEach((n, i) => { if (typeof n === 'number') out[`${prefix}${k}[${i}]`] = n; });
    else if (v && typeof v === 'object') numbersOf(v, `${prefix}${k}.`, out);
  }
  return out;
}

/**
 * Relative distance between two entries: the mean fractional difference over
 * the fields they share. Fractional rather than absolute, because a pitch in
 * hertz and a formant ratio are not comparable in raw units.
 */
function distance(a, b) {
  const na = numbersOf(a), nb = numbersOf(b);
  const keys = Object.keys(na).filter((k) => k in nb);
  if (!keys.length) return 0;
  let sum = 0;
  for (const k of keys) {
    const scale = Math.max(Math.abs(na[k]), Math.abs(nb[k]), 1e-6);
    sum += Math.abs(na[k] - nb[k]) / scale;
  }
  return sum / keys.length;
}

/** The closest pair in a table — the one that decides whether it is a set. */
function closestPair(table) {
  const names = Object.keys(table);
  let worst = Infinity, pair = ['', ''];
  for (let i = 0; i < names.length; i++) {
    for (let j = i + 1; j < names.length; j++) {
      const d = distance(table[names[i]], table[names[j]]);
      if (d < worst) { worst = d; pair = [names[i], names[j]]; }
    }
  }
  return { worst, pair, n: names.length };
}

console.log('声の単体検査 — 数ではなく違いを測る');

// --- timbres ----------------------------------------------------------------
{
  const { worst, pair, n } = closestPair(VOICE_TIMBRES);
  check('声色: 互いに別物', worst > 0.05,
    `${n} 種、最も近い ${pair[0]}/${pair[1]} で ${worst.toFixed(4)} (> 0.05)`);

  // Pitch is what a listener separates speakers by first, so it gets its own
  // check: a table whose formants differ but whose pitches are identical is
  // thirteen filters on one larynx.
  const pitches = Object.values(VOICE_TIMBRES)
    .map((t) => t.pitch ?? t.f0 ?? t.base ?? null)
    .filter((v) => typeof v === 'number');
  const lo = Math.min(...pitches), hi = Math.max(...pitches);
  check('声色: 基本周波数に幅がある', pitches.length >= 2 && hi / lo > 1.5,
    `${lo} – ${hi} Hz (比 ${(hi / lo).toFixed(2)} > 1.5), ${pitches.length} 件`);
}

// --- combat vocals and creature voices --------------------------------------
{
  const v = closestPair(VOCALS);
  check('戦闘発声: 互いに別物', v.worst > 0.03,
    `${v.n} 種、最も近い ${v.pair[0]}/${v.pair[1]} で ${v.worst.toFixed(4)} (> 0.03)`);

  const c = closestPair(CREATURE_VOICES);
  check('敵種別の発声: 互いに別物', c.worst > 0.05,
    `${c.n} 種、最も近い ${c.pair[0]}/${c.pair[1]} で ${c.worst.toFixed(4)} (> 0.05)`);
}

// --- phonemes ---------------------------------------------------------------
//
// Formant synthesis with one vowel is a hum. The first two formants are what
// separate vowels, so the set has to span a real area of that plane rather than
// sit at one point.
{
  const rows = Object.entries(PHONEMES);
  // The table stores formants as `f: [F1, F2, F3, F4]` in hertz. The first
  // version guessed field names and reported "unreadable", which is a harness
  // failure wearing the costume of a missing feature — the fifth of those
  // today, so it gets the same treatment as the rest: read the data first.
  const pts = rows
    .filter(([, p]) => Array.isArray(p.f) && p.f.length >= 2)
    .map(([k, p]) => [k, p.f[0], p.f[1]]);
  if (!pts.length) {
    check('音素: フォルマント平面に広がり', false, `f1/f2 が読めない (${rows.length} 音素)`);
  } else {
    const f1 = pts.map((p) => p[1]), f2 = pts.map((p) => p[2]);
    const s1 = Math.max(...f1) - Math.min(...f1);
    const s2 = Math.max(...f2) - Math.min(...f2);
    check('音素: フォルマント平面に広がり', s1 > 200 && s2 > 600,
      `F1 幅 ${s1.toFixed(0)} Hz (> 200), F2 幅 ${s2.toFixed(0)} Hz (> 600), ${pts.length} 音素`);
  }
  check('調音の種類', Object.keys(ARTICULATIONS || {}).length >= 3,
    `${Object.keys(ARTICULATIONS || {}).length} 種 (>= 3)`);
}

// --- text becomes speech ----------------------------------------------------
//
// The dialogue-voiced boolean is satisfied by a function existing. What it has
// to do is turn different lines into different utterances, and the same line
// into the same one — otherwise it is noise keyed to nothing.
if (typeof utteranceFromText === 'function') {
  const a = utteranceFromText('北の塔で待つ');
  const b = utteranceFromText('剣を取れ、時間がない');
  const a2 = utteranceFromText('北の塔で待つ');
  // It returns { segments: [...] }, not an array.
  const len = (u) => (Array.isArray(u) ? u.length : (u && u.segments ? u.segments.length : 0));
  check('台詞: 行が違えば発話も違う', len(a) > 0 && len(b) > 0 && JSON.stringify(a) !== JSON.stringify(b),
    `${len(a)} 単位 vs ${len(b)} 単位`);
  check('台詞: 同じ行は同じ発話', JSON.stringify(a) === JSON.stringify(a2),
    '決定的');
  check('台詞: 長さが行に比例する', len(b) > len(a),
    `${len(a)} → ${len(b)}`);
} else {
  check('台詞: 文から発話を作る', false, 'utteranceFromText が無い');
}

// --- music ------------------------------------------------------------------
{
  const m = MUSIC_MODES || {};
  const names = Object.keys(m);
  check('音楽: 場面ごとの調子', names.length >= 3, `${names.length} 種: ${names.join(', ')}`);
  if (names.length >= 2) {
    const { worst, pair } = closestPair(m);
    check('音楽: 調子が互いに別物', worst > 0.05,
      `最も近い ${pair[0]}/${pair[1]} で ${worst.toFixed(4)} (> 0.05)`);
  }
}

console.log(failures ? `\n${failures} 件 不合格` : '\n全て合格');
process.exit(failures ? 1 : 0);
