/* Editor.js — Single-run stage boundary editor. Always mounted (hidden when inactive). */
import React, { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import {
  STAGE_COLORS, OVERLAY_COLORS, sc, parseTs, fmtDur, clientToSvg,
  closestIdx, getBounds, ensureStage, addGrowth, API, mono, sans, T,
} from './shared';

const MARGIN = { top: 32, right: 16, bottom: 56, left: 64 };
const WIDTH = 1200, HEIGHT = 420;
const IW = WIDTH - MARGIN.left - MARGIN.right;
const IH = HEIGHT - MARGIN.top - MARGIN.bottom;

function oColor(k) { return OVERLAY_COLORS[k] || '#94a3b8'; }

export default function Editor({
  initialData, initialHeaders, initialFilename,
  onSave, onClose, embedded,
}) {
  const [data, setDataRaw] = useState(null);
  const [filename, setFilename] = useState('');
  const [headers, setHeaders] = useState([]);
  const [removedCols, setRemovedCols] = useState([]);
  const [metric, setMetric] = useState('growth');
  const [overlays, setOverlays] = useState({});
  const [showMaxGrowth, setShowMaxGrowth] = useState(false);
  const [showMaxCO2, setShowMaxCO2] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragIdx, setDragIdx] = useState(null);
  const [hoverIdx, setHoverIdx] = useState(null);
  const [showColMgr, setShowColMgr] = useState(false);
  const [ghostBoundaries, setGhostBoundaries] = useState(null); // original stage boundary indices
  const svgRef = useRef(null);
  const fileInputRef = useRef(null);
  const dataRef = useRef(data);
  const headersRef = useRef(headers);
  const filenameRef = useRef(filename);
  const onSaveRef = useRef(onSave);
  onSaveRef.current = onSave;

  // Track which file we've loaded to detect new-run-from-report
  const loadedFileRef = useRef(null);

  // Wrapped setData that auto-saves to parent
  const setData = useCallback((updater) => {
    setDataRaw(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      dataRef.current = next;
      setTimeout(() => {
        if (next && filenameRef.current && onSaveRef.current) {
          onSaveRef.current(filenameRef.current, next, headersRef.current);
        }
      }, 0);
      return next;
    });
  }, []);

  useEffect(() => { headersRef.current = headers; }, [headers]);
  useEffect(() => { filenameRef.current = filename; }, [filename]);

  // Load/reload when initialData changes to a DIFFERENT file
  useEffect(() => {
    if (!initialData || !initialHeaders || !initialFilename) return;
    // Only reload if it's a different file than what we already have loaded
    if (loadedFileRef.current === initialFilename && dataRef.current) return;

    let rows = [...initialData];
    const hdrs = [...initialHeaders];
    const hadStages = hdrs.includes('stage');
    if (!hadStages) { rows = ensureStage(rows, 4); hdrs.push('stage'); }
    else { rows = ensureStage(rows, 4); }
    if (hdrs.includes('distance')) {
      rows = addGrowth(rows);
      if (!hdrs.includes('growth')) hdrs.push('growth');
    }
    // Save original stage boundaries as ghost reference
    if (hadStages) setGhostBoundaries(getBounds(rows));
    else setGhostBoundaries(null);
    setDataRaw(rows); dataRef.current = rows;
    setHeaders(hdrs); headersRef.current = hdrs;
    setFilename(initialFilename); filenameRef.current = initialFilename;
    loadedFileRef.current = initialFilename;
    const nc = hdrs.filter(h => h !== 'timestamp' && h !== 'stage');
    if (nc.includes('growth')) setMetric('growth');
    else if (nc.includes('distance')) setMetric('distance');
    else if (nc.length) setMetric(nc[0]);
  }, [initialData, initialHeaders, initialFilename]);

  const handleUpload = useCallback(async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const form = new FormData(); form.append('file', file);
    try {
      const res = await fetch(`${API}/api/upload`, { method: 'POST', body: form });
      const json = await res.json();
      let rows = json.data; const hdrs = [...json.headers];
      const hadStages = hdrs.includes('stage');
      if (!hadStages) { rows = ensureStage(rows, 4); hdrs.push('stage'); }
      else { rows = ensureStage(rows, 4); }
      if (hdrs.includes('distance')) { rows = addGrowth(rows); if (!hdrs.includes('growth')) hdrs.push('growth'); }
      if (hadStages) setGhostBoundaries(getBounds(rows));
      else setGhostBoundaries(null);
      setDataRaw(rows); dataRef.current = rows;
      setHeaders(hdrs); headersRef.current = hdrs;
      setFilename(json.filename); filenameRef.current = json.filename;
      loadedFileRef.current = json.filename;
      setRemovedCols([]); setOverlays({}); setHoverIdx(null); setDragIdx(null);
      const nc = hdrs.filter(h => h !== 'timestamp' && h !== 'stage');
      if (nc.includes('growth')) setMetric('growth');
      else if (nc.includes('distance')) setMetric('distance');
      else if (nc.length) setMetric(nc[0]);
      if (onSaveRef.current) onSaveRef.current(json.filename, rows, hdrs);
    } catch (err) { alert('Upload failed: ' + err.message); }
    setUploading(false); e.target.value = '';
  }, []);

  const handleDownload = useCallback(async () => {
    if (!dataRef.current) return;
    const eH = headersRef.current.filter(h => !removedCols.includes(h));
    const eD = dataRef.current.map(row => { const o = {}; for (const h of eH) o[h] = row[h] ?? ''; return o; });
    try {
      const res = await fetch(`${API}/api/download`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: filenameRef.current, headers: eH, data: eD }),
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = filenameRef.current; a.click();
      URL.revokeObjectURL(url);
    } catch (err) { alert('Download failed: ' + err.message); }
  }, [removedCols]);

  const numericCols = useMemo(() => {
    if (!data || !data.length) return [];
    return headers.filter(h => {
      if (h === 'timestamp' || h === 'stage') return false;
      const v = data[0]?.[h]; return typeof v === 'number' && Number.isFinite(v);
    });
  }, [data, headers]);

  const overlayKeys = useMemo(() => {
    if (!data || !data.length) return [];
    return Object.keys(data[0]).filter(k =>
      k !== 'timestamp' && k !== 'stage' && k !== metric &&
      typeof data[0][k] === 'number' && Number.isFinite(data[0][k])
    );
  }, [data, metric]);

  const chartData = useMemo(() => {
    if (!data || !data.length) return null;
    const timestamps = data.map(d => parseTs(d.timestamp));
    const tMin = Math.min(...timestamps), tMax = Math.max(...timestamps), tR = tMax - tMin || 1;
    const vals = data.map(d => Number(d[metric]) || 0);
    const vMin = Math.min(...vals), vMax = Math.max(...vals);
    const mkS = (key) => { const arr = data.map(d => Number(d[key]) || 0); const lo = Math.min(...arr), hi = Math.max(...arr), r = hi - lo || 1; return { arr, yScale: (v) => IH - ((v - lo) / r) * IH }; };
    const series = {};
    for (const k of Object.keys(overlays)) { if (overlays[k] && k !== metric && data[0][k] !== undefined) series[k] = mkS(k); }
    const xScale = (t) => ((t - tMin) / tR) * IW;
    const yScale = (v) => IH - ((v - vMin) / ((vMax - vMin) || 1)) * IH;
    const boundaries = getBounds(data);
    const stages = data.map(d => Number(d.stage) || 0);
    const ranges = []; let start = 0;
    for (const b of boundaries) { ranges.push({ stage: stages[start], start, end: b - 1 }); start = b; }
    ranges.push({ stage: stages[start], start, end: data.length - 1 });
    let mgIdx = 0, mgRate = 0;
    for (let i = 1; i < data.length; i++) { const dt = (timestamps[i] - timestamps[i - 1]) / 60000; if (!dt) continue; const rate = Math.abs(vals[i] - vals[i - 1]) / dt; if (rate > mgRate) { mgRate = rate; mgIdx = i; } }
    const co2Arr = data.map(d => Number(d.co2) || 0);
    let mc2Idx = 0; for (let i = 1; i < co2Arr.length; i++) { if (co2Arr[i] > co2Arr[mc2Idx]) mc2Idx = i; }
    return { timestamps, vals, vMin, vMax, xScale, yScale, series, boundaries, ranges, mgIdx, mgRate, mc2Idx, co2Max: co2Arr[mc2Idx] };
  }, [data, metric, overlays]);

  const xTicks = useMemo(() => {
    if (!chartData || !data) return [];
    const step = Math.max(1, Math.floor(data.length / 10));
    return Array.from({ length: Math.ceil(data.length / step) }, (_, j) => {
      const i = j * step; const t = chartData.timestamps[i];
      return { x: chartData.xScale(t), label: new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) };
    });
  }, [chartData, data]);

  const handlePointerDown = useCallback((i, e) => { e.preventDefault(); e.stopPropagation(); setDragIdx(i); }, []);

  useEffect(() => {
    if (dragIdx === null) return;
    const svg = svgRef.current; if (!svg || !chartData) return;
    const { timestamps, xScale } = chartData;
    const onMove = (e) => {
      e.preventDefault();
      const cx = e.touches ? e.touches[0].clientX : e.clientX;
      const cy = e.touches ? e.touches[0].clientY : e.clientY;
      const chartX = clientToSvg(svg, cx, cy).x - MARGIN.left;
      const target = closestIdx(chartX, timestamps, xScale);
      const cur = dataRef.current; const curB = getBounds(cur);
      if (dragIdx >= curB.length) return;
      const prev = dragIdx > 0 ? curB[dragIdx - 1] : 1;
      const next = dragIdx < curB.length - 1 ? curB[dragIdx + 1] : cur.length - 1;
      const cl = Math.max(prev + 1, Math.min(next - 1, target));
      const old = curB[dragIdx]; if (cl === old) return;
      setData(p => {
        const nd = p.map(r => ({ ...r }));
        if (cl > old) { const s = Number(nd[old - 1].stage); for (let i = old; i < cl; i++) nd[i].stage = s; }
        else { const s = Number(nd[old].stage); for (let i = cl; i < old; i++) nd[i].stage = s; }
        return nd;
      });
    };
    const onUp = () => setDragIdx(null);
    window.addEventListener('pointermove', onMove); window.addEventListener('pointerup', onUp);
    window.addEventListener('touchmove', onMove, { passive: false }); window.addEventListener('touchend', onUp);
    return () => { window.removeEventListener('pointermove', onMove); window.removeEventListener('pointerup', onUp); window.removeEventListener('touchmove', onMove); window.removeEventListener('touchend', onUp); };
  }, [dragIdx, chartData, setData]);

  const handleMouseMove = useCallback((e) => {
    if (!svgRef.current || !chartData || dragIdx !== null) { setHoverIdx(null); return; }
    const chartX = clientToSvg(svgRef.current, e.clientX, e.clientY).x - MARGIN.left;
    if (chartX < 0 || chartX > IW) { setHoverIdx(null); return; }
    setHoverIdx(closestIdx(chartX, chartData.timestamps, chartData.xScale));
  }, [chartData, dragIdx]);

  const toggleOverlay = (k) => setOverlays(p => ({ ...p, [k]: !p[k] }));
  const toggleColRemove = (h) => setRemovedCols(p => p.includes(h) ? p.filter(c => c !== h) : [...p, h]);

  /* ── Render ── */
  if (!data) {
    if (embedded) return <div style={{ padding: 24, color: T.dim, fontFamily: mono }}>No run selected. Right-click a data point in the Report to edit.</div>;
    return (
      <div style={S.landing}>
        <div style={S.landingInner}>
          <div style={S.logoMark}>⬡</div>
          <h1 style={S.landingTitle}>Fermento</h1>
          <p style={S.landingSub}>Stage Boundary Editor</p>
          <p style={S.landingDesc}>Upload a fermentation run CSV to visualize and edit stage boundaries.</p>
          <button style={S.uploadBtn} onClick={() => fileInputRef.current?.click()} disabled={uploading}>{uploading ? 'Processing…' : 'Upload CSV'}</button>
          <input ref={fileInputRef} type="file" accept=".csv" style={{ display: 'none' }} onChange={handleUpload} />
        </div>
      </div>
    );
  }

  const hovered = hoverIdx !== null && data[hoverIdx] ? data[hoverIdx] : null;

  return (
    <div style={S.root}>
      <header style={S.header}>
        <div style={S.hLeft}>
          {embedded && onClose && <button style={S.btnGhost} onClick={onClose}>← Report</button>}
          <span style={S.fname}>{filename}</span>
          <span style={S.rowCt}>{data.length} rows</span>
        </div>
        <div style={S.hRight}>
          {!embedded && <button style={S.btnGhost} onClick={() => setShowColMgr(v => !v)}>{showColMgr ? '✕ Cols' : '⚙ Cols'}</button>}
          {!embedded && <button style={S.btnSec} onClick={() => fileInputRef.current?.click()}>New</button>}
          <button style={S.btnPri} onClick={handleDownload}>↓ CSV</button>
          {!embedded && <input ref={fileInputRef} type="file" accept=".csv" style={{ display: 'none' }} onChange={handleUpload} />}
        </div>
      </header>
      {showColMgr && !embedded && (
        <div style={S.colMgr}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 2 }}>Export columns</div>
          <div style={{ fontSize: 11, color: T.dim, marginBottom: 10, fontFamily: mono }}>Unchecked columns excluded from download.</div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {headers.map(h => <label key={h} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, fontFamily: mono, cursor: 'pointer', color: T.bright }}>
              <input type="checkbox" checked={!removedCols.includes(h)} onChange={() => toggleColRemove(h)} style={{ accentColor: T.indigo }} />
              <span style={{ opacity: removedCols.includes(h) ? 0.4 : 1 }}>{h}</span>
            </label>)}
          </div>
        </div>
      )}
      <div style={S.toolbar}>
        <div style={S.tSec}><label style={S.tLbl}>Primary</label>
          <select style={S.sel} value={metric} onChange={e => setMetric(e.target.value)}>{numericCols.map(c => <option key={c} value={c}>{c}</option>)}</select>
        </div>
        <div style={S.tSec}><label style={S.tLbl}>Overlays</label>
          <div style={S.tGrp}>{overlayKeys.map(k => <Chip key={k} label={k} color={oColor(k)} active={!!overlays[k]} onClick={() => toggleOverlay(k)} />)}</div>
        </div>
        <div style={S.tSec}><label style={S.tLbl}>Helpers</label>
          <div style={S.tGrp}>
            <Chip label="Max Δ" color="#a855f7" active={showMaxGrowth} onClick={() => setShowMaxGrowth(v => !v)} />
            {data[0]?.co2 !== undefined && <Chip label="Max CO₂" color="#f59e0b" active={showMaxCO2} onClick={() => setShowMaxCO2(v => !v)} />}
          </div>
        </div>
      </div>
      <div style={S.main}>
        <div style={S.chartWrap}>
          <svg ref={svgRef} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} style={S.svg} onMouseMove={handleMouseMove} onMouseLeave={() => setHoverIdx(null)}>
            <defs>{STAGE_COLORS.map((c, i) => <linearGradient key={i} id={`esg${i}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={c.stroke} stopOpacity={0.25} /><stop offset="100%" stopColor={c.stroke} stopOpacity={0.04} /></linearGradient>)}</defs>
            <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
              {[0,.25,.5,.75,1].map(f=><line key={f} x1={0} y1={f*IH} x2={IW} y2={f*IH} stroke="rgba(255,255,255,0.06)"/>)}
              {chartData?.ranges.map((r,i)=>{const x0=chartData.xScale(chartData.timestamps[r.start]);const x1=chartData.xScale(chartData.timestamps[r.end]);const c=sc(r.stage);const dur=chartData.timestamps[r.end]-chartData.timestamps[r.start];const mid=(x0+x1)/2;const gIdx=(Number.isFinite(r.stage)?Math.abs(Math.round(r.stage)):0)%STAGE_COLORS.length;return(<g key={i}><rect x={x0} y={0} width={Math.max(0,x1-x0)} height={IH} fill={`url(#esg${gIdx})`}/>{(x1-x0)>50&&(<><text x={mid} y={16} textAnchor="middle" fill={c.stroke} fontSize={11} fontFamily={mono} fontWeight={600}>Stage {r.stage}</text><text x={mid} y={30} textAnchor="middle" fill={c.stroke} fontSize={10} fontFamily={mono} opacity={0.7}>{fmtDur(dur)}</text></>)}</g>);})}
              {chartData&&<polyline points={data.map((_,i)=>`${chartData.xScale(chartData.timestamps[i])},${chartData.yScale(chartData.vals[i])}`).join(' ')} fill="none" stroke="#e2e8f0" strokeWidth={1.5} strokeLinejoin="round"/>}
              {chartData&&Object.entries(chartData.series).map(([k,s])=><polyline key={k} points={data.map((_,i)=>`${chartData.xScale(chartData.timestamps[i])},${s.yScale(s.arr[i])}`).join(' ')} fill="none" stroke={oColor(k)} strokeWidth={1} strokeOpacity={0.6} strokeLinejoin="round"/>)}
              {showMaxGrowth&&chartData&&(()=>{const x=chartData.xScale(chartData.timestamps[chartData.mgIdx]);return(<g><line x1={x} y1={0} x2={x} y2={IH} stroke="#a855f7" strokeWidth={1.5} strokeDasharray="6 3"/><text x={x+5} y={IH-8} fill="#a855f7" fontSize={10} fontFamily={mono}>Max Δ {chartData.mgRate.toFixed(2)}/min</text></g>);})()}
              {showMaxCO2&&chartData&&(()=>{const x=chartData.xScale(chartData.timestamps[chartData.mc2Idx]);return(<g><line x1={x} y1={0} x2={x} y2={IH} stroke="#f59e0b" strokeWidth={1.5} strokeDasharray="6 3"/><text x={x+5} y={IH-22} fill="#f59e0b" fontSize={10} fontFamily={mono}>Max CO₂: {chartData.co2Max}</text></g>);})()}
              {chartData?.boundaries.map((bIdx,i)=>{const bx=chartData.xScale(chartData.timestamps[bIdx]);const dr=dragIdx===i;return(<g key={i} onPointerDown={e=>handlePointerDown(i,e)} style={{cursor:'ew-resize',touchAction:'none'}}><rect x={bx-12} y={0} width={24} height={IH} fill="transparent"/><line x1={bx} y1={0} x2={bx} y2={IH} stroke={dr?'#fff':'rgba(255,255,255,0.5)'} strokeWidth={dr?2.5:1.5} strokeDasharray={dr?'none':'4 2'}/><polygon points={`${bx},${IH/2-10} ${bx+8},${IH/2} ${bx},${IH/2+10} ${bx-8},${IH/2}`} fill={dr?'#fff':'rgba(255,255,255,0.8)'} stroke={dr?'#6366f1':'rgba(255,255,255,0.3)'} strokeWidth={1.5}/></g>);})}
              {/* ghost boundaries — original stage positions */}
              {ghostBoundaries && chartData && ghostBoundaries.map((bIdx, i) => {
                const gx = chartData.xScale(chartData.timestamps[bIdx]);
                return <line key={`g${i}`} x1={gx} y1={0} x2={gx} y2={IH} stroke="rgba(255,255,255,0.12)" strokeWidth={1} strokeDasharray="2 4" />;
              })}
              {hoverIdx!==null&&chartData&&(()=>{const hx=chartData.xScale(chartData.timestamps[hoverIdx]);const hy=chartData.yScale(chartData.vals[hoverIdx]);return(<g><line x1={hx} y1={0} x2={hx} y2={IH} stroke="rgba(255,255,255,0.2)" strokeWidth={1}/><line x1={0} y1={hy} x2={IW} y2={hy} stroke="rgba(255,255,255,0.2)" strokeWidth={1}/><circle cx={hx} cy={hy} r={4} fill="#e2e8f0" stroke="#0f1117" strokeWidth={2}/></g>);})()}
              {xTicks.map((t,i)=><text key={i} x={t.x} y={IH+20} textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize={10} fontFamily={mono}>{t.label}</text>)}
              {chartData&&[0,.25,.5,.75,1].map(f=>{const v=chartData.vMin+(1-f)*(chartData.vMax-chartData.vMin);return<text key={f} x={-8} y={f*IH+4} textAnchor="end" fill="rgba(255,255,255,0.4)" fontSize={10} fontFamily={mono}>{Number.isInteger(v)?v:v.toFixed(1)}</text>;})}
              <text x={-8} y={-12} fill="rgba(255,255,255,0.5)" fontSize={11} fontFamily={sans} fontWeight={600}>{metric}</text>
            </g>
          </svg>
        </div>
        <div style={S.side}>
          <div style={S.sideTitle}>Data Point</div>
          {hovered?(<div>
            <div style={S.sideTs}>{hovered.timestamp}</div>
            {numericCols.map(k=><div key={k} style={S.sideRow}><span style={S.sideK}>{k}</span><span style={S.sideV}>{typeof hovered[k]==='number'?(Number.isInteger(hovered[k])?hovered[k]:hovered[k].toFixed(3)):hovered[k]}</span></div>)}
            <div style={{...S.sideRow,marginTop:8,paddingTop:8,borderTop:'1px solid rgba(255,255,255,0.08)'}}><span style={S.sideK}>stage</span><span style={{...S.sideV,color:sc(Number(hovered.stage)).stroke,fontWeight:700}}>{hovered.stage}</span></div>
            <div style={S.sideRow}><span style={S.sideK}>index</span><span style={S.sideV}>{hoverIdx}</span></div>
          </div>):(<div style={S.sideEmpty}>Hover over the chart</div>)}
        </div>
      </div>
      <div style={S.instr}><span style={{color:'rgba(255,255,255,0.4)',marginRight:6}}>◇</span>Drag diamond handles to adjust stage boundaries.</div>
    </div>
  );
}

function Chip({label,color,active,onClick}){
  return<button onClick={onClick} style={{display:'inline-flex',alignItems:'center',padding:'3px 9px',borderRadius:20,border:'1px solid',fontSize:11,fontFamily:mono,cursor:'pointer',background:active?color+'22':'transparent',borderColor:active?color:'rgba(255,255,255,0.15)',color:active?color:'rgba(255,255,255,0.5)'}}>
    <span style={{width:8,height:8,borderRadius:'50%',background:active?color:'rgba(255,255,255,0.2)',display:'inline-block',marginRight:6}}/>{label}
  </button>;
}

const S={
  root:{minHeight:'100vh',background:T.bg,color:T.bright,fontFamily:sans},
  landing:{minHeight:'100vh',background:T.bg,display:'flex',alignItems:'center',justifyContent:'center',fontFamily:sans,color:T.bright},
  landingInner:{textAlign:'center',maxWidth:420,padding:40},
  logoMark:{fontSize:56,color:T.indigo,marginBottom:16},
  landingTitle:{fontSize:40,fontWeight:700,margin:0,letterSpacing:'-0.03em'},
  landingSub:{fontSize:16,color:'rgba(255,255,255,0.4)',margin:'4px 0 24px',fontFamily:mono},
  landingDesc:{fontSize:15,lineHeight:1.6,color:'rgba(255,255,255,0.55)',marginBottom:32},
  uploadBtn:{background:T.indigo,color:'#fff',border:'none',borderRadius:8,padding:'14px 36px',fontSize:15,fontWeight:600,cursor:'pointer',fontFamily:sans},
  header:{display:'flex',justifyContent:'space-between',alignItems:'center',padding:'8px 16px',borderBottom:'1px solid rgba(255,255,255,0.08)',background:'rgba(15,17,23,0.95)',position:'sticky',top:44,zIndex:100,flexWrap:'wrap',gap:6},
  hLeft:{display:'flex',alignItems:'center',gap:8},
  fname:{fontFamily:mono,fontSize:12,color:'rgba(255,255,255,0.5)',background:'rgba(255,255,255,0.06)',padding:'3px 8px',borderRadius:5},
  rowCt:{fontFamily:mono,fontSize:11,color:'rgba(255,255,255,0.3)'},
  hRight:{display:'flex',gap:5,flexWrap:'wrap'},
  btnGhost:{background:'none',color:'rgba(255,255,255,0.6)',border:'1px solid rgba(255,255,255,0.1)',borderRadius:6,padding:'5px 10px',fontSize:12,cursor:'pointer',fontFamily:mono},
  btnSec:{background:'rgba(255,255,255,0.06)',color:T.bright,border:'1px solid rgba(255,255,255,0.1)',borderRadius:6,padding:'5px 12px',fontSize:12,cursor:'pointer',fontFamily:sans},
  btnPri:{background:T.indigo,color:'#fff',border:'none',borderRadius:6,padding:'5px 12px',fontSize:12,fontWeight:600,cursor:'pointer',fontFamily:sans},
  colMgr:{padding:'10px 16px',borderBottom:'1px solid rgba(255,255,255,0.06)',background:'rgba(99,102,241,0.04)'},
  toolbar:{display:'flex',alignItems:'center',gap:16,padding:'8px 16px',borderBottom:'1px solid rgba(255,255,255,0.06)',flexWrap:'wrap'},
  tSec:{display:'flex',alignItems:'center',gap:5},
  tLbl:{fontSize:10,fontWeight:600,textTransform:'uppercase',letterSpacing:'0.08em',color:'rgba(255,255,255,0.3)',fontFamily:mono},
  tGrp:{display:'flex',gap:4},
  sel:{background:'rgba(255,255,255,0.06)',color:T.bright,border:'1px solid rgba(255,255,255,0.12)',borderRadius:5,padding:'4px 8px',fontSize:12,fontFamily:mono,outline:'none'},
  main:{display:'flex',gap:0},
  chartWrap:{flex:1,padding:'12px 12px 6px',minWidth:0},
  svg:{width:'100%',height:'auto',display:'block',userSelect:'none',cursor:'crosshair'},
  side:{width:200,flexShrink:0,borderLeft:'1px solid rgba(255,255,255,0.06)',padding:'12px 10px',background:'rgba(255,255,255,0.02)',overflowY:'auto',alignSelf:'stretch'},
  sideTitle:{fontSize:10,fontWeight:600,textTransform:'uppercase',letterSpacing:'0.08em',color:'rgba(255,255,255,0.35)',fontFamily:mono,marginBottom:10},
  sideTs:{fontSize:11,fontWeight:700,color:T.indigo,fontFamily:mono,marginBottom:8,wordBreak:'break-all'},
  sideRow:{display:'flex',justifyContent:'space-between',alignItems:'center',padding:'2px 0'},
  sideK:{fontSize:10,color:'rgba(255,255,255,0.45)',fontFamily:mono},
  sideV:{fontSize:11,fontFamily:mono,fontWeight:500},
  sideEmpty:{fontSize:11,color:'rgba(255,255,255,0.25)',fontFamily:mono,lineHeight:1.5},
  instr:{textAlign:'center',padding:'10px 16px',fontSize:11,color:'rgba(255,255,255,0.3)',fontFamily:mono},
};
