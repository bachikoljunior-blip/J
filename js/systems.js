/* =============================================================================
 * ELDRIA — systems.js
 * アイテム / 所持品 / 成長 / 世界状態 / クエスト / 会話 / 商店 / セーブ
 * ========================================================================== */
'use strict';

/* ======================= アイテム ======================= */
(function () {
  const Items = G.Items = {};
  const DB = {
    /* 消耗品 */
    potion:    { name: '回復薬',      type: 'consumable', desc: 'HPを42%回復する薬湯。',  price: 40,  sell: 15 },
    hipotion:  { name: '上回復薬',    type: 'consumable', desc: 'HPを70%回復する濃い薬。',  price: 110, sell: 40 },
    herb:      { name: '月光草',      type: 'consumable', desc: '夜光を宿す薬草。少し回復。', price: 30, sell: 8 },
    /* 素材 */
    pelt:      { name: '狼の毛皮',    type: 'material', desc: '上質な獣の毛皮。売れる。', sell: 14 },
    bone:      { name: '古びた骨',    type: 'material', desc: '骸骨の残骸。売れる。', sell: 10 },
    magicstone:{ name: '魔石',        type: 'material', desc: '仄かに光る石。高く売れる。', sell: 25 },
    cargo:     { name: '商人の積荷',  type: 'quest', desc: 'モーガンが失くした積荷。' },
    /* 武器 */
    sword_traveler: { name: '旅人の剣',   type: 'weapon', kind: 'sword', atk: 8,  desc: '使い込まれた鉄の剣。', sell: 20 },
    sword_knight:   { name: '騎士の剣',   type: 'weapon', kind: 'sword', atk: 12, desc: '王都の騎士が帯びた剣。', price: 220, sell: 80 },
    sword_fang:     { name: '狼牙の剣',   type: 'weapon', kind: 'sword', atk: 16, desc: 'フェンリルの牙から鍛えた剣。', sell: 300 },
    axe_ruin:       { name: '遺跡の戦斧', type: 'weapon', kind: 'axe',  atk: 20, desc: '古代文明の重い戦斧。', sell: 400 },
    sword_dragon:   { name: '竜断ちの剣', type: 'weapon', kind: 'sword', atk: 26, desc: '竜をも断つと謳われた聖剣。', sell: 800 },
    spear_venom:    { name: '毒針の槍',   type: 'weapon', kind: 'spear', atk: 18, desc: '砂帝の毒針から作られた槍。', sell: 350 },
    sword_wind:     { name: '風の大剣',   type: 'weapon', kind: 'sword', atk: 23, desc: '風哭の洞窟に眠っていた大剣。', sell: 600 },
    /* 防具 */
    armor_cloth:    { name: '旅人の服',     type: 'armor', def: 2,  color: 0x5d7a9a, color2: 0x3e4f63, desc: '長旅に馴染んだ服。', sell: 10 },
    armor_leather:  { name: '旅装',         type: 'armor', def: 4,  color: 0x7a6a4a, color2: 0x554832, desc: '革を重ねた旅装。', price: 180, sell: 60 },
    armor_hunter:   { name: '狩人の革鎧',   type: 'armor', def: 7,  color: 0x5a6a3a, color2: 0x3d4828, desc: '狩人に好まれる軽鎧。', price: 340, sell: 120 },
    armor_guardian: { name: '遺跡守りの鎧', type: 'armor', def: 12, color: 0x8a8478, color2: 0x5a564e, desc: '巨像の核で強化された鎧。', sell: 400 },
    armor_dragon:   { name: '竜鱗の鎧',     type: 'armor', def: 18, color: 0x4a3a52, color2: 0x2e2436, desc: '黒竜の鱗を綴った最強の鎧。', sell: 900 }
  };
  Items.get = id => DB[id];
  Items.all = () => DB;
})();

