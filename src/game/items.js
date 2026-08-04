// ============================================================================
//  items.js — the equipment, consumable and spell database, plus the damage
//  maths that ties stats to weapons.
//
//  Weapons scale off stats on a letter grade like the games this is modelled
//  on: a Quality build with C/C scaling out-damages a pure-Strength build on a
//  D/B weapon only past a certain investment, which is what makes the level-up
//  screen a real decision instead of a formality.
// ============================================================================

export const SCALING_COEF = { S: 1.25, A: 0.98, B: 0.76, C: 0.56, D: 0.36, E: 0.20, '-': 0 };

export const UPGRADE_MUL = [1.00, 1.12, 1.24, 1.37, 1.50, 1.64, 1.78, 1.93, 2.08, 2.24, 2.40];
export const UPGRADE_COST = [0, 400, 700, 1100, 1700, 2600, 3800, 5400, 7600, 10500, 14500];
export const UPGRADE_MATERIAL = [0, 1, 1, 2, 2, 3, 3, 4, 5, 6, 8];

/** Diminishing-returns curve for a stat's contribution to weapon damage. */
export function statCurve(v) {
  if (v <= 0) return 0;
  // Three soft caps at 18 / 40 / 60, mirroring the pacing of the genre.
  if (v <= 18) return (v / 18) * 0.42;
  if (v <= 40) return 0.42 + ((v - 18) / 22) * 0.40;
  if (v <= 60) return 0.82 + ((v - 40) / 20) * 0.13;
  return Math.min(1.0, 0.95 + (v - 60) / 200);
}

export const DAMAGE_TYPE = {
  PHYSICAL: 'physical', FIRE: 'fire', LIGHTNING: 'lightning',
  MAGIC: 'magic', HOLY: 'holy', POISON: 'poison',
};

// ---------------------------------------------------------------------------
//  Weapons
//  shape: how the blade is built (length, width, thickness, colours)
// ---------------------------------------------------------------------------

const W = (id, name, cls, base, scaling, req, weight, extra = {}) => ({
  id, name, kind: 'weapon', class: cls, base, scaling, req, weight,
  rarity: extra.rarity || 1,
  value: extra.value || Math.round(base * 12 + weight * 30),
  desc: extra.desc || '',
  shape: extra.shape || {},
  element: extra.element || null,
  elementBase: extra.elementBase || 0,
  effect: extra.effect || null,
  crit: extra.crit || 1.0,
  ...extra,
});

