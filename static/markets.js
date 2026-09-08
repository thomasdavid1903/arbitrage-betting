'use strict';

/* All-markets page: reads the cached scan, so opening it costs nothing. */

let DATA = null;

const pct = v => (v * 100).toFixed(2) + '%';

function median(values) {
  const s = values.slice().sort((a, b) => a - b);
  return s[Math.floor(s.length / 2)];
}

/* ---------------- chart 1: overround by market type ---------------- */

function drawTypes(margins) {
  const svg = document.getElementById('chart-types');
  clear(svg);
  legend('legend-types', [['Best available', COLOR.s1], ['Median for the type', COLOR.s4]]);
  if (!margins.length) return;

  const groups = new Map();
  margins.forEach(r => {
    if (!groups.has(r.marketType)) groups.set(r.marketType, []);
    groups.get(r.marketType).push(r.overround);
  });

  const rows = Array.from(groups.entries())
    .map(e => ({ type: e[0], n: e[1].length, best: Math.min.apply(null, e[1]), median: median(e[1]) }))
    .filter(r => r.n >= 20)
    .sort((a, b) => a.best - b.best)
    .slice(0, 14);

  const rowH = 27, padL = 190, padR = 74, padT = 30, padB = 36;
  const w = Math.max(svg.clientWidth || 900, 640);
  const h = padT + rows.length * rowH + padB;
  svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
  svg.setAttribute('height', h);
  const plotW = w - padL - padR;

  const lo = Math.min(0.99, Math.min.apply(null, rows.map(r => r.best)) - 0.004);
  const hi = Math.max.apply(null, rows.map(r => r.median)) + 0.006;
  const X = v => padL + ((v - lo) / (hi - lo)) * plotW;

  for (let i = 0; i <= 5; i++) {
    const v = lo + (hi - lo) * (i / 5);
    el('line', { x1: X(v), x2: X(v), y1: padT - 8, y2: h - padB, stroke: COLOR.lineSoft }, svg);
    el('text', { x: X(v), y: h - padB + 16, fill: COLOR.muted, 'font-size': 10, 'text-anchor': 'middle' }, svg)
      .textContent = v.toFixed(3);
  }

  const bx = X(1);
  el('line', { x1: bx, x2: bx, y1: padT - 14, y2: h - padB, stroke: COLOR.good, 'stroke-width': 2, 'stroke-dasharray': '5 4' }, svg);
  el('text', { x: bx, y: padT - 19, fill: COLOR.good, 'font-size': 10, 'text-anchor': 'middle', 'letter-spacing': '.1em' }, svg)
    .textContent = 'ARBITRAGE ← 1.000';

  rows.forEach((r, i) => {
    const y = padT + i * rowH + rowH / 2;
    const isArb = r.best < 1;

    // A connector from best to median shows the spread within the type.
    el('line', { x1: X(r.best), x2: X(r.median), y1: y, y2: y, stroke: COLOR.line, 'stroke-width': 2 }, svg);
    el('circle', { cx: X(r.median), cy: y, r: 5, fill: COLOR.s4, stroke: COLOR.surface, 'stroke-width': 2 }, svg);
    el('circle', { cx: X(r.best), cy: y, r: 5.5, fill: isArb ? COLOR.good : COLOR.s1, stroke: COLOR.surface, 'stroke-width': 2 }, svg);

    el('text', { x: padL - 14, y: y + 4, fill: isArb ? COLOR.text : COLOR.sub, 'font-size': 11, 'text-anchor': 'end' }, svg)
      .textContent = short(r.type, 26);
    el('text', { x: X(r.median) + 12, y: y + 4, fill: COLOR.muted, 'font-size': 10.5 }, svg)
      .textContent = r.n;

    hit(svg, { x: 0, y: padT + i * rowH, width: w, height: rowH }, r.type, [
      ['Best overround', r.best.toFixed(4)],
      ['Median', r.median.toFixed(4)],
      ['Markets judged', r.n],
      ['Arbitrage?', isArb ? 'yes — ' + pct(1 / r.best - 1) : 'no']
    ]);
  });
}

/* ---------------- chart 2: distribution ---------------- */

