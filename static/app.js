'use strict';

/* Scanner page. Shared primitives (el, hit, legend, tiles, COLOR) come from
   chart-lib.js, which is loaded first. */

let STATE = { matches: [], selected: 0, meta: null };

const label = m => m.home + ' v ' + m.away;

/* ---------------- chart 1: closest to arbitrage ---------------- */

function drawMargin(matches) {
  const svg = document.getElementById('chart-margin');
  clear(svg);
  if (!matches.length) return;

  const rows = matches.slice(0, 18);
  const rowH = 26, padL = 250, padR = 82, padT = 30, padB = 34;
  const w = Math.max(svg.clientWidth || 900, 640);
  const h = padT + rows.length * rowH + padB;
  svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
  svg.setAttribute('height', h);

  const plotW = w - padL - padR;
  // The scale is anchored either side of 1.0, so distance from the
  // arbitrage line is what the eye measures.
  const hi = Math.max(Math.max.apply(null, rows.map(r => r.overround)), 1.02);
  const lo = Math.min(0.985, Math.min.apply(null, rows.map(r => r.overround)) - 0.004);
  const x = v => padL + ((v - lo) / (hi - lo)) * plotW;

  for (let i = 0; i <= 5; i++) {
    const v = lo + (hi - lo) * (i / 5);
    el('line', { x1: x(v), x2: x(v), y1: padT - 8, y2: h - padB, stroke: COLOR.lineSoft, 'stroke-width': 1 }, svg);
    el('text', { x: x(v), y: h - padB + 16, fill: COLOR.muted, 'font-size': 10, 'text-anchor': 'middle' }, svg)
      .textContent = v.toFixed(3);
  }

  const bx = x(1);
  el('line', { x1: bx, x2: bx, y1: padT - 14, y2: h - padB, stroke: COLOR.good, 'stroke-width': 2, 'stroke-dasharray': '5 4' }, svg);
  el('text', { x: bx, y: padT - 19, fill: COLOR.good, 'font-size': 10, 'text-anchor': 'middle', 'letter-spacing': '.1em' }, svg)
    .textContent = 'ARBITRAGE ← 1.000';

  rows.forEach((m, i) => {
    const y = padT + i * rowH;
    const barH = 13;
    const isArb = m.overround < 1;
    const colour = isArb ? COLOR.good : COLOR.s1;
    const selected = matches.indexOf(m) === STATE.selected;

    const x0 = Math.min(bx, x(m.overround));
    const x1 = Math.max(bx, x(m.overround));
    el('rect', {
      x: x0, y: y + (rowH - barH) / 2, width: Math.max(x1 - x0, 2), height: barH,
      rx: 4, fill: colour, opacity: isArb ? 1 : 0.82
    }, svg);

    el('text', {
      x: padL - 12, y: y + rowH / 2 + 4, 'text-anchor': 'end', 'font-size': 11,
      fill: selected ? COLOR.text : COLOR.sub
    }, svg).textContent = short(label(m), 34);

    el('text', {
      x: x1 + 8, y: y + rowH / 2 + 4, 'font-size': 11,
      fill: isArb ? COLOR.good : COLOR.sub
    }, svg).textContent = m.overround.toFixed(4);

    hit(svg, { x: 0, y: y, width: w, height: rowH }, label(m), [
      ['Overround', m.overround.toFixed(4)],
      ['Margin against you', ((m.overround - 1) * 100).toFixed(2) + '%'],
      ['Home / Draw / Away', m.decimals.map(fmtOdds).join('  ')],
      ['Books', m.books.join(' / ')]
    ], () => select(matches.indexOf(m)));
  });
}

/* ---------------- chart 2: margin distribution ---------------- */