export const WEAPONS = [
  // --- straight swords -----------------------------------------------------
  W('sword_broken', '折れた刻印剣', 'sword', 26, { str: 'D', dex: 'D' }, { str: 8, dex: 8 }, 3.0,
    { desc: '刻印者が最初に手にする、刃こぼれした剣。それでも斬れる。', shape: { len: 0.80, w: 0.095, t: 0.030, blade: [0.55, 0.56, 0.59], hilt: [0.24, 0.20, 0.16] }, rarity: 0, value: 0 }),
  W('sword_knight', '騎士長剣', 'sword', 38, { str: 'D', dex: 'C' }, { str: 10, dex: 12 }, 4.0,
    { desc: '王国騎士の標準装備。素直で扱いやすい。', shape: { len: 0.94, w: 0.102, t: 0.032, blade: [0.63, 0.65, 0.70], hilt: [0.30, 0.24, 0.18] } }),
  W('sword_ember', '残り火の細剣', 'sword', 34, { dex: 'B', fth: 'D' }, { str: 8, dex: 16 }, 3.2,
    { desc: '刃に消えぬ熾火が宿る。', element: DAMAGE_TYPE.FIRE, elementBase: 18, rarity: 2, shape: { len: 0.90, w: 0.082, t: 0.026, blade: [0.86, 0.52, 0.28], hilt: [0.28, 0.16, 0.12], glow: 0.35 } }),
  W('sword_mire', '沼影の刃', 'sword', 40, { dex: 'B' }, { str: 9, dex: 18 }, 3.6,
    { desc: '毒を纏った刺客の剣。', effect: { type: 'poison', build: 26 }, rarity: 2, shape: { len: 0.92, w: 0.090, t: 0.028, blade: [0.42, 0.58, 0.38], hilt: [0.18, 0.22, 0.16] } }),
  W('sword_oath', '誓約の剣', 'sword', 48, { str: 'C', dex: 'C', fth: 'C' }, { str: 16, dex: 16, fth: 14 }, 5.0,
    { desc: '鉄嶺の誓約者が佩く剣。折れることを知らない。', element: DAMAGE_TYPE.HOLY, elementBase: 14, rarity: 3, shape: { len: 1.00, w: 0.108, t: 0.034, blade: [0.76, 0.78, 0.85], hilt: [0.36, 0.30, 0.14], glow: 0.15 } }),

  W('sword_curved', '流水の曲刀', 'sword', 36, { dex: 'A' }, { str: 9, dex: 18 }, 3.4,
    { desc: '斬るのではなく、滑らせて裂く。技量が全て。', crit: 1.15, rarity: 2, shape: { len: 0.96, w: 0.088, t: 0.024, blade: [0.66, 0.68, 0.72], hilt: [0.22, 0.20, 0.24] },
      art: { id: 'art_flow', name: '流水', fp: 14, move: 'sword_h2', desc: '踏み込みながら滑る一突き。' } }),
  W('sword_thorn', '荊の剣', 'sword', 33, { str: 'D', dex: 'B' }, { str: 10, dex: 16 }, 3.3,
    { desc: '刃の背に返しが並ぶ。抜くときに、より深く裂ける。', effect: { type: 'bleed', build: 32 }, rarity: 2, shape: { len: 0.90, w: 0.086, t: 0.026, blade: [0.62, 0.56, 0.52], hilt: [0.26, 0.20, 0.18] } }),
  W('sword_stormmark', '雷紋の剣', 'sword', 37, { dex: 'C', fth: 'C' }, { str: 10, dex: 15, fth: 15 }, 3.6,
    { desc: '断崖の竜が落ちた日、この刃だけが焼け残った。', element: DAMAGE_TYPE.LIGHTNING, elementBase: 22, rarity: 3, shape: { len: 0.95, w: 0.094, t: 0.028, blade: [0.88, 0.86, 0.56], hilt: [0.28, 0.26, 0.20], glow: 0.4 },
      art: { id: 'art_bolt', name: '落雷', fp: 22, move: 'sword_h1', desc: '振り下ろしに雷を落とす。' } }),
  W('sword_hollow', '虚ろの刃', 'sword', 28, { dex: 'C', int: 'B' }, { str: 8, dex: 14, int: 20 }, 2.9,
    { desc: '軽い。軽すぎる。中身が抜けているのだ、たぶん持ち主も。', crit: 1.35, element: DAMAGE_TYPE.MAGIC, elementBase: 20, rarity: 3, shape: { len: 0.92, w: 0.078, t: 0.020, blade: [0.50, 0.48, 0.72], hilt: [0.20, 0.20, 0.28], glow: 0.3 } }),
  W('sword_pilgrim', '巡礼者の直剣', 'sword', 35, { str: 'C', fth: 'D' }, { str: 13, dex: 11, fth: 10 }, 3.8,
    { desc: '誰も彼も同じ剣を持って歩いた。同じ場所で倒れた。', shape: { len: 0.92, w: 0.100, t: 0.032, blade: [0.60, 0.58, 0.56], hilt: [0.30, 0.26, 0.20] } }),

  // --- greatswords ---------------------------------------------------------
  W('great_iron', '鉄大剣', 'greatsword', 58, { str: 'C', dex: 'E' }, { str: 20, dex: 10 }, 9.0,
    { desc: '鍛え上げただけの鉄塊。重さがそのまま威力になる。', shape: { len: 1.32, w: 0.145, t: 0.042, blade: [0.58, 0.58, 0.60], hilt: [0.26, 0.20, 0.15] } }),
  W('great_husk', '亡骸の大剣', 'greatsword', 66, { str: 'B' }, { str: 26, dex: 10 }, 11.5,
    { desc: '死してなお振るわれ続けた刃。', shape: { len: 1.44, w: 0.155, t: 0.048, blade: [0.44, 0.46, 0.44], hilt: [0.20, 0.18, 0.16] }, rarity: 2 }),
  W('great_cinder', '燼の斬馬刀', 'greatsword', 74, { str: 'B', fth: 'D' }, { str: 30, dex: 12, fth: 12 }, 13.0,
    { desc: '振るうたび灰が舞い、火が走る。', element: DAMAGE_TYPE.FIRE, elementBase: 32, rarity: 3, shape: { len: 1.56, w: 0.170, t: 0.052, blade: [0.52, 0.30, 0.22], hilt: [0.24, 0.16, 0.12], glow: 0.45 } }),
  W('great_frost', '白牙の大剣', 'greatsword', 70, { str: 'B', int: 'C' }, { str: 26, dex: 12, int: 16 }, 12.0,
    { desc: '峰の氷から削り出された刃。', element: DAMAGE_TYPE.MAGIC, elementBase: 30, effect: { type: 'frost', build: 30 }, rarity: 3, shape: { len: 1.48, w: 0.160, t: 0.046, blade: [0.72, 0.84, 0.92], hilt: [0.30, 0.34, 0.40], glow: 0.25 },
      art: { id: 'art_hoar', name: '白息', fp: 26, move: 'great_h2', desc: '回転しながら冷気を撒く。' } }),
  W('great_bell', '鐘割りの大剣', 'greatsword', 62, { str: 'A' }, { str: 28, dex: 8 }, 14.5,
    { desc: '刃ではなく厚み。鐘を割るために鋳られ、以来ずっと人を割っている。', rarity: 2, shape: { len: 1.40, w: 0.190, t: 0.070, blade: [0.48, 0.47, 0.46], hilt: [0.24, 0.20, 0.16] },
      art: { id: 'art_toll', name: '打鐘', fp: 24, move: 'great_h1', desc: '地を打ち、周囲の強靭を削ぐ。' } }),
  W('great_root', '根喰いの大剣', 'greatsword', 64, { str: 'B', fth: 'D' }, { str: 24, dex: 11, fth: 10 }, 11.0,
    { desc: '沼の底で二百年、木に食われていた。今は木が刃の側だ。', effect: { type: 'poison', build: 34 }, rarity: 3, shape: { len: 1.46, w: 0.150, t: 0.044, blade: [0.44, 0.52, 0.36], hilt: [0.26, 0.28, 0.20] } }),
  W('great_vow', '誓約の斬刃', 'greatsword', 68, { str: 'C', fth: 'B' }, { str: 22, dex: 12, fth: 22 }, 12.5,
    { desc: '誓いを立てた者にしか重さが分からない、と誓約者は言う。', element: DAMAGE_TYPE.HOLY, elementBase: 34, rarity: 3, shape: { len: 1.50, w: 0.158, t: 0.046, blade: [0.80, 0.78, 0.70], hilt: [0.36, 0.30, 0.16], glow: 0.2 } }),

  // --- spears --------------------------------------------------------------
  W('spear_ash', '灰木の槍', 'spear', 32, { str: 'D', dex: 'C' }, { str: 12, dex: 14 }, 4.5,
    { desc: '間合いを制する者が勝つ。', shape: { len: 1.85, w: 0.038, t: 0.032, blade: [0.70, 0.72, 0.74], hilt: [0.34, 0.26, 0.17], haft: true } }),
  W('spear_knight', '騎士槍', 'spear', 42, { str: 'C', dex: 'B' }, { str: 15, dex: 18 }, 5.5,
    { desc: '馬上でも徒歩でも。', shape: { len: 2.05, w: 0.042, t: 0.034, blade: [0.78, 0.80, 0.84], hilt: [0.30, 0.24, 0.16], haft: true } }),
  W('spear_drake', '竜牙の槍', 'spear', 52, { str: 'C', dex: 'B' }, { str: 18, dex: 22 }, 7.0,
    { desc: '断崖の竜の牙を穂先に据えた。', element: DAMAGE_TYPE.LIGHTNING, elementBase: 26, rarity: 3, shape: { len: 2.15, w: 0.048, t: 0.036, blade: [0.90, 0.86, 0.52], hilt: [0.28, 0.22, 0.16], haft: true, glow: 0.35 },
      art: { id: 'art_skewer', name: '貫き', fp: 20, move: 'spear_h1', desc: '一直線に踏み込む長い刺突。' } }),
  W('spear_harpoon', '銛', 'spear', 38, { str: 'D', dex: 'B' }, { str: 12, dex: 17 }, 4.8,
    { desc: '返しが肉に残る。抜こうとするほど傷が広がる。', effect: { type: 'bleed', build: 34 }, rarity: 2, shape: { len: 1.90, w: 0.044, t: 0.030, blade: [0.62, 0.60, 0.54], hilt: [0.24, 0.22, 0.18], haft: true } }),
  W('spear_hoar', '霜柱の槍', 'spear', 44, { dex: 'B', int: 'C' }, { str: 13, dex: 18, int: 14 }, 5.8,
    { desc: '穂先が常に濡れている。溶けているのではなく、凍り直している。', element: DAMAGE_TYPE.MAGIC, elementBase: 22, effect: { type: 'frost', build: 26 }, rarity: 3, shape: { len: 2.00, w: 0.044, t: 0.032, blade: [0.74, 0.86, 0.94], hilt: [0.28, 0.32, 0.38], haft: true, glow: 0.2 } }),
  W('spear_pilgrim', '巡礼の杖槍', 'spear', 30, { str: 'D', dex: 'C', fth: 'D' }, { str: 11, dex: 13, fth: 10 }, 4.0,
    { desc: '歩くための杖に、必要があって穂先をつけた。順序はいつもそうだ。', shape: { len: 1.90, w: 0.036, t: 0.030, blade: [0.66, 0.64, 0.60], hilt: [0.32, 0.26, 0.18], haft: true } }),

  // --- axes ----------------------------------------------------------------
  W('axe_wood', '樵の斧', 'axe', 40, { str: 'C' }, { str: 14, dex: 8 }, 5.5,
    { desc: '木を割るために作られたが、よく効く。', shape: { len: 0.72, w: 0.20, t: 0.05, blade: [0.60, 0.60, 0.62], hilt: [0.32, 0.24, 0.16], axe: true } }),
  W('axe_bandit', '野盗の戦斧', 'axe', 50, { str: 'B' }, { str: 20, dex: 9 }, 7.5,
    { desc: '刃こぼれと血脂の層で厚みを増している。', shape: { len: 0.86, w: 0.24, t: 0.055, blade: [0.52, 0.50, 0.48], hilt: [0.26, 0.20, 0.14], axe: true }, rarity: 2 }),
  W('axe_stone', '石喰いの大斧', 'axe', 68, { str: 'A' }, { str: 32, dex: 10 }, 14.0,
    { desc: '岩ごと砕く。当たれば、の話だが。', shape: { len: 1.05, w: 0.34, t: 0.075, blade: [0.46, 0.44, 0.42], hilt: [0.24, 0.20, 0.16], axe: true }, rarity: 3 }),

  W('hammer_iron', '鉄槌', 'axe', 62, { str: 'A' }, { str: 26, dex: 8 }, 11.0,
    { desc: '刃はない。だから刃こぼれもしない。鎧ごと潰す。', rarity: 2, shape: { len: 0.92, w: 0.26, t: 0.24, blade: [0.42, 0.42, 0.44], hilt: [0.28, 0.22, 0.15], axe: true } }),
  W('axe_cleaver', '肉断ちの鉈', 'axe', 44, { str: 'C', dex: 'D' }, { str: 15, dex: 10 }, 5.0,
    { desc: '料理人の道具だった。用途はさほど変わっていない。', effect: { type: 'bleed', build: 30 }, rarity: 2, shape: { len: 0.70, w: 0.22, t: 0.048, blade: [0.58, 0.54, 0.50], hilt: [0.28, 0.22, 0.16], axe: true } }),
  W('axe_ember', '燼の手斧', 'axe', 46, { str: 'C', fth: 'D' }, { str: 16, dex: 9, fth: 10 }, 6.0,
    { desc: '焦土で拾った斧は、みな柄が焼け落ちている。これは残っていた。', element: DAMAGE_TYPE.FIRE, elementBase: 24, rarity: 2, shape: { len: 0.80, w: 0.23, t: 0.052, blade: [0.56, 0.34, 0.24], hilt: [0.26, 0.18, 0.13], axe: true, glow: 0.3 } }),
  W('hammer_bell', '鐘槌', 'axe', 58, { str: 'B', fth: 'C' }, { str: 24, dex: 8, fth: 14 }, 12.5,
    { desc: '鐘守が振るう。当たった者は、しばらく音しか聞こえないという。', element: DAMAGE_TYPE.HOLY, elementBase: 26, rarity: 3, shape: { len: 0.98, w: 0.30, t: 0.28, blade: [0.62, 0.56, 0.32], hilt: [0.28, 0.22, 0.15], axe: true, glow: 0.15 },
      art: { id: 'art_peal', name: '響鳴', fp: 28, move: 'axe_h1', desc: '打点から音が広がり、強靭を剥がす。' } }),
  W('axe_twinmoon', '双月の斧', 'axe', 54, { str: 'B', dex: 'C' }, { str: 21, dex: 14 }, 8.5,
    { desc: '刃が二枚。振り切ったあとに、もう一度当たる。', crit: 1.10, rarity: 3, shape: { len: 0.94, w: 0.30, t: 0.058, blade: [0.54, 0.56, 0.60], hilt: [0.24, 0.20, 0.16], axe: true },
      art: { id: 'art_orbit', name: '双回', fp: 22, move: 'axe_h2', desc: '二枚の刃で連続して薙ぐ。' } }),

  // --- daggers -------------------------------------------------------------
  W('dagger_thief', '盗人の短刀', 'dagger', 20, { dex: 'B' }, { str: 6, dex: 14 }, 1.5,
    { desc: '速さと、背後を取る度胸があれば。', crit: 1.45, shape: { len: 0.44, w: 0.060, t: 0.020, blade: [0.60, 0.62, 0.65], hilt: [0.22, 0.18, 0.14] } }),
  W('dagger_ritual', '儀式短刀', 'dagger', 24, { dex: 'A', int: 'D' }, { str: 6, dex: 18, int: 12 }, 1.8,
    { desc: '刻印を刻むための刃。人にも効く。', crit: 1.55, element: DAMAGE_TYPE.MAGIC, elementBase: 12, rarity: 2, shape: { len: 0.48, w: 0.058, t: 0.019, blade: [0.62, 0.58, 0.82], hilt: [0.20, 0.18, 0.26], glow: 0.3 } }),

  W('dagger_frost', '霜の小刀', 'dagger', 22, { dex: 'A', int: 'C' }, { str: 6, dex: 16, int: 14 }, 1.6,
    { desc: '柄まで凍っている。握る側も無事では済まない。', crit: 1.50, element: DAMAGE_TYPE.MAGIC, elementBase: 14, effect: { type: 'frost', build: 24 }, rarity: 3, shape: { len: 0.46, w: 0.058, t: 0.018, blade: [0.72, 0.84, 0.92], hilt: [0.26, 0.30, 0.36], glow: 0.28 } }),

  W('dagger_venom', '毒牙', 'dagger', 21, { dex: 'A' }, { str: 6, dex: 17 }, 1.4,
    { desc: '刺すためではなく、塗るための刃。', crit: 1.40, effect: { type: 'poison', build: 38 }, rarity: 2, shape: { len: 0.42, w: 0.052, t: 0.017, blade: [0.48, 0.60, 0.42], hilt: [0.20, 0.24, 0.18] } }),
  W('dagger_bone', '骨錐', 'dagger', 18, { dex: 'A' }, { str: 5, dex: 15 }, 0.9,
    { desc: '誰かの腓骨を削っただけのもの。それでも鎧の隙間には十分入る。', crit: 1.70, rarity: 2, shape: { len: 0.40, w: 0.046, t: 0.016, blade: [0.82, 0.80, 0.72], hilt: [0.34, 0.32, 0.28] },
      art: { id: 'art_slip', name: '滑り', fp: 12, move: 'dagger_h2', desc: '下段から擦り上げ、体勢を崩す。' } }),

  // --- bows ----------------------------------------------------------------
  W('bow_short', '短弓', 'bow', 26, { dex: 'C' }, { str: 8, dex: 14 }, 2.5,
    { desc: '射程は短いが、素早く引ける。', ranged: true, shape: { len: 1.05, w: 0.04, t: 0.03, blade: [0.34, 0.26, 0.18], hilt: [0.28, 0.22, 0.15], bow: true } }),
  W('bow_long', '長弓', 'bow', 38, { dex: 'B' }, { str: 12, dex: 20 }, 4.0,
    { desc: '遠くの敵を、静かに減らす。', ranged: true, shape: { len: 1.45, w: 0.045, t: 0.032, blade: [0.30, 0.24, 0.17], hilt: [0.26, 0.20, 0.14], bow: true }, rarity: 2 }),

  W('bow_horn', '角弓', 'bow', 44, { str: 'C', dex: 'C' }, { str: 18, dex: 16 }, 5.2,
    { desc: '引くのに腕力がいる。当たれば、鎧の上からでも骨に届く。', ranged: true, rarity: 2, shape: { len: 1.25, w: 0.05, t: 0.036, blade: [0.44, 0.36, 0.24], hilt: [0.30, 0.24, 0.16], bow: true } }),
  W('bow_whisper', '囁きの弓', 'bow', 32, { dex: 'A' }, { str: 9, dex: 24 }, 2.8,
    { desc: '弦の音がしない。当たるまで、誰も撃たれたことに気づかない。', ranged: true, crit: 1.25, rarity: 3, shape: { len: 1.35, w: 0.038, t: 0.028, blade: [0.24, 0.22, 0.20], hilt: [0.20, 0.18, 0.15], bow: true } }),

  W('spear_mire', '沼守の三叉', 'spear', 46, { str: 'C', dex: 'B' }, { str: 16, dex: 19 }, 6.2,
    { desc: '沼の底から引き上げられた漁具。返しが深い。', effect: { type: 'bleed', build: 28 }, rarity: 2, shape: { len: 1.95, w: 0.052, t: 0.034, blade: [0.58, 0.62, 0.56], hilt: [0.26, 0.24, 0.18], haft: true } }),

  // --- catalysts -----------------------------------------------------------
  W('staff_apprentice', '徒弟の杖', 'staff', 14, { int: 'B' }, { str: 6, dex: 8, int: 14 }, 2.5,
    { desc: '魔力を編むための触媒。殴ることもできる、一応。', catalyst: 'int', shape: { len: 1.15, w: 0.05, t: 0.05, blade: [0.32, 0.28, 0.42], hilt: [0.26, 0.22, 0.30], staff: true, glow: 0.3 } }),
  W('staff_ember', '残り火の聖印', 'staff', 16, { fth: 'B' }, { str: 6, dex: 8, fth: 16 }, 2.0,
    { desc: '王冠の欠片を戴く聖印。祈りを火に変える。', catalyst: 'fth', rarity: 2, shape: { len: 0.85, w: 0.06, t: 0.05, blade: [0.72, 0.44, 0.24], hilt: [0.30, 0.24, 0.18], staff: true, glow: 0.5 } }),
  W('staff_glint', '輝石の杖', 'staff', 12, { int: 'A' }, { str: 6, dex: 8, int: 26 }, 3.0,
    { desc: '頭に嵌めた輝石が魔力を絞る。杖としては、もう殴れない。', catalyst: 'int', rarity: 3, shape: { len: 1.25, w: 0.055, t: 0.055, blade: [0.40, 0.46, 0.78], hilt: [0.24, 0.24, 0.34], staff: true, glow: 0.55 } }),
  W('staff_bone', '骨の触媒', 'staff', 18, { int: 'C', dex: 'D' }, { str: 7, dex: 12, int: 12 }, 1.8,
    { desc: '軽い。魔力の通りは悪いが、いざとなれば棍棒になる。', catalyst: 'int', shape: { len: 1.00, w: 0.05, t: 0.05, blade: [0.80, 0.78, 0.70], hilt: [0.34, 0.32, 0.28], staff: true, glow: 0.15 } }),
  W('staff_vow', '誓約の聖印', 'staff', 15, { fth: 'A' }, { str: 6, dex: 8, fth: 24 }, 2.2,
    { desc: '鉄嶺で二百年、同じ祈りだけを唱えてきた印。', catalyst: 'fth', rarity: 3, shape: { len: 0.90, w: 0.062, t: 0.052, blade: [0.80, 0.72, 0.34], hilt: [0.32, 0.28, 0.18], staff: true, glow: 0.45 } }),

  // --- shields (equipped in the off hand) ----------------------------------
  W('shield_wood', '木盾', 'shield', 8, { str: 'E' }, { str: 10, dex: 6 }, 3.5,
    { desc: '無いよりはるかに良い。', guard: 0.62, stability: 26, shape: { w: 0.40, h: 0.54, t: 0.055, face: [0.30, 0.23, 0.16], rim: [0.30, 0.30, 0.32] } }),
  W('shield_kite', '騎士の凧盾', 'shield', 12, { str: 'D' }, { str: 14, dex: 8 }, 5.5,
    { desc: '正面からの一撃を確実に受け止める。', guard: 0.80, stability: 42, shape: { w: 0.43, h: 0.70, t: 0.065, face: [0.36, 0.38, 0.44], rim: [0.36, 0.36, 0.40] } }),
  W('shield_oath', '誓約の大盾', 'shield', 18, { str: 'C' }, { str: 24, dex: 8 }, 11.0,
    { desc: '壁になることを選んだ者の証。', guard: 0.94, stability: 62, rarity: 3, shape: { w: 0.54, h: 0.88, t: 0.08, face: [0.33, 0.35, 0.40], rim: [0.62, 0.56, 0.30] } }),
  // A buckler trades guard for weight: it is for players who intend to parry,
  // not to hold. Blocking with it is a mistake the numbers make plain.
  W('shield_buckler', '小盾', 'shield', 6, { dex: 'D' }, { str: 8, dex: 12 }, 1.4,
    { desc: '受けるための盾ではない。弾くための盾だ。', guard: 0.42, stability: 16, shape: { w: 0.28, h: 0.30, t: 0.04, face: [0.50, 0.50, 0.54], rim: [0.60, 0.58, 0.52] } }),
  W('shield_bone', '骨盾', 'shield', 10, { str: 'D' }, { str: 12, dex: 8 }, 3.0,
    { desc: '肋を組んで革で括ってある。持ち主が誰だったかは考えないほうがいい。', guard: 0.70, stability: 32, rarity: 2, shape: { w: 0.40, h: 0.60, t: 0.06, face: [0.80, 0.78, 0.70], rim: [0.36, 0.32, 0.26] } }),
  W('shield_tower', '塔盾', 'shield', 22, { str: 'B' }, { str: 30, dex: 8 }, 16.0,
    { desc: '正面を捨てさせる盾。ただし、背中は自分で守れ。', guard: 0.99, stability: 78, rarity: 3, shape: { w: 0.58, h: 1.02, t: 0.10, face: [0.40, 0.40, 0.42], rim: [0.50, 0.48, 0.44] } }),
];

