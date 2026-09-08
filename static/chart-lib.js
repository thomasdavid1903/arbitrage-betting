'use strict';

/* Shared chart primitives for both pages: SVG element creation, the tooltip
   layer, legends and formatting. Loaded before app.js / history.js. */

const SVG = 'http://www.w3.org/2000/svg';

const CSS = getComputedStyle(document.documentElement);
const C = name => CSS.getPropertyValue(name).trim();

const COLOR = {
  s1: C('--series-1'), s2: C('--series-2'), s3: C('--series-3'),
  s4: C('--series-4'), s5: C('--series-5'),
  good: C('--good'), warning: C('--warning'), critical: C('--critical'),
  line: C('--line'), lineSoft: C('--line-soft'),
  text: C('--text-primary'), sub: C('--text-secondary'), muted: C('--text-muted'),
  surface: C('--surface-1')
};

function el(tag, attrs, parent) {
  const node = document.createElementNS(SVG, tag);
  for (const k in (attrs || {})) node.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(node);
  return node;
}

function clear(svg) { while (svg.firstChild) svg.removeChild(svg.firstChild); }

const tooltip = document.getElementById('tooltip');

function showTip(evt, title, rows) {
  tooltip.innerHTML = '<div class="t-title">' + title + '</div>' +
    rows.map(r => '<div class="t-row"><span>' + r[0] + '</span><span>' + r[1] + '</span></div>').join('');
  tooltip.classList.add('show');
  moveTip(evt);
}

function moveTip(evt) {
  const pad = 14;
  let x = evt.clientX + pad, y = evt.clientY + pad;
  const box = tooltip.getBoundingClientRect();
  if (x + box.width > innerWidth - 8) x = evt.clientX - box.width - pad;
  if (y + box.height > innerHeight - 8) y = evt.clientY - box.height - pad;
  tooltip.style.left = x + 'px';
  tooltip.style.top = y + 'px';
}

function hideTip() { tooltip.classList.remove('show'); }

// Hit areas are deliberately bigger than the marks they serve.
function hit(parent, attrs, title, rows, onClick) {
  attrs.fill = 'transparent';
  const zone = el('rect', attrs, parent);
  zone.addEventListener('mouseenter', e => showTip(e, title, rows));
  zone.addEventListener('mousemove', moveTip);
  zone.addEventListener('mouseleave', hideTip);
  if (onClick) {
    zone.style.cursor = 'pointer';
    zone.addEventListener('click', onClick);
  }
  return zone;
}

function legend(id, items) {
  const node = document.getElementById(id);
  if (!node) return;
  node.innerHTML = items.map(i =>
    '<span class="item"><span class="swatch" style="background:' + i[1] + '"></span>' + i[0] + '</span>'
  ).join('');
}

function tiles(id, items) {
  document.getElementById(id).innerHTML = items.map(t =>
    '<div class="tile' + (t.good ? ' good' : '') + '">' +
      '<div class="label">' + t.label + '</div>' +
      '<div class="value">' + t.value + '</div>' +
      '<div class="sub">' + (t.sub || '') + '</div>' +
    '</div>').join('');
}

const short = (s, n) => s.length > n ? s.slice(0, n - 1) + '…' : s;

const fmtOdds = v => v.toFixed(2);

const fmtTime = iso => {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { day: '2-digit', month: 'short' }) + ' ' +
         d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
};

// Ages run from under a minute to several days, so they are shown on a log
// scale; a linear axis would pile almost every value against the origin.
function fmtMinutes(m) {
  if (m == null) return '—';
  if (m < 1) return (m * 60).toFixed(0) + 's';
  if (m < 90) return m.toFixed(0) + 'm';
  if (m < 60 * 48) return (m / 60).toFixed(1) + 'h';
  return (m / 1440).toFixed(1) + 'd';
}
