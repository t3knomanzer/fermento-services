import React, { useState, useRef, useCallback, useEffect, useMemo } from 'react';

/* ───────── constants ───────── */
const STAGE_COLORS = [
  { fill: 'rgba(99,102,241,0.18)', stroke: '#6366f1', label: 'Stage 0 — Pre-fermentation' },
  { fill: 'rgba(16,185,129,0.18)', stroke: '#10b981', label: 'Stage 1 — Lag / Growth' },
  { fill: 'rgba(245,158,11,0.18)', stroke: '#f59e0b', label: 'Stage 2 — Active' },
  { fill: 'rgba(239,68,68,0.18)',  stroke: '#ef4444', label: 'Stage 3 — Mature / Decline' },
  { fill: 'rgba(168,85,247,0.18)', stroke: '#a855f7', label: 'Stage 4' },
  { fill: 'rgba(6,182,212,0.18)',  stroke: '#06b6d4', label: 'Stage 5' },
];

const API = process.env.REACT_APP_API_URL || '';

const MARGIN = { top: 32, right: 60, bottom: 56, left: 64 };
const WIDTH = 1200;
const HEIGHT = 420;
const INNER_W = WIDTH - MARGIN.left - MARGIN.right;
const INNER_H = HEIGHT - MARGIN.top - MARGIN.bottom;

