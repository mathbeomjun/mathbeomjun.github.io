// assets/flow.js — 홈페이지 상단의 곡선 그림.
// A closed curve evolving by curve shortening flow (Gage–Hamilton–Grayson):
// it becomes convex, rounds off, and shrinks to a point. Traces are kept.
// · 클릭(또는 Enter)하면 새 임의 곡선으로 다시 그립니다.
// · prefers-reduced-motion 사용자는 애니메이션 없이 최종 그림만 봅니다.
// · 조절값: TRACES(남길 단면 수), STOP_AREA(멈추는 시점의 넓이 비율), seedCurve() 의 진폭.
// · 색은 style.css 의 --oak(현재 곡선)와 --stone(단면)을 그대로 씁니다.
(function () {
  const canvas = document.getElementById("flow");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const NMAX = 240, TRACES = 13, STOP_AREA = 0.035;
  let raf = null, traces = [], pts = [], L0 = 1, A0 = 1, T = 0, nextTrace = 0, Text = 1, frameDT = 0;

  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

  function size() {
    const r = canvas.getBoundingClientRect(), d = window.devicePixelRatio || 1;
    canvas.width = Math.round(r.width * d); canvas.height = Math.round(r.height * d);
  }

  function seedCurve() {
    // a wavy embedded curve, given as a positive polar graph
    const rnd = (a, b) => a + Math.random() * (b - a);
    const k1 = 2 + Math.floor(Math.random() * 3), k2 = k1 + 1 + Math.floor(Math.random() * 3);
    const a1 = rnd(0.18, 0.3), a2 = rnd(0.08, 0.16), p1 = rnd(0, 6.28), p2 = rnd(0, 6.28);
    const out = [];
    for (let i = 0; i < NMAX; i++) {
      const t = (2 * Math.PI * i) / NMAX;
      const r = 1 + a1 * Math.sin(k1 * t + p1) + a2 * Math.sin(k2 * t + p2);
      out.push([r * Math.cos(t) * 1.08, r * Math.sin(t)]);
    }
    return out;
  }

  const length = (p) => p.reduce((s, q, i) => { const r = p[(i + 1) % p.length]; return s + Math.hypot(r[0] - q[0], r[1] - q[1]); }, 0);
  const area = (p) => Math.abs(p.reduce((s, q, i) => { const r = p[(i + 1) % p.length]; return s + q[0] * r[1] - r[0] * q[1]; }, 0)) / 2;

  function resample(p, n) {
    const m = p.length, cum = [0];
    for (let i = 0; i < m; i++) { const a = p[i], b = p[(i + 1) % m]; cum.push(cum[i] + Math.hypot(b[0] - a[0], b[1] - a[1])); }
    const L = cum[m], out = [];
    let j = 0;
    for (let k = 0; k < n; k++) {
      const s = (L * k) / n;
      while (cum[j + 1] < s) j++;
      const a = p[j], b = p[(j + 1) % m], t = (s - cum[j]) / (cum[j + 1] - cum[j] || 1);
      out.push([a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]);
    }
    return out;
  }

  function step(dtTarget) {
    let done = 0;
    while (done < dtTarget) {
      const L = length(pts);
      const n = Math.max(48, Math.min(NMAX, Math.round((NMAX * L) / L0)));
      pts = resample(pts, n);
      const h = L / n, dt = Math.min(0.24 * h * h, dtTarget - done);
      const next = pts.map((q, i) => {
        const a = pts[(i - 1 + n) % n], b = pts[(i + 1) % n];
        return [q[0] + (dt * (a[0] - 2 * q[0] + b[0])) / (h * h), q[1] + (dt * (a[1] - 2 * q[1] + b[1])) / (h * h)];
      });
      pts = next; done += dt;
    }
    T += dtTarget;
  }

  function draw() {
    const W = canvas.width, H = canvas.height, s = Math.min(W, H) * 0.34;
    ctx.clearRect(0, 0, W, H);
    const path = (p) => { ctx.beginPath(); p.forEach((q, i) => (i ? ctx.lineTo : ctx.moveTo).call(ctx, W / 2 + s * q[0], H / 2 - s * q[1])); ctx.closePath(); };
    const d = window.devicePixelRatio || 1;
    ctx.lineWidth = 1 * d; ctx.strokeStyle = css("--stone"); ctx.globalAlpha = 0.38;
    traces.forEach((t) => { path(t); ctx.stroke(); });
    ctx.globalAlpha = 1; ctx.lineWidth = 1.4 * d; ctx.strokeStyle = css("--oak");
    path(pts); ctx.stroke();
  }

  function start() {
    cancelAnimationFrame(raf);
    pts = seedCurve(); L0 = length(pts); A0 = area(pts);
    Text = A0 / (2 * Math.PI); T = 0; traces = [pts.map((q) => q.slice())];
    nextTrace = Text / TRACES; frameDT = Text / 260;
    if (reduce) {
      while (area(pts) > STOP_AREA * A0) { step(frameDT); if (T >= nextTrace) { traces.push(pts.map((q) => q.slice())); nextTrace += Text / TRACES; } }
      draw(); return;
    }
    const tick = () => {
      step(frameDT);
      if (T >= nextTrace) { traces.push(pts.map((q) => q.slice())); nextTrace += Text / TRACES; }
      draw();
      if (area(pts) > STOP_AREA * A0) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
  }

  size(); start();
  canvas.tabIndex = 0;
  canvas.addEventListener("click", start);
  canvas.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); start(); } });
  window.addEventListener("resize", () => { size(); draw(); });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", draw);
})();
