"""Self-contained HTML replay of a run: the table turn by turn, who did what,
the conversations, and the final push animated."""
from __future__ import annotations

import html
import json

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root {
  --bg: #f7f5f0; --panel: #ffffff; --ink: #1f1e1c; --muted: #6b675f; --line: #e2ddd2;
  --table: #efe9dc; --gap: #e4ebf2; --standing: #a39d90; --fallen: #23222a; --accent: #b8572e;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #17171a; --panel: #212125; --ink: #ecebe6; --muted: #a29e95; --line: #34343a;
    --table: #2a2824; --gap: #232a31; --standing: #6f6a60; --fallen: #f1efe8; --accent: #e08a5f;
  }
}
:root[data-theme="dark"] {
  --bg: #17171a; --panel: #212125; --ink: #ecebe6; --muted: #a29e95; --line: #34343a;
  --table: #2a2824; --gap: #232a31; --standing: #6f6a60; --fallen: #f1efe8; --accent: #e08a5f;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
main { max-width: 1200px; margin: 0 auto; padding: 20px 16px 40px; }
h1 { font-size: 22px; margin: 0 0 4px; }
.sub { color: var(--muted); margin-bottom: 16px; }
.layout { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: 16px; }
@media (max-width: 860px) { .layout { grid-template-columns: 1fr; } }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 12px; }
canvas { width: 100%; height: auto; display: block; border-radius: 6px; }
.controls { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-top: 10px; }
button { font: inherit; padding: 6px 12px; border-radius: 6px; border: 1px solid var(--line);
  background: var(--bg); color: var(--ink); cursor: pointer; }
button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
input[type=range] { flex: 1; min-width: 140px; accent-color: var(--accent); }
.legend { display: flex; flex-wrap: wrap; gap: 6px 14px; margin-top: 10px; font-size: 13px; color: var(--muted); }
.sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 8px; margin-top: 12px; }
.stat { background: var(--bg); border-radius: 8px; padding: 8px 10px; }
.stat b { display: block; font-size: 20px; }
.stat span { font-size: 12px; color: var(--muted); }
#side { max-height: 720px; overflow: auto; }
.who { font-weight: 600; }
.act { font-size: 13px; padding: 3px 0; border-bottom: 1px dashed var(--line); }
.convo { background: var(--bg); border-radius: 8px; padding: 8px 10px; margin: 8px 0; font-size: 14px; }
.convo .meta { font-size: 12px; color: var(--muted); margin-bottom: 4px; }
.msg { margin: 4px 0; }
.ev { font-size: 13px; color: var(--muted); }
h2 { font-size: 15px; margin: 12px 0 6px; }
</style>
</head>
<body>
<main>
  <h1>__TITLE__</h1>
  <div class="sub" id="sub"></div>
  <div class="layout">
    <div class="card">
      <canvas id="cv" width="1200" height="800"></canvas>
      <div class="controls">
        <button id="prev" aria-label="Previous turn">◀</button>
        <input id="turn" type="range" min="0" value="0" aria-label="Turn">
        <button id="next" aria-label="Next turn">▶</button>
        <button id="push" class="primary">Push</button>
        <span id="tlabel"></span>
      </div>
      <div class="legend" id="legend"></div>
      <div class="stats" id="stats"></div>
    </div>
    <div class="card" id="side"></div>
  </div>
</main>
<script>
const LOG = __DATA__;
const cv = document.getElementById('cv'), ctx = cv.getContext('2d');
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const regions = LOG.regions;
const W = Math.max(...regions.map(r => r.x1)), H = Math.max(...regions.map(r => r.y1));
const PALETTE = ['#2f6fb0','#c0563a','#3f8f5a','#8a5bb5','#c28a1f','#2a9a9a','#b44f84','#6b7d2f','#5d6bc4','#a0612f','#d0473f','#4b8f8c','#7a5c3a','#9c6ade','#3a7d2c'];
const names = LOG.agents.map(a => a.name);
const color = n => PALETTE[Math.max(0, names.indexOf(n)) % PALETTE.length];
const frames = [LOG.initial, ...LOG.turns.map(t => t.snapshot)];
let cur = frames.length - 1, anim = null;