/* ───────── helpers ───────── */
function formatDuration(ms) {
  const totalMin = Math.round(ms / 60000);
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function parseTimestamp(ts) {
  return new Date(ts.replace(' ', 'T')).getTime();
}

/** Convert browser mouse coords to SVG viewBox coords using the SVG CTM */
function clientToSvg(svg, clientX, clientY) {
  const pt = svg.createSVGPoint();
  pt.x = clientX;
  pt.y = clientY;
  const ctm = svg.getScreenCTM();
  if (!ctm) return { x: 0, y: 0 };
  const svgPt = pt.matrixTransform(ctm.inverse());
  return { x: svgPt.x, y: svgPt.y };
}

/** Find the data-row index closest to a chart-local x position */
function closestIndex(chartX, timestamps, xScale) {
  let best = 0;
  let bestDist = Infinity;
  for (let i = 0; i < timestamps.length; i++) {
    const d = Math.abs(xScale(timestamps[i]) - chartX);
    if (d < bestDist) { bestDist = d; best = i; }
  }
  return best;
}

/** Recompute boundary indices from stage column of current data */
function getBoundaries(data) {
  const b = [];
  for (let i = 1; i < data.length; i++) {
    if (Number(data[i].stage) !== Number(data[i - 1].stage)) b.push(i);
  }
  return b;
}

/* ───────── main app ───────── */
export default function App() {
  const [data, setData] = useState(null);
  const [filename, setFilename] = useState('');
  const [headers, setHeaders] = useState([]);
  const [metric, setMetric] = useState('distance');
  const [showCO2, setShowCO2] = useState(false);
  const [showTemp, setShowTemp] = useState(false);
  const [showHumidity, setShowHumidity] = useState(false);
  const [showMaxGrowth, setShowMaxGrowth] = useState(false);
  const [showMaxCO2, setShowMaxCO2] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragIdx, setDragIdx] = useState(null);
  const [hoverInfo, setHoverInfo] = useState(null);
  const svgRef = useRef(null);
  const fileInputRef = useRef(null);
  // mutable ref so the drag handler always reads the latest data
  const dataRef = useRef(data);
  dataRef.current = data;

  /* ── upload ── */
  const handleUpload = useCallback(async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await fetch(`${API}/api/upload`, { method: 'POST', body: form });
      const json = await res.json();
      setData(json.data);
      setHeaders(json.headers);
      setFilename(json.filename);
      const numCols = json.headers.filter(h => h !== 'timestamp' && h !== 'stage');
      if (numCols.includes('distance')) setMetric('distance');
      else if (numCols.length) setMetric(numCols[0]);
    } catch (err) {
      alert('Upload failed: ' + err.message);
    }
    setUploading(false);
    e.target.value = '';
  }, []);

  /* ── download ── */
  const handleDownload = useCallback(async () => {
    if (!data) return;
    try {
      const res = await fetch(`${API}/api/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename, headers, data }),
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert('Download failed: ' + err.message);
    }
  }, [data, filename, headers]);

  /* ── computed chart values ── */
  const chartData = useMemo(() => {
    if (!data) return null;
    const timestamps = data.map(d => parseTimestamp(d.timestamp));
    const tMin = Math.min(...timestamps);
    const tMax = Math.max(...timestamps);
    const tRange = tMax - tMin || 1;

    const vals = data.map(d => Number(d[metric]) || 0);
    const vMin = Math.min(...vals);
    const vMax = Math.max(...vals);
    const vRange = vMax - vMin || 1;

    const co2 = data.map(d => Number(d.co2) || 0);
    const co2Min = Math.min(...co2);
    const co2Max = Math.max(...co2);
    const co2Range = co2Max - co2Min || 1;

    const temp = data.map(d => Number(d.temperature) || 0);
    const tempMin = Math.min(...temp);
    const tempMax = Math.max(...temp);
    const tempRange = tempMax - tempMin || 1;

    const hum = data.map(d => Number(d.humidity) || 0);
    const humMin = Math.min(...hum);
    const humMax = Math.max(...hum);
    const humRange = humMax - humMin || 1;

    const xScale    = (t) => ((t - tMin) / tRange) * INNER_W;
    const yScale    = (v) => INNER_H - ((v - vMin) / vRange) * INNER_H;
    const co2YScale = (v) => INNER_H - ((v - co2Min) / co2Range) * INNER_H;
    const tempYScale = (v) => INNER_H - ((v - tempMin) / tempRange) * INNER_H;
    const humYScale  = (v) => INNER_H - ((v - humMin) / humRange) * INNER_H;

    const stages = data.map(d => Number(d.stage));
    const boundaries = getBoundaries(data);

    const ranges = [];
    let start = 0;
    for (const b of boundaries) {
      ranges.push({ stage: stages[start], start, end: b - 1 });
      start = b;
    }
    ranges.push({ stage: stages[start], start, end: data.length - 1 });

    let maxGrowthIdx = 0;
    let maxGrowthRate = 0;
    for (let i = 1; i < data.length; i++) {
      const dt = (timestamps[i] - timestamps[i - 1]) / 60000;
      if (dt === 0) continue;
      const rate = Math.abs(vals[i] - vals[i - 1]) / dt;
      if (rate > maxGrowthRate) { maxGrowthRate = rate; maxGrowthIdx = i; }
    }

    let maxCO2Idx = 0;
    for (let i = 1; i < co2.length; i++) {
      if (co2[i] > co2[maxCO2Idx]) maxCO2Idx = i;
    }

    return {
      timestamps, tMin, tMax,
      vals, vMin, vMax,
      co2, co2Min, co2Max,
      temp, tempMin, tempMax,
      hum, humMin, humMax,
      xScale, yScale, co2YScale, tempYScale, humYScale,
      stages, boundaries, ranges,
      maxGrowthIdx, maxGrowthRate,
      maxCO2Idx,
    };
  }, [data, metric]);

  /* ── boundary dragging ── */
  const handlePointerDown = useCallback((boundaryIndex, e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragIdx(boundaryIndex);
  }, []);

  useEffect(() => {
    if (dragIdx === null) return;
    const svg = svgRef.current;
    if (!svg || !chartData) return;

    const { timestamps, xScale } = chartData;

    const onMove = (e) => {
      e.preventDefault();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      const svgPt = clientToSvg(svg, clientX, clientY);
      const chartX = svgPt.x - MARGIN.left;

      const target = closestIndex(chartX, timestamps, xScale);

      // always recompute boundaries from the CURRENT data, not stale memo
      const currentData = dataRef.current;
      const currentBounds = getBoundaries(currentData);

      const prev = dragIdx > 0 ? currentBounds[dragIdx - 1] : 1;
      const next = dragIdx < currentBounds.length - 1 ? currentBounds[dragIdx + 1] : currentData.length - 1;
      const clamped = Math.max(prev + 1, Math.min(next - 1, target));

      const oldBoundary = currentBounds[dragIdx];
      if (clamped === oldBoundary) return;

      setData(prev => {
        const newData = prev.map(row => ({ ...row }));

        if (clamped > oldBoundary) {
          // moved right → extend left stage
          const leftStage = Number(newData[oldBoundary - 1].stage);
          for (let i = oldBoundary; i < clamped; i++) {
            newData[i].stage = leftStage;
          }
        } else {
          // moved left → extend right stage
          const rightStage = Number(newData[oldBoundary].stage);
          for (let i = clamped; i < oldBoundary; i++) {
            newData[i].stage = rightStage;
          }
        }
        return newData;
      });
    };

    const onUp = () => setDragIdx(null);

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    window.addEventListener('touchmove', onMove, { passive: false });
    window.addEventListener('touchend', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      window.removeEventListener('touchmove', onMove);
      window.removeEventListener('touchend', onUp);
    };
  }, [dragIdx, chartData]);

  /* ── hover tooltip ── */
  const handleMouseMove = useCallback((e) => {
    if (!svgRef.current || !chartData || dragIdx !== null) {
      setHoverInfo(null);
      return;
    }
    const svgPt = clientToSvg(svgRef.current, e.clientX, e.clientY);
    const chartX = svgPt.x - MARGIN.left;

    if (chartX < 0 || chartX > INNER_W) {
      setHoverInfo(null);
      return;
    }

    const idx = closestIndex(chartX, chartData.timestamps, chartData.xScale);
    setHoverInfo({ idx, x: chartData.xScale(chartData.timestamps[idx]) });
  }, [chartData, dragIdx]);

  /* ── x-axis ticks ── */
  const xTicks = useMemo(() => {
    if (!chartData || !data) return [];
    const count = 10;
    const step = Math.max(1, Math.floor(data.length / count));
    const ticks = [];
    for (let i = 0; i < data.length; i += step) {
      const t = chartData.timestamps[i];
      const d = new Date(t);
      ticks.push({
        x: chartData.xScale(t),
        label: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });
    }
    return ticks;
  }, [chartData, data]);

  /* ── render: landing ── */
  if (!data) {
    return (
      <div style={styles.landing}>
        <div style={styles.landingInner}>
          <div style={styles.logoMark}>⬡</div>
          <h1 style={styles.landingTitle}>Fermento</h1>
          <p style={styles.landingSubtitle}>Stage Boundary Editor</p>
          <p style={styles.landingDesc}>
            Upload a fermentation run CSV to visualize sensor data and interactively
            adjust stage boundaries by dragging.
          </p>
          <button
            style={styles.uploadBtn}
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? 'Processing…' : 'Upload CSV'}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            style={{ display: 'none' }}
            onChange={handleUpload}
          />
        </div>
      </div>
    );
  }

  const numericCols = headers.filter(h => h !== 'timestamp' && h !== 'stage');

  return (
    <div style={styles.root}>
      {/* header */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={styles.logoSmall}>⬡</span>
          <span style={styles.brand}>Fermento</span>
          <span style={styles.filename}>{filename}</span>
          <span style={styles.rowCount}>{data.length} rows</span>
        </div>
        <div style={styles.headerRight}>
          <button style={styles.btnSecondary} onClick={() => fileInputRef.current?.click()}>
            New file
          </button>
          <button style={styles.btnPrimary} onClick={handleDownload}>
            ↓ Download
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            style={{ display: 'none' }}
            onChange={handleUpload}
          />
        </div>
      </header>

      {/* toolbar */}
      <div style={styles.toolbar}>
        <div style={styles.toolSection}>
          <label style={styles.toolLabel}>Primary metric</label>
          <select style={styles.select} value={metric} onChange={(e) => setMetric(e.target.value)}>
            {numericCols.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div style={styles.toolSection}>
          <label style={styles.toolLabel}>Overlays</label>
          <div style={styles.toggleGroup}>
            {metric !== 'co2' && <ToggleChip label="CO₂" color="#f59e0b" active={showCO2} onClick={() => setShowCO2(v => !v)} />}
            {metric !== 'temperature' && <ToggleChip label="Temp" color="#ef4444" active={showTemp} onClick={() => setShowTemp(v => !v)} />}
            {metric !== 'humidity' && <ToggleChip label="Humidity" color="#06b6d4" active={showHumidity} onClick={() => setShowHumidity(v => !v)} />}
          </div>
        </div>
        <div style={styles.toolSection}>
          <label style={styles.toolLabel}>Helpers</label>
          <div style={styles.toggleGroup}>
            <ToggleChip label="Max Δ rate" color="#a855f7" active={showMaxGrowth} onClick={() => setShowMaxGrowth(v => !v)} />
            <ToggleChip label="Max CO₂" color="#f59e0b" active={showMaxCO2} onClick={() => setShowMaxCO2(v => !v)} />
          </div>
        </div>
        <div style={styles.toolSection}>
          <label style={styles.toolLabel}>Stages</label>
          <div style={styles.toggleGroup}>
            {chartData?.ranges.map((r, i) => (
              <span key={i} style={{
                ...styles.legendChip,
                background: STAGE_COLORS[r.stage % STAGE_COLORS.length].fill,
                borderColor: STAGE_COLORS[r.stage % STAGE_COLORS.length].stroke,
                color: STAGE_COLORS[r.stage % STAGE_COLORS.length].stroke,
              }}>
                {r.stage}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* chart */}
      <div style={styles.chartWrap}>
        <svg
          ref={svgRef}
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          style={styles.svg}
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setHoverInfo(null)}
        >
          <defs>
            {STAGE_COLORS.map((c, i) => (
              <linearGradient key={i} id={`stage-grad-${i}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={c.stroke} stopOpacity={0.25} />
                <stop offset="100%" stopColor={c.stroke} stopOpacity={0.04} />
              </linearGradient>
            ))}
          </defs>

          <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
            {/* grid */}
            {[0, 0.25, 0.5, 0.75, 1].map(frac => (
              <line key={frac} x1={0} y1={frac * INNER_H} x2={INNER_W} y2={frac * INNER_H}
                stroke="rgba(255,255,255,0.06)" strokeWidth={1} />
            ))}

            {/* stage regions */}
            {chartData?.ranges.map((r, i) => {
              const x0 = chartData.xScale(chartData.timestamps[r.start]);
              const x1 = chartData.xScale(chartData.timestamps[r.end]);
              const sc = STAGE_COLORS[r.stage % STAGE_COLORS.length];
              const dur = chartData.timestamps[r.end] - chartData.timestamps[r.start];
              const midX = (x0 + x1) / 2;
              return (
                <g key={i}>
                  <rect x={x0} y={0} width={Math.max(0, x1 - x0)} height={INNER_H}
                    fill={`url(#stage-grad-${r.stage % STAGE_COLORS.length})`} />
                  {(x1 - x0) > 40 && (<>
                    <text x={midX} y={16} textAnchor="middle" fill={sc.stroke}
                      fontSize={11} fontFamily="JetBrains Mono, monospace" fontWeight={600}>
                      Stage {r.stage}
                    </text>
                    <text x={midX} y={30} textAnchor="middle" fill={sc.stroke}
                      fontSize={10} fontFamily="JetBrains Mono, monospace" opacity={0.7}>
                      {formatDuration(dur)}
                    </text>
                  </>)}
                </g>
              );
            })}

            {/* primary metric */}
            {chartData && (
              <polyline
                points={data.map((_, i) =>
                  `${chartData.xScale(chartData.timestamps[i])},${chartData.yScale(chartData.vals[i])}`
                ).join(' ')}
                fill="none" stroke="#e2e8f0" strokeWidth={1.5} strokeLinejoin="round"
              />
            )}

            {/* overlays */}
            {showCO2 && metric !== 'co2' && chartData && (
              <polyline
                points={data.map((_, i) =>
                  `${chartData.xScale(chartData.timestamps[i])},${chartData.co2YScale(chartData.co2[i])}`
                ).join(' ')}
                fill="none" stroke="#f59e0b" strokeWidth={1} strokeOpacity={0.6} strokeLinejoin="round"
              />
            )}
            {showTemp && metric !== 'temperature' && chartData && (
              <polyline
                points={data.map((_, i) =>
                  `${chartData.xScale(chartData.timestamps[i])},${chartData.tempYScale(chartData.temp[i])}`
                ).join(' ')}
                fill="none" stroke="#ef4444" strokeWidth={1} strokeOpacity={0.6} strokeLinejoin="round"
              />
            )}
            {showHumidity && metric !== 'humidity' && chartData && (
              <polyline
                points={data.map((_, i) =>
                  `${chartData.xScale(chartData.timestamps[i])},${chartData.humYScale(chartData.hum[i])}`
                ).join(' ')}
                fill="none" stroke="#06b6d4" strokeWidth={1} strokeOpacity={0.6} strokeLinejoin="round"
              />
            )}

            {/* helper lines */}
            {showMaxGrowth && chartData && (
              <g>
                <line
                  x1={chartData.xScale(chartData.timestamps[chartData.maxGrowthIdx])} y1={0}
                  x2={chartData.xScale(chartData.timestamps[chartData.maxGrowthIdx])} y2={INNER_H}
                  stroke="#a855f7" strokeWidth={1.5} strokeDasharray="6 3" />
                <text
                  x={chartData.xScale(chartData.timestamps[chartData.maxGrowthIdx]) + 5} y={INNER_H - 8}
                  fill="#a855f7" fontSize={10} fontFamily="JetBrains Mono, monospace">
                  Max Δ {chartData.maxGrowthRate.toFixed(2)}/min
                </text>
              </g>
            )}
            {showMaxCO2 && chartData && (
              <g>
                <line
                  x1={chartData.xScale(chartData.timestamps[chartData.maxCO2Idx])} y1={0}
                  x2={chartData.xScale(chartData.timestamps[chartData.maxCO2Idx])} y2={INNER_H}
                  stroke="#f59e0b" strokeWidth={1.5} strokeDasharray="6 3" />
                <text
                  x={chartData.xScale(chartData.timestamps[chartData.maxCO2Idx]) + 5} y={INNER_H - 22}
                  fill="#f59e0b" fontSize={10} fontFamily="JetBrains Mono, monospace">
                  Max CO₂: {chartData.co2[chartData.maxCO2Idx]}
                </text>
              </g>
            )}

            {/* draggable boundary lines */}
            {chartData?.boundaries.map((bIdx, i) => {
              const bx = chartData.xScale(chartData.timestamps[bIdx]);
              const isDragging = dragIdx === i;
              return (
                <g key={i} onPointerDown={(e) => handlePointerDown(i, e)}
                  style={{ cursor: 'ew-resize', touchAction: 'none' }}>
                  <rect x={bx - 10} y={0} width={20} height={INNER_H} fill="transparent" />
                  <line x1={bx} y1={0} x2={bx} y2={INNER_H}
                    stroke={isDragging ? '#fff' : 'rgba(255,255,255,0.5)'}
                    strokeWidth={isDragging ? 2.5 : 1.5}
                    strokeDasharray={isDragging ? 'none' : '4 2'} />
                  <polygon
                    points={`${bx},${INNER_H / 2 - 10} ${bx + 8},${INNER_H / 2} ${bx},${INNER_H / 2 + 10} ${bx - 8},${INNER_H / 2}`}
                    fill={isDragging ? '#fff' : 'rgba(255,255,255,0.8)'}
                    stroke={isDragging ? '#6366f1' : 'rgba(255,255,255,0.3)'}
                    strokeWidth={1.5} />
                </g>
              );
            })}

            {/* hover crosshair */}
            {hoverInfo && chartData && (
              <g>
                <line x1={hoverInfo.x} y1={0} x2={hoverInfo.x} y2={INNER_H}
                  stroke="rgba(255,255,255,0.3)" strokeWidth={1} />
                <circle cx={hoverInfo.x} cy={chartData.yScale(chartData.vals[hoverInfo.idx])}
                  r={4} fill="#e2e8f0" stroke="#0f1117" strokeWidth={2} />
              </g>
            )}

            {/* x-axis */}
            {xTicks.map((t, i) => (
              <text key={i} x={t.x} y={INNER_H + 20} textAnchor="middle"
                fill="rgba(255,255,255,0.4)" fontSize={10} fontFamily="JetBrains Mono, monospace">
                {t.label}
              </text>
            ))}

            {/* y-axis */}
            {chartData && [0, 0.25, 0.5, 0.75, 1].map(frac => {
              const val = chartData.vMin + (1 - frac) * (chartData.vMax - chartData.vMin);
              return (
                <text key={frac} x={-8} y={frac * INNER_H + 4} textAnchor="end"
                  fill="rgba(255,255,255,0.4)" fontSize={10} fontFamily="JetBrains Mono, monospace">
                  {Number.isInteger(val) ? val : val.toFixed(1)}
                </text>
              );
            })}

            <text x={-8} y={-12} fill="rgba(255,255,255,0.5)"
              fontSize={11} fontFamily="DM Sans, sans-serif" fontWeight={600}>
              {metric}
            </text>
          </g>
        </svg>

        {/* tooltip */}
        {hoverInfo && data[hoverInfo.idx] && (
          <div style={{
            ...styles.tooltip,
            left: `${((hoverInfo.x + MARGIN.left) / WIDTH) * 100}%`,
          }}>
            <div style={styles.tooltipTime}>{data[hoverInfo.idx].timestamp}</div>
            <div><b>{metric}:</b> {data[hoverInfo.idx][metric]}</div>
            <div><b>CO₂:</b> {data[hoverInfo.idx].co2}</div>
            <div><b>Temp:</b> {data[hoverInfo.idx].temperature}°</div>
            <div><b>Humidity:</b> {data[hoverInfo.idx].humidity}%</div>
            <div><b>Stage:</b> {data[hoverInfo.idx].stage}</div>
          </div>
        )}
      </div>

      <div style={styles.instructions}>
        <span style={styles.instructionIcon}>◇</span>
        Drag the diamond handles on stage boundaries to adjust. Changes update the stage column in real-time.
        Download when finished.
      </div>
    </div>
  );
}