function drawHistogram(matches) {
  const svg = document.getElementById('chart-hist');
  clear(svg);
  if (!matches.length) return;

  const values = matches.map(m => m.overround);
  const lo = Math.min(0.99, Math.min.apply(null, values));
  const hi = Math.max.apply(null, values);
  const bins = 22, width = (hi - lo) / bins || 1;
  const counts = new Array(bins).fill(0);
  values.forEach(v => {
    counts[Math.min(bins - 1, Math.floor((v - lo) / width))]++;
  });

  const w = Math.max(svg.clientWidth || 520, 420), h = 250;
  const padL = 38, padR = 14, padT = 16, padB = 42;
  svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
  svg.setAttribute('height', h);

  const plotW = w - padL - padR, plotH = h - padT - padB;
  const max = Math.max.apply(null, counts);
  const X = i => padL + (i / bins) * plotW;
  const Y = c => padT + plotH - (c / max) * plotH;

  for (let i = 0; i <= 4; i++) {
    const yy = padT + plotH * (i / 4);
    el('line', { x1: padL, x2: w - padR, y1: yy, y2: yy, stroke: COLOR.lineSoft, 'stroke-width': 1 }, svg);
    el('text', { x: padL - 8, y: yy + 4, fill: COLOR.muted, 'font-size': 10, 'text-anchor': 'end' }, svg)
      .textContent = Math.round(max * (1 - i / 4));
  }

  const barW = plotW / bins;
  counts.forEach((c, i) => {
    if (!c) return;
    const binLo = lo + i * width;
    const isArb = binLo + width <= 1;
    el('rect', {
      x: X(i) + 1, y: Y(c), width: Math.max(barW - 2, 1), height: padT + plotH - Y(c),
      rx: 4, fill: isArb ? COLOR.good : COLOR.s1, opacity: 0.88
    }, svg);
    hit(svg, { x: X(i), y: padT, width: barW, height: plotH },
      'Overround ' + binLo.toFixed(3) + '–' + (binLo + width).toFixed(3),
      [['Matches', c], ['Share', (100 * c / values.length).toFixed(1) + '%']]);
  });

  if (lo < 1 && hi > 1) {
    const bx = padL + ((1 - lo) / (hi - lo)) * plotW;
    el('line', { x1: bx, x2: bx, y1: padT, y2: padT + plotH, stroke: COLOR.good, 'stroke-width': 2, 'stroke-dasharray': '5 4' }, svg);
  }

  [lo, (lo + hi) / 2, hi].forEach((v, i) => {
    el('text', {
      x: padL + plotW * (i / 2), y: h - padB + 18, fill: COLOR.muted, 'font-size': 10,
      'text-anchor': i === 0 ? 'start' : i === 2 ? 'end' : 'middle'
    }, svg).textContent = v.toFixed(3);
  });

  el('text', { x: padL + plotW / 2, y: h - 6, fill: COLOR.muted, 'font-size': 10, 'text-anchor': 'middle', 'letter-spacing': '.1em' }, svg)
    .textContent = 'OVERROUND';
}

/* ---------------- chart 3: bookmaker edge ---------------- */

function drawBooks(matches) {
  const svg = document.getElementById('chart-books');
  clear(svg);
  legend('legend-books', [['Home', COLOR.s1], ['Draw', COLOR.s2], ['Away', COLOR.s3]]);
  if (!matches.length) return;

  const tally = new Map();
  matches.forEach(m => m.books.forEach((b, i) => {
    if (!tally.has(b)) tally.set(b, [0, 0, 0]);
    tally.get(b)[i]++;
  }));

  const rows = Array.from(tally.entries())
    .map(e => ({ name: e[0], counts: e[1], total: e[1][0] + e[1][1] + e[1][2] }))
    .sort((a, b) => b.total - a.total);

  const rowH = 34, padL = 96, padR = 48, padT = 8, padB = 24;
  const w = Math.max(svg.clientWidth || 520, 420);
  const h = padT + rows.length * rowH + padB;
  svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
  svg.setAttribute('height', h);

  const plotW = w - padL - padR;
  const max = Math.max.apply(null, rows.map(r => r.total));
  const colours = [COLOR.s1, COLOR.s2, COLOR.s3];
  const names = ['Home', 'Draw', 'Away'];

  rows.forEach((r, i) => {
    const y = padT + i * rowH, barH = 15;
    let x = padL;
    r.counts.forEach((c, j) => {
      if (!c) return;
      const segW = (c / max) * plotW;
      // 2px surface gap between stacked segments.
      el('rect', {
        x: x, y: y + (rowH - barH) / 2, width: Math.max(segW - 2, 1), height: barH,
        rx: 4, fill: colours[j]
      }, svg);
      hit(svg, { x: x, y: y, width: Math.max(segW, 3), height: rowH }, r.name,
        [[names[j] + ' best price', c], ['Total best prices', r.total]]);
      x += segW;
    });

    el('text', { x: padL - 12, y: y + rowH / 2 + 4, fill: COLOR.sub, 'font-size': 11, 'text-anchor': 'end' }, svg)
      .textContent = r.name;
    el('text', { x: x + 8, y: y + rowH / 2 + 4, fill: COLOR.muted, 'font-size': 11 }, svg)
      .textContent = r.total;
  });
}

/* ---------------- chart 4: arbitrage geometry ---------------- */

