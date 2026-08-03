// ============================================================================
//  quests.js — the main chain, side quests, NPCs and their dialogue.
//
//  Quests are data-driven state machines. Each step declares a condition the
//  game checks against its own event log, so nothing here needs to know how
//  combat or exploration are implemented — a step just says "kill 6 of these"
//  or "reach that place" and the tracker resolves it.
// ============================================================================

export const QUEST_STATE = { LOCKED: 0, ACTIVE: 1, DONE: 2, FAILED: 3 };

// Quest fields beyond the obvious:
//   turnIn   — the final step is only *ready* when its condition is met; the
//              quest closes in conversation with this NPC, which is what makes
//              the reward land and what gives the giver something to react to.
//   excludes — accepting this quest fails the listed ones outright. Two people
//              wanting opposite things is the cheapest real choice there is.
//   failOn   — a world event that ends the quest badly. Nothing is retried.
//   requires — another quest that must be DONE before this one can be taken.
export const QUESTS = [
  {
    id: 'main_1', main: true, name: '灰の目覚め', giver: 'harum', turnIn: 'harum',
    summary: '村長ハラムに話を聞き、王冠の断片について知る。',
    steps: [
      { id: 's1', text: '灯火の村でハラムと話す', type: 'talk', target: 'harum' },
      { id: 's2', text: '囁きの森の縛り手を討つ', type: 'boss', target: 'warden' },
      { id: 's3', text: 'ハラムに報告する', type: 'talk', target: 'harum' },
    ],
    rewards: { souls: 1200, items: [['flask_hp', 1]], flaskUp: 'hp' },
    next: 'main_2',
  },
  {
    id: 'main_2', main: true, name: '沈殿の玉座', giver: 'harum', turnIn: 'harum',
    summary: '灰泥の沼に沈んだ社の奥、泥の女王が断片を抱いている。',
    steps: [
      { id: 's1', text: '灰泥の沼へ向かう', type: 'reach', target: 'grace_mire' },
      { id: 's2', text: '泥の女王を討つ', type: 'boss', target: 'mirequeen' },
      { id: 's3', text: 'ハラムに報告する', type: 'talk', target: 'harum' },
    ],
    rewards: { souls: 3000, items: [['antidote', 5], ['mat_chunk', 2]], flaskUp: 'hp' },
    next: 'main_3',
  },
  {
    id: 'main_3', main: true, name: '鉄の掟', giver: 'vane', turnIn: 'vane',
    summary: '鉄嶺の誓約者は断片を「守っている」と言う。話が通じるとは限らない。',
    steps: [
      { id: 's1', text: '鉄砦でヴェインと話す', type: 'talk', target: 'vane' },
      { id: 's2', text: '誓約の闘技場で鉄の誓約者を討つ', type: 'boss', target: 'ironsworn' },
      { id: 's3', text: 'ヴェインに報告する', type: 'talk', target: 'vane' },
    ],
    rewards: { souls: 6000, items: [['mat_core', 1]], flaskUp: 'fp' },
    next: 'main_4',
  },
  {
    id: 'main_4', main: true, name: '竜の棚', giver: null,
    summary: '蒼玉の断崖。竜が断片を巣に敷いている。',
    steps: [
      { id: 's1', text: '断崖の竜を討つ', type: 'boss', target: 'drake' },
    ],
    rewards: { souls: 10000, items: [['mat_core', 2]], flaskUp: 'hp' },
    next: 'main_5',
  },
  {
    id: 'main_5', main: true, name: '燼の玉座', giver: null,
    summary: '焦土の中心。灰の王が最後の断片を戴いている。',
    steps: [
      { id: 's1', text: '灰の王を討つ', type: 'boss', target: 'ashking' },
    ],
    rewards: { souls: 18000, items: [['mat_emberheart', 1]], flaskUp: 'fp' },
    next: 'main_6',
  },
  {
    id: 'main_6', main: true, name: '残り火の頂', giver: null,
    summary: '五つの断片が揃った。白牙峰の頂で、王冠は再び形を持つ。',
    steps: [
      { id: 's1', text: '五つの断片を集める', type: 'items', target: ['key_shard_1', 'key_shard_2', 'key_shard_3', 'key_shard_4', 'key_shard_5'] },
      { id: 's2', text: '白牙峰の頂へ登る', type: 'reach', target: 'grace_peak' },
      { id: 's3', text: '残り火の王と対峙する', type: 'boss', target: 'sovereign' },
    ],
    rewards: { souls: 50000, items: [] },
    next: null,
  },

  // --- side quests ---------------------------------------------------------
  {
    id: 'side_wolves', name: '狼を減らす', giver: 'harum', turnIn: 'harum',
    summary: '村の周りに灰狼が増えすぎた。十匹も減らせば落ち着くだろう。',
    steps: [{ id: 's1', text: '灰狼を10体討つ', type: 'kill', target: 'ashwolf', count: 10 }],
    rewards: { souls: 900, items: [['mat_fang', 3], ['tal_hunter', 1]] },
  },
  {
    id: 'side_smith', name: '鍛冶の火', giver: 'dorg', turnIn: 'dorg', requires: 'main_1',
    summary: 'ドルグの炉は火が弱い。焦土の残り火があれば、また鍛てる。',
    steps: [{ id: 's1', text: '残り火のかけらを3つ渡す', type: 'deliver', target: 'ember_shard', count: 3 }],
    rewards: { souls: 1500, items: [['mat_chunk', 2]], unlock: 'smith_tier2' },
  },
  {
    id: 'side_sera', name: '灰纏いの願い', giver: 'sera', turnIn: 'sera',
    summary: 'セラは焦土で失くしたものを探している。灰の輪に落ちているはずだと。',
    steps: [
      { id: 's1', text: '灰の輪で「灰の主」を討つ', type: 'kill', target: 'wraith_lord', count: 1 },
      { id: 's2', text: 'セラに報告する', type: 'talk', target: 'sera' },
    ],
    rewards: { souls: 4000, items: [['tal_lastlight', 1]], spell: 'sp_pyre' },
  },
  {
    id: 'side_mira', name: '商人の護衛', giver: 'mira', turnIn: 'mira',
    summary: 'ミラは道中の野盗に困っている。首魁を潰せば、しばらく通れる。',
    steps: [{ id: 's1', text: '野盗の首魁を討つ', type: 'kill', target: 'bandit_chief', count: 1 }],
    rewards: { souls: 1800, items: [['ember_shard', 2]], unlock: 'merchant_tier2' },
  },
  {
    id: 'side_shrines', name: '古き祠を巡る', giver: null, turnIn: 'io',
    summary: '祠に触れると、体の奥で何かが確かになる。全部で12。',
    steps: [{ id: 's1', text: '祠を6つ見つける', type: 'shrine', count: 6 }],
    rewards: { souls: 3000, items: [['tal_vigor', 1]] },
    autoStart: true,
  },

  // --- the ledger: two people want the same book for opposite reasons ------
  {
    id: 'side_ledger_burn', name: '帳面を焼く', giver: 'mira', turnIn: 'mira',
    requires: 'side_mira', excludes: ['side_ledger_sell'],
    summary: '首魁の帳面には、奪われた側の名前が並んでいる。ミラは焼けと言う。',
    steps: [{ id: 's1', text: '首魁の帳面をミラに渡す', type: 'deliver', target: 'key_ledger', count: 1 }],
    rewards: { souls: 2600, items: [['tal_greed', 1], ['homeward', 2]], unlock: 'merchant_tier2' },
  },
  {
    id: 'side_ledger_sell', name: '帳面を売る', giver: 'kaim', turnIn: 'kaim',
    requires: 'side_mira', excludes: ['side_ledger_burn'],
    summary: 'カイムは帳面に値をつけた。名前が並んでいるからこそ、値がつく。',
    steps: [{ id: 's1', text: '首魁の帳面をカイムに渡す', type: 'deliver', target: 'key_ledger', count: 1 }],
    rewards: { souls: 7000, items: [['ember_heart', 2]], unlock: 'bounty_open' },
  },

  // --- the bell: silence it, or keep it ringing ---------------------------
  {
    id: 'side_bell_silence', name: '鐘を黙らせる', giver: 'vane', turnIn: 'vane',
    excludes: ['side_bell_keep'],
    summary: '鐘楼の鐘が鳴るたび、死者が起き上がる。ヴェインは番人ごと止めろと言う。',
    steps: [{ id: 's1', text: '鐘楼の番人を討つ', type: 'boss', target: 'bellkeeper' }],
    rewards: { souls: 9000, items: [['tal_bulwark', 1], ['mat_core', 2]] },
  },
  {
    id: 'side_bell_keep', name: '鐘を守る', giver: 'kaim', turnIn: 'kaim',
    excludes: ['side_bell_silence'],
    failOn: { type: 'boss', target: 'bellkeeper' },
    summary: 'カイムは鐘の青銅を欲しがっている。鐘が鳴っているうちだけ、それは取れる。',
    steps: [{ id: 's1', text: '鐘の青銅を6つ集めて渡す', type: 'deliver', target: 'mat_bellbronze', count: 6 }],
    rewards: { souls: 9000, items: [['hammer_bell', 1], ['mat_core', 2]] },
  },

  // --- 灯守イオ (wood) -----------------------------------------------------
  {
    id: 'side_io_lanterns', name: '灯を継ぐ', giver: 'io', turnIn: 'io',
    summary: '囁きの森の灯が次々に消えている。消しているものがいる。',
    steps: [{ id: 's1', text: '森の徘徊者を12体討つ', type: 'kill_any', target: ['rootling', 'kodama', 'hexbinder'], count: 12 }],
    rewards: { souls: 2200, items: [['tal_focus', 1], ['flask_fp', 1]] },
  },
  {
    id: 'side_io_rootheart', name: '森の心臓', giver: 'io', turnIn: 'io',
    requires: 'side_io_lanterns',
    summary: '森の底に、脈を打つものがある。イオはそれを「父」と呼ぶ。',
    steps: [{ id: 's1', text: '根の父を討つ', type: 'boss', target: 'rootfather' }],
    rewards: { souls: 12000, items: [['great_root', 1], ['tal_marrow', 1]], spell: 'sp_venom_mist' },
  },

  // --- 墓掘りグリム (mire) -------------------------------------------------
  {
    id: 'side_grim_bones', name: '数が合わない', giver: 'grim', turnIn: 'grim',
    summary: 'グリムは埋めた数と掘り出した数が合わないと言う。まず骨を持ってこい、と。',
    steps: [{ id: 's1', text: '白い骨を5つ渡す', type: 'deliver', target: 'mat_bone', count: 5 }],
    rewards: { souls: 1400, items: [['head_bone', 1], ['mat_shard', 3]] },
  },
  {
    id: 'side_grim_stalkers', name: '泥に潜むもの', giver: 'grim', turnIn: 'grim',
    requires: 'side_grim_bones',
    summary: '掘り返した穴に、何かが先に入っている。',
    steps: [{ id: 's1', text: '沼の潜むものを6体討つ', type: 'kill_any', target: ['mirestalker', 'mireleech'], count: 6 }],
    rewards: { souls: 3200, items: [['body_bone', 1], ['antidote', 6]] },
  },
  {
    id: 'side_grim_choir', name: '沈める合唱', giver: 'grim', turnIn: 'grim',
    requires: 'side_grim_stalkers',
    summary: '沼の底から歌が聞こえる。グリムは「聞くな」と言い、地図を寄越した。',
    steps: [{ id: 's1', text: '沈める合唱を討つ', type: 'boss', target: 'sunkenchoir' }],
    rewards: { souls: 11000, items: [['staff_glint', 1], ['arms_bone', 1], ['legs_bone', 1]] },
  },

  // --- 隠者ネイ (crag) -----------------------------------------------------
  {
    id: 'side_nei_crows', name: '鴉を落とす', giver: 'nei', turnIn: 'nei',
    summary: '断崖の鴉が棚の卵を持っていく。ネイはもう投げるものがないと言う。',
    steps: [{ id: 's1', text: '崖の飛ぶものを8体討つ', type: 'kill_any', target: ['ashcrow', 'frostwolf'], count: 8 }],
    rewards: { souls: 3400, items: [['bow_horn', 1], ['throwing_spike', 10]] },
  },
  {
    id: 'side_nei_carls', name: '石守の礼', giver: 'nei', turnIn: 'nei',
    requires: 'side_nei_crows',
    summary: '石を喰う者たちが棚を削っている。放っておけば、棚ごと落ちる。',
    steps: [{ id: 's1', text: '石を喰う者を4体討つ', type: 'kill_any', target: ['stonecarl', 'stoneeater'], count: 4 }],
    rewards: { souls: 5200, items: [['tal_glutton', 1], ['mat_core', 1]] },
  },

  // --- 唄い手ルシャ (peak) -------------------------------------------------
  {
    id: 'side_lusha_stalk', name: '雪を走るもの', giver: 'lusha', turnIn: 'lusha',
    summary: 'ルシャの唄には返しがあった。今は雪のほうが先に返してくる。',
    steps: [{ id: 's1', text: '雪の獣を6体討つ', type: 'kill_any', target: ['snowstalker', 'frostwolf'], count: 6 }],
    rewards: { souls: 4200, items: [['head_hoar', 1], ['warm_stone', 5]] },
  },
  {
    id: 'side_lusha_song', name: '凍てた誓文', giver: 'lusha', turnIn: 'lusha',
    requires: 'side_lusha_stalk',
    summary: '頂の手前に、凍りついたまま座っている男がいる。ルシャはその名を知っている。',
    steps: [{ id: 's1', text: '霜の司を討つ', type: 'boss', target: 'frostjarl' }],
    rewards: { souls: 16000, items: [['body_hoar', 1], ['tal_crownward', 1]], spell: 'sp_bulwark' },
  },

  // --- セラ、続き (waste) --------------------------------------------------
  {
    id: 'side_ember_priests', name: '祈りを止める', giver: 'sera', turnIn: 'sera',
    requires: 'side_sera',
    summary: '焦土の祈祷者が、倒したはずのものを起こし直している。',
    steps: [{ id: 's1', text: '焦土の祈る者を5体討つ', type: 'kill_any', target: ['emberpriest', 'wraith'], count: 5 }],
    rewards: { souls: 5600, items: [['tal_ashskin', 1], ['resin_fire', 4]] },
  },
  {
    id: 'side_widow', name: '弔い', giver: 'sera', turnIn: 'sera',
    requires: 'side_ember_priests',
    summary: '姉を焼いた火は、まだ誰かの形をしている。セラは「終わらせて」とだけ言った。',
    steps: [{ id: 's1', text: '燼の寡婦を討つ', type: 'boss', target: 'emberwidow' }],
    rewards: { souls: 18000, items: [['tal_finality', 1], ['mat_emberheart', 1]], spell: 'sp_wrath' },
  },

  // --- 職人と行商、続き ----------------------------------------------------
  {
    id: 'side_dorg_blackiron', name: '黒鉄', giver: 'dorg', turnIn: 'dorg',
    requires: 'side_smith',
    summary: '炉が本気を出した。ドルグは今度は素材の話をしている。',
    steps: [{ id: 's1', text: '鍛石の核を2つ渡す', type: 'deliver', target: 'mat_core', count: 2 }],
    rewards: { souls: 6000, items: [['great_bell', 1], ['mat_chunk', 3]], unlock: 'smith_ember' },
  },
  {
    id: 'side_mira_route', name: '街道を開く', giver: 'mira', turnIn: 'mira',
    requires: 'side_mira',
    summary: '首魁は消えたが、その下の連中は残っている。数が減れば荷は通る。',
    steps: [{ id: 's1', text: '街道の野盗を20体討つ', type: 'kill_any', target: ['bandit', 'bandit_archer'], count: 20 }],
    rewards: { souls: 4800, items: [['tal_beggar', 1], ['ember_heart', 1]] },
  },
  {
    id: 'side_kaim_bounty', name: '賞金首', giver: 'kaim', turnIn: 'kaim',
    summary: 'カイムは首に値をつけて回っている。名のあるものを二つ持ってこい、と。',
    steps: [{
      id: 's1', text: '名のある敵を2体討つ', type: 'kill_any',
      target: ['bandit_chief', 'wolf_alpha', 'sentinel_captain', 'wraith_lord'], count: 2,
    }],
    rewards: { souls: 6400, items: [['tal_duelist', 1], ['oil_black', 4]] },
  },

  // --- 誓約者、続き --------------------------------------------------------
  {
    id: 'side_vane_relief', name: '誓約を解く', giver: 'vane', turnIn: 'vane',
    requires: 'main_3',
    summary: '誓約者は誓いを果たした。果たしたことを知らない者が、まだ立っている。',
    steps: [{ id: 's1', text: '誓約騎士を6体討つ', type: 'kill', target: 'oathknight', count: 6 }],
    rewards: { souls: 7200, items: [['great_vow', 1], ['staff_vow', 1]] },
  },

  // --- world-tracking, no giver -------------------------------------------
  {
    id: 'side_relics', name: '遺構をめぐる', giver: null, turnIn: 'nei',
    summary: '倒れた柱にも順序がある。数を見れば、何が起きたかが分かる。',
    steps: [{ id: 's1', text: '遺構を6つ見つける', type: 'explore', prefix: 'ruin_', count: 6 }],
    rewards: { souls: 3600, items: [['tal_thin', 1]] },
    autoStart: true,
  },
  {
    id: 'side_graces', name: '篝火をつなぐ', giver: null, turnIn: 'lusha',
    summary: '火から火へ。それだけが地図になる。',
    steps: [{ id: 's1', text: '篝火を6つ見つける', type: 'explore', prefix: 'grace_', count: 6 }],
    rewards: { souls: 2800, items: [['homeward', 3], ['tal_feather', 1]] },
    autoStart: true,
  },
  {
    id: 'side_slayer', name: '数える者', giver: null, turnIn: 'kaim',
    summary: '何体倒したか数えている者がいる。お前ではない。',
    steps: [{ id: 's1', text: '150体を討つ', type: 'kill_total', count: 150 }],
    rewards: { souls: 9000, items: [['tal_hound', 1]] },
    autoStart: true,
  },
];

