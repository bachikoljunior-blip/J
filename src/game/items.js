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
    { desc: '斬るのではなく、滑らせて裂く。技量が全て。', crit: 1.15, rarity: 2, shape: { len: 0.96, w: 0.088, t: 0.024, blade: [0.66, 0.68, 0.72], hilt: [0.22, 0.20, 0.24] } }),

  // --- greatswords ---------------------------------------------------------
  W('great_iron', '鉄大剣', 'greatsword', 58, { str: 'C', dex: 'E' }, { str: 20, dex: 10 }, 9.0,
    { desc: '鍛え上げただけの鉄塊。重さがそのまま威力になる。', shape: { len: 1.32, w: 0.145, t: 0.042, blade: [0.58, 0.58, 0.60], hilt: [0.26, 0.20, 0.15] } }),
  W('great_husk', '亡骸の大剣', 'greatsword', 66, { str: 'B' }, { str: 26, dex: 10 }, 11.5,
    { desc: '死してなお振るわれ続けた刃。', shape: { len: 1.44, w: 0.155, t: 0.048, blade: [0.44, 0.46, 0.44], hilt: [0.20, 0.18, 0.16] }, rarity: 2 }),
  W('great_cinder', '燼の斬馬刀', 'greatsword', 74, { str: 'B', fth: 'D' }, { str: 30, dex: 12, fth: 12 }, 13.0,
    { desc: '振るうたび灰が舞い、火が走る。', element: DAMAGE_TYPE.FIRE, elementBase: 32, rarity: 3, shape: { len: 1.56, w: 0.170, t: 0.052, blade: [0.52, 0.30, 0.22], hilt: [0.24, 0.16, 0.12], glow: 0.45 } }),
  W('great_frost', '白牙の大剣', 'greatsword', 70, { str: 'B', int: 'C' }, { str: 26, dex: 12, int: 16 }, 12.0,
    { desc: '峰の氷から削り出された刃。', element: DAMAGE_TYPE.MAGIC, elementBase: 30, effect: { type: 'frost', build: 30 }, rarity: 3, shape: { len: 1.48, w: 0.160, t: 0.046, blade: [0.72, 0.84, 0.92], hilt: [0.30, 0.34, 0.40], glow: 0.25 } }),

  // --- spears --------------------------------------------------------------
  W('spear_ash', '灰木の槍', 'spear', 32, { str: 'D', dex: 'C' }, { str: 12, dex: 14 }, 4.5,
    { desc: '間合いを制する者が勝つ。', shape: { len: 1.85, w: 0.038, t: 0.032, blade: [0.70, 0.72, 0.74], hilt: [0.34, 0.26, 0.17], haft: true } }),
  W('spear_knight', '騎士槍', 'spear', 42, { str: 'C', dex: 'B' }, { str: 15, dex: 18 }, 5.5,
    { desc: '馬上でも徒歩でも。', shape: { len: 2.05, w: 0.042, t: 0.034, blade: [0.78, 0.80, 0.84], hilt: [0.30, 0.24, 0.16], haft: true } }),
  W('spear_drake', '竜牙の槍', 'spear', 52, { str: 'C', dex: 'B' }, { str: 18, dex: 22 }, 7.0,
    { desc: '断崖の竜の牙を穂先に据えた。', element: DAMAGE_TYPE.LIGHTNING, elementBase: 26, rarity: 3, shape: { len: 2.15, w: 0.048, t: 0.036, blade: [0.90, 0.86, 0.52], hilt: [0.28, 0.22, 0.16], haft: true, glow: 0.35 } }),

  // --- axes ----------------------------------------------------------------
  W('axe_wood', '樵の斧', 'axe', 40, { str: 'C' }, { str: 14, dex: 8 }, 5.5,
    { desc: '木を割るために作られたが、よく効く。', shape: { len: 0.72, w: 0.20, t: 0.05, blade: [0.60, 0.60, 0.62], hilt: [0.32, 0.24, 0.16], axe: true } }),
  W('axe_bandit', '野盗の戦斧', 'axe', 50, { str: 'B' }, { str: 20, dex: 9 }, 7.5,
    { desc: '刃こぼれと血脂の層で厚みを増している。', shape: { len: 0.86, w: 0.24, t: 0.055, blade: [0.52, 0.50, 0.48], hilt: [0.26, 0.20, 0.14], axe: true }, rarity: 2 }),
  W('axe_stone', '石喰いの大斧', 'axe', 68, { str: 'A' }, { str: 32, dex: 10 }, 14.0,
    { desc: '岩ごと砕く。当たれば、の話だが。', shape: { len: 1.05, w: 0.34, t: 0.075, blade: [0.46, 0.44, 0.42], hilt: [0.24, 0.20, 0.16], axe: true }, rarity: 3 }),

  W('hammer_iron', '鉄槌', 'axe', 62, { str: 'A' }, { str: 26, dex: 8 }, 11.0,
    { desc: '刃はない。だから刃こぼれもしない。鎧ごと潰す。', rarity: 2, shape: { len: 0.92, w: 0.26, t: 0.24, blade: [0.42, 0.42, 0.44], hilt: [0.28, 0.22, 0.15], axe: true } }),

  // --- daggers -------------------------------------------------------------
  W('dagger_thief', '盗人の短刀', 'dagger', 20, { dex: 'B' }, { str: 6, dex: 14 }, 1.5,
    { desc: '速さと、背後を取る度胸があれば。', crit: 1.45, shape: { len: 0.44, w: 0.060, t: 0.020, blade: [0.60, 0.62, 0.65], hilt: [0.22, 0.18, 0.14] } }),
  W('dagger_ritual', '儀式短刀', 'dagger', 24, { dex: 'A', int: 'D' }, { str: 6, dex: 18, int: 12 }, 1.8,
    { desc: '刻印を刻むための刃。人にも効く。', crit: 1.55, element: DAMAGE_TYPE.MAGIC, elementBase: 12, rarity: 2, shape: { len: 0.48, w: 0.058, t: 0.019, blade: [0.62, 0.58, 0.82], hilt: [0.20, 0.18, 0.26], glow: 0.3 } }),

  W('dagger_frost', '霜の小刀', 'dagger', 22, { dex: 'A', int: 'C' }, { str: 6, dex: 16, int: 14 }, 1.6,
    { desc: '柄まで凍っている。握る側も無事では済まない。', crit: 1.50, element: DAMAGE_TYPE.MAGIC, elementBase: 14, effect: { type: 'frost', build: 24 }, rarity: 3, shape: { len: 0.46, w: 0.058, t: 0.018, blade: [0.72, 0.84, 0.92], hilt: [0.26, 0.30, 0.36], glow: 0.28 } }),

  // --- bows ----------------------------------------------------------------
  W('bow_short', '短弓', 'bow', 26, { dex: 'C' }, { str: 8, dex: 14 }, 2.5,
    { desc: '射程は短いが、素早く引ける。', ranged: true, shape: { len: 1.05, w: 0.04, t: 0.03, blade: [0.34, 0.26, 0.18], hilt: [0.28, 0.22, 0.15], bow: true } }),
  W('bow_long', '長弓', 'bow', 38, { dex: 'B' }, { str: 12, dex: 20 }, 4.0,
    { desc: '遠くの敵を、静かに減らす。', ranged: true, shape: { len: 1.45, w: 0.045, t: 0.032, blade: [0.30, 0.24, 0.17], hilt: [0.26, 0.20, 0.14], bow: true }, rarity: 2 }),

  W('spear_mire', '沼守の三叉', 'spear', 46, { str: 'C', dex: 'B' }, { str: 16, dex: 19 }, 6.2,
    { desc: '沼の底から引き上げられた漁具。返しが深い。', effect: { type: 'bleed', build: 28 }, rarity: 2, shape: { len: 1.95, w: 0.052, t: 0.034, blade: [0.58, 0.62, 0.56], hilt: [0.26, 0.24, 0.18], haft: true } }),

  // --- catalysts -----------------------------------------------------------
  W('staff_apprentice', '徒弟の杖', 'staff', 14, { int: 'B' }, { str: 6, dex: 8, int: 14 }, 2.5,
    { desc: '魔力を編むための触媒。殴ることもできる、一応。', catalyst: 'int', shape: { len: 1.15, w: 0.05, t: 0.05, blade: [0.32, 0.28, 0.42], hilt: [0.26, 0.22, 0.30], staff: true, glow: 0.3 } }),
  W('staff_ember', '残り火の聖印', 'staff', 16, { fth: 'B' }, { str: 6, dex: 8, fth: 16 }, 2.0,
    { desc: '王冠の欠片を戴く聖印。祈りを火に変える。', catalyst: 'fth', rarity: 2, shape: { len: 0.85, w: 0.06, t: 0.05, blade: [0.72, 0.44, 0.24], hilt: [0.30, 0.24, 0.18], staff: true, glow: 0.5 } }),

  // --- shields (equipped in the off hand) ----------------------------------
  W('shield_wood', '木盾', 'shield', 8, { str: 'E' }, { str: 10, dex: 6 }, 3.5,
    { desc: '無いよりはるかに良い。', guard: 0.62, stability: 26, shape: { w: 0.40, h: 0.54, t: 0.055, face: [0.30, 0.23, 0.16], rim: [0.30, 0.30, 0.32] } }),
  W('shield_kite', '騎士の凧盾', 'shield', 12, { str: 'D' }, { str: 14, dex: 8 }, 5.5,
    { desc: '正面からの一撃を確実に受け止める。', guard: 0.80, stability: 42, shape: { w: 0.43, h: 0.70, t: 0.065, face: [0.36, 0.38, 0.44], rim: [0.36, 0.36, 0.40] } }),
  W('shield_oath', '誓約の大盾', 'shield', 18, { str: 'C' }, { str: 24, dex: 8 }, 11.0,
    { desc: '壁になることを選んだ者の証。', guard: 0.94, stability: 62, rarity: 3, shape: { w: 0.54, h: 0.88, t: 0.08, face: [0.33, 0.35, 0.40], rim: [0.62, 0.56, 0.30] } }),
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
];

