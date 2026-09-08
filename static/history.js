'use strict';

/* Price-movement page. Everything here is read from disk via /api/history;
   this page never calls the odds API. */

let DATA = null;

/* Ages span seconds to days, so every age axis is log scaled. */
const LOG_MIN = 0.5;                       // half a minute
const lg = v => Math.log10(Math.max(v, LOG_MIN));

function logTicks(maxMinutes, X, minGapPx) {
  const ticks = [1, 5, 15, 60, 240, 1440, 10080].filter(t => t <= maxMinutes * 1.3);
  if (!X) return ticks;
  // Drop any tick that would land too close to the last one kept.
  const kept = [];
  ticks.forEach(t => {
    if (!kept.length || X(t) - X(kept[kept.length - 1]) >= (minGapPx || 46)) kept.push(t);
  });
  return kept;
}

/* ---------------- chart 1: reaction speed by bookmaker ---------------- */

function drawBooks(churn) {
  const svg = document.getElementById('chart-books');
  clear(svg);
  legend('legend-books', [['25th–75th percentile', COLOR.s1], ['Median', COLOR.text]]);
  const rows = churn.books || [];
  if (!rows.length) return;

  const rowH = 42, padL = 118, padR = 88, padT = 16, padB = 42;
  const w = Math.max(svg.clientWidth || 900, 640);
  const h = padT + rows.length * rowH + padB;
  svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
  svg.setAttribute('height', h);

  const plotW = w - padL - padR;
  const maxAge = Math.max.apply(null, rows.map(r => r.p75)) * 1.2;
  const X = v => padL + ((lg(v) - lg(LOG_MIN)) / (lg(maxAge) - lg(LOG_MIN))) * plotW;

  logTicks(maxAge, X).forEach(t => {
    el('line', { x1: X(t), x2: X(t), y1: padT, y2: h - padB, stroke: COLOR.lineSoft }, svg);
    el('text', { x: X(t), y: h - padB + 16, fill: COLOR.muted, 'font-size': 10, 'text-anchor': 'middle' }, svg)
      .textContent = fmtMinutes(t);
  });
  el('text', { x: padL + plotW / 2, y: h - 8, fill: COLOR.muted, 'font-size': 10, 'text-anchor': 'middle', 'letter-spacing': '.1em' }, svg)
    .textContent = 'TIME A PRICE STANDS BEFORE MOVING (LOG SCALE)';

  rows.forEach((r, i) => {
    const y = padT + i * rowH;
    const barH = 13;
    // The bar spans the quartiles; the notch marks the median.
    const x0 = X(r.p25), x1 = X(r.p75), med = X(r.median);
    el('rect', {
      x: x0, y: y + (rowH - barH) / 2, width: Math.max(x1 - x0, 3), height: barH,
      rx: 4, fill: COLOR.s1, opacity: 0.85
    }, svg);
    el('line', {
      x1: med, x2: med, y1: y + (rowH - barH) / 2 - 3, y2: y + (rowH + barH) / 2 + 3,
      stroke: COLOR.text, 'stroke-width': 2
    }, svg);

    el('text', { x: padL - 12, y: y + rowH / 2 + 4, fill: COLOR.sub, 'font-size': 11.5, 'text-anchor': 'end' }, svg)
      .textContent = r.book;
    el('text', { x: x1 + 10, y: y + rowH / 2 + 4, fill: COLOR.text, 'font-size': 11 }, svg)
      .textContent = fmtMinutes(r.median);

    hit(svg, { x: 0, y: y, width: w, height: rowH }, r.book, [
      ['Median age', fmtMinutes(r.median)],
      ['Quartiles', fmtMinutes(r.p25) + ' – ' + fmtMinutes(r.p75)],
      ['Moved within 5 min', r.freshShare + '%'],
      ['Prices observed', r.count]
    ]);
  });
}

/* ---------------- chart 2: by time to kick-off ---------------- */