export const QUEST_BY_ID = new Map(QUESTS.map((q) => [q.id, q]));

// ---------------------------------------------------------------------------
//  NPCs
// ---------------------------------------------------------------------------

export const NPCS = {
  harum: {
    id: 'harum', name: '村長ハラム', role: 'quest', region: 'meadow',
    palette: { SKIN: [0.68, 0.54, 0.44], CLOTH: [0.36, 0.30, 0.22], ARMOR: [0.34, 0.28, 0.22], HAIR: [0.72, 0.70, 0.66] },
    dialogue: 'harum',
  },
  mira: {
    id: 'mira', name: '行商人ミラ', role: 'merchant', region: 'meadow',
    palette: { SKIN: [0.74, 0.58, 0.46], CLOTH: [0.30, 0.24, 0.36], ARMOR: [0.32, 0.26, 0.38], HAIR: [0.22, 0.16, 0.12], ACCENT: [0.62, 0.44, 0.18] },
    dialogue: 'mira',
    stock: [
      'flask_hp', 'herb_green', 'antidote', 'throwing_knife', 'firebomb',
      'stone_whet', 'resin_fire', 'homeward', 'mat_shard',
      'sword_knight', 'shield_wood', 'bow_short', 'tal_vigor', 'tal_endure',
    ],
    stockTier2: ['mat_chunk', 'spear_knight', 'axe_bandit', 'tal_feather', 'tal_greed', 'sp_bolt', 'sp_flame'],
  },
  dorg: {
    id: 'dorg', name: '鍛冶師ドルグ', role: 'smith', region: 'meadow',
    palette: { SKIN: [0.60, 0.44, 0.34], CLOTH: [0.28, 0.24, 0.22], ARMOR: [0.36, 0.32, 0.28], HAIR: [0.34, 0.24, 0.14], LEATHER: [0.26, 0.20, 0.15] },
    dialogue: 'dorg',
  },
  vane: {
    id: 'vane', name: '誓約者ヴェイン', role: 'quest', region: 'ridge',
    palette: { SKIN: [0.58, 0.46, 0.40], CLOTH: [0.28, 0.20, 0.20], ARMOR: [0.48, 0.46, 0.44], ACCENT: [0.68, 0.56, 0.22], HAIR: [0.18, 0.16, 0.14] },
    dialogue: 'vane',
  },
  sera: {
    id: 'sera', name: '灰纏いのセラ', role: 'quest', region: 'waste',
    palette: { SKIN: [0.66, 0.52, 0.44], CLOTH: [0.36, 0.28, 0.25], ARMOR: [0.32, 0.25, 0.22], ACCENT: [0.76, 0.38, 0.18], HAIR: [0.46, 0.22, 0.12] },
    dialogue: 'sera',
  },
  io: {
    id: 'io', name: '灯守イオ', role: 'quest', region: 'wood',
    palette: { SKIN: [0.70, 0.58, 0.48], CLOTH: [0.26, 0.32, 0.24], ARMOR: [0.28, 0.34, 0.26], LEATHER: [0.26, 0.24, 0.18], ACCENT: [0.86, 0.72, 0.34], HAIR: [0.30, 0.26, 0.18] },
    dialogue: 'io',
  },
  grim: {
    id: 'grim', name: '墓掘りグリム', role: 'quest', region: 'mire',
    palette: { SKIN: [0.54, 0.48, 0.42], CLOTH: [0.24, 0.26, 0.22], ARMOR: [0.28, 0.28, 0.24], LEATHER: [0.28, 0.22, 0.16], ACCENT: [0.46, 0.44, 0.38], HAIR: [0.20, 0.20, 0.18] },
    dialogue: 'grim',
  },
  nei: {
    id: 'nei', name: '隠者ネイ', role: 'quest', region: 'crag',
    palette: { SKIN: [0.62, 0.56, 0.50], CLOTH: [0.34, 0.36, 0.40], ARMOR: [0.36, 0.38, 0.42], LEATHER: [0.30, 0.28, 0.26], ACCENT: [0.60, 0.64, 0.72], HAIR: [0.74, 0.72, 0.68] },
    dialogue: 'nei',
  },
  lusha: {
    id: 'lusha', name: '唄い手ルシャ', role: 'quest', region: 'peak',
    palette: { SKIN: [0.72, 0.62, 0.56], CLOTH: [0.30, 0.36, 0.44], ARMOR: [0.32, 0.38, 0.46], LEATHER: [0.28, 0.30, 0.34], ACCENT: [0.78, 0.86, 0.96], HAIR: [0.84, 0.86, 0.90] },
    dialogue: 'lusha',
  },
  kaim: {
    id: 'kaim', name: '賞金首買いカイム', role: 'merchant', region: 'ridge',
    palette: { SKIN: [0.58, 0.44, 0.36], CLOTH: [0.26, 0.22, 0.24], ARMOR: [0.40, 0.36, 0.30], LEATHER: [0.30, 0.24, 0.18], ACCENT: [0.60, 0.50, 0.20], HAIR: [0.16, 0.14, 0.12] },
    dialogue: 'kaim',
    stock: [
      'flask_fp', 'blood_stanch', 'warm_stone', 'throwing_spike', 'pot_poison',
      'oil_black', 'herb_iron', 'mat_shard', 'shield_buckler', 'dagger_venom',
      'spear_harpoon', 'tal_swift', 'tal_pyre',
    ],
    stockTier2: ['mat_core', 'axe_twinmoon', 'sword_thorn', 'bow_whisper', 'tal_duelist', 'tal_marrow', 'sp_glint', 'sp_lightspear'],
  },
};