function drawDistribution(margins) {
  const svg = document.getElementById('chart-dist');
  clear(svg);
  if (!margins.length) return;

  const values = margins.map(r => r.overround).filter(v => v < 1.35);
  const lo = Math.min(0.99, Math.min.apply(null, values));
  const hi = Math.max.apply(null, values);
  const bins = 26, width = (hi - lo) / bins || 1;
  const counts = new Array(bins).fill(0);
  values.forEach(v => counts[Math.min(bins - 1, Math.floor((v - lo) / width))]++);

  const w = Math.max(svg.clientWidth || 520, 420), h = 258;
  const padL = 44, padR = 14, padT = 14, padB = 42;
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
    const isArb = binLo + width <= 1;
    el('rect', {
      x: padL + i * barW + 1, y: Y(c), width: Math.max(barW - 2, 1), height: padT + plotH - Y(c),
      rx: 4, fill: isArb ? COLOR.good : COLOR.s1, opacity: 0.88
    }, svg);
    hit(svg, { x: padL + i * barW, y: padT, width: barW, height: plotH },
      'Overround ' + binLo.toFixed(3) + '–' + (binLo + width).toFixed(3),
      [['Markets', c], ['Share', (100 * c / values.length).toFixed(1) + '%']]);
  });

  if (lo < 1) {
    const bx = padL + ((1 - lo) / (hi - lo)) * plotW;
    el('line', { x1: bx, x2: bx, y1: padT, y2: padT + plotH, stroke: COLOR.good, 'stroke-width': 2, 'stroke-dasharray': '5 4' }, svg);
  }

  [lo, (lo + hi) / 2, hi].forEach((v, i) => {
    el('text', {
      x: padL + plotW * (i / 2), y: h - padB + 16, fill: COLOR.muted, 'font-size': 10,
      'text-anchor': i === 0 ? 'start' : i === 2 ? 'end' : 'middle'
    }, svg).textContent = v.toFixed(3);
  });
  el('text', { x: padL + plotW / 2, y: h - 6, fill: COLOR.muted, 'font-size': 10, 'text-anchor': 'middle', 'letter-spacing': '.1em' }, svg)
    .textContent = 'OVERROUND';
}

/* ---------------- chart 3: closest individual markets ---------------- */

function drawClosest(margins) {
  const svg = document.getElementById('chart-closest');
  clear(svg);
  const rows = margins.slice(0, 12);
  if (!rows.length) return;

  const rowH = 21, padL = 20, padR = 66, padT = 22, padB = 30;
  const w = Math.max(svg.clientWidth || 520, 420);
  const h = padT + rows.length * rowH + padB;
  svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
  svg.setAttribute('height', h);
  const plotW = w - padL - padR;

  const hiV = Math.max(Math.max.apply(null, rows.map(r => r.overround)), 1.004);
  const loV = Math.min(0.99, Math.min.apply(null, rows.map(r => r.overround)) - 0.002);
  const X = v => padL + ((v - loV) / (hiV - loV)) * plotW;
  const bx = X(1);

  el('line', { x1: bx, x2: bx, y1: padT - 12, y2: h - padB, stroke: COLOR.good, 'stroke-width': 2, 'stroke-dasharray': '5 4' }, svg);
  el('text', { x: bx, y: padT - 16, fill: COLOR.good, 'font-size': 10, 'text-anchor': 'middle' }, svg)
    .textContent = '1.000';

  rows.forEach((r, i) => {
    const y = padT + i * rowH;
    const isArb = r.overround < 1;
    const x0 = Math.min(bx, X(r.overround)), x1 = Math.max(bx, X(r.overround));
    el('rect', {
      x: x0, y: y + 4, width: Math.max(x1 - x0, 2), height: 11,
      rx: 4, fill: isArb ? COLOR.good : COLOR.s1, opacity: 0.85
    }, svg);
    el('text', { x: x1 + 8, y: y + 13, fill: isArb ? COLOR.good : COLOR.sub, 'font-size': 10.5 }, svg)
      .textContent = r.overround.toFixed(4);

    hit(svg, { x: 0, y: y, width: w, height: rowH },
      r.marketName || r.marketType,
      [['Fixture', r.home + ' v ' + r.away],
       ['Overround', r.overround.toFixed(4)],
       ['Books involved', r.books],
       ['Outcomes', r.outcomes]]);
  });

  el('text', { x: padL, y: h - padB + 18, fill: COLOR.muted, 'font-size': 10, 'letter-spacing': '.1em' }, svg)
    .textContent = 'HOVER FOR THE FIXTURE AND MARKET';
}