// ---------------------------------------------------------------------------
//  Armour
// ---------------------------------------------------------------------------

const A = (id, name, slot, set, def, poise, weight, colors, extra = {}) => ({
  id, name, kind: 'armor', slot, set, def, poise, weight, colors,
  rarity: extra.rarity || 1,
  value: extra.value || Math.round(def * 30 + weight * 25),
  desc: extra.desc || '',
  resist: extra.resist || {},
  ...extra,
});

export const ARMOR = [
  // set: 刻印者 (starting rags)
  A('head_marked', '刻印者の頭巾', 'head', 'marked', 1.5, 1, 1.0, { cloth: [0.30, 0.28, 0.26], armor: [0.26, 0.24, 0.22] }, { rarity: 0, value: 0, desc: '色の抜けた布。' }),
  A('body_marked', '刻印者のぼろ', 'body', 'marked', 3.5, 3, 2.5, { cloth: [0.32, 0.29, 0.26], armor: [0.28, 0.26, 0.24], leather: [0.24, 0.20, 0.17] }, { rarity: 0, value: 0 }),
  A('arms_marked', '刻印者の手甲', 'arms', 'marked', 1.2, 1, 0.8, { cloth: [0.30, 0.28, 0.25] }, { rarity: 0, value: 0 }),
  A('legs_marked', '刻印者の脚衣', 'legs', 'marked', 2.0, 2, 1.4, { leather: [0.26, 0.23, 0.20] }, { rarity: 0, value: 0 }),

  // set: 野盗
  A('head_bandit', '野盗の面覆い', 'head', 'bandit', 2.4, 2, 1.2, { cloth: [0.36, 0.26, 0.20], armor: [0.30, 0.26, 0.22] }),
  A('body_bandit', '野盗の胴鎧', 'body', 'bandit', 6.5, 7, 5.5, { armor: [0.34, 0.28, 0.22], cloth: [0.30, 0.24, 0.20], leather: [0.28, 0.22, 0.17] }),
  A('arms_bandit', '野盗の腕当て', 'arms', 'bandit', 2.4, 2, 1.6, { cloth: [0.32, 0.26, 0.21] }),
  A('legs_bandit', '野盗の脚甲', 'legs', 'bandit', 3.6, 4, 2.8, { leather: [0.30, 0.24, 0.19] }),

  // set: 騎士
  A('head_knight', '騎士兜', 'head', 'knight', 5.5, 6, 3.6, { armor: [0.58, 0.60, 0.66], cloth: [0.30, 0.32, 0.38] }, { rarity: 2 }),
  A('body_knight', '騎士鎧', 'body', 'knight', 13.0, 16, 11.0, { armor: [0.56, 0.58, 0.64], cloth: [0.26, 0.30, 0.40], leather: [0.30, 0.26, 0.22] }, { rarity: 2 }),
  A('arms_knight', '騎士の籠手', 'arms', 'knight', 5.0, 5, 3.4, { armor: [0.56, 0.58, 0.64] }, { rarity: 2 }),
  A('legs_knight', '騎士の脚甲', 'legs', 'knight', 7.5, 8, 5.8, { armor: [0.54, 0.56, 0.62], leather: [0.28, 0.24, 0.20] }, { rarity: 2 }),

  // set: 誓約者
  A('head_oath', '誓約者の兜', 'head', 'oath', 8.0, 10, 5.4, { armor: [0.48, 0.46, 0.44], accent: [0.66, 0.54, 0.22] }, { rarity: 3, resist: { fire: 0.1 } }),
  A('body_oath', '誓約者の重鎧', 'body', 'oath', 19.0, 26, 17.0, { armor: [0.46, 0.44, 0.42], cloth: [0.34, 0.20, 0.18], accent: [0.66, 0.54, 0.22] }, { rarity: 3, resist: { fire: 0.12 } }),
  A('arms_oath', '誓約者の籠手', 'arms', 'oath', 7.5, 9, 5.2, { armor: [0.46, 0.44, 0.42] }, { rarity: 3 }),
  A('legs_oath', '誓約者の具足', 'legs', 'oath', 11.0, 13, 8.8, { armor: [0.44, 0.42, 0.40] }, { rarity: 3 }),

  // set: 灰纏い
  A('head_ash', '灰纏いの頭巾', 'head', 'ash', 4.0, 3, 1.6, { cloth: [0.34, 0.28, 0.26], armor: [0.30, 0.24, 0.22] }, { rarity: 3, resist: { fire: 0.22 } }),
  A('body_ash', '灰纏いの外套', 'body', 'ash', 9.5, 8, 5.0, { cloth: [0.36, 0.28, 0.25], armor: [0.32, 0.25, 0.22], accent: [0.72, 0.36, 0.18] }, { rarity: 3, resist: { fire: 0.28 } }),
  A('arms_ash', '灰纏いの腕巻き', 'arms', 'ash', 3.5, 3, 1.4, { cloth: [0.34, 0.27, 0.24] }, { rarity: 3, resist: { fire: 0.18 } }),
  A('legs_ash', '灰纏いの脚衣', 'legs', 'ash', 5.5, 5, 2.6, { leather: [0.30, 0.24, 0.21] }, { rarity: 3, resist: { fire: 0.18 } }),

  // set: 魔道
  A('head_arcane', '魔道の兜巾', 'head', 'arcane', 3.0, 2, 1.1, { cloth: [0.24, 0.22, 0.34], accent: [0.46, 0.42, 0.78] }, { rarity: 2, resist: { magic: 0.2 } }),
  A('body_arcane', '魔道のローブ', 'body', 'arcane', 7.0, 5, 3.4, { cloth: [0.22, 0.21, 0.32], accent: [0.44, 0.40, 0.76], leather: [0.24, 0.22, 0.26] }, { rarity: 2, resist: { magic: 0.25 } }),
  A('arms_arcane', '魔道の腕輪', 'arms', 'arcane', 2.6, 2, 1.0, { cloth: [0.24, 0.22, 0.34] }, { rarity: 2 }),
  A('legs_arcane', '魔道の裾', 'legs', 'arcane', 4.2, 3, 1.9, { cloth: [0.22, 0.20, 0.30] }, { rarity: 2 }),

  // set: 巡礼 — the cheap middle. Nothing it does is remarkable, which is the
  // point: it is what a player wears while deciding what they actually are.
  A('head_pilgrim', '巡礼の笠', 'head', 'pilgrim', 2.8, 2, 1.3, { cloth: [0.42, 0.38, 0.30], leather: [0.30, 0.26, 0.20] }),
  A('body_pilgrim', '巡礼の外套', 'body', 'pilgrim', 7.5, 6, 4.4, { cloth: [0.40, 0.36, 0.29], armor: [0.34, 0.31, 0.26], leather: [0.30, 0.25, 0.20] }),
  A('arms_pilgrim', '巡礼の手甲', 'arms', 'pilgrim', 2.8, 2, 1.3, { leather: [0.32, 0.27, 0.21] }),
  A('legs_pilgrim', '巡礼の脚絆', 'legs', 'pilgrim', 4.4, 4, 2.3, { cloth: [0.38, 0.34, 0.28] }),

  // set: 沈黙 — light enough to keep a light roll while carrying a real weapon.
  A('head_silence', '沈黙の面', 'head', 'silence', 2.6, 1, 0.7, { cloth: [0.18, 0.18, 0.20], accent: [0.34, 0.40, 0.34] }, { rarity: 3, resist: { poison: 0.18 } }),
  A('body_silence', '沈黙の衣', 'body', 'silence', 6.0, 4, 2.6, { cloth: [0.17, 0.17, 0.19], leather: [0.20, 0.19, 0.18], accent: [0.32, 0.38, 0.32] }, { rarity: 3, resist: { poison: 0.24 } }),
  A('arms_silence', '沈黙の腕', 'arms', 'silence', 2.2, 1, 0.6, { cloth: [0.18, 0.18, 0.20] }, { rarity: 3 }),
  A('legs_silence', '沈黙の脚衣', 'legs', 'silence', 3.6, 2, 1.2, { leather: [0.19, 0.19, 0.20] }, { rarity: 3, resist: { poison: 0.14 } }),

  // set: 骨甲 — heavy, and the only armour that shrugs off holy and magic both.
  A('head_bone', '骨兜', 'head', 'bone', 6.2, 8, 4.2, { armor: [0.80, 0.78, 0.70], leather: [0.28, 0.24, 0.20] }, { rarity: 3, resist: { magic: 0.14, holy: 0.14 } }),
  A('body_bone', '骨鎧', 'body', 'bone', 15.0, 20, 13.5, { armor: [0.78, 0.76, 0.68], cloth: [0.26, 0.24, 0.22], leather: [0.26, 0.22, 0.18] }, { rarity: 3, resist: { magic: 0.18, holy: 0.18 } }),
  A('arms_bone', '骨の籠手', 'arms', 'bone', 5.8, 7, 4.0, { armor: [0.78, 0.76, 0.68] }, { rarity: 3, resist: { magic: 0.10 } }),
  A('legs_bone', '骨の具足', 'legs', 'bone', 8.8, 10, 6.6, { armor: [0.76, 0.74, 0.66], leather: [0.26, 0.22, 0.18] }, { rarity: 3, resist: { holy: 0.10 } }),

  // set: 霜衛 — the peak's answer to the mire's poison.
  A('head_hoar', '霜衛の兜', 'head', 'hoar', 5.0, 5, 3.0, { armor: [0.62, 0.70, 0.78], cloth: [0.34, 0.40, 0.48] }, { rarity: 3, resist: { magic: 0.16 } }),
  A('body_hoar', '霜衛の鎧', 'body', 'hoar', 12.0, 14, 9.5, { armor: [0.60, 0.68, 0.76], cloth: [0.32, 0.38, 0.46], leather: [0.28, 0.30, 0.34] }, { rarity: 3, resist: { magic: 0.22, fire: 0.08 } }),
  A('arms_hoar', '霜衛の籠手', 'arms', 'hoar', 4.6, 5, 2.9, { armor: [0.60, 0.68, 0.76] }, { rarity: 3 }),
  A('legs_hoar', '霜衛の脚甲', 'legs', 'hoar', 7.0, 7, 5.0, { armor: [0.58, 0.66, 0.74] }, { rarity: 3, resist: { magic: 0.12 } }),

  // set: 竜鱗 — the heaviest thing in the game. Wearing all four is a decision
  // about how you dodge, not a decision about defence.
  A('head_drake', '竜鱗の兜', 'head', 'drake', 9.0, 12, 6.8, { armor: [0.40, 0.42, 0.50], accent: [0.78, 0.70, 0.32] }, { rarity: 4, resist: { lightning: 0.22, fire: 0.14 } }),
  A('body_drake', '竜鱗の胸当て', 'body', 'drake', 21.0, 30, 21.0, { armor: [0.38, 0.40, 0.48], leather: [0.30, 0.28, 0.34], accent: [0.78, 0.70, 0.32] }, { rarity: 4, resist: { lightning: 0.28, fire: 0.18 } }),
  A('arms_drake', '竜鱗の籠手', 'arms', 'drake', 8.4, 11, 6.4, { armor: [0.38, 0.40, 0.48] }, { rarity: 4, resist: { lightning: 0.14 } }),
  A('legs_drake', '竜鱗の具足', 'legs', 'drake', 12.5, 16, 10.6, { armor: [0.36, 0.38, 0.46], leather: [0.28, 0.26, 0.32] }, { rarity: 4, resist: { lightning: 0.16 } }),
];