// ---------------------------------------------------------------------------
//  Dialogue trees
//  Nodes: { text, options: [{ text, goto | action }] }
//  `cond` on an option hides it unless the predicate passes.
// ---------------------------------------------------------------------------

/** True when the giver's current step is a delivery the player can make now. */
export function canDeliver(ctx, questId) {
  const quest = QUEST_BY_ID.get(questId);
  const s = ctx.q.get(questId);
  if (!quest || !s || s.status !== QUEST_STATE.ACTIVE) return false;
  const step = quest.steps[s.step];
  if (!step || step.type !== 'deliver') return false;
  return ctx.p.countItem(step.target) >= (step.count || 1);
}

/** True when a quest can still be taken: not running, not over, not gated. */
export function canOffer(q, id) {
  const quest = QUEST_BY_ID.get(id);
  if (!quest) return false;
  if (q.isActive(id) || q.isDone(id) || q.isFailed(id)) return false;
  if (quest.requires && !q.isDone(quest.requires)) return false;
  return true;
}

export const DIALOGUE = {
  harum: {
    start: {
      text: ({ q }) => (q.isDone('main_6')
        ? '……お前が戻ってくるとは思っていなかった。火は、どうなった。'
        : q.isDone('main_3')
          ? 'まだ立っているか。三つも獲ったな。……村の連中は、お前を数えなくなった。指が足りんのだ。'
          : q.isDone('main_1')
            ? 'よく戻った、刻印者。……お前だけが、まだ歩いている。'
            : 'また一人、灰から起き上がったか。……座れ、話は短い。'),
      options: [
        { text: '縛り手は倒した', goto: 'main1_done', cond: ({ q }) => q.isStepReady('main_1', 's3') },
        { text: '女王は沈めた', goto: 'main2_done', cond: ({ q }) => q.isStepReady('main_2', 's3') },
        { text: '王冠の断片について', goto: 'crown' },
        { text: 'この土地について', goto: 'land' },
        { text: '仕事はあるか', goto: 'work', cond: ({ q }) => canOffer(q, 'side_wolves') },
        { text: '狼は減らした', goto: 'wolves_done', cond: ({ q }) => q.isStepReady('side_wolves', 's1') },
        { text: '……去る', action: 'close' },
      ],
    },
    main1_done: {
      text: '……本当に殺したのか。あれは木だった頃から、あそこに立っていた。\nお前が持ってきたのは断片ではない。断片が抜けた場所の静けさだ。……村で、二十年ぶりに鳥が鳴いた。',
      options: [{ text: '受け取る', action: 'complete_main_1' }],
    },
    main2_done: {
      text: '沼が引いたと使いが来た。膝までだった水が、足首になったと。……女王が抱えていたのは断片ではなく、水位だったのかもしれん。\nもう二つだ。休め。休めるうちに。',
      options: [{ text: '受け取る', action: 'complete_main_2' }],
    },
    crown: {
      text: '残り火の王冠が砕けて、五つの断片が地に散った。断片は、それを握った者を化け物に変える。……今も五つ、全部が誰かの手にある。',
      options: [
        { text: '断片はどこに', goto: 'crown2' },
        { text: '戻る', goto: 'start' },
      ],
    },
    crown2: {
      text: '森、沼、嶺、崖、焦土。順番はお前が決めろ。ただ、森から行け。あそこの縛り手は、まだ「元は木だった」ことを覚えている。話は通じんが、動きは素直だ。',
      options: [{ text: '分かった', action: 'accept_main1' }],
    },
    land: {
      text: 'アルドラス。かつて麦の国だった。今は、死なない連中が歩き回る国だ。……お前も含めてな。',
      options: [
        { text: '刻印とは何だ', goto: 'mark' },
        { text: '村のことを', goto: 'village' },
        { text: '戻る', goto: 'start' },
      ],
    },
    mark: {
      text: '王冠が砕けたとき、近くにいた者に灰が焼き付いた。それが刻印だ。死んでも起き上がる。……起き上がるたび、何かを一つ忘れる。',
      options: [
        { text: '忘れると、どうなる', goto: 'mark2' },
        { text: '戻る', goto: 'land' },
      ],
    },
    mark2: {
      text: '亡骸兵を見ただろう。あれも元は刻印者だ。名前を忘れ、顔を忘れ、最後に「なぜ歩いているか」を忘れる。……お前がまだ喋れているのは、運がいいだけだ。',
      options: [{ text: '……', goto: 'start' }],
    },
    village: {
      text: '灯火の村。名前の通り、火を絶やさんことだけが決まりだ。火が消えた夜に何が来るかは、二度ほど見た。二度とも、朝には人が減っていた。',
      options: [
        { text: '数が減ったと言ったな', goto: 'village2' },
        { text: '戻る', goto: 'land' },
      ],
    },
    village2: {
      text: '減った、とは言った。死んだ、とは言っていない。……朝になると、家が一軒ぶん、みな覚えていないのだ。誰の家だったかも、誰が住んでいたかも。\n私は帳面をつけている。数が合わんと分かるのは、それだけだ。',
      options: [{ text: '戻る', goto: 'land' }],
    },
    work: {
      text: '村の周りに灰狼が増えた。子供が外に出られん。十匹も減らせば、しばらくは静かになる。',
      options: [
        { text: '引き受ける', action: 'accept_side_wolves' },
        { text: '今はいい', goto: 'start' },
      ],
    },
    wolves_done: {
      text: 'ほう……本当にやったのか。これは礼だ。持っていけ。',
      options: [{ text: '受け取る', action: 'complete_side_wolves' }],
    },
  },

  mira: {
    start: {
      text: 'あら、生きてる人。珍しい。……買う? 売る? どっちでもいいけど、冷やかしは嫌よ。',
      options: [
        { text: '買い物をする', action: 'shop' },
        { text: '売る', action: 'sell' },
        { text: '仕事はあるか', goto: 'work', cond: ({ q }) => canOffer(q, 'side_mira') },
        { text: '首魁は片付けた', goto: 'done', cond: ({ q }) => q.isStepReady('side_mira', 's1') },
        { text: '帳面を拾った', goto: 'ledger', cond: (c) => canOffer(c.q, 'side_ledger_burn') && c.p.countItem('key_ledger') > 0 },
        { text: '帳面を渡す', goto: 'ledger_done', cond: (c) => canDeliver(c, 'side_ledger_burn') },
        { text: '街道の話を', goto: 'route', cond: ({ q }) => canOffer(q, 'side_mira_route') },
        { text: '街道は静かになった', goto: 'route_done', cond: ({ q }) => q.isStepReady('side_mira_route', 's1') },
        { text: '去る', action: 'close' },
      ],
    },
    ledger: {
      text: 'それ、見せなさい。……ああ、やっぱり。几帳面な男だったのね、あいつ。誰から何を取ったか、全部書いてある。\n焼きなさい。名前が残っていると、取り返しに来る人が出る。取り返しに来た人は、たいてい帰ってこない。',
      options: [
        { text: '売れば金になるのでは', goto: 'ledger_greed' },
        { text: '焼こう', action: 'accept_side_ledger_burn' },
        { text: '考えておく', goto: 'start' },
      ],
    },
    ledger_greed: {
      text: '……なるわね。鉄砦のカイムなら高く買うわ。あの男は名前を買って、名前で商売をする。\n止めはしない。ただ、そのあと私に売りに来るのはやめて。',
      options: [
        { text: 'やはり焼こう', action: 'accept_side_ledger_burn' },
        { text: '戻る', goto: 'start' },
      ],
    },
    ledger_done: {
      text: '……よし。火に入れて。見ていなくていいわ、私が見ている。\n……終わり。これで、あの帳面に載っていた人たちは、ただ死んだだけの人になった。それが親切かは知らないけど。',
      options: [{ text: '渡す', action: 'complete_side_ledger_burn' }],
    },
    route: {
      text: '首魁は消えたけど、下の連中は残ってる。頭がないぶん、かえって手当たり次第よ。\n二十も減らせば、荷車が通る。通れば、あなたに売れるものも増える。',
      options: [
        { text: '引き受ける', action: 'accept_side_mira_route' },
        { text: '今はいい', goto: 'start' },
      ],
    },
    route_done: {
      text: '荷が着いたわ。三年ぶりに、割れていない壺で。……ありがとう、と言うべきなんでしょうね。言うわ。ありがとう。',
      options: [{ text: '受け取る', action: 'complete_side_mira_route' }],
    },
    work: {
      text: '街道の野盗。首魁を潰してくれたら、しばらく安全に通れる。……そうしたら、いい品も回せるわ。',
      options: [
        { text: '奥の品とは', goto: 'goods' },
        { text: '引き受ける', action: 'accept_side_mira' },
        { text: '断る', goto: 'start' },
      ],
    },
    goods: {
      text: '鍛石の塊、上等な護符、魔術の書。……焦土から拾ってきたものよ。売り物にするには、まず街道が通らないと運べないの。',
      options: [
        { text: '焦土まで行くのか', goto: 'waste' },
        { text: '戻る', goto: 'work' },
      ],
    },
    waste: {
      text: '行くわけないでしょう。灰纏いから買うの。あの子たちは灰の中で生きられる。……代わりに、長くは生きられないけど。',
      options: [{ text: '戻る', goto: 'start' }],
    },
    done: {
      text: '本当にやったの? ……いいわ、約束は約束。奥の品も見せてあげる。',
      options: [{ text: '受け取る', action: 'complete_side_mira' }],
    },
  },

  dorg: {
    start: {
      text: '鉄は嘘をつかん。打てば応える。……何を持ってきた?',
      options: [
        { text: '武器を強化する', action: 'smith' },
        { text: '炉のことを聞く', goto: 'forge', cond: ({ q }) => canOffer(q, 'side_smith') },
        { text: '残り火を持ってきた', goto: 'forge_done', cond: (c) => canDeliver(c, 'side_smith') },
        { text: '黒鉄を打てるか', goto: 'black', cond: ({ q }) => canOffer(q, 'side_dorg_blackiron') },
        { text: '核を持ってきた', goto: 'black_done', cond: (c) => canDeliver(c, 'side_dorg_blackiron') },
        { text: '去る', action: 'close' },
      ],
    },
    black: {
      text: 'あの鐘割りを覚えているか。鐘楼の連中が使う、刃のない大剣だ。あれは黒鉄でしか鋳れん。\n鍛石の核を二つ持ってこい。一つは鋳型に食わせる。もう一つは……まあ、失敗ぶんだ。正直に言っておく。',
      options: [
        { text: '探してくる', action: 'accept_side_dorg_blackiron' },
        { text: '戻る', goto: 'start' },
      ],
    },
    black_done: {
      text: '……二つとも寄越せ。手を離すな、そのまま炉へ。\n（長い沈黙）……一度で通った。二十年打っていて、初めてだ。持っていけ。俺が持っていても、振る腕がない。',
      options: [{ text: '渡す', action: 'complete_side_dorg_blackiron' }],
    },
    forge: {
      text: '火が弱い。普通の炭では、あの鉄は溶けん。……焦土の残り火のかけらが三つあれば、炉はまた本気を出す。',
      options: [
        { text: '黒鉄について', goto: 'blackiron' },
        { text: '探してくる', action: 'accept_side_smith' },
        { text: '戻る', goto: 'start' },
      ],
    },
    blackiron: {
      text: '黒鉄は鉄ではない。王冠の欠片が落ちた場所の土が、勝手にそうなる。叩けば伸びる。焼けば冷める。……だが決して錆びん。死なんのだ、あれも。',
      options: [
        { text: '刻印と同じか', goto: 'blackiron2' },
        { text: '戻る', goto: 'forge' },
      ],
    },
    blackiron2: {
      text: '……同じだ。お前の骨も、いずれそうなる。だから武器は選べ。長く付き合うことになる。',
      options: [{ text: '戻る', goto: 'start' }],
    },
    forge_done: {
      text: '……ふん。よし。これで上の段階まで打てる。持ってこい、何本でも。',
      options: [{ text: '渡す', action: 'complete_side_smith' }],
    },
  },

  vane: {
    start: {
      text: ({ q }) => (q.isDone('main_3')
        ? '誓いは果たされた。……お前が果たしたのだ、刻印者。'
        : '止まれ。鉄嶺より先は、誓約者の領だ。……断片が目当てか。'),
      options: [
        { text: '誓約者は倒した', goto: 'main3_done', cond: ({ q }) => q.isStepReady('main_3', 's3') },
        { text: '断片を渡してもらう', goto: 'refuse', cond: ({ q }) => !q.isDone('main_3') && !q.isActive('main_3') },
        { text: '誓約とは何だ', goto: 'oath' },
        { text: '鐘の音が止まらない', goto: 'bell', cond: ({ q }) => canOffer(q, 'side_bell_silence') && !q.isActive('side_bell_keep') },
        { text: '番人は黙らせた', goto: 'bell_done', cond: ({ q }) => q.isStepReady('side_bell_silence', 's1') },
        { text: '残った騎士たちは', goto: 'relief', cond: ({ q }) => canOffer(q, 'side_vane_relief') },
        { text: '騎士たちは眠らせた', goto: 'relief_done', cond: ({ q }) => q.isStepReady('side_vane_relief', 's1') },
        { text: '去る', action: 'close' },
      ],
    },
    main3_done: {
      text: '……終わったか。\n（長い間）二百年だ。飯を運んだのは俺で、運ぶのをやめたのも俺だ。それでも誓いは俺のものではなかった。あれのものだった。\n持っていけ。断片も、掟も。俺はもう、門番ではない。',
      options: [{ text: '受け取る', action: 'complete_main_3' }],
    },
    bell: {
      text: '鐘楼の鐘だ。あれが鳴るたび、埋めたものが起き上がる。番人は鳴らすのが仕事だと思っている。二百年前はそうだった。\n……止めてくれ。番人ごとで構わん。',
      options: [
        { text: '鐘は誰のものだ', goto: 'bell2' },
        { text: '引き受ける', action: 'accept_side_bell_silence' },
        { text: '考えておく', goto: 'start' },
      ],
    },
    bell2: {
      text: '砦のものだ。だが青銅を欲しがる男が一人、値をつけて回っている。鳴っているうちしか削れんと言ってな。\n……どちらかしか選べん。鳴らし続けさせるか、黙らせるか。',
      options: [
        { text: '黙らせる', action: 'accept_side_bell_silence' },
        { text: '戻る', goto: 'start' },
      ],
    },
    bell_done: {
      text: '音が消えた。……砦の連中が、何の音がしないのか分からんという顔をしている。二百年ぶりの静けさだ。誰も静けさを覚えていない。',
      options: [{ text: '受け取る', action: 'complete_side_bell_silence' }],
    },
    relief: {
      text: '誓いは果たされた。だが闘技場の外に、それを知らん者が六人ばかり立っている。俺の同輩だ。\n……頼めるか。俺の手では、どうしても止まる。',
      options: [
        { text: '引き受ける', action: 'accept_side_vane_relief' },
        { text: '断る', goto: 'start' },
      ],
    },
    relief_done: {
      text: '……六人とも、か。\n名を言おう。ハルド、テオ、ヴェン、二人のカイ、そして俺の弟だ。覚えなくていい。俺が覚える。これは俺の分の誓いだった。',
      options: [{ text: '受け取る', action: 'complete_side_vane_relief' }],
    },
    oath: {
      text: '王冠が砕けたとき、我らは「断片を誰にも渡さぬ」と誓った。……誓いは守られている。守られすぎて、誰も理由を覚えていない。',
      options: [
        { text: '闘技場のあれは何だ', goto: 'sworn' },
        { text: 'あなたは戦わないのか', goto: 'why' },
        { text: '戻る', goto: 'start' },
      ],
    },
    sworn: {
      text: '初代の誓約者だ。断片を握ったまま二百年、あそこに立っている。……我らは交代で飯を運んでいた。三十年前に、食わなくなった。',
      options: [{ text: '戻る', goto: 'oath' }],
    },
    why: {
      text: '挑んだ。四度。四度とも起き上がって、四度とも同じことを思った——あれは俺を殺す気がない、と。誓いを果たさせる相手を待っているのだ。',
      options: [
        { text: 'それが俺だと', goto: 'why2' },
        { text: '戻る', goto: 'oath' },
      ],
    },
    why2: {
      text: '知らん。だが門は開いている。二百年、誰の前でも開いていた。……行くなら、今日でも構わん。',
      options: [{ text: '戻る', goto: 'start' }],
    },
    refuse: {
      text: '渡せぬ。だが——闘技場は開いている。誓いは力にのみ譲る。それが鉄の掟だ。行け。あれを倒したなら、断片はお前のものだ。',
      options: [{ text: '行く', action: 'accept_main3' }],
    },
  },

  sera: {
    start: {
      text: '灰は降り続けるのに、積もらないの。……不思議でしょう。全部、どこかに吸われてる。',
      options: [
        { text: '何を探している', goto: 'search', cond: ({ q }) => canOffer(q, 'side_sera') },
        { text: '灰の主は倒した', goto: 'done', cond: ({ q }) => q.isStepReady('side_sera', 's2') },
        { text: '祈祷者のことを', goto: 'priests', cond: ({ q }) => canOffer(q, 'side_ember_priests') },
        { text: '祈りは止めた', goto: 'priests_done', cond: ({ q }) => q.isStepReady('side_ember_priests', 's1') },
        { text: '姉のことを', goto: 'widow', cond: ({ q }) => canOffer(q, 'side_widow') },
        { text: '……終わらせた', goto: 'widow_done', cond: ({ q }) => q.isStepReady('side_widow', 's1') },
        { text: '焦土について', goto: 'waste' },
        { text: '去る', action: 'close' },
      ],
    },
    priests: {
      text: 'あなたが倒したものが、朝には立っている。……見たでしょう。\n祈祷者よ。灰に向かって祈って、灰から人の形を借りるの。五人ばかり、輪のあたりにいる。',
      options: [
        { text: 'なぜ起こす', goto: 'priests2' },
        { text: '止めてくる', action: 'accept_side_ember_priests' },
        { text: '戻る', goto: 'start' },
      ],
    },
    priests2: {
      text: '寂しいからだと思う。……笑わないで。灰纏いはみんなそう。焦土から出られない人間が、出られない人間を増やしている。それだけのこと。\nわたしも、あと何年かで祈る側になるわ。',
      options: [
        { text: '止めてくる', action: 'accept_side_ember_priests' },
        { text: '戻る', goto: 'start' },
      ],
    },
    priests_done: {
      text: '静かになった。……朝に立っているものが、いなくなった。\nありがとう、と言うのは変ね。あなたが殺したのは、わたしの同族だもの。それでも言うわ。',
      options: [{ text: '受け取る', action: 'complete_side_ember_priests' }],
    },
    widow: {
      text: '聖印は返ってきた。姉は返ってこない。……当たり前だけど。\nでも、火が残っているの。灰の輪の奥に、人の形をした火が。近づくと、姉の歩き方をする。',
      options: [
        { text: 'それは姉なのか', goto: 'widow2' },
        { text: '行ってくる', action: 'accept_side_widow' },
        { text: '戻る', goto: 'start' },
      ],
    },
    widow2: {
      text: '違う。姉は焼けた。焼けたものが、姉の形を覚えているだけ。\n……でも、覚えているうちは、姉が終わっていないということでしょう。終わらせて。わたしにはできない。二度、行って、二度とも足が止まった。',
      options: [
        { text: '行ってくる', action: 'accept_side_widow' },
        { text: '戻る', goto: 'start' },
      ],
    },
    widow_done: {
      text: '……火が消えた場所は、灰が積もるのね。初めて見た。\n積もるということは、終わったということ。姉は、ようやく死んだのだと思う。……これを持っていって。わたしにはもう、使う手がない。',
      options: [{ text: '受け取る', action: 'complete_side_widow' }],
    },
    search: {
      text: '姉の聖印。灰の輪で落とした。……取りに行こうとして、二度死んだわ。三度目はもう、体が足りない。',
      options: [
        { text: '代わりに行こう', action: 'accept_side_sera' },
        { text: '悪いが', goto: 'start' },
      ],
    },
    waste: {
      text: '王冠が砕けたのはここ。火は消えず、灰は積もらず、死者は歩く。……三つとも、同じ理由なんだと思う。',
      options: [
        { text: 'その理由とは', goto: 'why' },
        { text: '灰纏いとは', goto: 'clad' },
        { text: '戻る', goto: 'start' },
      ],
    },
    why: {
      text: '終わっていないから。火は燃え尽きるまでが火で、灰は積もるまでが灰で、人は死ぬまでが人。……全部、途中で止められてる。誰かが握ったままなの。',
      options: [{ text: '戻る', goto: 'waste' }],
    },
    clad: {
      text: '灰を吸って生きる人。焦土でしか呼吸ができなくなる代わりに、灰に殺されない。……姉がそう。わたしもそう。もう外には出られないわ。',
      options: [
        { text: '姉は', goto: 'sister' },
        { text: '戻る', goto: 'waste' },
      ],
    },
    sister: {
      text: '灰の輪へ行った。「火を消してくる」と言って。……止めなかったのは、わたしも同じことを考えていたから。',
      options: [{ text: '戻る', goto: 'start' }],
    },
    done: {
      text: 'これ……姉のだわ。……ありがとう。お礼と言っては何だけど、この祈りを教える。姉が使っていたもの。',
      options: [{ text: '受け取る', action: 'complete_side_sera' }],
    },
  },

  io: {
    start: {
      text: ({ q }) => (q.isDone('side_io_rootheart')
        ? '森が静かだ。……静かというのは、何も言わないという意味ではない。今は、言うことがないだけだ。'
        : '灯を見に来たのか。それとも、灯を消しに来たほうか。……どちらでもいい。座れ。'),
      options: [
        { text: '灯とは', goto: 'lantern' },
        { text: '森の話を', goto: 'wood' },
        { text: '消えた灯のことを', goto: 'work', cond: ({ q }) => canOffer(q, 'side_io_lanterns') },
        { text: '森のものは減らした', goto: 'work_done', cond: ({ q }) => q.isStepReady('side_io_lanterns', 's1') },
        { text: '森の底のことを', goto: 'heart', cond: ({ q }) => canOffer(q, 'side_io_rootheart') },
        { text: '祠に触れてきた', goto: 'shrines_done', cond: ({ q }) => q.isStepReady('side_shrines', 's1') },
        { text: '……父を止めた', goto: 'heart_done', cond: ({ q }) => q.isStepReady('side_io_rootheart', 's1') },
        { text: '去る', action: 'close' },
      ],
    },
    lantern: {
      text: '森に十二の灯がある。木に吊るしてあるのではない。木が吊るされているのだ。\n灯のある木は動かん。灯が消えると、朝には別の場所に生えている。……道を覚えても意味がないのは、そのせいだ。',
      options: [
        { text: '誰が吊るした', goto: 'lantern2' },
        { text: '戻る', goto: 'start' },
      ],
    },
    lantern2: {
      text: '私の前の灯守が。その前の灯守も。……最初の一人が誰だったかは、灯が知っている。私は訊いたことがない。訊けば答えるだろうが、答えを聞いた灯守は、みな次の朝にいない。',
      options: [{ text: '戻る', goto: 'start' }],
    },
    wood: {
      text: '囁きの森という名は、囁きが聞こえるからではない。囁きしか聞こえないからだ。\n大きな音を立てるものは、みな森に食われた。だからここのものは小さくて、数が多い。',
      options: [
        { text: '縛り手のことを', goto: 'warden' },
        { text: '戻る', goto: 'start' },
      ],
    },
    warden: {
      text: '縛り手か。あれは森の側ではない。森が断片を飲んで、吐き出せずに固めたものだ。\n……お前が殺したのなら、森は礼を言っている。私が代わりに言おう。ありがとう。そして、まだ根が残っている。',
      options: [{ text: '戻る', goto: 'start' }],
    },
    work: {
      text: '灯が次々に消える。風ではない。小さいものが、十二匹ばかりで一つの灯に群がる。\n十二ほど減らしてくれ。同じ数だ。偶然ではないと思う。',
      options: [
        { text: '引き受ける', action: 'accept_side_io_lanterns' },
        { text: '今はいい', goto: 'start' },
      ],
    },
    work_done: {
      text: '灯が四つ、ひとりでに点いた。……点け直してはいない。\n持っていけ。灯守は物を持たん。持てば、灯を持つ手がなくなる。',
      options: [{ text: '受け取る', action: 'complete_side_io_lanterns' }],
    },
    heart: {
      text: '森の底に、脈を打つものがある。私はそれを父と呼んでいる。灯守はみなそう呼ぶ。\n……そろそろだ。父が起きると、灯は全部消える。消えたあとの森を、私は見たくない。',
      options: [
        { text: 'なぜ父と', goto: 'heart2' },
        { text: '行ってくる', action: 'accept_side_io_rootheart' },
        { text: '戻る', goto: 'start' },
      ],
    },
    heart2: {
      text: '灯守は森に拾われた子どもだからだ。私も、その前も。父が根を伸ばして拾い、灯を持たせる。\n……つまり、頼んでいることは分かっている。分かった上で頼んでいる。',
      options: [
        { text: '行ってくる', action: 'accept_side_io_rootheart' },
        { text: '戻る', goto: 'start' },
      ],
    },
    shrines_done: {
      text: '祠に触れたな。手を見れば分かる。……あれは古い灯だ。灯守が立てるより前の、誰かが立てた灯。\n触れた者に何かを渡すのは、灯の仕事ではない。渡しているのは、触れられて嬉しいからだ。それだけのことだと思う。',
      options: [{ text: '受け取る', action: 'complete_side_shrines' }],
    },
    heart_done: {
      text: '……脈が止まった。足の裏で分かる。\n私は今日から、拾われた子どもではない。ただの男だ。ずいぶん軽い。持っていけ、これは父の腕だったものだ。',
      options: [{ text: '受け取る', action: 'complete_side_io_rootheart' }],
    },
  },

  grim: {
    start: {
      text: ({ q }) => (q.isDone('side_grim_choir')
        ? '歌がやんだ。……穴を掘る音だけになった。ようやく仕事らしくなった。'
        : '掘りに来たか、埋めに来たか。……見れば分かる。掘りに来た顔だ。'),
      options: [
        { text: '何を数えている', goto: 'count' },
        { text: '沼のことを', goto: 'mire' },
        { text: '骨がいるのか', goto: 'bones', cond: ({ q }) => canOffer(q, 'side_grim_bones') },
        { text: '骨を持ってきた', goto: 'bones_done', cond: (c) => canDeliver(c, 'side_grim_bones') },
        { text: '穴の話を', goto: 'holes', cond: ({ q }) => canOffer(q, 'side_grim_stalkers') },
        { text: '潜むものは片付けた', goto: 'holes_done', cond: ({ q }) => q.isStepReady('side_grim_stalkers', 's1') },
        { text: '歌のことを', goto: 'song', cond: ({ q }) => canOffer(q, 'side_grim_choir') },
        { text: '歌は止めた', goto: 'song_done', cond: ({ q }) => q.isStepReady('side_grim_choir', 's1') },
        { text: '去る', action: 'close' },
      ],
    },
    count: {
      text: '埋めた数と、掘り出した数だ。合わん。\n埋めたのが四百十二。掘り出したのが四百三十。……十八人ぶん、多い。誰も埋めていないものが、埋まっている。',
      options: [
        { text: '誰が埋めた', goto: 'count2' },
        { text: '戻る', goto: 'start' },
      ],
    },
    count2: {
      text: '自分で入ったのだろうな。沼は柔らかい。歩いていて、そのまま入れる。\n……そういうのを見たことがある。止めなかった。あれは沈むために歩いていた。止めれば、また歩き直すだけだ。',
      options: [{ text: '戻る', goto: 'start' }],
    },
    mire: {
      text: '灰泥の沼。水ではない、灰が溶けたものだ。だから腐らん。掘り出した骨は、埋めた日のままの顔をしている。\n……それが一番きつい。腐ってくれれば、忘れられるのに。',
      options: [{ text: '戻る', goto: 'start' }],
    },
    bones: {
      text: '数が合わんと言ったろう。合わせるには、まず手持ちの骨を数え直さねばならん。\n白い骨を五つ持ってこい。亡骸兵が落とす。あれは死んでも骨を落とす。死に慣れているのだ。',
      options: [
        { text: '探してくる', action: 'accept_side_grim_bones' },
        { text: '戻る', goto: 'start' },
      ],
    },
    bones_done: {
      text: '……五つ。よし。\n（数える音）……四百十七。まだ合わん。だが近づいた。近づいたということは、いずれ届くということだ。持っていけ、兜だ。骨のは軽い。',
      options: [{ text: '渡す', action: 'complete_side_grim_bones' }],
    },
    holes: {
      text: '掘った穴に、翌朝には先客がいる。泥の中を泳ぐものだ。\n埋めるべきものが埋まらん。六匹も潰してくれれば、仕事が進む。',
      options: [
        { text: '引き受ける', action: 'accept_side_grim_stalkers' },
        { text: '戻る', goto: 'start' },
      ],
    },
    holes_done: {
      text: '穴が穴のままだった。三日ぶりだ。\n……礼に鎧をやる。骨のだ。持ち主は文句を言わん。四百十二人のうちの誰かだが、もう分からん。',
      options: [{ text: '受け取る', action: 'complete_side_grim_stalkers' }],
    },
    song: {
      text: '沼の底から歌が聞こえる。夜だけだ。……三人ぶんの声がする。\n聞くな、とだけ言っておく。聞くと、掘る手が止まる。止まった連中は、みな沼のほうへ歩いていった。数が合わんのはそれだ。',
      options: [
        { text: 'それでも行く', action: 'accept_side_grim_choir' },
        { text: '戻る', goto: 'start' },
      ],
    },
    song_done: {
      text: '……静かだ。\n昨夜、初めて数が合った。四百三十が、四百三十だ。十八人は歌のほうへ歩いていって、歌のほうに埋まっていた。\nこれを持っていけ。杖だ。歌っていたものが持っていた。',
      options: [{ text: '受け取る', action: 'complete_side_grim_choir' }],
    },
  },

  nei: {
    start: {
      text: '……人か。久しぶりだ。鴉は人の声を真似るから、しばらく確かめていた。\n真似ないものは、たいてい本物だ。',
      options: [
        { text: 'ここで何をしている', goto: 'why' },
        { text: '棚のことを', goto: 'shelf' },
        { text: '鴉のことを', goto: 'crows', cond: ({ q }) => canOffer(q, 'side_nei_crows') },
        { text: '鴉は落とした', goto: 'crows_done', cond: ({ q }) => q.isStepReady('side_nei_crows', 's1') },
        { text: '石を喰う者のことを', goto: 'carls', cond: ({ q }) => canOffer(q, 'side_nei_carls') },
        { text: '遺構をいくつも見た', goto: 'relics_done', cond: ({ q }) => q.isStepReady('side_relics', 's1') },
        { text: '石喰いは減らした', goto: 'carls_done', cond: ({ q }) => q.isStepReady('side_nei_carls', 's1') },
        { text: '去る', action: 'close' },
      ],
    },
    why: {
      text: '数えている。棚の岩がいくつ落ちたか。\n三十年で四百と七つだ。棚は減っている。竜が去っても、棚は減り続ける。……つまり、竜のせいではなかった。',
      options: [
        { text: 'では何のせいだ', goto: 'why2' },
        { text: '戻る', goto: 'start' },
      ],
    },
    why2: {
      text: '石を喰うものがいる。文字通り喰う。棚の下に穴を開けて、上から順に落としていく。\n……三十年見ていて分かったのは、それだけだ。三十年だぞ。分かるのが遅すぎた。',
      options: [{ text: '戻る', goto: 'start' }],
    },
    shelf: {
      text: '蒼玉の断崖。棚というのは、崖の途中に張り出した岩のことだ。竜が巣にしていた。\n巣の下には、竜が落としたものが積もっている。骨と、鱗と、それから鎧だ。中身ごと落とされた鎧が。',
      options: [{ text: '戻る', goto: 'start' }],
    },
    crows: {
      text: '鴉が棚の卵を持っていく。竜の卵ではない、鳥のだ。それでも棚の生き物が減れば、棚は死ぬ。\n……八羽ほど落としてくれ。私はもう、投げるものがない。石を投げると棚が減る。',
      options: [
        { text: '引き受ける', action: 'accept_side_nei_crows' },
        { text: '戻る', goto: 'start' },
      ],
    },
    crows_done: {
      text: '静かだ。人の声を真似るものがいないと、こんなに静かなのか。\n……少し寂しい。持っていけ、角の弓だ。私はもう引けん。',
      options: [{ text: '受け取る', action: 'complete_side_nei_crows' }],
    },
    carls: {
      text: '石を喰うものを四体。四体でいい。あれは群れん、だから四体で棚一つぶんだ。\n……崖の縁で戦うな。あれは自分ごと落とす。落ちても石は痛くない。',
      options: [
        { text: '引き受ける', action: 'accept_side_nei_carls' },
        { text: '戻る', goto: 'start' },
      ],
    },
    relics_done: {
      text: '六つか。……なら、順序が分かる。倒れた柱は、倒れた向きで語る。六つあれば線が引ける。\n線の先は焦土だ。全部の柱が、焦土のほうを向いて倒れている。押されたのではない。逃げたのだ。\n持っていけ。軽くなる護符だ。逃げるときに要る。',
      options: [{ text: '受け取る', action: 'complete_side_relics' }],
    },
    carls_done: {
      text: '今朝は、落ちた岩が零だった。三十年で初めてだ。\n……数えるのをやめてもいいかもしれん。持っていけ。護符だ。重いものを持てるようになる。私には要らん、持つものがない。',
      options: [{ text: '受け取る', action: 'complete_side_nei_carls' }],
    },
  },

  lusha: {
    start: {
      text: ({ q }) => (q.isDone('side_lusha_song')
        ? '唄が返ってくるようになった。……雪ではなく、人の声で。'
        : '唄うか。……唄わなくていい。ここでは唄うと、雪のほうが返してくる。'),
      options: [
        { text: '唄とは', goto: 'song' },
        { text: '頂のことを', goto: 'peak' },
        { text: '雪の獣のことを', goto: 'beasts', cond: ({ q }) => canOffer(q, 'side_lusha_stalk') },
        { text: '雪の獣は減らした', goto: 'beasts_done', cond: ({ q }) => q.isStepReady('side_lusha_stalk', 's1') },
        { text: '凍った男のことを', goto: 'jarl', cond: ({ q }) => canOffer(q, 'side_lusha_song') },
        { text: '篝火を辿ってきた', goto: 'graces_done', cond: ({ q }) => q.isStepReady('side_graces', 's1') },
        { text: '……司は倒した', goto: 'jarl_done', cond: ({ q }) => q.isStepReady('side_lusha_song', 's1') },
        { text: '去る', action: 'close' },
      ],
    },
    song: {
      text: '唄い手は、名を唄って残す者のことだ。書けば消える。石に彫っても、王冠が砕けてからは消える。\n……唄は消えない。唄う者がいるかぎりは。私は今、四百三十人ぶん覚えている。',
      options: [
        { text: '忘れたらどうなる', goto: 'song2' },
        { text: '戻る', goto: 'start' },
      ],
    },
    song2: {
      text: 'その者が、いなかったことになる。刻印者が忘れられて亡骸兵になるのと、順序が逆なだけだ。\n……だから唄う。眠るときも、少し唄っている。止めると一人減る。',
      options: [{ text: '戻る', goto: 'start' }],
    },
    peak: {
      text: '白牙峰。頂に火がある。あの火だけが、この島で唯一「消えていない」ものだ。ほかの火は全部、消えないだけで、燃えてもいない。\n……違いが分かるようになったら、お前も長い。',
      options: [{ text: '戻る', goto: 'start' }],
    },
    beasts: {
      text: '雪を走るものが増えた。あれは唄を覚える。私の唄を、私の声で返してくる。\n……六匹ほど。頼む。自分の声で名を呼ばれるのは、思っていたよりこたえる。',
      options: [
        { text: '引き受ける', action: 'accept_side_lusha_stalk' },
        { text: '戻る', goto: 'start' },
      ],
    },
    beasts_done: {
      text: '静かになった。……私の声が、私からしか聞こえない。当たり前のことが、ずいぶん贅沢だ。\n持っていけ。兜だ。凍らずに済む。',
      options: [{ text: '受け取る', action: 'complete_side_lusha_stalk' }],
    },
    jarl: {
      text: '頂の手前に、凍ったまま座っている男がいる。名は唄に入っている。誓約者の一人だ。\n……逃げたのではない。誓いを持ったまま、ここまで登って、座った。座ったまま二百年だ。',
      options: [
        { text: '死んでいるのか', goto: 'jarl2' },
        { text: '会ってくる', action: 'accept_side_lusha_song' },
        { text: '戻る', goto: 'start' },
      ],
    },
    jarl2: {
      text: '死んでいれば唄わない。……去年から、返してくるようになった。私の唄を、氷の下から。\n終わらせてやってくれ。私は唄うことしかできん。唄えば唄うほど、あれは目を覚ます。',
      options: [
        { text: '会ってくる', action: 'accept_side_lusha_song' },
        { text: '戻る', goto: 'start' },
      ],
    },
    graces_done: {
      text: '火から火へ。……それを唄にした者はいない。地図は唄にならん。名前がないからだ。\nだが、お前が辿った順序には名前がある。お前の名だ。……一人ぶん、覚えておく。',
      options: [{ text: '受け取る', action: 'complete_side_graces' }],
    },
    jarl_done: {
      text: '……返ってこなくなった。\n名を唄に残す。四百三十一人目だ。誓文は持っていけ、半分しか読めんが、半分は読める。それだけあれば十分なこともある。',
      options: [{ text: '受け取る', action: 'complete_side_lusha_song' }],
    },
  },

  kaim: {
    start: {
      text: ({ q }) => (q.hasFlag('bounty_open')
        ? 'また来たか。話の分かる客は久しぶりだ。……奥の品も出そう。'
        : '首はあるか。名のあるやつのだ。……ないなら、買うほうか?'),
      options: [
        { text: '買い物をする', action: 'shop' },
        { text: '売る', action: 'sell' },
        { text: '賞金首の話を', goto: 'bounty', cond: ({ q }) => canOffer(q, 'side_kaim_bounty') },
        { text: '数なら覚えている', goto: 'slayer_done', cond: ({ q }) => q.isStepReady('side_slayer', 's1') },
        { text: '二つ討った', goto: 'bounty_done', cond: ({ q }) => q.isStepReady('side_kaim_bounty', 's1') },
        { text: '帳面がある', goto: 'ledger', cond: (c) => canOffer(c.q, 'side_ledger_sell') && c.p.countItem('key_ledger') > 0 },
        { text: '帳面を渡す', goto: 'ledger_done', cond: (c) => canDeliver(c, 'side_ledger_sell') },
        { text: '鐘のことを', goto: 'bell', cond: ({ q }) => canOffer(q, 'side_bell_keep') && !q.isActive('side_bell_silence') },
        { text: '青銅を持ってきた', goto: 'bell_done', cond: (c) => canDeliver(c, 'side_bell_keep') },
        { text: '去る', action: 'close' },
      ],
    },
    bounty: {
      text: '名のあるやつを二つ。首魁でも、狼の長でも、隊長でも、灰の主でもいい。\n名があるということは、誰かが困っているということだ。困っている者がいれば、金が出る。単純な商売だ。',
      options: [
        { text: '誰が金を出す', goto: 'bounty2' },
        { text: '引き受ける', action: 'accept_side_kaim_bounty' },
        { text: '断る', goto: 'start' },
      ],
    },
    bounty2: {
      text: '砦だ。それと村。……あとは、名を消したい奴。誰とは言わん。\n言っておくが、俺は名を売り買いしているだけだ。殺すのはお前だ。そこは間違えるな。',
      options: [
        { text: '引き受ける', action: 'accept_side_kaim_bounty' },
        { text: '戻る', goto: 'start' },
      ],
    },
    slayer_done: {
      text: '百五十。……数えていたのは俺だ。お前ではない。\n言っておくが、俺は名のあるやつしか帳面に書かん。百五十のうち、名があったのは四つだ。残りの百四十六は、ただの数だ。\n……それでも数えた。誰かが数えないと、無かったことになる。持っていけ。',
      options: [{ text: '受け取る', action: 'complete_side_slayer' }],
    },
    bounty_done: {
      text: '二つとも確認した。……いい仕事だ。速いのは価値がある。遅い奴は、二つ目を取る前に自分が一つ目になる。\n取っておけ。護符だ。弾けるようになる。',
      options: [{ text: '受け取る', action: 'complete_side_kaim_bounty' }],
    },
    ledger: {
      text: 'それか。……見せろ。ああ、これだ。これは金になる。\n名前が並んでいるからな。名前を消したい者は、名前が並んでいる紙に高い値をつける。行商の女は焼けと言っただろう。焼けば、値がゼロになる。',
      options: [
        { text: '焼けと言われた', goto: 'ledger2' },
        { text: '売ろう', action: 'accept_side_ledger_sell' },
        { text: '考えておく', goto: 'start' },
      ],
    },
    ledger2: {
      text: '言うだろうな。あの女は載っている側だ。\n……好きにしろ。ただ、焼いたところで、取り返しに来る連中は帳面がなくても来る。来る先が分からなくなるだけだ。それを親切と呼ぶかは、お前が決めろ。',
      options: [
        { text: '売ろう', action: 'accept_side_ledger_sell' },
        { text: '戻る', goto: 'start' },
      ],
    },
    ledger_done: {
      text: '受け取った。……これで六人ぶんの名が、俺の側に来た。\n約束の分だ。奥の品も出す。言っておくが、俺はお前を載せていない。まだな。',
      options: [{ text: '渡す', action: 'complete_side_ledger_sell' }],
    },
    bell: {
      text: '鐘楼の鐘だ。あれの青銅は、鳴っているあいだしか削れん。振動で表面が浮くのだ。理屈は知らん、そうなる。\n六つ集めてこい。鐘が鳴っているうちにだ。番人を殺せば鳴りやむ。……つまり、殺すなということだ。',
      options: [
        { text: '誓約者は黙らせろと言った', goto: 'bell2' },
        { text: '集めてくる', action: 'accept_side_bell_keep' },
        { text: '断る', goto: 'start' },
      ],
    },
    bell2: {
      text: '言うだろうな。あれは死者が起きるのが気に入らん。俺は起きようが構わん、青銅が要る。\n……どちらか片方だ。両方は取れん。鐘は一つしかない。',
      options: [
        { text: '集めてくる', action: 'accept_side_bell_keep' },
        { text: '戻る', goto: 'start' },
      ],
    },
    bell_done: {
      text: '六つ、揃ったな。……重い。いい重さだ。\n槌をやろう。同じ青銅で打った。当たった奴は、しばらく音しか聞こえんそうだ。……鐘の側の気持ちが分かるわけだ。',
      options: [{ text: '渡す', action: 'complete_side_bell_keep' }],
    },
  },
};