function drawGeometry(match) {
  const svg = document.getElementById('chart-geom');
  clear(svg);
  legend('legend-geom', [
    ['Home win breaks even', COLOR.s1],
    ['Draw breaks even', COLOR.s2],
    ['Away win breaks even', COLOR.s3],
    ['Profitable region', COLOR.good]
  ]);
  if (!match) return;

  // core.py works in fractional odds; the page shows decimals.
  const b1 = match.decimals[0] - 1;
  const b2 = match.decimals[1] - 1;
  const b3 = match.decimals[2] - 1;
  const z = 1000;

  const w = Math.max(svg.clientWidth || 900, 640), h = 400;
  const padL = 66, padR = 26, padT = 34, padB = 48;
  svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
  svg.setAttribute('height', h);
  const plotW = w - padL - padR, plotH = h - padT - padB;

  // Frame on where the three lines actually meet, mirroring core.search_box.
  // Framing on their full extent instead would squash everything into a
  // corner whenever one outcome is a long shot priced at 60.0.
  const cross = (m1, c1, m2, c2) => {
    if (Math.abs(m1 - m2) < 1e-9) return null;
    const x = (c2 - c1) / (m1 - m2);
    return [x, m1 * x + c1];
  };
  const corners = [
    cross(b1, -z, 1 / b2, z / b2),
    cross(b1, -z, -1, z * b3),
    cross(1 / b2, z / b2, -1, z * b3)
  ].filter(p => p && isFinite(p[0]) && isFinite(p[1]));

  let xMax = z * 2.2, yMax = z * 2.2;
  if (corners.length) {
    xMax = Math.max.apply(null, corners.map(p => p[0])) * 1.45;
    yMax = Math.max.apply(null, corners.map(p => p[1])) * 1.45;
  }
  // Near-parallel constraints meet a very long way out (a 1.06 home price
  // against a 23.0 draw), which would shrink everything readable to nothing.
  // Clamp to a window a few times the fixed stake and say when it is cropped.
  const CAP = z * 8;
  const cropped = xMax > CAP || yMax > CAP;
  xMax = Math.min(Math.max(xMax, z * 0.5), CAP);
  yMax = Math.min(Math.max(yMax, z * 0.5), CAP);
  const X = v => padL + (v / xMax) * plotW;
  const Y = v => padT + plotH - (v / yMax) * plotH;

  el('rect', { x: padL, y: padT, width: plotW, height: plotH, fill: 'none', stroke: COLOR.line, 'stroke-width': 1 }, svg);
  for (let i = 1; i < 5; i++) {
    el('line', { x1: padL + plotW * i / 5, x2: padL + plotW * i / 5, y1: padT, y2: padT + plotH, stroke: COLOR.lineSoft }, svg);
    el('line', { x1: padL, x2: padL + plotW, y1: padT + plotH * i / 5, y2: padT + plotH * i / 5, stroke: COLOR.lineSoft }, svg);
  }
  for (let i = 0; i <= 5; i++) {
    el('text', { x: padL + plotW * i / 5, y: h - padB + 17, fill: COLOR.muted, 'font-size': 10, 'text-anchor': 'middle' }, svg)
      .textContent = Math.round(xMax * i / 5);
    el('text', { x: padL - 8, y: padT + plotH - plotH * i / 5 + 4, fill: COLOR.muted, 'font-size': 10, 'text-anchor': 'end' }, svg)
      .textContent = Math.round(yMax * i / 5);
  }
  el('text', { x: padL + plotW / 2, y: h - 8, fill: COLOR.muted, 'font-size': 10, 'text-anchor': 'middle', 'letter-spacing': '.1em' }, svg)
    .textContent = 'STAKE ON HOME WIN (x)';
  const midY = padT + plotH / 2;
  el('text', { x: 16, y: midY, fill: COLOR.muted, 'font-size': 10, 'text-anchor': 'middle', 'letter-spacing': '.1em', transform: 'rotate(-90 16 ' + midY + ')' }, svg)
    .textContent = 'STAKE ON DRAW (y)';

  // Sample the feasible region; this mirrors core.is_arbitrage exactly.
  const steps = 140, cw = xMax / steps, ch = yMax / steps;
  let cells = 0, sx = 0, sy = 0;
  const region = el('g', { fill: COLOR.good, opacity: 0.32 }, svg);
  for (let i = 0; i < steps; i++) {
    for (let j = 0; j < steps; j++) {
      const px = i * cw, py = j * ch;
      if (py < b1 * px - z && py > (z + px) / b2 && py < -px + z * b3) {
        el('rect', { x: X(px), y: Y(py + ch), width: plotW / steps + 0.8, height: plotH / steps + 0.8 }, region);
        cells++; sx += px; sy += py;
      }
    }
  }

  [[COLOR.s1, x => b1 * x - z], [COLOR.s2, x => (z + x) / b2], [COLOR.s3, x => -x + z * b3]]
    .forEach(spec => {
      const pts = [];
      for (let i = 0; i <= 80; i++) {
        const px = xMax * i / 80, py = spec[1](px);
        if (py >= 0 && py <= yMax) pts.push(X(px) + ',' + Y(py));
      }
      if (pts.length > 1) {
        el('polyline', { points: pts.join(' '), fill: 'none', stroke: spec[0], 'stroke-width': 2, 'stroke-linecap': 'round' }, svg);
      }
    });

  // Status sits bottom-left, the match name top-right: they never collide.
  el('text', { x: padL + 12, y: padT + plotH - 12, 'font-size': 11, fill: cells ? COLOR.good : COLOR.muted }, svg)
    .textContent = cells
      ? 'ARBITRAGE REGION — every point inside profits on all three outcomes'
      : 'NO FEASIBLE REGION — the three constraints never overlap';

  if (cells) {
    const cx = sx / cells, cy = sy / cells;
    el('circle', { cx: X(cx), cy: Y(cy), r: 5, fill: COLOR.good, stroke: COLOR.surface, 'stroke-width': 2 }, svg);
    hit(svg, { x: X(cx) - 14, y: Y(cy) - 14, width: 28, height: 28 }, 'Centre of the region', [
      ['Stake home', '£' + cx.toFixed(0)],
      ['Stake draw', '£' + cy.toFixed(0)],
      ['Stake away', '£1000']
    ]);
  }

  el('text', { x: w - padR, y: padT - 12, 'font-size': 11, fill: COLOR.text, 'text-anchor': 'end' }, svg)
    .textContent = short(label(match), 42) + '  ·  ' + match.decimals.map(fmtOdds).join(' / ');

  if (cropped) {
    el('text', { x: padL, y: padT - 12, 'font-size': 10, fill: COLOR.muted }, svg)
      .textContent = 'view cropped — constraints meet off-scale';
  }
}