function drawKickoff(churn) {
  const svg = document.getElementById('chart-kickoff');
  clear(svg);
  const rows = churn.buckets || [];
  if (!rows.length) return;

  const w = Math.max(svg.clientWidth || 520, 420), h = 262;
  const padL = 84, padR = 58, padT = 14, padB = 44;
  svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
  svg.setAttribute('height', h);

  const plotW = w - padL - padR;
  const rowH = (h - padT - padB) / rows.length;
  const maxAge = Math.max.apply(null, rows.map(r => r.p75)) * 1.25;
  const X = v => padL + ((lg(v) - lg(LOG_MIN)) / (lg(maxAge) - lg(LOG_MIN))) * plotW;

  logTicks(maxAge, X).forEach(t => {
    el('line', { x1: X(t), x2: X(t), y1: padT, y2: h - padB, stroke: COLOR.lineSoft }, svg);
    el('text', { x: X(t), y: h - padB + 16, fill: COLOR.muted, 'font-size': 10, 'text-anchor': 'middle' }, svg)
      .textContent = fmtMinutes(t);
  });

  rows.forEach((r, i) => {
    const y = padT + i * rowH;
    const barH = 12;
    const x0 = X(r.p25), x1 = X(r.p75);
    el('rect', {
      x: x0, y: y + (rowH - barH) / 2, width: Math.max(x1 - x0, 3), height: barH,
      rx: 4, fill: COLOR.s1, opacity: 0.8
    }, svg);
    const med = X(r.median);
    el('line', {
      x1: med, x2: med, y1: y + (rowH - barH) / 2 - 3, y2: y + (rowH + barH) / 2 + 3,
      stroke: COLOR.text, 'stroke-width': 2
    }, svg);

    el('text', { x: padL - 12, y: y + rowH / 2 + 4, fill: COLOR.sub, 'font-size': 11, 'text-anchor': 'end' }, svg)
      .textContent = r.window;
    el('text', { x: Math.max(x1, med) + 9, y: y + rowH / 2 + 4, fill: COLOR.muted, 'font-size': 10.5 }, svg)
      .textContent = fmtMinutes(r.median);

    hit(svg, { x: 0, y: y, width: w, height: rowH }, 'Kick-off ' + r.window, [
      ['Median age', fmtMinutes(r.median)],
      ['p25 – p75', fmtMinutes(r.p25) + ' – ' + fmtMinutes(r.p75)],
      ['Prices observed', r.count]
    ]);
  });

  el('text', { x: padL + plotW / 2, y: h - 8, fill: COLOR.muted, 'font-size': 10, 'text-anchor': 'middle', 'letter-spacing': '.1em' }, svg)
    .textContent = 'PRICE AGE (LOG SCALE)';
}

/* ---------------- chart 3: age distribution ---------------- */

function drawAges(churn) {
  const svg = document.getElementById('chart-ages');
  clear(svg);
  const ages = churn.ages || [];
  if (!ages.length) return;

  const w = Math.max(svg.clientWidth || 520, 420), h = 262;
  const padL = 38, padR = 14, padT = 14, padB = 44;
  svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
  svg.setAttribute('height', h);
  const plotW = w - padL - padR, plotH = h - padT - padB;

  const maxAge = Math.max.apply(null, ages);
  const bins = 20;
  const loL = lg(LOG_MIN), hiL = lg(maxAge * 1.05);
  const counts = new Array(bins).fill(0);
  ages.forEach(a => {
    const t = (lg(a) - loL) / (hiL - loL);
    counts[Math.min(bins - 1, Math.max(0, Math.floor(t * bins)))]++;
  });

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
    const binLo = Math.pow(10, loL + (hiL - loL) * (i / bins));
    const binHi = Math.pow(10, loL + (hiL - loL) * ((i + 1) / bins));
    // Under five minutes is the band a fast scanner can actually catch.
    const fast = binHi <= 5;
    el('rect', {
      x: padL + i * barW + 1, y: Y(c), width: Math.max(barW - 2, 1), height: padT + plotH - Y(c),
      rx: 4, fill: fast ? COLOR.good : COLOR.s1, opacity: 0.88
    }, svg);
    hit(svg, { x: padL + i * barW, y: padT, width: barW, height: plotH },
      fmtMinutes(binLo) + ' – ' + fmtMinutes(binHi),
      [['Prices', c], ['Share', (100 * c / ages.length).toFixed(1) + '%']]);
  });

  [0, 0.5, 1].forEach(t => {
    el('text', {
      x: padL + plotW * t, y: h - padB + 16, fill: COLOR.muted, 'font-size': 10,
      'text-anchor': t === 0 ? 'start' : t === 1 ? 'end' : 'middle'
    }, svg).textContent = fmtMinutes(Math.pow(10, loL + (hiL - loL) * t));
  });
  el('text', { x: padL + plotW / 2, y: h - 8, fill: COLOR.muted, 'font-size': 10, 'text-anchor': 'middle', 'letter-spacing': '.1em' }, svg)
    .textContent = 'PRICE AGE (LOG SCALE)';
}

/* ---------------- chart 4: overround across scans ---------------- */