/* ---------------- arbitrage cards ---------------- */

function drawArbs(rows) {
  const box = document.getElementById('arbs');
  if (!rows.length) {
    box.innerHTML = '<p class="empty">No arbitrage in the last scan.</p>';
    return;
  }

  box.innerHTML = rows.map(r => {
    const legs = r.outcomes.map(o =>
      '<tr>' +
        '<td>' + o.name + '</td>' +
        '<td class="num">' + o.price.toFixed(2) + '</td>' +
        '<td class="book">' + o.book + '</td>' +
        '<td class="num">£' + o.stake.toFixed(2) + '</td>' +
        '<td class="num book">' + (o.limit ? '£' + Math.round(o.limit) : 'unknown') + '</td>' +
      '</tr>').join('');

    const stakeNote = r.limited
      ? 'capped at £' + r.total.toFixed(0) + ' by the books’ own limits'
      : 'shown on an example £' + r.total.toFixed(0) + ' stake; no published limit';

    return '<div class="arb-card">' +
      '<div class="arb-head">' +
        '<div>' +
          '<div class="arb-title">' + r.marketName + (r.handicap ? ' <span class="book">(' + r.handicap + ')</span>' : '') + '</div>' +
          '<div class="book">' + r.home + ' v ' + r.away + ' · ' + fmtTime(r.startTime) + '</div>' +
        '</div>' +
        '<div class="arb-return">' +
          '<span class="pill arb">+' + pct(r.ratio) + '</span>' +
          (r.singleBook ? ' <span class="pill near">single book</span>' : '') +
        '</div>' +
      '</div>' +
      '<table class="arb-legs"><thead><tr>' +
        '<th>Outcome</th><th class="num">Odds</th><th>Book</th><th class="num">Stake</th><th class="num">Max</th>' +
      '</tr></thead><tbody>' + legs + '</tbody></table>' +
      '<div class="arb-foot">Profit £' + r.profit.toFixed(2) + ' whichever way it goes — ' + stakeNote + '.</div>' +
    '</div>';
  }).join('');
}

/* ---------------- tiles ---------------- */

function drawTiles(data) {
  const s = data.marketSummary, c = data.marketCoverage;
  const oneXtwo = data.matches.filter(m => m.arb).length;

  tiles('tiles', [
    { label: 'Markets judged', value: c.judged.toLocaleString(), sub: 'of ' + c.collected.toLocaleString() + ' collected' },
    { label: 'Arbitrages', value: s.total, sub: s.crossBook + ' across two books', good: s.total > 0 },
    { label: 'Best return', value: s.total ? '+' + pct(s.bestRatio) : '—', sub: 'per pound staked', good: s.total > 0 },
    { label: '1X2 only', value: oneXtwo, sub: 'what the old scanner saw' },
    { label: 'Requests', value: data.requests, sub: 'same cost as before' }
  ]);
}

/* ---------------- load ---------------- */

const statusEl = document.getElementById('status');
const statusText = document.getElementById('status-text');

function setStatus(text, kind) {
  statusText.textContent = text;
  statusEl.className = 'status' + (kind ? ' ' + kind : '');
}

function render(data) {
  DATA = data;
  drawTiles(data);
  drawTypes(data.marketMargins || []);
  drawDistribution(data.marketMargins || []);
  drawClosest(data.marketMargins || []);
  drawArbs(data.markets || []);
}

async function load() {
  try {
    const res = await fetch('/api/cached');
    const data = await res.json();
    if (data.empty || !data.marketMargins) {
      setStatus('No scan with market data yet — run a scan from the scanner page.', '');
      return;
    }
    render(data);
    setStatus('Scan from ' + fmtTime(new Date(data.scannedAt * 1000).toISOString()) +
      ' · ' + data.marketCoverage.judged.toLocaleString() + ' markets judged · read from cache', '');
  } catch (err) {
    setStatus('Could not load: ' + err.message, 'error');
  }
}

let resizeTimer = null;
addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => { if (DATA) render(DATA); }, 150);
});

load();