/* ======================= 所持品 ======================= */
(function () {
  const Inv = G.Inv = {};
  Inv.items = {};
  Inv.gold = 0;
  Inv.equip = { weapon: 'sword_traveler', armor: 'armor_cloth' };
  Inv.upgrades = {};          // itemId -> 強化段階 (0-5)
  Inv.upgLevel = id => Inv.upgrades[id] || 0;

  Inv.add = function (id, n) {
    Inv.items[id] = (Inv.items[id] || 0) + (n || 1);
    G.events.emit('invChange');
  };
  Inv.remove = function (id, n) {
    n = n || 1;
    if ((Inv.items[id] || 0) < n) return false;
    Inv.items[id] -= n;
    if (Inv.items[id] <= 0) delete Inv.items[id];
    G.events.emit('invChange');
    return true;
  };
  Inv.count = id => Inv.items[id] || 0;
  Inv.addGold = function (n) {
    Inv.gold += n;
    if (n > 0) G.Audio.sfx('gold');
    G.events.emit('invChange');
  };
  Inv.equipItem = function (id) {
    const it = G.Items.get(id);
    if (!it) return;
    if (it.type === 'weapon') Inv.equip.weapon = id;
    else if (it.type === 'armor') Inv.equip.armor = id;
    else return;
    G.Audio.sfx('ui');
    G.Player.buildRig();
    G.events.emit('invChange');
  };
})();

/* ======================= 成長 ======================= */
(function () {
  const S = G.Stats = {};
  S.level = 1;
  S.xp = 0;

  S.xpNeed = function (lv) { return Math.round(50 * Math.pow(lv || S.level, 1.4)); };
  S.maxHp = () => 96 + S.level * 14;
  S.maxSta = () => 92 + S.level * 8;
  S.atk = function () {
    const w = G.Items.get(G.Inv.equip.weapon);
    return (w ? w.atk : 5) + (S.level - 1) * 2 + G.Inv.upgLevel(G.Inv.equip.weapon) * 2;
  };
  S.def = function () {
    const a = G.Items.get(G.Inv.equip.armor);
    return (a ? a.def : 0) + Math.floor((S.level - 1) * 0.6) + G.Inv.upgLevel(G.Inv.equip.armor);
  };
  S.addXP = function (n) {
    S.xp += n;
    G.events.emit('xpGain', n);
    while (S.xp >= S.xpNeed()) {
      S.xp -= S.xpNeed();
      S.level++;
      G.Player.hp = Math.min(S.maxHp(), G.Player.hp + Math.round(S.maxHp() * 0.4));
      G.Player.stamina = S.maxSta();
      G.Audio.sfx('levelup');
      G.UI.toast('レベルアップ！ Lv.' + S.level, 'gold');
      G.events.emit('levelup', S.level);
      G.FX.burst(G.Player.pos.x, G.Player.pos.y + 1, G.Player.pos.z,
        { n: 24, color: 0xffdd44, speed: 3, up: 1.5, gravity: -2, life: 1.0, size: 3.5 });
    }
  };
})();

/* ======================= 世界状態 ======================= */
(function () {
  G.State = {
    tod: 9.5,          // 時刻 0-24
    day: 1,
    weather: 0,        // 0=晴 1=雨 (現在値)
    weatherTarget: 0,
    weatherTimer: 180,
    bossKilled: {},
    openedChests: {},
    herbs: {},
    shrines: {},       // 灯した祠
    respawn: 'shrine1',
    mainStage: 0,      // 進行度 (表示用)
    cleared: false,    // 黒竜討伐済み
    playtime: 0,
    titles: {},        // 獲得した称号
    killCount: 0
  };
})();

