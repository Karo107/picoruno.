/* ==== KIT：BGM・効果音・保存・シェアの共通部品（各ゲームに埋め込んで使う） ==== */
const KIT = (() => {
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  };

  /* ---------- 音 ---------- */
  let ctx = null, master, musicBus, sfxBus, verb, muted = store.get("picoruno-mute", false);
  function ensure() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
      master = ctx.createGain();
      master.gain.value = muted ? 0 : 1;
      const comp = ctx.createDynamicsCompressor();
      comp.threshold.value = -16; comp.ratio.value = 4;
      master.connect(comp); comp.connect(ctx.destination);
      musicBus = ctx.createGain(); musicBus.gain.value = 0.55; musicBus.connect(master);
      sfxBus = ctx.createGain(); sfxBus.gain.value = 0.9; sfxBus.connect(master);
      // 残響（生成したインパルス応答）
      verb = ctx.createConvolver();
      const len = ctx.sampleRate * 2.2, ir = ctx.createBuffer(2, len, ctx.sampleRate);
      for (let c = 0; c < 2; c++) { const d = ir.getChannelData(c); for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 2.6); }
      verb.buffer = ir;
      const vg = ctx.createGain(); vg.gain.value = 0.32; verb.connect(vg); vg.connect(master);
    }
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  }
  const now = () => (ctx ? ctx.currentTime : 0);
  const mtof = m => 440 * Math.pow(2, (m - 69) / 12);

  /* 1音。f: 周波数, to: 終わりの周波数, t: 開始までの秒, dur: 長さ */
  function tone(o) {
    if (!ensure()) return;
    const { f = 440, to = null, t = 0, dur = 0.2, type = "sine", vol = 0.3, a = 0.005, rel = null, bus = sfxBus, wet = 0.15, lp = null, detune = 0, pan = 0 } = o;
    const s = now() + t, g = ctx.createGain(), osc = ctx.createOscillator();
    osc.type = type; osc.frequency.setValueAtTime(f, s); osc.detune.value = detune;
    if (to) osc.frequency.exponentialRampToValueAtTime(Math.max(20, to), s + dur);
    g.gain.setValueAtTime(0.0001, s);
    g.gain.linearRampToValueAtTime(vol, s + a);
    g.gain.exponentialRampToValueAtTime(0.0001, s + (rel || dur));
    let node = osc;
    if (lp) { const fl = ctx.createBiquadFilter(); fl.type = "lowpass"; fl.frequency.value = lp; node.connect(fl); node = fl; }
    node.connect(g);
    let out = g;
    if (pan && ctx.createStereoPanner) { const p = ctx.createStereoPanner(); p.pan.value = pan; g.connect(p); out = p; }
    out.connect(bus);
    if (wet) { const w = ctx.createGain(); w.gain.value = wet; out.connect(w); w.connect(verb); }
    osc.start(s); osc.stop(s + (rel || dur) + 0.05);
  }
  let noiseBuf = null;
  function noise(o) {
    if (!ensure()) return;
    const { t = 0, dur = 0.2, vol = 0.3, f = 1200, to = null, q = 0.8, type = "bandpass", a = 0.004, bus = sfxBus, wet = 0.1 } = o;
    if (!noiseBuf) { noiseBuf = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate); const d = noiseBuf.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1; }
    const s = now() + t, src = ctx.createBufferSource(), fl = ctx.createBiquadFilter(), g = ctx.createGain();
    src.buffer = noiseBuf; src.loop = true;
    fl.type = type; fl.frequency.setValueAtTime(f, s); fl.Q.value = q;
    if (to) fl.frequency.exponentialRampToValueAtTime(to, s + dur);
    g.gain.setValueAtTime(0.0001, s); g.gain.linearRampToValueAtTime(vol, s + a); g.gain.exponentialRampToValueAtTime(0.0001, s + dur);
    src.connect(fl); fl.connect(g); g.connect(bus);
    if (wet) { const w = ctx.createGain(); w.gain.value = wet; g.connect(w); w.connect(verb); }
    src.start(s, Math.random()); src.stop(s + dur + 0.05);
  }

  /* 楽器 */
  const inst = {
    epiano(m, t, d, v) { const f = mtof(m); tone({ f, t, dur: d * 1.6, vol: v, type: "sine", bus: musicBus, wet: 0.25, a: 0.004 }); tone({ f: f * 2, t, dur: 0.5, vol: v * 0.35, type: "sine", bus: musicBus, wet: 0.2 }); tone({ f: f * 3.01, t, dur: 0.18, vol: v * 0.12, type: "sine", bus: musicBus, wet: 0.1 }); },
    bell(m, t, d, v) { const f = mtof(m); tone({ f, t, dur: d * 2.2, vol: v, bus: musicBus, wet: 0.35 }); tone({ f: f * 3.98, t, dur: 0.35, vol: v * 0.25, bus: musicBus, wet: 0.35 }); },
    marimba(m, t, d, v) { const f = mtof(m); tone({ f, t, dur: 0.45, vol: v, bus: musicBus, wet: 0.2 }); tone({ f: f * 4, t, dur: 0.07, vol: v * 0.3, bus: musicBus, wet: 0.1 }); },
    pluck(m, t, d, v) { tone({ f: mtof(m), t, dur: Math.min(0.6, d * 1.2), vol: v, type: "triangle", lp: 2400, bus: musicBus, wet: 0.25 }); },
    flute(m, t, d, v) { tone({ f: mtof(m), t, dur: d * 0.95, vol: v * 0.8, type: "sine", a: 0.06, bus: musicBus, wet: 0.4 }); tone({ f: mtof(m) * 2, t, dur: d * 0.9, vol: v * 0.08, type: "triangle", a: 0.08, bus: musicBus, wet: 0.4 }); },
    chip(m, t, d, v) { tone({ f: mtof(m), t, dur: d * 0.9, vol: v * 0.45, type: "square", lp: 3000, bus: musicBus, wet: 0.08 }); },
    pad(m, t, d, v) { const f = mtof(m); for (const dt of [-7, 7]) tone({ f, t, dur: d, vol: v * 0.5, type: "sawtooth", a: d * 0.35, lp: 900, detune: dt, bus: musicBus, wet: 0.5 }); },
    koto(m, t, d, v) { const f = mtof(m); tone({ f, to: f * 0.995, t, dur: 0.9, vol: v, type: "triangle", lp: 3200, a: 0.002, bus: musicBus, wet: 0.35 }); tone({ f: f * 2, t, dur: 0.25, vol: v * 0.3, type: "sine", bus: musicBus, wet: 0.2 }); },
    bass(m, t, d, v) { tone({ f: mtof(m), t, dur: d * 0.9, vol: v, type: "triangle", lp: 600, bus: musicBus, wet: 0 }); tone({ f: mtof(m), t, dur: d * 0.9, vol: v * 0.6, type: "sine", bus: musicBus, wet: 0 }); },
    kick(t, v) { tone({ f: 130, to: 42, t, dur: 0.28, vol: v, type: "sine", bus: musicBus, wet: 0 }); },
    snare(t, v) { noise({ t, dur: 0.16, vol: v * 0.6, f: 1900, q: 0.7, bus: musicBus, wet: 0.2 }); },
    hat(t, v) { noise({ t, dur: 0.04, vol: v * 0.35, f: 8000, type: "highpass", bus: musicBus, wet: 0 }); },
    shaker(t, v) { noise({ t, dur: 0.07, vol: v * 0.25, f: 6000, q: 2, bus: musicBus, wet: 0.05 }); }
  };

  /* ---------- BGM（シード付きの自動作曲。4小節のフレーズをくりかえす） ---------- */
  function rng(seed) { let s = seed >>> 0 || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
  let song = null, timer = null, nextT = 0, step = 0;
  /* opts: {bpm, key(midi), chords:[[度数...]...], lead, chord, beat:"lofi"|"waltz"|"none"|"chip"|"shaker", seed, scale:[...], swing, leadVol, density} */
  function musicStart(opts) {
    if (!ensure()) return;
    musicStop();
    const r = rng(opts.seed || 7);
    const scale = opts.scale || [0, 2, 4, 7, 9];      // ペンタトニック
    const beats = opts.beat === "waltz" ? 3 : 4;
    const steps = beats * 4;                           // 16分音符
    // 4小節ぶんのメロディを作る（2小節目と4小節目は少し変える）
    const motif = [];
    for (let bar = 0; bar < 4; bar++) {
      const line = [];
      let deg = Math.floor(r() * scale.length);
      for (let s = 0; s < steps; s++) {
        const strong = s % 4 === 0;
        if (r() < (strong ? 0.62 : 0.2) * (opts.density || 1)) {
          deg = Math.max(0, Math.min(scale.length * 2 - 1, deg + Math.floor(r() * 5) - 2));
          const len = strong && r() < 0.5 ? 4 : 2;
          line.push({ s, deg, len });
        }
      }
      motif.push(line);
    }
    motif[2] = motif[0].map(n => ({ ...n }));          // 3小節目は1小節目のくりかえし
    song = { ...opts, beats, steps, motif, scale };
    nextT = now() + 0.1; step = 0;
    timer = setInterval(schedule, 40);
  }
  function schedule() {
    if (!song || !ctx) return;
    const spb = 60 / song.bpm, sixteenth = spb / 4;
    while (nextT < now() + 0.25) {
      const bar = Math.floor(step / song.steps), s = step % song.steps;
      const chordDegs = song.chords[bar % song.chords.length];
      const key = song.key || 60;
      const sw = (s % 2 === 1) ? (song.swing || 0) * sixteenth : 0;
      const t = nextT + sw - now();
      // コード
      if (s === 0) chordDegs.forEach((d, i) => (inst[song.chord || "epiano"])(key + d, t + i * 0.012, spb * song.beats * 0.9, (song.chordVol || 0.08)));
      if (song.beat === "waltz" && (s === 4 || s === 8)) chordDegs.slice(1).forEach(d => inst[song.chord || "epiano"](key + d, t, spb * 0.8, (song.chordVol || 0.08) * 0.6));
      // ベース
      if (song.bassOn !== false) {
        if (s === 0) inst.bass(key - 24 + chordDegs[0], t, spb * 1.8, 0.22);
        if (song.beat !== "waltz" && s === 8) inst.bass(key - 24 + chordDegs[0] + (bar % 2 ? 7 : 0), t, spb * 1.6, 0.18);
      }
      // リズム
      const bt = song.beat || "lofi";
      if (bt === "lofi") { if (s === 0 || s === 10) inst.kick(t, 0.38); if (s === 4 || s === 12) inst.snare(t, 0.25); if (s % 2 === 0) inst.hat(t, s % 4 === 2 ? 0.5 : 0.3); }
      else if (bt === "chip") { if (s % 4 === 0) inst.kick(t, 0.3); if (s === 4 || s === 12) inst.snare(t, 0.2); if (s % 2 === 1) inst.hat(t, 0.3); }
      else if (bt === "waltz") { if (s === 0) inst.kick(t, 0.25); if (s === 4 || s === 8) inst.shaker(t, 0.6); }
      else if (bt === "shaker") { if (s % 2 === 0) inst.shaker(t, s % 4 === 0 ? 0.7 : 0.4); if (s === 0) inst.kick(t, 0.2); }
      // メロディ
      if (song.lead) {
        const line = song.motif[bar % 4];
        for (const n of line) if (n.s === s) {
          const oct = Math.floor(n.deg / song.scale.length), d = song.scale[n.deg % song.scale.length];
          inst[song.lead](key + 12 + oct * 12 + d, t, sixteenth * n.len, song.leadVol || 0.1);
        }
      }
      nextT += sixteenth; step++;
    }
  }
  function musicStop() { if (timer) clearInterval(timer); timer = null; song = null; }
  function setMuted(m) {
    muted = m; store.set("picoruno-mute", m);
    if (master) master.gain.setTargetAtTime(m ? 0 : 1, ctx.currentTime, 0.05);
  }

  /* ---------- そのほか ---------- */
  function vibrate(p) { try { navigator.vibrate && navigator.vibrate(p); } catch (e) {} }
  function tweet(text, url) {
    const u = "https://twitter.com/intent/tweet?text=" + encodeURIComponent(text) + (url ? "&url=" + encodeURIComponent(url) : "");
    window.open(u, "_blank", "noopener");
  }
  async function shareImage(canvas, name, text) {
    const blob = await new Promise(r => canvas.toBlob(r, "image/png"));
    const file = new File([blob], name, { type: "image/png" });
    try {
      if (navigator.canShare && navigator.canShare({ files: [file] })) { await navigator.share({ files: [file], text }); return "shared"; }
    } catch (e) { if (e && e.name === "AbortError") return "cancel"; }
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    return "downloaded";
  }
  function loadImages(map) {
    const out = {};
    return Promise.all(Object.entries(map).map(([k, src]) => new Promise(res => {
      const im = new Image(); im.onload = () => { out[k] = im; res(); }; im.onerror = () => { out[k] = null; res(); }; im.src = src;
    }))).then(() => out);
  }

  /* 遊んだ回数を数える（トップページの ▶ 回数）。同じタブでの再読みこみは1回だけ。 */
  function countPlay(G) {
    const K = "picoruno-played:" + G;
    try { if (sessionStorage.getItem(K)) return; sessionStorage.setItem(K, "1"); } catch (e) {}
    const KEY = "sb_publishable_5hbtIPW-1y5MqsoiLC6X_A_oZMG0Z5Z";
    fetch("https://fymwlpbspigpeaoenhhp.supabase.co/rest/v1/rpc/add_play", { method: "POST", keepalive: true,
      headers: { apikey: KEY, Authorization: "Bearer " + KEY, "Content-Type": "application/json" }, body: JSON.stringify({ g: G }) })
      .then(r => { if (!r.ok) throw 0; })
      .catch(() => { try { const d = JSON.parse(localStorage.getItem("picoruno-stats") || "{}"); d[G] = d[G] || { plays: 0, likes: 0 }; d[G].plays++; localStorage.setItem("picoruno-stats", JSON.stringify(d)); } catch (e) {} });
  }

  /* セーフエリア（ノッチなど）の大きさ(px) */
  let safeEl = null;
  function safe() {
    if (!safeEl) {
      safeEl = document.createElement("div");
      safeEl.style.cssText = "position:fixed;left:0;top:0;width:0;visibility:hidden;pointer-events:none;padding-top:env(safe-area-inset-top);padding-bottom:env(safe-area-inset-bottom)";
      document.body.appendChild(safeEl);
    }
    const cs = getComputedStyle(safeEl);
    return { top: parseFloat(cs.paddingTop) || 0, bottom: parseFloat(cs.paddingBottom) || 0 };
  }

  return { bus: () => (ensure(), sfxBus), noiseBuffer: () => { ensure(); if (!noiseBuf) noise({ vol: 0.0001, dur: 0.01 }); return noiseBuf; }, safe, countPlay, store, ensure, tone, noise, inst, mtof, music: { start: musicStart, stop: musicStop }, get muted() { return muted; }, setMuted, vibrate, tweet, shareImage, loadImages, rng };
})();