// ---------------------------------------------------------------------------
//  Talismans — passive modifiers
// ---------------------------------------------------------------------------

export const TALISMANS = [
  { id: 'tal_vigor', name: '生命の護符', kind: 'talisman', desc: '最大HPが12%上がる。', mods: { hpMul: 1.12 }, weight: 0.6, rarity: 1, value: 900 },
  { id: 'tal_endure', name: '不屈の護符', kind: 'talisman', desc: 'スタミナ回復が25%速くなる。', mods: { staminaRegenMul: 1.25 }, weight: 0.6, rarity: 1, value: 900 },
  { id: 'tal_hunter', name: '狩人の護符', kind: 'talisman', desc: '与ダメージ+8%、被ダメージ+6%。', mods: { dmgMul: 1.08, takenMul: 1.06 }, weight: 0.5, rarity: 2, value: 1600 },
  { id: 'tal_stone', name: '石の護符', kind: 'talisman', desc: '強靭度+18。', mods: { poiseAdd: 18 }, weight: 1.4, rarity: 2, value: 1600 },
  { id: 'tal_feather', name: '羽の護符', kind: 'talisman', desc: '装備重量の許容が15%増える。', mods: { loadMul: 1.15 }, weight: 0.3, rarity: 2, value: 1800 },
  { id: 'tal_ember', name: '残り火の護符', kind: 'talisman', desc: '炎ダメージ+15%、炎耐性+20%。', mods: { fireMul: 1.15, fireResist: 0.2 }, weight: 0.7, rarity: 2, value: 2200 },
  { id: 'tal_leech', name: '吸命の護符', kind: 'talisman', desc: '致命の一撃でHPを回復する。', mods: { critHeal: 45 }, weight: 0.8, rarity: 3, value: 3200 },
  { id: 'tal_greed', name: '強欲の護符', kind: 'talisman', desc: '獲得する残り火が20%増える。', mods: { soulsMul: 1.2 }, weight: 0.4, rarity: 2, value: 2400 },
  { id: 'tal_parry', name: '受け流しの護符', kind: 'talisman', desc: 'パリィ受付が長くなり、致命ダメージ+20%。', mods: { parryWindow: 0.08, critMul: 1.2 }, weight: 0.6, rarity: 3, value: 3600 },
  { id: 'tal_focus', name: '集中の護符', kind: 'talisman', desc: '最大FPが25%上がる。', mods: { fpMul: 1.25 }, weight: 0.5, rarity: 2, value: 2000 },
  { id: 'tal_wolf', name: '狼の牙', kind: 'talisman', desc: '連続攻撃するほど威力が上がる（最大+18%）。', mods: { comboRamp: 0.06 }, weight: 0.6, rarity: 3, value: 3400 },
  { id: 'tal_lastlight', name: '最後の灯', kind: 'talisman', desc: 'HPが25%以下のとき与ダメージ+25%。', mods: { desperation: 0.25 }, weight: 0.7, rarity: 3, value: 4200 },

  // The second half of the list is deliberately lopsided. A talisman that only
  // gives is a tax on the slot; a talisman that gives and takes is a decision.
  { id: 'tal_glutton', name: '大食らいの護符', kind: 'talisman', desc: '装備重量の許容が32%増える。被ダメージ+10%。', mods: { loadMul: 1.32, takenMul: 1.10 }, weight: 1.2, rarity: 3, value: 5200 },
  { id: 'tal_thin', name: '痩せ我慢の護符', kind: 'talisman', desc: '装備重量の許容が18%減り、与ダメージ+16%。', mods: { loadMul: 0.82, dmgMul: 1.16 }, weight: 0.2, rarity: 3, value: 4800 },
  { id: 'tal_bulwark', name: '城壁の護符', kind: 'talisman', desc: '強靭度+30。スタミナ回復が15%遅くなる。', mods: { poiseAdd: 30, staminaRegenMul: 0.85 }, weight: 2.2, rarity: 3, value: 4400 },
  { id: 'tal_swift', name: '疾風の護符', kind: 'talisman', desc: 'スタミナ回復が45%速くなる。最大HP-8%。', mods: { staminaRegenMul: 1.45, hpMul: 0.92 }, weight: 0.3, rarity: 3, value: 4600 },
  { id: 'tal_duelist', name: '果たし合いの護符', kind: 'talisman', desc: 'パリィ受付がさらに長くなり、致命ダメージ+45%。最大HP-10%。', mods: { parryWindow: 0.13, critMul: 1.45, hpMul: 0.90 }, weight: 0.6, rarity: 4, value: 8800 },
  { id: 'tal_carrion', name: '腐肉喰いの護符', kind: 'talisman', desc: '致命の一撃で大きく回復する。被ダメージ+8%。', mods: { critHeal: 110, takenMul: 1.08 }, weight: 0.9, rarity: 4, value: 9200 },
  { id: 'tal_pyre', name: '火葬の護符', kind: 'talisman', desc: '炎ダメージ+32%。炎耐性-15%。', mods: { fireMul: 1.32, fireResist: -0.15 }, weight: 0.7, rarity: 3, value: 5600 },
  { id: 'tal_ashskin', name: '灰肌の護符', kind: 'talisman', desc: '炎耐性+38%。与ダメージ-6%。', mods: { fireResist: 0.38, dmgMul: 0.94 }, weight: 1.0, rarity: 3, value: 4200 },
  { id: 'tal_hound', name: '猟犬の牙', kind: 'talisman', desc: '連続攻撃の伸びが大きい（最大+33%）。', mods: { comboRamp: 0.11 }, weight: 0.8, rarity: 4, value: 9600 },
  { id: 'tal_ember_deep', name: '深き残り火', kind: 'talisman', desc: '最大FPが45%上がる。最大スタミナ回復-10%。', mods: { fpMul: 1.45, staminaRegenMul: 0.90 }, weight: 0.7, rarity: 3, value: 5400 },
  { id: 'tal_marrow', name: '髄の護符', kind: 'talisman', desc: '最大HPが22%上がる。装備重量の許容-8%。', mods: { hpMul: 1.22, loadMul: 0.92 }, weight: 1.6, rarity: 3, value: 6400 },
  { id: 'tal_beggar', name: '物乞いの護符', kind: 'talisman', desc: '獲得する残り火が55%増える。被ダメージ+18%。', mods: { soulsMul: 1.55, takenMul: 1.18 }, weight: 0.4, rarity: 3, value: 6800 },
  { id: 'tal_finality', name: '終いの護符', kind: 'talisman', desc: 'HPが25%以下のとき与ダメージ+55%。最大HP-12%。', mods: { desperation: 0.55, hpMul: 0.88 }, weight: 0.8, rarity: 4, value: 12000 },
  { id: 'tal_crownward', name: '王冠の残響', kind: 'talisman', desc: '与ダメージ+14%、強靭度+10。最大FP-20%。', mods: { dmgMul: 1.14, poiseAdd: 10, fpMul: 0.80 }, weight: 1.1, rarity: 4, value: 13000 },
];