/* ======================= クエスト ======================= */
(function () {
  const Q = G.Quests = {};

  const DEFS = {
    main1: { name: '目覚めの村',   desc: '長老ハルドと話す', main: true, mark: { x: 2, z: -17 } },
    main2: { name: '森の脅威',     desc: '西の森の白狼王フェンリルを討つ', main: true, boss: 'fenrir',
             reward: { gold: 200, items: { sword_fang: 1 } }, mark: { x: -430, z: -140 } },
    main3: { name: '遺跡の巨像',   desc: '東の遺跡に眠る巨像を倒す', main: true, boss: 'golem',
             reward: { gold: 300, items: { armor_guardian: 1 } }, mark: { x: 430, z: -80 } },
    main4: { name: '黒竜討伐',     desc: '北の頂に座す黒竜ヴァルドレクを討つ', main: true, boss: 'dragon',
             reward: { gold: 1000, items: { armor_dragon: 1 } }, final: true, mark: { x: -40, z: -640 } },
    side_herb:  { name: '月光草の採取', desc: '月光草を5本集めてリナに届ける', giver: 'healer',
                  collect: 'herb', count: 5, reward: { gold: 120, items: { hipotion: 2 } } },
    side_wolf:  { name: '狼狩り',       desc: '野狼を6匹狩ってガルドに報告する', giver: 'hunter',
                  kill: 'wolf', count: 6, reward: { gold: 150, items: { potion: 2 } } },
    side_cargo: { name: '失われた積荷', desc: '南の廃墟から積荷を持ち帰る', giver: 'merchant',
                  fetch: 'cargo', reward: { gold: 250 }, mark: { x: 150, z: 430 } },
    side_bandit: { name: '盗賊退治', desc: '街道を荒らす盗賊を5人倒しモーガンに報告', giver: 'merchant',
                  kill: 'bandit', count: 5, reward: { gold: 260, items: { hipotion: 2 } }, mark: { x: -150, z: 250 } },
    side_scorp: { name: '砂漠の異変', desc: '砂丘の主・砂帝スコルグを討つ', giver: 'hunter',
                  boss: 'scorpking', reward: { gold: 500, items: { spear_venom: 1 } }, mark: { x: 390, z: 380 } },
    side_cave: { name: '風哭の洞窟', desc: '山麓の洞窟の最深部で風の大剣を見つける', giver: 'elder',
                  fetch: 'sword_wind', reward: { gold: 400 }, mark: { x: -260, z: -360 } }
  };
  Q.DEFS = DEFS;
  Q.state = {};   // id -> {status:'active'|'ready'|'done', progress}

  Q.start = function (id) {
    if (Q.state[id]) return;
    Q.state[id] = { status: 'active', progress: 0 };
    const D = DEFS[id];
    // 対象アイテムを既に持っている場合は即「報告待ち」に
    if (D.fetch && G.Inv.count(D.fetch) > 0) Q.state[id].status = 'ready';
    if (D.collect && G.Inv.count(D.collect) >= D.count) Q.state[id].status = 'ready';
    G.UI.toast('クエスト開始: ' + D.name, 'quest');
    G.Audio.sfx('uiOpen');
    G.events.emit('questChange');
    // 対象ボスを既に討伐済みなら即完了 (順序破り対策)
    if (D.boss && G.State.bossKilled[D.boss]) Q.complete(id);
  };

  Q.isActive = id => Q.state[id] && Q.state[id].status === 'active';
  Q.isReady = id => Q.state[id] && Q.state[id].status === 'ready';
  Q.isDone = id => Q.state[id] && Q.state[id].status === 'done';

  Q.complete = function (id) {
    const st = Q.state[id];
    if (!st || st.status === 'done') return;
    st.status = 'done';
    const D = DEFS[id];
    G.UI.toast('クエスト達成: ' + D.name, 'gold');
    G.Audio.sfx('questDone');
    if (D.reward) {
      if (D.reward.gold) G.Inv.addGold(D.reward.gold);
      if (D.reward.items) {
        for (const k in D.reward.items) {
          G.Inv.add(k, D.reward.items[k]);
          G.UI.toast(G.Items.get(k).name + ' を手に入れた', 'gold');
        }
      }
    }
    if (D.main) {
      G.State.mainStage++;
      // 次のメインクエスト
      const order = ['main1', 'main2', 'main3', 'main4'];
      const idx = order.indexOf(id);
      if (idx >= 0 && idx < order.length - 1) Q.start(order[idx + 1]);
    }
    if (D.final) {
      G.State.cleared = true;
      G.events.emit('gameClear');
    }
    G.events.emit('questChange');
  };

  /* 進行中クエストの表示用リスト */
  Q.trackerLines = function () {
    const out = [];
    for (const id in Q.state) {
      const st = Q.state[id];
      if (st.status === 'done') continue;
      const D = DEFS[id];
      let line = D.name;
      if (D.kill) line += ` (${Math.min(st.progress, D.count)}/${D.count})`;
      else if (D.collect) line += ` (${Math.min(G.Inv.count(D.collect), D.count)}/${D.count})`;
      if (st.status === 'ready') line += ' — 報告する';
      // 目標地点 (ready なら村へ報告)
      const mk = st.status === 'ready' ? { x: 0, z: 0 } : (D.mark || null);
      out.push({ id, line, main: !!D.main, ready: st.status === 'ready',
                 desc: st.status === 'ready' ? '依頼主に報告しよう' : D.desc,
                 mx: mk ? mk.x : null, mz: mk ? mk.z : null });
    }
    out.sort((a, b) => (b.main ? 1 : 0) - (a.main ? 1 : 0));
    return out;
  };

  /* マップに出すマーカー */
  Q.marks = function () {
    const out = [];
    for (const id in Q.state) {
      const st = Q.state[id];
      if (st.status === 'done') continue;
      const D = DEFS[id];
      if (st.status === 'active' && D.mark) out.push({ x: D.mark.x, z: D.mark.z, name: D.name });
      if (st.status === 'ready') out.push({ x: 0, z: 0, name: '村へ報告' });
    }
    return out;
  };

  /* イベント連携 */
  G.events.on('kill', d => {
    for (const id in Q.state) {
      const st = Q.state[id], D = DEFS[id];
      if (st.status !== 'active' || !D.kill) continue;
      if (D.kill === d.type) {
        st.progress++;
        if (st.progress >= D.count) {
          st.status = 'ready';
          G.UI.toast(D.name + ': 達成！ 依頼主に報告しよう', 'quest');
          G.Audio.sfx('questDone');
        }
        G.events.emit('questChange');
      }
    }
  });

  G.events.on('collect', d => {
    for (const id in Q.state) {
      const st = Q.state[id], D = DEFS[id];
      if (st.status !== 'active') continue;
      if (D.collect === d.id && G.Inv.count(D.collect) >= D.count) {
        st.status = 'ready';
        G.UI.toast(D.name + ': 集まった！ リナに届けよう', 'quest');
        G.Audio.sfx('questDone');
        G.events.emit('questChange');
      }
      if (D.fetch === d.id) {
        st.status = 'ready';
        G.UI.toast(D.name + ': 積荷を見つけた！', 'quest');
        G.Audio.sfx('questDone');
        G.events.emit('questChange');
      }
    }
  });

  G.events.on('bossKilled', bossId => {
    for (const id in Q.state) {
      const st = Q.state[id], D = DEFS[id];
      if (st.status === 'active' && D.boss === bossId) Q.complete(id);
    }
  });
})();