/* ---------------- table + tiles ---------------- */

function drawTable(matches) {
  const body = document.querySelector('#table tbody');
  body.innerHTML = '';
  matches.forEach((m, i) => {
    const tr = document.createElement('tr');
    const state = m.arb ? '<span class="pill arb">Arb</span>'
      : m.overround < 1.01 ? '<span class="pill near">Near</span>' : '';
    tr.innerHTML =
      '<td>' + label(m) + '</td>' +
      '<td>' + fmtTime(m.startTime) + '</td>' +
      '<td class="num">' + fmtOdds(m.decimals[0]) + '</td>' +
      '<td class="num">' + fmtOdds(m.decimals[1]) + '</td>' +
      '<td class="num">' + fmtOdds(m.decimals[2]) + '</td>' +
      '<td class="book">' + m.books.join(' / ') + '</td>' +
      '<td class="num">' + m.overround.toFixed(4) + '</td>' +
      '<td>' + state + '</td>';
    tr.style.cursor = 'pointer';
    tr.addEventListener('click', () => select(i));
    body.appendChild(tr);
  });
}

function drawTiles(data) {
  const matches = data.matches;
  const arbs = matches.filter(m => m.arb);
  const near = matches.filter(m => m.overround < 1.01).length;
  const best = matches.length ? matches[0].overround : null;

  tiles('tiles', [
    { label: 'Matches priced', value: matches.length, sub: (data.tournaments || []).length + ' competitions' },
    { label: 'Arbitrages', value: arbs.length, sub: arbs.length ? 'place all three legs' : 'none this scan', good: arbs.length > 0 },
    { label: 'Best overround', value: best === null ? '—' : best.toFixed(4), sub: best === null ? '' : ((best - 1) * 100).toFixed(2) + '% against you', good: best !== null && best < 1 },
    { label: 'Within 1%', value: near, sub: 'candidates to watch' },
    { label: 'Requests used', value: data.requests, sub: data.fromCache ? 'cached — no quota spent' : data.elapsed + 's elapsed' }
  ]);
}