// ---------------------------------------------------------------------------
//  Tracker
// ---------------------------------------------------------------------------

export class QuestLog {
  constructor() {
    this.state = new Map();     // questId -> { status, step, counters }
    this.flags = new Set();
    for (const q of QUESTS) {
      this.state.set(q.id, { status: q.autoStart ? QUEST_STATE.ACTIVE : QUEST_STATE.LOCKED, step: 0, counters: {} });
    }
  }

  get(id) { return this.state.get(id); }
  isActive(id) { return this.state.get(id)?.status === QUEST_STATE.ACTIVE; }
  isDone(id) { return this.state.get(id)?.status === QUEST_STATE.DONE; }
  isFailed(id) { return this.state.get(id)?.status === QUEST_STATE.FAILED; }
  hasFlag(f) { return this.flags.has(f); }
  setFlag(f) { this.flags.add(f); }

  start(id) {
    const q = QUEST_BY_ID.get(id);
    const s = this.state.get(id);
    if (!q || !s) return false;
    if (s.status === QUEST_STATE.DONE || s.status === QUEST_STATE.FAILED) return false;
    if (s.status === QUEST_STATE.ACTIVE) return false;
    if (q.requires && !this.isDone(q.requires)) return false;
    s.status = QUEST_STATE.ACTIVE;
    s.step = 0;

    // Taking a side closes the other one for good. Nothing here un-fails a
    // quest, because a choice the player can walk back is not a choice.
    for (const other of q.excludes || []) {
      const o = this.state.get(other);
      if (o && o.status !== QUEST_STATE.DONE) o.status = QUEST_STATE.FAILED;
    }
    return true;
  }