/* ── toggle chip ── */
function ToggleChip({ label, color, active, onClick }) {
  return (
    <button onClick={onClick} style={{
      ...styles.chip,
      background: active ? color + '22' : 'transparent',
      borderColor: active ? color : 'rgba(255,255,255,0.15)',
      color: active ? color : 'rgba(255,255,255,0.5)',
    }}>
      <span style={{
        width: 8, height: 8, borderRadius: '50%',
        background: active ? color : 'rgba(255,255,255,0.2)',
        display: 'inline-block', marginRight: 6,
      }} />
      {label}
    </button>
  );
}

/* ───────── styles ───────── */
const styles = {
  root: { minHeight: '100vh', background: '#0f1117', color: '#e2e8f0', fontFamily: 'DM Sans, sans-serif' },
  landing: {
    minHeight: '100vh', background: '#0f1117', display: 'flex',
    alignItems: 'center', justifyContent: 'center', fontFamily: 'DM Sans, sans-serif', color: '#e2e8f0',
  },
  landingInner: { textAlign: 'center', maxWidth: 420, padding: 40 },
  logoMark: { fontSize: 56, color: '#6366f1', marginBottom: 16 },
  landingTitle: { fontSize: 40, fontWeight: 700, margin: 0, letterSpacing: '-0.03em' },
  landingSubtitle: { fontSize: 16, color: 'rgba(255,255,255,0.4)', margin: '4px 0 24px', fontFamily: 'JetBrains Mono, monospace' },
  landingDesc: { fontSize: 15, lineHeight: 1.6, color: 'rgba(255,255,255,0.55)', marginBottom: 32 },
  uploadBtn: {
    background: '#6366f1', color: '#fff', border: 'none', borderRadius: 8,
    padding: '14px 36px', fontSize: 15, fontWeight: 600, cursor: 'pointer', fontFamily: 'DM Sans, sans-serif',
  },
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '12px 24px', borderBottom: '1px solid rgba(255,255,255,0.08)',
    background: 'rgba(15,17,23,0.95)', backdropFilter: 'blur(12px)',
    position: 'sticky', top: 0, zIndex: 100,
  },
  headerLeft: { display: 'flex', alignItems: 'center', gap: 12 },
  logoSmall: { fontSize: 22, color: '#6366f1' },
  brand: { fontWeight: 700, fontSize: 18, letterSpacing: '-0.02em' },
  filename: {
    fontFamily: 'JetBrains Mono, monospace', fontSize: 13, color: 'rgba(255,255,255,0.5)',
    background: 'rgba(255,255,255,0.06)', padding: '4px 10px', borderRadius: 6,
  },
  rowCount: { fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: 'rgba(255,255,255,0.35)' },
  headerRight: { display: 'flex', gap: 8 },
  btnSecondary: {
    background: 'rgba(255,255,255,0.06)', color: '#e2e8f0',
    border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6,
    padding: '8px 16px', fontSize: 13, cursor: 'pointer', fontFamily: 'DM Sans, sans-serif',
  },
  btnPrimary: {
    background: '#6366f1', color: '#fff', border: 'none', borderRadius: 6,
    padding: '8px 16px', fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'DM Sans, sans-serif',
  },
  toolbar: {
    display: 'flex', alignItems: 'center', gap: 24, padding: '12px 24px',
    borderBottom: '1px solid rgba(255,255,255,0.06)', flexWrap: 'wrap',
  },
  toolSection: { display: 'flex', alignItems: 'center', gap: 8 },
  toolLabel: {
    fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em',
    color: 'rgba(255,255,255,0.35)', fontFamily: 'JetBrains Mono, monospace',
  },
  select: {
    background: 'rgba(255,255,255,0.06)', color: '#e2e8f0',
    border: '1px solid rgba(255,255,255,0.12)', borderRadius: 6,
    padding: '6px 10px', fontSize: 13, fontFamily: 'JetBrains Mono, monospace', outline: 'none',
  },
  toggleGroup: { display: 'flex', gap: 6 },
  chip: {
    display: 'inline-flex', alignItems: 'center', padding: '4px 10px',
    borderRadius: 20, border: '1px solid', fontSize: 12,
    fontFamily: 'JetBrains Mono, monospace', cursor: 'pointer', background: 'none',
  },
  legendChip: {
    display: 'inline-flex', alignItems: 'center', padding: '3px 10px',
    borderRadius: 20, border: '1px solid', fontSize: 11,
    fontFamily: 'JetBrains Mono, monospace', fontWeight: 600,
  },
  chartWrap: { position: 'relative', padding: '24px 24px 8px' },
  svg: { width: '100%', height: 'auto', display: 'block', userSelect: 'none' },
  tooltip: {
    position: 'absolute', top: 8, transform: 'translateX(-50%)',
    background: 'rgba(15,17,23,0.92)', border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: 8, padding: '10px 14px', fontSize: 12,
    fontFamily: 'JetBrains Mono, monospace', color: '#e2e8f0', lineHeight: 1.6,
    pointerEvents: 'none', whiteSpace: 'nowrap', zIndex: 50, backdropFilter: 'blur(8px)',
  },
  tooltipTime: { fontWeight: 700, marginBottom: 4, color: '#6366f1' },
  instructions: {
    textAlign: 'center', padding: '16px 24px', fontSize: 13,
    color: 'rgba(255,255,255,0.35)', fontFamily: 'JetBrains Mono, monospace',
  },
  instructionIcon: { color: 'rgba(255,255,255,0.5)', marginRight: 8 },
};