// ---------------------------------------------------------------------------
//  Consumables & materials
// ---------------------------------------------------------------------------

export const CONSUMABLES = [
  { id: 'flask_hp', name: '緋色の聖杯瓶', kind: 'consumable', desc: 'HPを回復する。篝火で補充される。', flask: 'hp', value: 0, stack: 20 },
  { id: 'flask_fp', name: '蒼色の聖杯瓶', kind: 'consumable', desc: 'FPを回復する。篝火で補充される。', flask: 'fp', value: 0, stack: 20 },
  { id: 'herb_green', name: '緑花草', kind: 'consumable', desc: 'スタミナ回復を一時的に高める。', effect: { staminaRegen: 1.6, dur: 45 }, value: 120, stack: 12 },
  { id: 'antidote', name: '毒消し草', kind: 'consumable', desc: '毒を治療する。', effect: { cure: 'poison' }, value: 150, stack: 12 },
  { id: 'throwing_knife', name: '投げナイフ', kind: 'consumable', desc: '遠くの敵に小さな傷を。', throw: { dmg: 42 }, value: 60, stack: 30 },
  { id: 'firebomb', name: '火炎壺', kind: 'consumable', desc: '割れて炎が広がる。', throw: { dmg: 95, element: 'fire', radius: 3.2 }, value: 180, stack: 20 },
  { id: 'ember_shard', name: '残り火のかけら', kind: 'consumable', desc: '砕くと残り火を得る。', souls: 800, value: 400, stack: 30 },
  { id: 'stone_whet', name: '砥石', kind: 'consumable', desc: '一定時間、武器の物理攻撃力を上げる。', effect: { atkMul: 1.15, dur: 60 }, value: 260, stack: 10 },
  { id: 'resin_fire', name: '火の樹脂', kind: 'consumable', desc: '一定時間、武器に炎を付与する。', effect: { addFire: 55, dur: 60 }, value: 300, stack: 10 },
  { id: 'homeward', name: '帰還の骨片', kind: 'consumable', desc: '最後に休んだ篝火へ戻る。', homeward: true, value: 500, stack: 5 },
  { id: 'blood_stanch', name: '止血草', kind: 'consumable', desc: '出血を治療する。', effect: { cure: 'bleed' }, value: 150, stack: 12 },
  { id: 'warm_stone', name: '温石', kind: 'consumable', desc: '凍傷を治療する。', effect: { cure: 'frost' }, value: 170, stack: 12 },
  { id: 'resin_magic', name: '輝石の樹脂', kind: 'consumable', desc: '一定時間、武器に魔力を付与する。', effect: { addMagic: 60, dur: 60 }, value: 340, stack: 10 },
  { id: 'oil_black', name: '黒油', kind: 'consumable', desc: '一定時間、物理攻撃力を大きく上げる。持続は短い。', effect: { atkMul: 1.32, dur: 25 }, value: 520, stack: 8 },
  { id: 'herb_iron', name: '鉄花草', kind: 'consumable', desc: 'スタミナ回復を長く底上げする。', effect: { staminaRegen: 1.35, dur: 110 }, value: 260, stack: 12 },
  { id: 'pot_poison', name: '毒壺', kind: 'consumable', desc: '割れて毒霧が広がる。', throw: { dmg: 45, element: 'poison', radius: 3.6 }, value: 220, stack: 20 },
  { id: 'pot_frost', name: '霜壺', kind: 'consumable', desc: '割れて冷気が広がる。', throw: { dmg: 60, element: 'magic', radius: 3.0 }, value: 260, stack: 20 },
  { id: 'throwing_spike', name: '投げ杭', kind: 'consumable', desc: '重い。遠くには飛ばないが、よく効く。', throw: { dmg: 96 }, value: 140, stack: 20 },
  { id: 'ember_heart', name: '残り火の熾', kind: 'consumable', desc: '砕くと大きな残り火を得る。', souls: 5200, value: 2600, stack: 20 },
  { id: 'bell_shard', name: '鐘の欠片', kind: 'consumable', desc: '鳴らすと近くの敵が一斉にこちらを向く。使い道はある。', throw: { dmg: 1 }, value: 90, stack: 20 },
];