/* ======================= 会話 ======================= */
(function () {
  const D = G.Dialogue = {};
  const Q = G.Quests;

  /* NPC ごとに現在の状況に応じた会話ツリーを生成 */
  D.build = function (npcId) {
    switch (npcId) {
      case 'elder': {
        if (Q.isActive('main1')) {
          return {
            text: 'おお、目を覚ましたか、旅の方。ここはミストヴェイル村。……この大地エルドリアは今、北の頂に巣食う黒竜ヴァルドレクの呪いで魔物に溢れておる。',
            options: [
              { label: '詳しく聞く', next: {
                text: '竜を討つには、まず力を付けねばならん。西の森の白狼王、東の遺跡の巨像……奴らを越えた者だけが、竜の頂に立てる。頼めるか、旅の方よ。',
                options: [
                  { label: '引き受ける', action: () => { Q.complete('main1'); }, closeText: '感謝する。まずは西の森じゃ。祠を灯せば、力尽きてもそこへ戻れる。' },
                  { label: '考えておく', close: true }
                ]
              } },
              { label: '立ち去る', close: true }
            ]
          };
        }
        if (Q.isActive('main2')) return { text: '西の森の奥、静寂の空き地に白狼王フェンリルがおる。突進は横に転がってかわすのじゃ。', options: [{ label: '分かった', close: true }] };
        if (Q.isActive('main3')) return { text: '東の遺跡の巨像は岩の拳を振るう。懐に入り、攻撃の後の隙を突け。', options: [{ label: '分かった', close: true }] };
        if (Q.isActive('main4')) return { text: '北の頂へは山麓の祠から登るがよい。竜の炎は地を這う……走り続けよ。そなたに風の加護があらんことを。', options: [{ label: '行ってくる', close: true }] };
        if (!Q.state['side_cave'] && G.State.mainStage >= 3) {
          return {
            text: 'そういえば……北西の山麓に「風哭の洞窟」と呼ばれる古い坑道がある。風の唸る奥底に、古の大剣が眠っておるそうじゃ。腕に覚えがあるなら行ってみるがよい。',
            options: [
              { label: '探索する', action: () => Q.start('side_cave'), closeText: '洞窟の入り口は山麓の祠の南東じゃ。中は暗い。魔物に気をつけよ。' },
              { label: 'また今度', close: true }
            ]
          };
        }
        if (Q.isReady('side_cave')) {
          return {
            text: 'おお、それが風の大剣か……! 見事じゃ。剣はそなたが持つがよい。これは褒美じゃ。',
            options: [{ label: '受け取る', action: () => Q.complete('side_cave'), close: true }]
          };
        }
        if (G.State.cleared) return { text: 'そなたが黒竜を討ったと聞いた時、村中が歓声に沸いたわい。エルドリアの英雄よ、この村はいつでもそなたの家じゃ。', options: [{ label: 'ありがとう', close: true }] };
        return { text: '風が穏やかじゃな……。', options: [{ label: '立ち去る', close: true }] };
      }
      case 'healer': {
        if (!Q.state['side_herb'] && G.State.mainStage >= 1) {
          return {
            text: 'あなたが長老の言っていた旅人さんね。私はリナ、薬師をしています。……お願いがあるの。夜に光る月光草を5本、集めてもらえないかしら?',
            options: [
              { label: '引き受ける', action: () => Q.start('side_herb'), closeText: 'ありがとう! 草原や森の光る草を探してみて。摘んだら私に届けてね。' },
              { label: 'また今度', close: true }
            ]
          };
        }
        if ((Q.isReady('side_herb') || Q.isActive('side_herb')) && G.Inv.count('herb') >= Q.DEFS.side_herb.count) {
          return {
            text: 'まあ、こんなに立派な月光草……! 本当にありがとう。お礼にこの薬を持っていって。',
            options: [{ label: '渡す', action: () => {
              if (G.Inv.remove('herb', Q.DEFS.side_herb.count)) Q.complete('side_herb');
            }, close: true }]
          };
        }
        if (Q.isReady('side_herb') || Q.isActive('side_herb')) return { text: '月光草は暗くなると淡く光るわ。草原を探してみて。5本必要よ。', options: [{ label: '分かった', close: true }] };
        return {
          text: '怪我はない? 疲れたらここで休んでいってね。',
          options: [
            { label: '休ませてもらう (全回復)', action: () => { G.Player.heal(9999); G.Player.stamina = G.Stats.maxSta(); }, closeText: 'はい、これで大丈夫。気をつけてね。' },
            { label: '大丈夫', close: true }
          ]
        };
      }
      case 'merchant': {
        const opts = [];
        if (!Q.state['side_cargo'] && G.State.mainStage >= 1) {
          opts.push({
            label: '困りごとを聞く',
            next: {
              text: '実はな、南の廃墟のあたりで盗賊に襲われて積荷を捨てて逃げてきたんだ。取り戻してくれたら礼は弾むぜ。',
              options: [
                { label: '引き受ける', action: () => Q.start('side_cargo'), closeText: '恩に着るよ! 南の廃墟だ、気をつけてな。' },
                { label: 'また今度', close: true }
              ]
            }
          });
        }
        if (Q.isReady('side_cargo') && G.Inv.count('cargo') > 0) {
          return {
            text: 'おお! それは俺の積荷じゃないか! あんた、命の恩人だ!',
            options: [{ label: '積荷を渡す', action: () => { G.Inv.remove('cargo', 1); Q.complete('side_cargo'); }, close: true }]
          };
        }
        if (!Q.state['side_bandit'] && G.State.mainStage >= 2) {
          opts.push({
            label: '盗賊の噂を聞く',
            next: {
              text: '最近、街道に盗賊が出て仕入れが滞ってるんだ。5人ばかり懲らしめてくれたら礼をするぜ。西と東の草原に焚き火の野営地がある。',
              options: [
                { label: '引き受ける', action: () => Q.start('side_bandit'), closeText: '頼んだぜ! 奴ら結構腕が立つから気をつけな。' },
                { label: 'また今度', close: true }
              ]
            }
          });
        }
        if (Q.isReady('side_bandit')) {
          return {
            text: 'おお、盗賊どもが逃げ出したって噂だ! あんたのおかげだな。これは約束の礼だ。',
            options: [{ label: '受け取る', action: () => Q.complete('side_bandit'), close: true }]
          };
        }
        opts.unshift({ label: '買い物をする', action: () => G.UI.openShop(), close: true });
        opts.push({ label: '立ち去る', close: true });
        return { text: 'いらっしゃい! 旅の必需品ならなんでも揃うぜ。', options: opts };
      }
      case 'smith': {
        return {
          text: 'おう、旅の人か。俺はドヴァン、鍛冶師だ。魔石と素材があれば装備を鍛えてやるぜ。+5まで強化できる。',
          options: [
            { label: '装備を強化する', action: () => G.UI.openForge(), close: true },
            { label: 'コツを聞く', next: {
              text: '魔石は岩の子鬼や骸骨がよく落とす。毛皮や骨も無駄にするなよ。強化は攻撃+2、防御+1ずつ効いてくる。',
              options: [{ label: '参考になった', close: true }]
            } },
            { label: '立ち去る', close: true }
          ]
        };
      }
      case 'hunter': {
        if (!Q.state['side_wolf'] && G.State.mainStage >= 1) {
          return {
            text: '俺はガルド、この村の狩人だ。最近、野狼が増えすぎて家畜が危ねえ。6匹ばかり間引いてくれねえか?',
            options: [
              { label: '引き受ける', action: () => Q.start('side_wolf'), closeText: '助かるぜ。奴らは森や草原をうろついてる。夜は物騒だから気をつけな。' },
              { label: 'また今度', close: true }
            ]
          };
        }
        if (Q.isReady('side_wolf')) {
          return {
            text: 'おう、見事な狩りっぷりだったってな! これは約束の礼だ。',
            options: [{ label: '受け取る', action: () => Q.complete('side_wolf'), close: true }]
          };
        }
        if (Q.isActive('side_wolf')) return { text: '狼どもは群れる前に仕留めるんだ。回避は転がりが基本だぜ。', options: [{ label: '分かった', close: true }] };
        if (Q.isDone('side_wolf') && !Q.state['side_scorp']) {
          return {
            text: '南東の砂漠で、馬鹿でかいサソリが隊商を襲ってるらしい。「砂帝スコルグ」……訛った名だが奴は本物の化物だ。挑むか?',
            options: [
              { label: '討伐を引き受ける', action: () => Q.start('side_scorp'), closeText: '砂丘の廃墟に巣があるそうだ。突進は横っ飛びでかわせ。生きて帰れよ。' },
              { label: 'また今度', close: true }
            ]
          };
        }
        if (Q.isActive('side_scorp')) return { text: 'スコルグは砂丘の廃墟だ。尻尾の一撃は喰らうな。', options: [{ label: '分かった', close: true }] };
        return { text: '戦いのコツか? 敵が構えたら転がって背後を取れ。あとはスタミナ管理だな。', options: [{ label: '参考になった', close: true }] };
      }
    }
    return { text: '……', options: [{ label: '立ち去る', close: true }] };
  };

  D.start = function (npc) {
    G.events.emit('talk', npc.id);
    G.UI.showDialogue(npc.name, D.build(npc.id));
  };
})();