export const MATERIALS = [
  { id: 'mat_shard', name: '鍛石の欠片', kind: 'material', desc: '武器強化に使う、ありふれた石。', tier: 1, value: 200 },
  { id: 'mat_chunk', name: '鍛石の塊', kind: 'material', desc: '+4 より先の強化に必要。', tier: 2, value: 800 },
  { id: 'mat_core', name: '鍛石の核', kind: 'material', desc: '+7 より先の強化に必要。', tier: 3, value: 2400 },
  { id: 'mat_emberheart', name: '燼の心臓', kind: 'material', desc: '最上位の強化に必要な、王冠の残滓。', tier: 4, value: 8000 },
  { id: 'mat_hide', name: '獣の皮', kind: 'material', desc: '交易品。', value: 90 },
  { id: 'mat_fang', name: '灰狼の牙', kind: 'material', desc: '交易品。', value: 160 },
];

export const KEY_ITEMS = [
  { id: 'key_shard_1', name: '残り火の断片・森', kind: 'key', desc: '縛り手より奪った王冠の断片。' },
  { id: 'key_shard_2', name: '残り火の断片・沼', kind: 'key', desc: '沈殿の玉座より。' },
  { id: 'key_shard_3', name: '残り火の断片・嶺', kind: 'key', desc: '誓約の闘技場より。' },
  { id: 'key_shard_4', name: '残り火の断片・崖', kind: 'key', desc: '竜の棚より。' },
  { id: 'key_shard_5', name: '残り火の断片・焦土', kind: 'key', desc: '燼の玉座より。' },
  { id: 'key_ironrite', name: '鉄の割符', kind: 'key', desc: '鉄砦の門を開く。' },
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