export const MATERIALS = [
  { id: 'mat_shard', name: '鍛石の欠片', kind: 'material', desc: '武器強化に使う、ありふれた石。', tier: 1, value: 200 },
  { id: 'mat_chunk', name: '鍛石の塊', kind: 'material', desc: '+4 より先の強化に必要。', tier: 2, value: 800 },
  { id: 'mat_core', name: '鍛石の核', kind: 'material', desc: '+7 より先の強化に必要。', tier: 3, value: 2400 },
  { id: 'mat_emberheart', name: '燼の心臓', kind: 'material', desc: '最上位の強化に必要な、王冠の残滓。', tier: 4, value: 8000 },
  { id: 'mat_hide', name: '獣の皮', kind: 'material', desc: '交易品。', value: 90 },
  { id: 'mat_fang', name: '灰狼の牙', kind: 'material', desc: '交易品。', value: 160 },
  { id: 'mat_bone', name: '白い骨', kind: 'material', desc: '交易品。誰のものかは訊かれない。', value: 120 },
  { id: 'mat_scale', name: '竜の鱗', kind: 'material', desc: '交易品。焼いても焦げない。', value: 420 },
  { id: 'mat_bellbronze', name: '鐘の青銅', kind: 'material', desc: '交易品。叩くと、離れた場所で音がする。', value: 640 },
  { id: 'mat_ashsalt', name: '灰塩', kind: 'material', desc: '交易品。焦土の風が運んでくる。', value: 200 },
];