function select(i) {
  STATE.selected = i;
  drawGeometry(STATE.matches[i]);
  drawMargin(STATE.matches);
  const rows = document.querySelectorAll('#table tbody tr');
  rows.forEach((tr, j) => tr.classList.toggle('selected', i === j));
  document.getElementById('chart-geom').scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

function render(data) {
  STATE.matches = data.matches;
  STATE.meta = data;
  STATE.selected = 0;
  legend('legend-margin', [
    ['Below 1.0 — arbitrage', COLOR.good],
    ['Above 1.0 — margin against you', COLOR.s1]
  ]);
  drawTiles(data);
  drawMargin(data.matches);
  drawHistogram(data.matches);
  drawBooks(data.matches);
  drawGeometry(data.matches[0]);
  drawTable(data.matches);
}

/* ---------------- wiring ---------------- */

const statusEl = document.getElementById('status');
const statusText = document.getElementById('status-text');

function setStatus(text, kind) {
  statusText.textContent = text;
  statusEl.className = 'status' + (kind ? ' ' + kind : '');
}

async function run(url, options, message) {
  setStatus(message, 'live');
  document.getElementById('scan').disabled = true;
  try {
    const res = await fetch(url, options);
    const data = await res.json();
    if (data.error) { setStatus(data.error, 'error'); return; }
    if (data.empty) { setStatus('No cached scan yet — paste a key and scan.', ''); return; }
    render(data);
    const when = new Date(data.scannedAt * 1000).toLocaleTimeString();
    setStatus((data.fromCache ? 'Cached scan from ' : 'Scanned ') + when +
      ' · ' + data.matches.length + ' matches · ' + data.requests + ' requests' +
      ((data.missing || []).length ? ' · skipped ' + data.missing.join(', ') : ''), '');
  } catch (err) {
    setStatus('Request failed: ' + err.message, 'error');
  } finally {
    document.getElementById('scan').disabled = false;
  }
}

document.getElementById('scan').addEventListener('click', () => {
  const key = document.getElementById('key').value.trim();
  if (!key) { setStatus('Paste an OddsPapi key first.', 'error'); return; }
  try { sessionStorage.setItem('oddspapi_key', key); } catch (e) { /* private mode */ }
  run('/api/scan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ apiKey: key })
  }, 'Scanning — one request per bookmaker, throttled…');
});

document.getElementById('reload').addEventListener('click', () =>
  run('/api/cached', {}, 'Loading last scan…'));

try {
  const saved = sessionStorage.getItem('oddspapi_key');
  if (saved) document.getElementById('key').value = saved;
} catch (e) { /* private mode */ }

let resizeTimer = null;
addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => { if (STATE.meta) render(STATE.meta); }, 150);
});

run('/api/cached', {}, 'Loading last scan…');

/* ---------------- scheduled scanning ---------------- */

const schedState = document.getElementById('sched-state');

function renderSchedule(s) {
  if (!s) return;
  const bits = [];
  if (s.running) {
    bits.push('Running every ' + Math.round(s.intervalSeconds / 60) + ' min');
    bits.push(s.scans + ' scans, ' + s.spent + ' of ' + s.budget + ' requests spent');
    if (s.nextScanAt) bits.push('next at ' + new Date(s.nextScanAt).toLocaleTimeString());
  } else {
    bits.push(s.scans ? 'Stopped after ' + s.scans + ' scans (' + s.spent + ' requests)' : 'Idle.');
    if (s.stoppedBecause && s.scans) bits.push(s.stoppedBecause);
    if (s.lastError) bits.push(s.lastError);
  }
  schedState.textContent = bits.join(' · ');

  const alerts = s.alerts || [];
  document.getElementById('sched-alerts').innerHTML = alerts.length
    ? alerts.slice(0, 8).map(a =>
        '<div class="alert-row"><strong>+' + (a.ratio * 100).toFixed(2) + '%</strong> ' +
        a.market + ' — ' + a.fixture +
        ' <span class="when">£' + (a.profit || 0).toFixed(2) + ' on £' + (a.total || 0).toFixed(0) +
        ' · ' + (a.books || []).join(' / ') +
        ' · ' + new Date(a.at).toLocaleTimeString() + '</span></div>').join('')
    : '';
}

async function schedulePost(body) {
  const res = await fetch('/api/schedule', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  const data = await res.json();
  if (data.error || data.ok === false) {
    schedState.textContent = data.error || data.message;
    return;
  }
  renderSchedule(data.state);
}

document.getElementById('sched-start').addEventListener('click', () => {
  const key = document.getElementById('key').value.trim();
  if (!key) { schedState.textContent = 'Paste an OddsPapi key first.'; return; }
  schedulePost({
    apiKey: key,
    intervalSeconds: Number(document.getElementById('sched-interval').value),
    budgetRequests: Number(document.getElementById('sched-budget').value)
  });
});

document.getElementById('sched-stop').addEventListener('click', () =>
  schedulePost({ action: 'stop' }));

// Poll the schedule state so a running job stays visible across reloads.
setInterval(async () => {
  try { renderSchedule(await (await fetch('/api/schedule')).json()); } catch (e) { /* offline */ }
}, 5000);
fetch('/api/schedule').then(r => r.json()).then(renderSchedule).catch(() => {});