/* ======================= 称号 (実績) ======================= */
(function () {
  const A = G.Achieve = {};
  const DEFS = {
    first_kill: { name: '初陣',         desc: '初めて魔物を倒した' },
    kills_100:  { name: '百戦錬磨',     desc: '魔物を100体倒した' },
    all_shrines:{ name: '導きの灯',     desc: '全ての祠を灯した' },
    lv10:       { name: '熟達の旅人',   desc: 'レベル10に到達した' },
    boss_first: { name: '狩人の証',     desc: '初めてボスを討伐した' },
    all_bosses: { name: '大地の守護者', desc: '全てのボスを討伐した' },
    cave:       { name: '風を断つ者',   desc: '風の大剣を手に入れた' },
    clear:      { name: '竜殺し',       desc: '黒竜ヴァルドレクを討った' },
    upgrade5:   { name: '名工の相棒',   desc: '装備を+5まで強化した' }
  };
  A.DEFS = DEFS;
  A.earn = function (id) {
    if (!DEFS[id] || G.State.titles[id]) return;
    G.State.titles[id] = true;
    G.UI.toast('称号獲得 「' + DEFS[id].name + '」', 'gold');
    G.Audio.sfx('questDone');
  };
  G.events.on('kill', () => {
    G.State.killCount = (G.State.killCount || 0) + 1;
    A.earn('first_kill');
    if (G.State.killCount >= 100) A.earn('kills_100');
  });
  G.events.on('bossKilled', id => {
    A.earn('boss_first');
    if (id === 'dragon') A.earn('clear');
    if (['fenrir', 'golem', 'scorpking', 'dragon'].every(b => G.State.bossKilled[b])) A.earn('all_bosses');
  });
  G.events.on('collect', d => { if (d.id === 'sword_wind') A.earn('cave'); });
  G.events.on('shrineLit', () => {
    if (Object.keys(G.State.shrines).length >= G.World.shrines.length) A.earn('all_shrines');
  });
  G.events.on('levelup', lv => { if (lv >= 10) A.earn('lv10'); });
  G.events.on('upgraded', d => { if (d.lvl >= 5) A.earn('upgrade5'); });
})();

