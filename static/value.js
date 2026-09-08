'use strict';

/* Value bets: computed from the last scan's raw markets, so this page costs
   no requests. */

let DATA = null;

const pct = v => (v * 100).toFixed(2) + '%';

const esc = s => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

function currentSport() {
  const picked = document.querySelector('input[name="sport"]:checked');
  return picked ? picked.value : 'football';
}

function rowsFor(data) {
  const onlyStandard = document.getElementById('only-standard').checked;
  return onlyStandard ? data.rows.filter(r => r.ruleRisk === 'standard') : data.rows;
}

/* ---------------- chart 1: value per bookmaker ---------------- */

function drawBooks(rows) {
  const svg = document.getElementById('chart-books');
  clear(svg);
  if (!rows.length) return;

  const tally = new Map();
  rows.forEach(r => {
    if (!tally.has(r.book)) tally.set(r.book, []);
    tally.get(r.book).push(r.edge);
  });
  const books = Array.from(tally.entries())
    .map(e => ({
      book: e[0], count: e[1].length,
      mean: e[1].reduce((a, b) => a + b, 0) / e[1].length,
      best: Math.max.apply(null, e[1])
    }))
    .sort((a, b) => b.count - a.count);

  const rowH = 30, padL = 104, padR = 92, padT = 10, padB = 34;
  const w = Math.max(svg.clientWidth || 520, 420);
  const h = padT + books.length * rowH + padB;
  svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
  svg.setAttribute('height', h);

  const plotW = w - padL - padR;
  const max = Math.max.apply(null, books.map(b => b.count));

  for (let i = 0; i <= 4; i++) {
    const x = padL + plotW * (i / 4);
    el('line', { x1: x, x2: x, y1: padT, y2: h - padB, stroke: COLOR.lineSoft }, svg);
    el('text', { x: x, y: h - padB + 16, fill: COLOR.muted, 'font-size': 10, 'text-anchor': 'middle' }, svg)
      .textContent = Math.round(max * i / 4);
  }
  el('text', { x: padL + plotW / 2, y: h - 6, fill: COLOR.muted, 'font-size': 10, 'text-anchor': 'middle', 'letter-spacing': '.1em' }, svg)
    .textContent = 'VALUE PRICES FOUND';

  books.forEach((b, i) => {
    const y = padT + i * rowH, barH = 14;
    const width = (b.count / max) * plotW;
    el('rect', {
      x: padL, y: y + (rowH - barH) / 2, width: Math.max(width, 2), height: barH,
      rx: 4, fill: COLOR.s1, opacity: 0.85
    }, svg);
    el('text', { x: padL - 12, y: y + rowH / 2 + 4, fill: COLOR.sub, 'font-size': 11, 'text-anchor': 'end' }, svg)
      .textContent = b.book;
    el('text', { x: padL + width + 10, y: y + rowH / 2 + 4, fill: COLOR.muted, 'font-size': 10.5 }, svg)
      .textContent = b.count + '  ·  +' + pct(b.mean);

    hit(svg, { x: 0, y: y, width: w, height: rowH }, b.book, [
      ['Value prices', b.count],
      ['Mean edge', '+' + pct(b.mean)],
      ['Best edge', '+' + pct(b.best)]
    ]);
  });
}

/* ---------------- chart 2: edge distribution ---------------- */

function drawDistribution(rows) {
  const svg = document.getElementById('chart-dist');
  clear(svg);
  if (!rows.length) return;

  const values = rows.map(r => r.edge);
  const lo = Math.min.apply(null, values);
  const hi = Math.max.apply(null, values);
  const bins = 22, width = (hi - lo) / bins || 1;
  const counts = new Array(bins).fill(0);
  values.forEach(v => counts[Math.min(bins - 1, Math.floor((v - lo) / width))]++);

  const w = Math.max(svg.clientWidth || 520, 420), h = 258;
  const padL = 40, padR = 14, padT = 14, padB = 42;
  svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
  svg.setAttribute('height', h);
  const plotW = w - padL - padR, plotH = h - padT - padB;

  const max = Math.max.apply(null, counts);
  const Y = c => padT + plotH - (c / max) * plotH;

  for (let i = 0; i <= 4; i++) {
    const yy = padT + plotH * (i / 4);
    el('line', { x1: padL, x2: w - padR, y1: yy, y2: yy, stroke: COLOR.lineSoft }, svg);
    el('text', { x: padL - 8, y: yy + 4, fill: COLOR.muted, 'font-size': 10, 'text-anchor': 'end' }, svg)
      .textContent = Math.round(max * (1 - i / 4));
  }

  const barW = plotW / bins;
  counts.forEach((c, i) => {
    if (!c) return;
    const binLo = lo + i * width;
    el('rect', {
      x: padL + i * barW + 1, y: Y(c), width: Math.max(barW - 2, 1), height: padT + plotH - Y(c),
      rx: 4, fill: COLOR.s1, opacity: 0.88
    }, svg);
    hit(svg, { x: padL + i * barW, y: padT, width: barW, height: plotH },
      'Edge +' + pct(binLo) + ' to +' + pct(binLo + width),
      [['Prices', c], ['Share', (100 * c / values.length).toFixed(1) + '%']]);
  });

  [lo, (lo + hi) / 2, hi].forEach((v, i) => {
    el('text', {
      x: padL + plotW * (i / 2), y: h - padB + 16, fill: COLOR.muted, 'font-size': 10,
      'text-anchor': i === 0 ? 'start' : i === 2 ? 'end' : 'middle'
    }, svg).textContent = '+' + pct(v);
  });
  el('text', { x: padL + plotW / 2, y: h - 6, fill: COLOR.muted, 'font-size': 10, 'text-anchor': 'middle', 'letter-spacing': '.1em' }, svg)
    .textContent = 'EDGE OVER FAIR ODDS';
}