function fit() {
  const w = cv.clientWidth || 800;
  cv.width = Math.round(w * devicePixelRatio);
  cv.height = Math.round(w * H / W * devicePixelRatio);
  draw();
}
function draw(fallenAt) {
  const s = cv.width / W;
  ctx.fillStyle = css('--panel'); ctx.fillRect(0, 0, cv.width, cv.height);
  for (const r of regions) {
    ctx.fillStyle = r.kind === 'table' ? css('--table') : css('--gap');
    ctx.fillRect(r.x0 * s, r.y0 * s, (r.x1 - r.x0) * s, (r.y1 - r.y0) * s);
    if (regions.length > 1) { ctx.fillStyle = css('--muted'); ctx.font = `${12 * devicePixelRatio}px sans-serif`;
      ctx.fillText(r.name, r.x0 * s + 6, r.y0 * s + 16 * devicePixelRatio); }
  }
  const snap = fallenAt ? LOG.push.before_push : frames[cur];
  for (const [id, x, y, a, state, builder, start] of snap) {
    const rad = a * Math.PI / 180;
    const down = fallenAt ? (state === 'down' || (LOG.push.times[id] !== undefined && LOG.push.times[id] <= fallenAt.t)) : state === 'down';
    if (down) {
      ctx.strokeStyle = fallenAt ? css('--fallen') : color(builder);
      ctx.lineWidth = Math.max(2, s * 0.3); ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(x * s, y * s); ctx.lineTo((x + .9 * Math.cos(rad)) * s, (y + .9 * Math.sin(rad)) * s); ctx.stroke();
    } else {
      const hx = -Math.sin(rad) * .25, hy = Math.cos(rad) * .25;
      ctx.strokeStyle = fallenAt ? css('--standing') : color(builder);
      ctx.lineWidth = Math.max(1.5, s * 0.12);
      ctx.beginPath(); ctx.moveTo((x - hx) * s, (y - hy) * s); ctx.lineTo((x + hx) * s, (y + hy) * s); ctx.stroke();
      if (start) { ctx.strokeStyle = css('--accent'); ctx.lineWidth = 2 * devicePixelRatio;
        ctx.beginPath(); ctx.arc(x * s, y * s, .7 * s, 0, 7); ctx.stroke(); }
    }
  }
}
function esc(s) { const d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; }
function describe(d) {
  const k = d.kind;
  if (k === 'talk') return `talks to ${Array.isArray(d.to) ? d.to.join(', ') : (d.to || 'everyone')}`;
  if (k === 'build') return `builds ${(d.strokes || []).length} stroke(s)${d.restand ? ', re-stands knocked dominoes' : ''}${d.start ? ', marks start' : ''}`;
  if (k === 'take_down') return 'takes down dominoes';
  if (k === 'inspect') return 'inspects';
  if (k === 'visit') return `visits ${d.where}`;
  return k;
}
function side() {
  const el = document.getElementById('side');
  if (cur === 0) { el.innerHTML = '<h2>Before the first turn</h2><p class="ev">Use ▶ to step through turns, or Push to watch the final push.</p>'; return; }
  const t = LOG.turns[cur - 1];
  if (t.clock !== undefined) { liveSide(el, t); return; }
  let h = `<h2>Turn ${t.turn}</h2>`;
  for (const [n, d] of Object.entries(t.decisions))
    h += `<div class="act"><span class="sw" style="background:${color(n)}"></span><span class="who">${esc(n)}</span> ${esc(describe(d))}</div>`;
  for (const c of t.conversations) {
    h += `<div class="convo"><div class="meta">${esc(c.members.join(', '))}${c.pulled_in.length ? ' · pulled in: ' + esc(c.pulled_in.join(', ')) : ''}</div>`;
    for (const m of c.messages) h += `<div class="msg"><span class="who">${esc(m.speaker)}:</span> ${esc(m.message)}</div>`;
    h += '</div>';
  }
  const ev = t.events.filter(e => e.type !== 'build' && e.type !== 'inspect');
  for (const e of ev) {
    if (e.type === 'bump') h += `<div class="ev">💥 ${esc(e.who)} bumped the table near ${esc(e.near)}: ${e.knocked} fell</div>`;
    if (e.type === 'take_down') h += `<div class="ev">✋ ${esc(e.who)} took down ${e.ids.length} (${esc(Object.entries(e.whose).map(([k,v]) => k + ': ' + v).join(', '))})</div>`;
    if (e.type === 'visit') h += `<div class="ev">👀 ${esc(e.who)} looked closely at ${esc(e.where)}</div>`;
    if (e.type === 'move') h += `<div class="ev">🚶 ${esc(e.who)} walked to ${esc(e.where)}</div>`;
  }
  el.innerHTML = h;
}
function liveDo(d) {
  const k = d.do || 'continue';
  if (k === 'build') return `starts building (${(d.strokes || []).map(s => s.type).join(', ') || 're-standing'})${d.start ? ', marks start' : ''}`;
  if (k === 'take_down') return 'starts taking down dominoes';
  if (k === 'inspect') return 'inspects';
  if (k === 'stop') return 'stops and watches';
  if (k === 'walk') return `walks to ${d.where}`;
  return 'keeps going';
}
function liveSide(el, t) {
  let h = `<h2>${esc(t.clock)}</h2>`;
  for (const [n, d] of Object.entries(t.decisions))
    h += `<div class="act"><span class="sw" style="background:${color(n)}"></span><span class="who">${esc(n)}</span> ${esc(liveDo(d))}${d.thinking ? ` <span class="ev">· ${esc(d.thinking)}</span>` : ''}</div>`;
  for (const x of (t.held || [])) h += `<div class="ev">🤐 ${esc(x.who)} held a thought; ${esc(x.yielded_to)} spoke first</div>`;
  for (const e of t.events) {
    if (e.type === 'bump') h += `<div class="ev">💥 ${esc(e.who)} bumped the table near ${esc(e.near)}: ${e.knocked} fell</div>`;
    if (e.type === 'take_down') h += `<div class="ev">✋ ${esc(e.who)} took down ${e.ids.length}</div>`;
  }
  h += '<h2>Conversation so far</h2>';
  const msgs = [];
  for (const r of LOG.turns.slice(0, cur)) for (const c of r.conversations) for (const m of c.messages)
    msgs.push([r.clock, m]);
  for (const [clk, m] of msgs.slice(-40)) {
    const to = Array.isArray(m.to) ? m.to.join(', ') : (m.to || 'everyone');
    h += `<div class="msg"><span class="ev">${esc(clk)}</span> <span class="who" style="color:${color(m.speaker)}">${esc(m.speaker)}</span> <span class="ev">→ ${esc(to)}</span>: ${esc(m.message)}</div>`;
  }
  el.innerHTML = h;
  el.scrollTop = el.scrollHeight;
}
function stats() {
  const p = LOG.push, el = document.getElementById('stats');
  let h = '';
  for (const [name, v] of Object.entries(p.per_table)) {
    h += `<div class="stat"><b>${Math.round(v.completion * 100)}%</b><span>${esc(name)}: fell from the push</span></div>`;
    h += `<div class="stat"><b>${v.placed}</b><span>${esc(name)}: dominoes placed</span></div>`;
  }
  h += `<div class="stat"><b>${p.duration.toFixed(1)} s</b><span>push duration</span></div>`;
  if (p.row_success !== null && p.row_success !== undefined) h += `<div class="stat"><b>${p.row_success ? 'Yes' : 'No'}</b><span>every picture revealed in time</span></div>`;
  el.innerHTML = h;
}
const slider = document.getElementById('turn');
slider.max = frames.length - 1;
function go(i) { if (anim) { cancelAnimationFrame(anim); anim = null; }
  cur = Math.max(0, Math.min(frames.length - 1, i)); slider.value = cur;
  const tt = cur > 0 ? LOG.turns[cur - 1] : null;
  document.getElementById('tlabel').textContent = cur === 0 ? 'start' : (tt.clock !== undefined ? tt.clock : `turn ${cur} of ${frames.length - 1}`);
  draw(); side(); }