export const KEY_ITEMS = [
  { id: 'key_shard_1', name: '残り火の断片・森', kind: 'key', desc: '縛り手より奪った王冠の断片。' },
  { id: 'key_shard_2', name: '残り火の断片・沼', kind: 'key', desc: '沈殿の玉座より。' },
  { id: 'key_shard_3', name: '残り火の断片・嶺', kind: 'key', desc: '誓約の闘技場より。' },
  { id: 'key_shard_4', name: '残り火の断片・崖', kind: 'key', desc: '竜の棚より。' },
  { id: 'key_shard_5', name: '残り火の断片・焦土', kind: 'key', desc: '燼の玉座より。' },
  { id: 'key_ironrite', name: '鉄の割符', kind: 'key', desc: '鉄砦の門を開く。' },
  { id: 'key_bellrope', name: '鐘の綱', kind: 'key', desc: '鐘楼の番人が握っていた。まだ温かい。' },
  { id: 'key_sisterseal', name: '姉の聖印', kind: 'key', desc: '灰の輪で拾った、焼け残りの聖印。' },
  { id: 'key_ledger', name: '首魁の帳面', kind: 'key', desc: '誰から何を奪ったかが、几帳面に記されている。' },
  { id: 'key_rootheart', name: '根の心臓', kind: 'key', desc: '囁きの森の底にあったもの。まだ脈を打つ。' },
  { id: 'key_coldvow', name: '凍てた誓文', kind: 'key', desc: '白牙峰で凍りついた誓約書。読めるのは半分だけ。' },
];

// ---------------------------------------------------------------------------
//  Spells
// ---------------------------------------------------------------------------