  fail(id) {
    const s = this.state.get(id);
    if (!s || s.status !== QUEST_STATE.ACTIVE) return false;
    s.status = QUEST_STATE.FAILED;
    return true;
  }

  /** True when the current step's condition is satisfied but not yet claimed. */
  isStepReady(id, stepId) {
    const q = QUEST_BY_ID.get(id);
    const s = this.state.get(id);
    if (!q || !s || s.status !== QUEST_STATE.ACTIVE) return false;
    const step = q.steps[s.step];
    if (!step || step.id !== stepId) return false;
    return !!s.counters[`${step.id}_ready`];
  }

  markReady(id, stepId) {
    const s = this.state.get(id);
    if (s) s.counters[`${stepId}_ready`] = 1;
  }

  advance(id) {
    const q = QUEST_BY_ID.get(id);
    const s = this.state.get(id);
    if (!q || !s || s.status !== QUEST_STATE.ACTIVE) return null;
    s.step++;
    if (s.step >= q.steps.length) {
      s.status = QUEST_STATE.DONE;
      // Chain here rather than at the call site: a quest that finishes by
      // killing a boss never passes through the dialogue path, and without
      // this the main line silently stops handing out its next objective.
      if (q.next) this.start(q.next);
      return { completed: true, quest: q };
    }
    return { completed: false, quest: q, step: q.steps[s.step] };
  }