/* ---------------- table ---------------- */

function drawTable(rows) {
  const body = document.querySelector('#table tbody');
  body.innerHTML = rows.slice(0, 60).map(r => {
    const book = r.link
      ? '<a class="book-link" href="' + esc(r.link) + '" target="_blank" rel="noopener noreferrer">' +
        esc(r.book) + (r.deepLink ? ' ↗' : ' (fixture) ↗') + '</a>'
      : '<span class="book">' + esc(r.book) + '</span>';
    const rules = r.ruleRisk === 'standard' ? '<span class="pill ok">standard</span>'
      : r.ruleRisk === 'divergent' ? '<span class="pill risk">rules differ</span>'
      : '<span class="pill near">unchecked</span>';
    return '<tr>' +
      '<td>' + esc(r.marketName) + (r.handicap ? ' <span class="book">(' + r.handicap + ')</span>' : '') + '</td>' +
      '<td>' + esc(r.outcome) + '</td>' +
      '<td class="book">' + esc((r.home || '') + ' v ' + (r.away || '')) + '</td>' +
      '<td>' + book + '</td>' +
      '<td class="num">' + r.price.toFixed(2) + '</td>' +
      '<td class="num book">' + r.fairPrice.toFixed(2) + '</td>' +
      '<td class="num" style="color:var(--good)">+' + pct(r.edge) + '</td>' +
      '<td class="num book">' + (r.kelly * 100).toFixed(1) + '%</td>' +
      '<td class="num book">' + (r.limit ? '£' + Math.round(r.limit) : '—') + '</td>' +
      '<td>' + rules + '</td>' +
    '</tr>';
  }).join('');
}

/* ---------------- render ---------------- */

function render(data) {
  DATA = data;
  const rows = rowsFor(data);
  const s = data.summary;
  const mean = rows.length ? rows.reduce((a, r) => a + r.edge, 0) / rows.length : 0;

  tiles('tiles', [
    { label: 'Value prices', value: rows.length, sub: 'vs ' + data.arbCount + ' arbitrages', good: rows.length > 0 },
    { label: 'Best edge', value: rows.length ? '+' + pct(Math.max.apply(null, rows.map(r => r.edge))) : '—', sub: 'over fair odds' },
    { label: 'Mean edge', value: rows.length ? '+' + pct(mean) : '—', sub: 'across all of them' },
    { label: 'Standard rules', value: data.rows.filter(r => r.ruleRisk === 'standard').length, sub: 'settled alike by both books' },
    { label: 'Reference', value: s.reference, sub: 'margin stripped out' }
  ]);

  drawBooks(rows);
  drawDistribution(rows);
  drawTable(rows);

  document.getElementById('method-note').textContent =
    'Fair odds come from removing Pinnacle’s margin with the power method: it solves for the exponent k ' +
    'in sum((1/odds)^k) = 1, which takes more margin off long shots than off favourites. Dividing by the ' +
    'margin instead — the usual shortcut — made every outsider look like value here: mean edge rose ' +
    'from 3.6% at short prices to 7.3% above 10.0, which was the method, not the market.';
}

/* ---------------- load ---------------- */

const statusEl = document.getElementById('status');
const statusText = document.getElementById('status-text');

function setStatus(text, kind) {
  statusText.textContent = text;
  statusEl.className = 'status' + (kind ? ' ' + kind : '');
}

async function load() {
  const sport = currentSport();
  setStatus('Computing from the last ' + sport + ' scan…', 'live');
  try {
    const res = await fetch('/api/value?sport=' + sport);
    const data = await res.json();
    if (data.empty) {
      setStatus('No ' + sport + ' scan stored yet — run one from the markets page.', '');
      return;
    }
    render(data);
    setStatus(data.summary.total + ' value prices from the ' + sport + ' scan of ' +
      (data.scannedAt ? new Date(data.scannedAt * 1000).toLocaleString() : 'unknown time') +
      ' · computed from stored data, no API calls', '');
  } catch (err) {
    setStatus('Could not load: ' + err.message, 'error');
  }
}

document.querySelectorAll('input[name="sport"]').forEach(el =>
  el.addEventListener('change', load));
document.getElementById('only-standard').addEventListener('change', () => {
  if (DATA) render(DATA);
});

let resizeTimer = null;
addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => { if (DATA) render(DATA); }, 150);
});

load();
