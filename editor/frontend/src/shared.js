/* shared.js — Constants, helpers, style tokens shared across the app */

/* ── stage colors ── */
export const STAGE_COLORS = [
  { fill: 'rgba(99,102,241,0.18)', stroke: '#6366f1', bg: '#6366f1' },
  { fill: 'rgba(16,185,129,0.18)', stroke: '#10b981', bg: '#10b981' },
  { fill: 'rgba(245,158,11,0.18)', stroke: '#f59e0b', bg: '#f59e0b' },
  { fill: 'rgba(239,68,68,0.18)',  stroke: '#ef4444', bg: '#ef4444' },
  { fill: 'rgba(168,85,247,0.18)', stroke: '#a855f7', bg: '#a855f7' },
  { fill: 'rgba(6,182,212,0.18)',  stroke: '#06b6d4', bg: '#06b6d4' },
];

export const STAGE_NAMES = { 0: 'Lag', 1: 'Exponential', 2: 'Peak', 3: 'Decline' };

export const STAGE_CHART_COLORS = {
  Lag: '#6baed6', Exponential: '#74c476', Peak: '#fdd835', Decline: '#ef6c57',
};

export const OVERLAY_COLORS = {
  co2: '#f59e0b', temperature: '#ef4444', humidity: '#06b6d4',
  growth_norm: '#a855f7', co2_norm: '#22d3ee', distance: '#94a3b8',
};

export const BAND_DEFS = [
  { label: '22–25', lo: 22, hi: 25, color: '#60a5fa' },
  { label: '25–28', lo: 25, hi: 28, color: '#34d399' },
  { label: '28–31', lo: 28, hi: 31, color: '#fbbf24' },
  { label: '31–34', lo: 31, hi: 34, color: '#fb923c' },
  { label: '34–36', lo: 34, hi: 36, color: '#f87171' },
];

/* ── theme tokens ── */
export const T = {
  bg: '#0f1117',
  panel: '#181c27',
  grid: '#252a38',
  dim: '#5a5f72',
  txt: '#9ca0af',
  bright: '#d4d8e4',
  white: '#eceff8',
  green: '#22c55e',
  amber: '#f59e0b',
  red: '#ef4444',
  cyan: '#38bdf8',
  indigo: '#6366f1',
};

export const mono = 'JetBrains Mono, monospace';
export const sans = 'DM Sans, sans-serif';

/* ── API ── */
export const API = process.env.REACT_APP_API_URL || '';

/* ── helpers ── */
export function parseTs(ts) {
  return new Date(ts.replace(' ', 'T')).getTime();
}

export function fmtDur(ms) {
  const m = Math.round(ms / 60000);
  const h = Math.floor(m / 60);
  return h > 0 ? `${h}h ${m % 60}m` : `${m}m`;
}

export function fmtMin(min) {
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return h > 0 ? `${h}h ${m}m` : `${Math.round(min)}m`;
}

export function sc(stage) {
  const s = Number(stage);
  const idx = Number.isFinite(s) ? Math.abs(Math.round(s)) % STAGE_COLORS.length : 0;
  return STAGE_COLORS[idx] || STAGE_COLORS[0];
}

export function clientToSvg(svg, cx, cy) {
  const pt = svg.createSVGPoint();
  pt.x = cx; pt.y = cy;
  const ctm = svg.getScreenCTM();
  if (!ctm) return { x: 0, y: 0 };
  return pt.matrixTransform(ctm.inverse());
}

export function closestIdx(chartX, timestamps, xScale) {
  let best = 0, bestD = Infinity;
  for (let i = 0; i < timestamps.length; i++) {
    const d = Math.abs(xScale(timestamps[i]) - chartX);
    if (d < bestD) { bestD = d; best = i; }
  }
  return best;
}

export function getBounds(data) {
  const b = [];
  for (let i = 1; i < data.length; i++) {
    if (Number(data[i].stage) !== Number(data[i - 1].stage)) b.push(i);
  }
  return b;
}

export function ensureStage(rows, numStages = 4) {
  const chunk = Math.ceil(rows.length / numStages);
  return rows.map((r, i) => {
    const v = r.stage !== undefined && r.stage !== '' ? Number(r.stage) : NaN;
    return { ...r, stage: Number.isFinite(v) ? v : Math.min(Math.floor(i / chunk), numStages - 1) };
  });
}

export function addGrowth(rows) {
  const dists = rows.map(r => Number(r.distance) || 0);
  const mx = Math.max(...dists);
  return rows.map((r, i) => ({ ...r, growth: mx - dists[i] }));
}

/**
 * Build a run profile (stats summary) from a single run's row data.
 * Mirrors _build_run_profiles from analysis.py
 */
export function buildRunProfile(runId, rows) {
  const timestamps = rows.map(r => parseTs(r.timestamp));
  const t0 = timestamps[0];
  const elapsed = timestamps.map(t => (t - t0) / 60000); // minutes
  const dists = rows.map(r => Number(r.distance) || 0);
  const rise = dists.map(d => dists[0] - d);
  const temps = rows.map(r => Number(r.temperature) || 0);
  const co2s = rows.map(r => Number(r.co2) || 0);
  const stages = rows.map(r => Number(r.stage) || 0);

  const meanTemp = temps.reduce((a, b) => a + b, 0) / temps.length;
  const duration = elapsed[elapsed.length - 1];
  const totalRise = Math.max(...rise);
  const co2Max = Math.max(...co2s);

  // per-stage durations
  const stageDurs = {};
  const stageStarts = {};
  for (let s = 0; s < 4; s++) {
    const indices = stages.map((st, i) => st === s ? i : -1).filter(i => i >= 0);
    if (indices.length > 0) {
      stageStarts[s] = elapsed[indices[0]];
      stageDurs[s] = elapsed[indices[indices.length - 1]] - elapsed[indices[0]];
    }
  }

  return {
    run: String(runId),
    temp: meanTemp,
    duration,
    samples: rows.length,
    totalRise,
    co2Max,
    lagDur: stageDurs[0] || 0,
    expDur: stageDurs[1] || 0,
    peakDur: stageDurs[2] || 0,
    decDur: stageDurs[3] || 0,
    lagStart: stageStarts[0] || 0,
    expStart: stageStarts[1] || 0,
    peakStart: stageStarts[2] || 0,
    decStart: stageStarts[3] || 0,
  };
}