slider.oninput = () => go(+slider.value);
document.getElementById('prev').onclick = () => go(cur - 1);
document.getElementById('next').onclick = () => go(cur + 1);
document.getElementById('push').onclick = () => {
  if (anim) cancelAnimationFrame(anim);
  const t0 = performance.now(), dur = Math.max(.5, LOG.push.duration), speed = Math.max(1, dur / 6);
  const tick = now => { const t = (now - t0) / 1000 * speed; draw({t});
    document.getElementById('tlabel').textContent = `push: ${Math.min(t, dur).toFixed(1)} s`;
    if (t < dur + .3) anim = requestAnimationFrame(tick); else anim = null; };
  anim = requestAnimationFrame(tick);
};
document.getElementById('legend').innerHTML = LOG.agents.map(a =>
  `<span><span class="sw" style="background:${color(a.name)}"></span>${esc(a.name)}</span>`).join('');
document.getElementById('sub').textContent = LOG.engine === 'live'
  ? `${LOG.agents.length} agents · ${Math.round(LOG.config.duration / 60)} minutes · round ${LOG.config.round_no}`
  : `${LOG.agents.length} agents · ${LOG.turns.length} turns · round ${LOG.config.round_no}`;
stats();
window.addEventListener('resize', fit);
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => draw());
go(cur); fit();
</script>
</body>
</html>
"""


def write_replay(log: dict, path: str, title: str = "Domino Art replay") -> str:
    data = json.dumps(log, separators=(",", ":")).replace("</", "<\\/")
    with open(path, "w") as f:
        f.write(TEMPLATE.replace("__TITLE__", html.escape(title)).replace("__DATA__", data))
    return path