function drawTrend(history) {
  const svg = document.getElementById('chart-trend');
  clear(svg);
  legend('legend-trend', [['Best overround', COLOR.s1], ['Median overround', COLOR.s2]]);
  if (!history.length) return;

  const w = Math.max(svg.clientWidth || 900, 640), h = 260;
  const padL = 62, padR = 24, padT = 20, padB = 46;
  svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
  svg.setAttribute('height', h);
  const plotW = w - padL - padR, plotH = h - padT - padB;

  const times = history.map(p => new Date(p.scannedAt).getTime());
  const t0 = Math.min.apply(null, times), t1 = Math.max.apply(null, times);
  const values = history.flatMap(p => [p.best, p.median]);
  const lo = Math.min(0.998, Math.min.apply(null, values) - 0.002);
  const hi = Math.max.apply(null, values) + 0.002;

  const X = t => t1 === t0 ? padL + plotW / 2 : padL + ((t - t0) / (t1 - t0)) * plotW;
  const Y = v => padT + plotH - ((v - lo) / (hi - lo)) * plotH;

  for (let i = 0; i <= 4; i++) {
    const v = lo + (hi - lo) * (i / 4);
    el('line', { x1: padL, x2: w - padR, y1: Y(v), y2: Y(v), stroke: COLOR.lineSoft }, svg);
    el('text', { x: padL - 8, y: Y(v) + 4, fill: COLOR.muted, 'font-size': 10, 'text-anchor': 'end' }, svg)
      .textContent = v.toFixed(4);
  }

  if (lo < 1 && hi > 1) {
    el('line', { x1: padL, x2: w - padR, y1: Y(1), y2: Y(1), stroke: COLOR.good, 'stroke-width': 2, 'stroke-dasharray': '5 4' }, svg);
    el('text', { x: padL + 4, y: Y(1) - 6, fill: COLOR.good, 'font-size': 10 }, svg)
      .textContent = 'ARBITRAGE';
  }

  [['best', COLOR.s1], ['median', COLOR.s2]].forEach(spec => {
    const pts = history.map((p, i) => X(times[i]) + ',' + Y(p[spec[0]]));
    if (pts.length > 1) {
      el('polyline', { points: pts.join(' '), fill: 'none', stroke: spec[1], 'stroke-width': 2, 'stroke-linecap': 'round' }, svg);
    }
    history.forEach((p, i) => {
      el('circle', { cx: X(times[i]), cy: Y(p[spec[0]]), r: 4.5, fill: spec[1], stroke: COLOR.surface, 'stroke-width': 2 }, svg);
    });
  });

  history.forEach((p, i) => {
    hit(svg, { x: X(times[i]) - 18, y: padT, width: 36, height: plotH }, fmtTime(p.scannedAt), [
      ['Best overround', p.best.toFixed(4)],
      ['Median', p.median.toFixed(4)],
      ['Matches', p.matches],
      ['Arbs', p.arbs]
    ]);
  });

  if (history.length === 1) {
    el('text', { x: padL + plotW / 2, y: padT + 14, fill: COLOR.muted, 'font-size': 11, 'text-anchor': 'middle' }, svg)
      .textContent = 'one scan on file — the trend appears as more are stored';
  }
}

/* ---------------- table + tiles ---------------- */

function drawTable(history) {
  const body = document.querySelector('#table tbody');
  body.innerHTML = '';
  history.slice().reverse().forEach(p => {
    const tr = document.createElement('tr');
    tr.innerHTML =
      '<td>' + fmtTime(p.scannedAt) + '</td>' +
      '<td class="num">' + p.matches + '</td>' +
      '<td class="num">' + p.best.toFixed(4) + '</td>' +
      '<td class="num">' + p.median.toFixed(4) + '</td>' +
      '<td class="num">' + (p.arbs ? '<span class="pill arb">' + p.arbs + '</span>' : '0') + '</td>' +
      '<td class="num">' + p.within1pct + '</td>';
    body.appendChild(tr);
  });
}

function drawTiles(data) {
  const churn = data.churn, st = data.stats;
  const fastest = (churn.books || [])[0];
  const slowest = (churn.books || [])[churn.books.length - 1];

  tiles('tiles', [
    { label: 'Scans stored', value: st.scans, sub: st.priceRows.toLocaleString() + ' price rows' },
    { label: 'Fastest book', value: fastest ? fastest.book : '—', sub: fastest ? 'median ' + fmtMinutes(fastest.median) : '' },
    { label: 'Slowest book', value: slowest ? slowest.book : '—', sub: slowest ? 'median ' + fmtMinutes(slowest.median) : '' },
    {
      label: 'Lag between them',
      value: fastest && slowest ? fmtMinutes(slowest.median - fastest.median) : '—',
      sub: 'how long a gap can persist',
      good: true
    },
    { label: 'Store size', value: (st.bytes / 1024).toFixed(0) + ' KB', sub: 'on disk, no API needed' }
  ]);
}

function note(data) {
  const books = data.churn.books || [];
  if (books.length < 2) return;
  const fastest = books[0], slowest = books[books.length - 1];
  document.getElementById('note-books').textContent =
    fastest.book + ' reprices roughly ' + (slowest.median / fastest.median).toFixed(0) +
    '× more often than ' + slowest.book + '. An arbitrage is that gap: it opens when ' +
    fastest.book + ' moves and closes when ' + slowest.book + ' follows. ' +
    'These ages are length-biased — a scan lands more often inside a long quiet spell than a short one — so treat them as an upper bound.';
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
  drawBooks(data.churn);
  drawKickoff(data.churn);
  drawAges(data.churn);
  drawTrend(data.overround);
  drawTable(data.overround);
  note(data);
}

async function load() {
  try {
    const res = await fetch('/api/history');
    const data = await res.json();
    if (!data.stats.scans) {
      setStatus('No scans stored yet — run one from the scanner page.', '');
      return;
    }
    render(data);
    setStatus(data.stats.scans + ' scans stored · ' + data.churn.total.toLocaleString() +
      ' price observations · ' + fmtTime(data.stats.first) + ' to ' + fmtTime(data.stats.last) +
      ' · read from disk, no API calls', '');
  } catch (err) {
    setStatus('Could not load stored scans: ' + err.message, 'error');
  }
}

let resizeTimer = null;
addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => { if (DATA) render(DATA); }, 150);
});

load();
