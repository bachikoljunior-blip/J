// ============================================================================
//  quests.js — the main chain, side quests, NPCs and their dialogue.
//
//  Quests are data-driven state machines. Each step declares a condition the
//  game checks against its own event log, so nothing here needs to know how
//  combat or exploration are implemented — a step just says "kill 6 of these"
//  or "reach that place" and the tracker resolves it.
// ============================================================================

export const QUEST_STATE = { LOCKED: 0, ACTIVE: 1, DONE: 2, FAILED: 3 };

export const QUESTS = [
  {
    id: 'main_1', main: true, name: '灰の目覚め', giver: 'harum',
    summary: '村長ハラムに話を聞き、王冠の断片について知る。',
    steps: [
      { id: 's1', text: '灯火の村でハラムと話す', type: 'talk', target: 'harum' },
      { id: 's2', text: '囁きの森の縛り手を討つ', type: 'boss', target: 'warden' },
    ],
    rewards: { souls: 1200, items: [['flask_hp', 1]], flaskUp: 'hp' },
    next: 'main_2',
  },
  {
    id: 'main_2', main: true, name: '沈殿の玉座', giver: 'harum',
    summary: '灰泥の沼に沈んだ社の奥、泥の女王が断片を抱いている。',
    steps: [
      { id: 's1', text: '灰泥の沼へ向かう', type: 'reach', target: 'grace_mire' },
      { id: 's2', text: '泥の女王を討つ', type: 'boss', target: 'mirequeen' },
    ],
    rewards: { souls: 3000, items: [['antidote', 5], ['mat_chunk', 2]], flaskUp: 'hp' },
    next: 'main_3',
  },
  {
    id: 'main_3', main: true, name: '鉄の掟', giver: 'vane',
    summary: '鉄嶺の誓約者は断片を「守っている」と言う。話が通じるとは限らない。',
    steps: [
      { id: 's1', text: '鉄砦でヴェインと話す', type: 'talk', target: 'vane' },
      { id: 's2', text: '誓約の闘技場で鉄の誓約者を討つ', type: 'boss', target: 'ironsworn' },
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
    id: 'side_wolves', name: '狼を減らす', giver: 'harum',
    summary: '村の周りに灰狼が増えすぎた。十匹も減らせば落ち着くだろう。',
    steps: [{ id: 's1', text: '灰狼を10体討つ', type: 'kill', target: 'ashwolf', count: 10 }],
    rewards: { souls: 900, items: [['mat_fang', 3], ['tal_hunter', 1]] },
  },
  {
    id: 'side_smith', name: '鍛冶の火', giver: 'dorg', requires: 'main_1',
    summary: 'ドルグの炉は火が弱い。焦土の残り火があれば、また鍛てる。',
    steps: [{ id: 's1', text: '残り火のかけらを3つ渡す', type: 'deliver', target: 'ember_shard', count: 3 }],
    rewards: { souls: 1500, items: [['mat_chunk', 2]], unlock: 'smith_tier2' },
  },
  {
    id: 'side_sera', name: '灰纏いの願い', giver: 'sera',
    summary: 'セラは焦土で失くしたものを探している。灰の輪に落ちているはずだと。',
    steps: [
      { id: 's1', text: '灰の輪で「灰の主」を討つ', type: 'kill', target: 'wraith_lord', count: 1 },
      { id: 's2', text: 'セラに報告する', type: 'talk', target: 'sera' },
    ],
    rewards: { souls: 4000, items: [['tal_lastlight', 1]], spell: 'sp_pyre' },
  },
  {
    id: 'side_mira', name: '商人の護衛', giver: 'mira',
    summary: 'ミラは道中の野盗に困っている。首魁を潰せば、しばらく通れる。',
    steps: [{ id: 's1', text: '野盗の首魁を討つ', type: 'kill', target: 'bandit_chief', count: 1 }],
    rewards: { souls: 1800, items: [['ember_shard', 2]], unlock: 'merchant_tier2' },
  },
  {
    id: 'side_shrines', name: '古き祠を巡る', giver: null,
    summary: '祠に触れると、体の奥で何かが確かになる。全部で12。',
    steps: [{ id: 's1', text: '祠を6つ見つける', type: 'shrine', count: 6 }],
    rewards: { souls: 3000, items: [['tal_vigor', 1]] },
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
};

// ---------------------------------------------------------------------------
//  Dialogue trees
//  Nodes: { text, options: [{ text, goto | action }] }
//  `cond` on an option hides it unless the predicate passes.
// ---------------------------------------------------------------------------

export const DIALOGUE = {
  harum: {
    start: {
      text: ({ q }) => (q.isDone('main_1')
        ? 'よく戻った、刻印者。……お前だけが、まだ歩いている。'
        : 'また一人、灰から起き上がったか。……座れ、話は短い。'),
      options: [
        { text: '王冠の断片について', goto: 'crown' },
        { text: 'この土地について', goto: 'land' },
        { text: '仕事はあるか', goto: 'work', cond: ({ q }) => !q.isActive('side_wolves') && !q.isDone('side_wolves') },
        { text: '狼は減らした', goto: 'wolves_done', cond: ({ q }) => q.isStepReady('side_wolves', 's1') },
        { text: '……去る', action: 'close' },
      ],
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
        { text: '仕事はあるか', goto: 'work', cond: ({ q }) => !q.isActive('side_mira') && !q.isDone('side_mira') },
        { text: '首魁は片付けた', goto: 'done', cond: ({ q }) => q.isStepReady('side_mira', 's1') },
        { text: '去る', action: 'close' },
      ],
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
        { text: '炉のことを聞く', goto: 'forge', cond: ({ q }) => !q.isActive('side_smith') && !q.isDone('side_smith') },
        { text: '残り火を持ってきた', goto: 'forge_done', cond: ({ q }) => q.isStepReady('side_smith', 's1') },
        { text: '去る', action: 'close' },
      ],
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
        { text: '断片を渡してもらう', goto: 'refuse', cond: ({ q }) => !q.isDone('main_3') },
        { text: '誓約とは何だ', goto: 'oath' },
        { text: '去る', action: 'close' },
      ],
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
        { text: '何を探している', goto: 'search', cond: ({ q }) => !q.isActive('side_sera') && !q.isDone('side_sera') },
        { text: '灰の主は倒した', goto: 'done', cond: ({ q }) => q.isStepReady('side_sera', 's1') },
        { text: '焦土について', goto: 'waste' },
        { text: '去る', action: 'close' },
      ],
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
  hasFlag(f) { return this.flags.has(f); }
  setFlag(f) { this.flags.add(f); }

  start(id) {
    const s = this.state.get(id);
    if (!s || s.status === QUEST_STATE.DONE) return false;
    if (s.status === QUEST_STATE.ACTIVE) return false;
    s.status = QUEST_STATE.ACTIVE;
    s.step = 0;
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
        // Steps that do not need a conversation to close advance immediately.
        if (step.type !== 'talk' || event.type === 'talk') {
          if (step.type === 'kill' || step.type === 'boss' || step.type === 'reach'
            || step.type === 'shrine' || step.type === 'items' || step.type === 'talk') {
            const r = this.advance(q.id);
            progressed.push({ quest: q, result: r });
          }
        }
      }
    }
    return progressed;
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