/* ======================= 鍛冶 (強化) ======================= */
(function () {
  const F = G.Forge = {};
  /* 段階 lvl→lvl+1 のコスト */
  F.cost = function (lvl) {
    return {
      gold: [80, 180, 320, 500, 750][lvl] || 9999,
      mats: [
        { magicstone: 1 },
        { magicstone: 2 },
        { magicstone: 3, bone: 2 },
        { magicstone: 4, pelt: 3 },
        { magicstone: 6, bone: 3, pelt: 3 }
      ][lvl] || {}
    };
  };
  F.canUpgrade = function (id) {
    const lvl = G.Inv.upgLevel(id);
    if (lvl >= 5) return { ok: false, reason: '最大強化済み' };
    const c = F.cost(lvl);
    if (G.Inv.gold < c.gold) return { ok: false, reason: 'ゴールド不足', cost: c };
    for (const m in c.mats) {
      if (G.Inv.count(m) < c.mats[m]) return { ok: false, reason: G.Items.get(m).name + ' 不足', cost: c };
    }
    return { ok: true, cost: c };
  };
  F.upgrade = function (id) {
    const r = F.canUpgrade(id);
    if (!r.ok) { G.UI.toast(r.reason); return false; }
    G.Inv.gold -= r.cost.gold;
    for (const m in r.cost.mats) G.Inv.remove(m, r.cost.mats[m]);
    G.Inv.upgrades[id] = G.Inv.upgLevel(id) + 1;
    G.events.emit('upgraded', { id, lvl: G.Inv.upgrades[id] });
    G.Audio.sfx('clang');
    G.Audio.sfx('levelup');
    const it = G.Items.get(id);
    G.UI.toast(it.name + ' を +' + G.Inv.upgrades[id] + ' に強化した', 'gold');
    G.events.emit('invChange');
    return true;
  };
})();