  currentStep(id) {
    const q = QUEST_BY_ID.get(id);
    const s = this.state.get(id);
    if (!q || !s || s.status !== QUEST_STATE.ACTIVE) return null;
    return q.steps[s.step] || null;
  }

  /** Feed world events in; returns the list of quests that progressed. */
  notify(event) {
    const progressed = [];
    for (const q of QUESTS) {
      const s = this.state.get(q.id);
      if (!s || s.status !== QUEST_STATE.ACTIVE) continue;

      // Failure is checked before progress: an event can end a quest that the
      // same event would otherwise have advanced.
      if (q.failOn && this._matchesFail(q.failOn, event)) {
        s.status = QUEST_STATE.FAILED;
        progressed.push({ quest: q, result: { failed: true, quest: q } });
        continue;
      }

      const step = q.steps[s.step];
      if (!step) continue;

      let hit = false;
      switch (step.type) {
        case 'kill':
          if (event.type === 'kill' && event.archetype === step.target) {
            const key = `${step.id}_count`;
            s.counters[key] = (s.counters[key] || 0) + 1;
            if (s.counters[key] >= (step.count || 1)) hit = true;
          }
          break;
        case 'kill_any':
          if (event.type === 'kill' && step.target.indexOf(event.archetype) >= 0) {
            const key = `${step.id}_count`;
            s.counters[key] = (s.counters[key] || 0) + 1;
            if (s.counters[key] >= (step.count || 1)) hit = true;
          }
          break;
        case 'kill_total':
          if (event.type === 'kill') {
            const key = `${step.id}_count`;
            s.counters[key] = (s.counters[key] || 0) + 1;
            if (s.counters[key] >= (step.count || 1)) hit = true;
          }
          break;
        case 'explore':
          // Distinct places only, so pacing back and forth over one ruin does
          // not tick the counter.
          if (event.type === 'reach' && typeof event.poi === 'string'
            && event.poi.indexOf(step.prefix) === 0) {
            const seen = `${step.id}_seen_${event.poi}`;
            if (!s.counters[seen]) {
              s.counters[seen] = 1;
              const key = `${step.id}_count`;
              s.counters[key] = (s.counters[key] || 0) + 1;
              if (s.counters[key] >= (step.count || 1)) hit = true;
            }
          }
          break;
        case 'boss':
          if (event.type === 'boss' && event.boss === step.target) hit = true;
          break;
        case 'reach':
          if (event.type === 'reach' && event.poi === step.target) hit = true;
          break;
        case 'talk':
          if (event.type === 'talk' && event.npc === step.target) hit = true;
          break;
        case 'shrine':
          if (event.type === 'shrine') {
            const key = `${step.id}_count`;
            s.counters[key] = (s.counters[key] || 0) + 1;
            if (s.counters[key] >= (step.count || 1)) hit = true;
          }
          break;
        case 'items':
          if (event.type === 'inventory') {
            const need = Array.isArray(step.target) ? step.target : [step.target];
            if (need.every((id) => event.has(id))) hit = true;
          }
          break;
        case 'deliver':
          // Resolved explicitly by the dialogue action, not by world events.
          break;
        default: break;
      }

      if (hit) {
        this.markReady(q.id, step.id);
        // The last step of a quest with a turn-in stays ready-but-open: the
        // reward is handed over in conversation, which is also the only place
        // the giver gets to react to what the player actually did.
        const isFinal = s.step === q.steps.length - 1;
        if (isFinal && q.turnIn) continue;
        const r = this.advance(q.id);
        progressed.push({ quest: q, result: r });
      }
    }
    return progressed;
  }

  _matchesFail(cond, event) {
    switch (cond.type) {
      case 'boss': return event.type === 'boss' && event.boss === cond.target;
      case 'kill': return event.type === 'kill' && event.archetype === cond.target;
      case 'reach': return event.type === 'reach' && event.poi === cond.target;
      default: return false;
    }
  }

  serialize() {
    const out = {};
    for (const [k, v] of this.state) out[k] = { s: v.status, p: v.step, c: v.counters };
    return { quests: out, flags: Array.from(this.flags) };
  }

  deserialize(data) {
    if (!data) return;
    for (const k in data.quests || {}) {
      const v = data.quests[k];
      if (this.state.has(k)) this.state.set(k, { status: v.s, step: v.p, counters: v.c || {} });
    }
    this.flags = new Set(data.flags || []);
  }
}