export const SPELLS = [
  { id: 'sp_bolt', name: '魔力の弾', school: 'int', fp: 8, dmg: 55, scale: 'int', speed: 26, life: 3.0, color: [0.55, 0.60, 1.0], desc: '基本にして万能。', req: { int: 10 }, cast: 0.45, value: 800 },
  { id: 'sp_shard', name: '輝石の礫', school: 'int', fp: 14, dmg: 92, scale: 'int', speed: 22, life: 3.2, color: [0.6, 0.75, 1.0], desc: 'やや遅いが、重い。', req: { int: 16 }, cast: 0.7, value: 2000 },
  { id: 'sp_frost', name: '氷の吐息', school: 'int', fp: 22, dmg: 70, scale: 'int', speed: 14, life: 1.2, cone: true, effect: { type: 'frost', build: 34 }, color: [0.7, 0.9, 1.0], desc: '前方に冷気を吹き付ける。', req: { int: 22 }, cast: 0.9, value: 4200 },
  { id: 'sp_blade', name: '魔力の刃', school: 'int', fp: 18, dmg: 0, buff: { addMagic: 70, dur: 60 }, color: [0.6, 0.55, 1.0], desc: '武器に魔力を纏わせる。', req: { int: 18 }, cast: 1.1, value: 3400 },
  { id: 'sp_flame', name: '火の玉', school: 'fth', fp: 12, dmg: 78, scale: 'fth', speed: 20, life: 3.0, element: 'fire', color: [1.0, 0.55, 0.2], desc: '祈りを火に変える。', req: { fth: 12 }, cast: 0.6, value: 1200 },
  { id: 'sp_pyre', name: '燼の柱', school: 'fth', fp: 30, dmg: 165, scale: 'fth', element: 'fire', ground: true, radius: 3.6, delay: 0.6, color: [1.0, 0.4, 0.15], desc: '足元から火柱が立つ。', req: { fth: 24 }, cast: 1.2, value: 5200 },
  { id: 'sp_heal', name: '癒しの祈り', school: 'fth', fp: 26, heal: 240, scale: 'fth', color: [0.9, 0.95, 0.7], desc: 'HPを回復する。', req: { fth: 14 }, cast: 1.4, value: 2600 },
  { id: 'sp_ward', name: '守りの祈り', school: 'fth', fp: 20, buff: { defMul: 1.35, dur: 40 }, color: [0.95, 0.9, 0.6], desc: '一時的に防御を高める。', req: { fth: 18 }, cast: 1.1, value: 3000 },

  // The spell list is shaped by delivery, not by damage: a fast cheap bolt, a
  // slow heavy one, a cone, a ground trap and a buff each want a different
  // distance and a different moment, so two casters rarely stand in the same
  // place even at the same level.
  { id: 'sp_glint', name: '輝石の閃', school: 'int', fp: 5, dmg: 38, scale: 'int', speed: 34, life: 2.4, color: [0.72, 0.82, 1.0], desc: '速く、安い。詠唱の隙がほとんどない。', req: { int: 12 }, cast: 0.26, value: 1400 },
  { id: 'sp_comet', name: '彗星', school: 'int', fp: 34, dmg: 235, scale: 'int', speed: 16, life: 4.0, color: [0.55, 0.62, 1.0], desc: '遅く、重い。当てるための隙は自分で作れ。', req: { int: 32 }, cast: 1.6, value: 7600 },
  { id: 'sp_gale', name: '魔風', school: 'int', fp: 20, dmg: 84, scale: 'int', speed: 20, life: 0.9, cone: true, color: [0.66, 0.72, 0.92], desc: '前方を薙ぐ。群れを崩すためのもの。', req: { int: 20 }, cast: 0.7, value: 3800 },
  { id: 'sp_quake', name: '地割れ', school: 'int', fp: 28, dmg: 190, scale: 'int', ground: true, radius: 5.0, delay: 0.8, color: [0.50, 0.46, 0.70], desc: '足元の地面が遅れて割れる。逃げ場を奪うためのもの。', req: { int: 26 }, cast: 1.3, value: 6200 },
  { id: 'sp_venom_mist', name: '毒の霧', school: 'int', fp: 24, dmg: 56, scale: 'int', speed: 12, life: 1.4, cone: true, effect: { type: 'poison', build: 42 }, color: [0.52, 0.74, 0.36], desc: '毒を吹き付ける。効くまでが遅く、効いてからが長い。', req: { int: 18 }, cast: 0.9, value: 4400 },
  { id: 'sp_mirror', name: '鏡の刃', school: 'int', fp: 22, dmg: 0, buff: { addMagic: 120, dur: 45 }, color: [0.70, 0.68, 1.0], desc: '武器に強い魔力を纏わせる。持続は短い。', req: { int: 28 }, cast: 1.2, value: 6800 },

  { id: 'sp_lightspear', name: '光の槍', school: 'fth', fp: 18, dmg: 128, scale: 'fth', speed: 30, life: 3.0, element: 'holy', color: [1.0, 0.94, 0.68], desc: '真っ直ぐ飛ぶ。祈りとしては、ずいぶん無作法な形をしている。', req: { fth: 20 }, cast: 0.7, value: 3600 },
  { id: 'sp_thunder', name: '雷の投擲', school: 'fth', fp: 26, dmg: 172, scale: 'fth', speed: 40, life: 2.6, element: 'lightning', color: [0.95, 0.92, 0.55], desc: '竜の骨に残った雷を借りる。', req: { fth: 26 }, cast: 0.9, value: 5800 },
  { id: 'sp_wrath', name: '断罪', school: 'fth', fp: 34, dmg: 215, scale: 'fth', element: 'holy', ground: true, radius: 4.4, delay: 0.9, color: [1.0, 0.88, 0.6], desc: '罪の上に落ちる。誰の罪かは問われない。', req: { fth: 30 }, cast: 1.5, value: 8200 },
  { id: 'sp_censer', name: '香炉の火', school: 'fth', fp: 20, dmg: 74, scale: 'fth', speed: 15, life: 1.1, cone: true, element: 'fire', color: [1.0, 0.66, 0.28], desc: '前方に炎を撒く。近い相手ほど焼ける。', req: { fth: 18 }, cast: 0.7, value: 3400 },
  { id: 'sp_mend', name: '深き癒し', school: 'fth', fp: 48, heal: 620, scale: 'fth', color: [0.92, 0.98, 0.76], desc: '大きく回復する。その間、無防備になる。', req: { fth: 28 }, cast: 2.2, value: 7400 },
  { id: 'sp_bulwark', name: '不屈の祈り', school: 'fth', fp: 22, buff: { staminaRegen: 1.8, dur: 50 }, color: [0.90, 0.86, 0.62], desc: 'しばらくの間、息が上がらなくなる。', req: { fth: 16 }, cast: 1.0, value: 4200 },
  { id: 'sp_vow', name: '誓いの火', school: 'fth', fp: 26, dmg: 0, buff: { addFire: 95, atkMul: 1.10, dur: 45 }, color: [1.0, 0.62, 0.26], desc: '武器に誓いの火を移す。', req: { fth: 24 }, cast: 1.3, value: 6600 },
];

// ---------------------------------------------------------------------------
//  Lookup
// ---------------------------------------------------------------------------

const ALL = [...WEAPONS, ...ARMOR, ...TALISMANS, ...CONSUMABLES, ...MATERIALS, ...KEY_ITEMS];
export const ITEM_BY_ID = new Map(ALL.map((i) => [i.id, i]));
export const SPELL_BY_ID = new Map(SPELLS.map((s) => [s.id, s]));

export function getItem(id) { return ITEM_BY_ID.get(id) || null; }
export function getSpell(id) { return SPELL_BY_ID.get(id) || null; }

// ---------------------------------------------------------------------------
//  Derived numbers
// ---------------------------------------------------------------------------

/** Attack rating of a weapon at a given upgrade level with given stats. */
export function weaponAttack(weapon, level, stats) {
  if (!weapon) return { physical: 12, element: 0, elementType: null, total: 12 };
  const mul = UPGRADE_MUL[Math.min(level, UPGRADE_MUL.length - 1)];
  const base = weapon.base * mul;
  let scaled = 0;
  for (const key in weapon.scaling) {
    const grade = weapon.scaling[key];
    const coef = SCALING_COEF[grade] || 0;
    scaled += base * coef * statCurve(stats[key] || 0);
  }
  const physical = base + scaled;
  const element = weapon.elementBase ? weapon.elementBase * mul * (1 + statCurve(stats.fth || 0) * 0.4) : 0;
  return {
    physical, element, elementType: weapon.element,
    total: physical + element,
  };
}

/** Whether the wielder meets the requirements; below them, damage tanks. */
export function meetsRequirements(weapon, stats) {
  if (!weapon || !weapon.req) return true;
  for (const k in weapon.req) if ((stats[k] || 0) < weapon.req[k]) return false;
  return true;
}

export function requirementPenalty(weapon, stats) {
  if (meetsRequirements(weapon, stats)) return 1;
  let worst = 1;
  for (const k in weapon.req) {
    const have = stats[k] || 0, need = weapon.req[k];
    if (have < need) worst = Math.min(worst, 0.35 + 0.65 * (have / need));
  }
  return worst;
}

/** Physical damage after defence — a soft, diminishing reduction. */
export function mitigate(damage, defense, resist = 0) {
  const afterDef = damage * (110 / (110 + Math.max(0, defense)));
  return Math.max(1, afterDef * (1 - Math.min(0.85, resist)));
}

export const RARITY_COLOR = ['#9aa0a6', '#e8e4dc', '#7fc7ff', '#d7a2ff', '#ffbe5c'];
export const RARITY_NAME = ['粗製', '通常', '希少', '精霊', '伝説'];