/* ======================= 商店 ======================= */
(function () {
  const Shop = G.Shop = {};
  Shop.stock = ['potion', 'hipotion', 'sword_knight', 'armor_leather', 'armor_hunter'];

  Shop.buy = function (id) {
    const it = G.Items.get(id);
    if (!it || !it.price) return false;
    if (G.Inv.gold < it.price) { G.UI.toast('ゴールドが足りない…'); return false; }
    G.Inv.gold -= it.price;
    G.Inv.add(id, 1);
    G.Audio.sfx('gold');
    G.UI.toast(it.name + ' を購入した');
    return true;
  };

  Shop.sell = function (id) {
    const it = G.Items.get(id);
    if (!it || !it.sell) return false;
    // 装備中の最後の1個は売れない
    if ((G.Inv.equip.weapon === id || G.Inv.equip.armor === id) && G.Inv.count(id) <= 1) {
      G.UI.toast('装備中の品は売れない');
      return false;
    }
    if (!G.Inv.remove(id, 1)) return false;
    G.Inv.addGold(it.sell);
    return true;
  };
})();

/* ======================= セーブ / ロード ======================= */
(function () {
  const S = G.Save = {};
  const KEY = 'eldria_save_v1';

  S.exists = function () {
    try { return !!localStorage.getItem(KEY); } catch (e) { return false; }
  };

  S.save = function () {
    try {
      const p = G.Player;
      const data = {
        v: 1,
        stats: { level: G.Stats.level, xp: G.Stats.xp },
        hp: p.hp, sta: p.stamina,
        pos: { x: Math.round(p.pos.x * 10) / 10, z: Math.round(p.pos.z * 10) / 10 },
        inv: G.Inv.items, gold: G.Inv.gold, equip: G.Inv.equip,
        quests: G.Quests.state,
        horse: { x: Math.round(G.Horse.pos.x), z: Math.round(G.Horse.pos.z) },
        upg: G.Inv.upgrades,
        state: {
          tod: G.State.tod, day: G.State.day,
          bossKilled: G.State.bossKilled,
          openedChests: G.State.openedChests,
          herbs: G.State.herbs,
          shrines: G.State.shrines,
          respawn: G.State.respawn,
          mainStage: G.State.mainStage,
          cleared: G.State.cleared,
          playtime: G.State.playtime,
          titles: G.State.titles,
          killCount: G.State.killCount
        }
      };
      localStorage.setItem(KEY, JSON.stringify(data));
      return true;
    } catch (e) { return false; }
  };

  S.load = function () {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (e) { return null; }
  };

  S.apply = function (data) {
    G.Stats.level = data.stats.level;
    G.Stats.xp = data.stats.xp;
    G.Inv.items = data.inv || {};
    G.Inv.gold = data.gold || 0;
    G.Inv.equip = data.equip || { weapon: 'sword_traveler', armor: 'armor_cloth' };
    G.Quests.state = data.quests || {};
    Object.assign(G.State, data.state || {});
    const p = G.Player;
    p.hp = Math.min(data.hp || G.Stats.maxHp(), G.Stats.maxHp());
    p.stamina = Math.min(data.sta || G.Stats.maxSta(), G.Stats.maxSta());
    if (data.pos) {
      p.pos.set(data.pos.x, G.World.heightAt(data.pos.x, data.pos.z), data.pos.z);
    }
    if (data.horse) G.Horse.teleport(data.horse.x, data.horse.z);
    G.Inv.upgrades = data.upg || {};
  };

  S.reset = function () {
    try { localStorage.removeItem(KEY); } catch (e) {}
  };

  S.newGame = function () {
    G.Stats.level = 1; G.Stats.xp = 0;
    G.Inv.items = { potion: 3 };
    G.Inv.gold = 50;
    G.Inv.equip = { weapon: 'sword_traveler', armor: 'armor_cloth' };
    G.Inv.upgrades = {};
    G.Quests.state = {};
    G.State.tod = 9.5; G.State.day = 1;
    G.State.bossKilled = {}; G.State.openedChests = {};
    G.State.herbs = {}; G.State.shrines = {};
    G.State.respawn = 'shrine1';
    G.State.mainStage = 0; G.State.cleared = false; G.State.playtime = 0;
    G.State.titles = {}; G.State.killCount = 0;
    const p = G.Player;
    p.hp = G.Stats.maxHp();
    p.stamina = G.Stats.maxSta();
    p.pos.set(6, G.World.heightAt(6, 34), 34);
    G.Quests.start('main1');
  };
})();
