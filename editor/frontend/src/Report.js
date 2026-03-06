/* Report.js — Multi-run dashboard with unified upload and 7 LOOCV panels */
import React, { useState, useCallback, useMemo, useRef } from 'react';
import {
  STAGE_CHART_COLORS, BAND_DEFS, T, mono, sans, API,
  buildRunProfile, fmtMin,
} from './shared';

const PW = 580, PH = 360;
const PM = { top: 44, right: 24, bottom: 52, left: 58 };
const PIW = PW - PM.left - PM.right;
const PIH = PH - PM.top - PM.bottom;
const CYAN = '#38bdf8';
const GREEN = '#22c55e';
const AMBER = '#f59e0b';
const RED = '#ef4444';

function maeColor(mae) { return mae > 30 ? RED : mae > 15 ? AMBER : GREEN; }

export default function Report({ runs, onMultiUpload, onEditRun }) {
  const [uploading, setUploading] = useState(false);
  const [tooltip, setTooltip] = useState(null);
  const [ctxMenu, setCtxMenu] = useState(null);
  const [loocv, setLoocv] = useState(null);
  const fileInputRef = useRef(null);

  const handleGlobalClick = useCallback(() => setCtxMenu(null), []);

  /* ── Unified upload: accepts .csv AND .json together ── */
  const handleUpload = useCallback(async (e) => {
    const allFiles = Array.from(e.target.files || []);
    if (!allFiles.length) return;

    // Separate CSVs from JSON
    const csvFiles = allFiles.filter(f => f.name.toLowerCase().endsWith('.csv'));
    const jsonFiles = allFiles.filter(f => f.name.toLowerCase().endsWith('.json'));

    // Process JSON (loocv) client-side
    for (const jf of jsonFiles) {
      try {
        const text = await jf.text();
        const data = JSON.parse(text);
        setLoocv(data);
      } catch (err) { alert('Invalid JSON in ' + jf.name + ': ' + err.message); }
    }

    // Upload CSVs to backend
    if (csvFiles.length) {
      setUploading(true);
      const form = new FormData();
      csvFiles.forEach(f => form.append('files', f));
      try {
        const res = await fetch(`${API}/api/upload-multi`, { method: 'POST', body: form });
        const json = await res.json();
        onMultiUpload(json.runs);
      } catch (err) { alert('CSV upload failed: ' + err.message); }
      setUploading(false);
    }

    e.target.value = '';
  }, [onMultiUpload]);

  const runIdToFilename = useMemo(() => {
    const map = {};
    for (const fn of Object.keys(runs)) map[fn.replace(/\.csv$/i, '')] = fn;
    return map;
  }, [runs]);

  const profiles = useMemo(() => {
    const entries = Object.entries(runs);
    if (!entries.length) return [];
    let profs = entries.map(([fn, r]) => {
      const runId = fn.replace(/\.csv$/i, '');
      return buildRunProfile(runId, r.data);
    }).sort((a, b) => a.temp - b.temp);
    if (loocv) {
      profs = profs.map(p => {
        const ld = loocv[p.run];
        if (!ld) return { ...p, mae: null, worst: null, expErr: null, peakErr: null, decErr: null };
        return { ...p, mae: ld.mae ?? null, worst: ld.worst ?? null, expErr: ld.exp_err ?? null, peakErr: ld.peak_err ?? null, decErr: ld.dec_err ?? null };
      });
    }
    return profs;
  }, [runs, loocv]);

  const hasLoocv = useMemo(() => loocv !== null && profiles.some(p => p.mae != null), [loocv, profiles]);

  const handleDownloadAll = useCallback(async () => {
    const runList = Object.values(runs).map(r => ({ filename: r.filename, headers: r.headers, data: r.data }));
    try {
      const res = await fetch(`${API}/api/download-zip`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ runs: runList }),
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = 'fermento-runs.zip'; a.click();
      URL.revokeObjectURL(url);
    } catch (err) { alert('Download failed: ' + err.message); }
  }, [runs]);

  const handleContextMenu = useCallback((e, runId) => {
    e.preventDefault(); e.stopPropagation();
    setCtxMenu({ x: e.clientX, y: e.clientY, runId });
  }, []);

  const handleCtxEdit = useCallback(() => {
    if (!ctxMenu) return;
    const filename = runIdToFilename[ctxMenu.runId];
    if (filename) onEditRun(filename);
    setCtxMenu(null);
  }, [ctxMenu, runIdToFilename, onEditRun]);

  const runCount = Object.keys(runs).length;

  /* ── Hidden file input (accepts both .csv and .json) ── */
  const fileInput = <input ref={fileInputRef} type="file" accept=".csv,.json" multiple style={{ display: 'none' }} onChange={handleUpload} />;

  if (!runCount) {
    return (
      <div style={S.landing} onClick={handleGlobalClick}>
        <div style={S.landingInner}>
          <div style={S.logoMark}>⬡</div>
          <h1 style={S.landingTitle}>Fermento Report</h1>
          <p style={S.landingSub}>Dataset Analysis Dashboard</p>
          <p style={S.landingDesc}>
            Upload your fermentation run CSVs to generate an interactive analysis dashboard.
            You can include a <span style={{ color: T.amber, fontFamily: mono }}>loocv.json</span> in the same selection for error analysis panels.
          </p>
          <button style={S.uploadBtn} onClick={() => fileInputRef.current?.click()} disabled={uploading}>
            {uploading ? 'Processing…' : 'Upload Files'}
          </button>
          <p style={{ marginTop: 10, fontSize: 11, color: T.dim, fontFamily: mono }}>Select .csv files + optionally loocv.json together</p>
          {loocv && <p style={{ marginTop: 8, fontSize: 12, color: GREEN, fontFamily: mono }}>✓ LOOCV loaded ({Object.keys(loocv).length} runs)</p>}
          {fileInput}
        </div>
      </div>
    );
  }

  return (
    <div style={S.root} onClick={handleGlobalClick}>
      <div style={S.subHeader}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={S.badge}>{runCount} runs · {profiles.reduce((s, p) => s + p.samples, 0).toLocaleString()} samples</span>
          {hasLoocv && <span style={{ ...S.badge, background: 'rgba(34,197,94,0.1)', color: GREEN }}>LOOCV ✓</span>}
        </div>
        <div style={S.hRight}>
          <button style={S.btnSec} onClick={() => fileInputRef.current?.click()}>+ Add files</button>
          <button style={S.btnPri} onClick={handleDownloadAll}>↓ Download All</button>
          {fileInput}
        </div>
      </div>

      <div style={S.runList}>
        {Object.keys(runs).map(fn => {
          const rid = fn.replace(/\.csv$/i, '');
          return <button key={fn} style={S.runChip}
            onClick={e => handleContextMenu(e, rid)}
            onContextMenu={e => handleContextMenu(e, rid)}>{rid}</button>;
        })}
      </div>

      <DraggablePanelGrid profiles={profiles} setTooltip={setTooltip} onCtx={handleContextMenu} hasLoocv={hasLoocv} />

      {tooltip && <div style={{ ...S.tooltip, left: tooltip.x, top: tooltip.y }}>{tooltip.text}</div>}
      {ctxMenu && (
        <div style={{ ...S.ctxMenu, left: ctxMenu.x, top: ctxMenu.y }} onClick={e => e.stopPropagation()}>
          <div style={S.ctxTitle}>Run {ctxMenu.runId}</div>
          <button style={S.ctxItem} onClick={handleCtxEdit}
            onMouseEnter={e => e.target.style.background = 'rgba(255,255,255,0.06)'}
            onMouseLeave={e => e.target.style.background = 'none'}>
            ✎ Edit stages
          </button>
        </div>
      )}
    </div>
  );
}


/* ══════════════════════════════════════════════════════════════════════════ */
/*  DRAGGABLE PANEL GRID                                                    */
/* ══════════════════════════════════════════════════════════════════════════ */

const PANEL_DEFS = [
  { id: 'coverage',   label: 'Coverage by Band',    loocvOnly: false, wide: false },
  { id: 'maxerror',   label: 'Max Error by Run',    loocvOnly: true,  wide: false },
  { id: 'stages',     label: 'Stage Durations',     loocvOnly: false, wide: true  },
  { id: 'mae',        label: 'MAE vs Temperature',  loocvOnly: true,  wide: false },
  { id: 'stageerr',   label: 'Stage Errors',        loocvOnly: true,  wide: false },
  { id: 'tempvsdur',  label: 'Temp vs Duration',    loocvOnly: false, wide: false },
  { id: 'co2',        label: 'CO₂ vs Temperature',  loocvOnly: false, wide: false },
];

function DraggablePanelGrid({ profiles, setTooltip, onCtx, hasLoocv }) {
  const [order, setOrder] = useState(null);
  const [dragItem, setDragItem] = useState(null);
  const [dragOver, setDragOver] = useState(null);

  // Compute visible panels based on LOOCV availability
  const visibleIds = useMemo(() => {
    return PANEL_DEFS.filter(p => !p.loocvOnly || hasLoocv).map(p => p.id);
  }, [hasLoocv]);

  // Use custom order if set, otherwise default
  const panelOrder = useMemo(() => {
    if (order) {
      // Filter to only visible panels, preserving custom order
      const filtered = order.filter(id => visibleIds.includes(id));
      // Add any new visible panels not in the saved order
      const missing = visibleIds.filter(id => !filtered.includes(id));
      return [...filtered, ...missing];
    }
    return visibleIds;
  }, [order, visibleIds]);

  const handleDragStart = useCallback((e, id) => {
    setDragItem(id);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', id);
  }, []);

  const handleDragOver = useCallback((e, id) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (id !== dragItem) setDragOver(id);
  }, [dragItem]);

  const handleDrop = useCallback((e, targetId) => {
    e.preventDefault();
    if (!dragItem || dragItem === targetId) { setDragItem(null); setDragOver(null); return; }
    setOrder(prev => {
      const current = prev || [...panelOrder];
      const fromIdx = current.indexOf(dragItem);
      const toIdx = current.indexOf(targetId);
      if (fromIdx === -1 || toIdx === -1) return current;
      const newOrder = [...current];
      newOrder.splice(fromIdx, 1);
      newOrder.splice(toIdx, 0, dragItem);
      return newOrder;
    });
    setDragItem(null);
    setDragOver(null);
  }, [dragItem, panelOrder]);

  const handleDragEnd = useCallback(() => {
    setDragItem(null);
    setDragOver(null);
  }, []);

  const renderPanel = (id) => {
    const props = { profiles, setTooltip, onCtx };
    switch (id) {
      case 'coverage':  return <PanelCoverageByBand {...props} hasLoocv={hasLoocv} />;
      case 'maxerror':  return <PanelMaxErrorByRun {...props} />;
      case 'stages':    return <PanelStageDurations {...props} wide={true} />;
      case 'mae':       return <PanelMAEvsTemp {...props} />;
      case 'stageerr':  return <PanelPerStageErrors {...props} />;
      case 'tempvsdur': return <PanelTempVsDuration {...props} />;
      case 'co2':       return <PanelCO2VsTemp {...props} hasLoocv={hasLoocv} />;
      default: return null;
    }
  };

  const getDef = (id) => PANEL_DEFS.find(p => p.id === id);

  return (
    <div style={S.panelGrid}>
      {panelOrder.map(id => {
        const def = getDef(id);
        if (!def) return null;
        const isDragging = dragItem === id;
        const isOver = dragOver === id;
        return (
          <div
            key={id}
            draggable
            onDragStart={e => handleDragStart(e, id)}
            onDragOver={e => handleDragOver(e, id)}
            onDrop={e => handleDrop(e, id)}
            onDragEnd={handleDragEnd}
            style={{
              gridColumn: def.wide ? '1 / -1' : 'auto',
              opacity: isDragging ? 0.4 : 1,
              transition: 'opacity 0.15s, outline 0.15s',
              outline: isOver ? `2px solid ${T.indigo}` : '2px solid transparent',
              outlineOffset: 2,
              borderRadius: 12,
              cursor: 'grab',
              position: 'relative',
            }}
          >
            {/* drag handle indicator */}
            <div style={{
              position: 'absolute', top: 6, right: 10, zIndex: 10,
              color: T.dim, fontSize: 10, fontFamily: mono,
              opacity: 0.4, pointerEvents: 'none', userSelect: 'none',
            }}>⠿</div>
            {renderPanel(id)}
          </div>
        );
      })}
    </div>
  );
}


/* ══════════════════════════════════════════════════════════════════════════ */
/*  PANELS                                                                  */
/* ══════════════════════════════════════════════════════════════════════════ */
function PanelCoverageByBand({ profiles, setTooltip, onCtx, hasLoocv }) {
  const bandStats = useMemo(() => BAND_DEFS.map(band => {
    const sub = profiles.filter(p => p.temp >= band.lo && p.temp < band.hi);
    const maes = sub.filter(p => p.mae != null).map(p => p.mae);
    return {
      ...band, count: sub.length, runs: sub,
      avgMae: maes.length ? maes.reduce((a, b) => a + b, 0) / maes.length : 0,
    };
  }), [profiles]);

  const maxC = Math.max(...bandStats.map(b => b.count), 1);
  const maxMae = hasLoocv ? Math.max(...bandStats.map(b => b.avgMae), 1) * 1.2 : 1;
  const xS = i => (i + 0.5) * (PIW / bandStats.length);
  const bW = PIW / bandStats.length * 0.3;

  return (
    <div style={S.panel}><svg viewBox={`0 0 ${PW} ${PH}`} style={S.panelSvg}>
      <text x={PW/2} y={22} textAnchor="middle" fill={T.white} fontSize={13} fontWeight={700} fontFamily={sans}>
        {hasLoocv ? 'Coverage vs Error by Temperature Band' : 'Temperature Coverage by Band'}
      </text>
      <g transform={`translate(${PM.left},${PM.top})`}>
        {[0,.25,.5,.75,1].map(f => <line key={f} x1={0} y1={f*PIH} x2={PIW} y2={f*PIH} stroke={T.grid} strokeWidth={0.5} />)}

        {bandStats.map((b, i) => {
          const countH = PIH - (b.count / (maxC * 1.2)) * PIH;
          const runList = b.runs.map(r => `Run ${r.run} (${r.temp.toFixed(1)}°${hasLoocv && r.mae != null ? `, MAE ${r.mae.toFixed(1)}` : ''})`).join('\n');
          return (
            <g key={i}
              onMouseEnter={e => setTooltip({ text: `${b.label}°C — ${b.count} run${b.count !== 1 ? 's' : ''}${hasLoocv ? `\nAvg MAE: ${b.avgMae.toFixed(1)} min` : ''}\n\n${runList}`, x: e.clientX + 12, y: e.clientY - 20 })}
              onMouseLeave={() => setTooltip(null)}
              onContextMenu={e => { if (b.runs.length >= 1) onCtx(e, b.runs[0].run); else e.preventDefault(); }}>
              {/* run count bar */}
              <rect x={hasLoocv ? xS(i) - bW - 2 : xS(i) - bW / 2} y={countH} width={bW} height={PIH - countH} fill={b.color} opacity={0.85} rx={2} />
              {/* count label on bar */}
              {b.count > 0 && <text x={hasLoocv ? xS(i) - 2 : xS(i)} y={countH - 4} textAnchor="middle" fill={b.color} fontSize={9} fontFamily={mono} fontWeight={600}>{b.count}</text>}
              {/* MAE bar (only with LOOCV) */}
              {hasLoocv && b.avgMae > 0 && (() => {
                const maeH = PIH - (b.avgMae / maxMae) * PIH;
                return <rect x={xS(i) + 2} y={maeH} width={bW} height={PIH - maeH} fill={b.color} opacity={0.35} rx={2} stroke={b.color} strokeWidth={1} strokeDasharray="3 2" />;
              })()}
              {/* thin coverage warning */}
              {b.count <= 1 && <rect x={xS(i) - PIW / bandStats.length / 2} y={0} width={PIW / bandStats.length} height={PIH} fill={RED} opacity={0.06} />}
            </g>
          );
        })}

        {bandStats.map((b, i) => <text key={i} x={xS(i)} y={PIH + 16} textAnchor="middle" fill={T.dim} fontSize={9} fontFamily={mono}>{b.label}°</text>)}
        <text x={PIW/2} y={PIH + 38} textAnchor="middle" fill={T.txt} fontSize={10} fontFamily={sans}>Temperature Band (°C)</text>
        <text x={-PIH/2} y={-42} textAnchor="middle" fill={T.txt} fontSize={10} fontFamily={sans} transform="rotate(-90)">Number of Runs</text>
        {[0,.25,.5,.75,1].map(f => { const v = Math.round(maxC * 1.2 * (1 - f)); return <text key={f} x={-8} y={f*PIH + 3} textAnchor="end" fill={T.dim} fontSize={9} fontFamily={mono}>{v}</text>; })}

        {/* legend */}
        <g transform={`translate(${PIW - 100}, 0)`}><rect width={10} height={10} fill={CYAN} opacity={0.85} rx={2} /><text x={14} y={9} fill={T.txt} fontSize={8} fontFamily={mono}># Runs</text></g>
        {hasLoocv && <g transform={`translate(${PIW - 100}, 14)`}><rect width={10} height={10} fill={CYAN} opacity={0.35} rx={2} stroke={CYAN} strokeWidth={1} /><text x={14} y={9} fill={T.txt} fontSize={8} fontFamily={mono}>Avg MAE</text></g>}
      </g>
    </svg></div>
  );
}


/* ── Panel 2: MAE vs Temperature ── */
function PanelMAEvsTemp({ profiles, setTooltip, onCtx }) {
  const withMae = profiles.filter(p => p.mae != null);
  if (!withMae.length) return null;
  const tMin = Math.min(...withMae.map(p => p.temp)) - 1, tMax = Math.max(...withMae.map(p => p.temp)) + 1;
  const maeMax = Math.max(...withMae.map(p => p.mae)) * 1.15;
  const xS = t => ((t - tMin) / (tMax - tMin)) * PIW, yS = m => PIH - (m / maeMax) * PIH;
  return (
    <div style={S.panel}><svg viewBox={`0 0 ${PW} ${PH}`} style={S.panelSvg}>
      <text x={PW/2} y={22} textAnchor="middle" fill={T.white} fontSize={13} fontWeight={700} fontFamily={sans}>LOOCV Error vs Temperature</text>
      <g transform={`translate(${PM.left},${PM.top})`}>
        {[0,.25,.5,.75,1].map(f=><line key={f} x1={0} y1={f*PIH} x2={PIW} y2={f*PIH} stroke={T.grid} strokeWidth={0.5}/>)}
        <line x1={0} y1={yS(15)} x2={PIW} y2={yS(15)} stroke={AMBER} strokeWidth={0.8} strokeDasharray="4 3" opacity={0.5}/>
        <text x={PIW-4} y={yS(15)-4} textAnchor="end" fill={AMBER} fontSize={7} fontFamily={mono}>15 min</text>
        <line x1={0} y1={yS(30)} x2={PIW} y2={yS(30)} stroke={RED} strokeWidth={0.8} strokeDasharray="4 3" opacity={0.5}/>
        <text x={PIW-4} y={yS(30)-4} textAnchor="end" fill={RED} fontSize={7} fontFamily={mono}>30 min</text>
        {withMae.map((p,i)=>{const sz=Math.max(4,Math.min(10,p.mae*0.3));return(
          <circle key={i} cx={xS(p.temp)} cy={yS(p.mae)} r={sz} fill={maeColor(p.mae)} opacity={0.85} stroke={T.panel} strokeWidth={1} style={{cursor:'context-menu'}}
            onContextMenu={e=>onCtx(e,p.run)}
            onMouseEnter={e=>setTooltip({text:`Run ${p.run}\nMAE: ${p.mae.toFixed(1)} min\nWorst: ${p.worst?.toFixed(1)} min\nTemp: ${p.temp.toFixed(1)}°C`,x:e.clientX+12,y:e.clientY-20})}
            onMouseLeave={()=>setTooltip(null)}/>);})}
        {withMae.filter(p=>p.mae>20||p.mae<6).map((p,i)=><text key={i} x={xS(p.temp)+8} y={yS(p.mae)+3} fill={p.mae>20?RED:GREEN} fontSize={7} fontFamily={mono} fontWeight={600}>Run {p.run}</text>)}
        {[22,24,26,28,30,32,34,36].filter(t=>t>=tMin&&t<=tMax).map(t=><text key={t} x={xS(t)} y={PIH+16} textAnchor="middle" fill={T.dim} fontSize={9} fontFamily={mono}>{t}°</text>)}
        <text x={PIW/2} y={PIH+38} textAnchor="middle" fill={T.txt} fontSize={10} fontFamily={sans}>Mean Temperature (°C)</text>
        <text x={-PIH/2} y={-42} textAnchor="middle" fill={T.txt} fontSize={10} fontFamily={sans} transform="rotate(-90)">MAE (min)</text>
        {[0,.25,.5,.75,1].map(f=>{const v=(maeMax*(1-f)).toFixed(0);return<text key={f} x={-8} y={f*PIH+3} textAnchor="end" fill={T.dim} fontSize={9} fontFamily={mono}>{v}</text>;})}
        {[{l:'MAE ≤ 15',c:GREEN},{l:'15 < MAE ≤ 30',c:AMBER},{l:'MAE > 30',c:RED}].map((e,i)=><g key={i} transform={`translate(4,${i*14})`}><circle cx={5} cy={5} r={4} fill={e.c}/><text x={14} y={9} fill={T.txt} fontSize={7} fontFamily={mono}>{e.l}</text></g>)}
      </g>
    </svg></div>
  );
}


/* ── Panel 3: Stage Durations ── */
function PanelStageDurations({ profiles, setTooltip, onCtx, wide }) {
  const vbW = wide ? 1180 : PW;
  const innerW = vbW - PM.left - PM.right;
  const maxDur = useMemo(() => Math.max(...profiles.map(p => p.lagDur + p.expDur + p.peakDur + p.decDur), 1), [profiles]);
  const barW = Math.min(36, innerW / profiles.length - 4);
  const xS = i => (i + 0.5) * (innerW / profiles.length);
  const yS = v => PIH - (v / (maxDur * 1.15)) * PIH;
  return (
    <div style={S.panel}><svg viewBox={`0 0 ${vbW} ${PH}`} style={S.panelSvg}>
      <text x={vbW/2} y={22} textAnchor="middle" fill={T.white} fontSize={13} fontWeight={700} fontFamily={sans}>Stage Durations by Run (sorted by temperature)</text>
      <g transform={`translate(${PM.left},${PM.top})`}>
        {[0,.25,.5,.75,1].map(f=><line key={f} x1={0} y1={f*PIH} x2={innerW} y2={f*PIH} stroke={T.grid} strokeWidth={0.5}/>)}
        {profiles.map((p,i)=>{const stacks=[{key:'lagDur',label:'Lag',color:STAGE_CHART_COLORS.Lag},{key:'expDur',label:'Exponential',color:STAGE_CHART_COLORS.Exponential},{key:'peakDur',label:'Peak',color:STAGE_CHART_COLORS.Peak},{key:'decDur',label:'Decline',color:STAGE_CHART_COLORS.Decline}];let bottom=0;return(
          <g key={i} onContextMenu={e=>onCtx(e,p.run)}>
            {stacks.map(s=>{const val=p[s.key];const y=yS(bottom+val);const h=yS(bottom)-y;bottom+=val;return<rect key={s.key} x={xS(i)-barW/2} y={y} width={barW} height={Math.max(0,h)} fill={s.color} opacity={0.88} rx={1} onMouseEnter={e=>setTooltip({text:`Run ${p.run}\n${s.label}: ${fmtMin(val)}\nTotal: ${fmtMin(p.duration)}\nTemp: ${p.temp.toFixed(1)}°C`,x:e.clientX+12,y:e.clientY-20})} onMouseLeave={()=>setTooltip(null)}/>;} )}
            <text x={xS(i)} y={yS(bottom)-4} textAnchor="middle" fill={T.dim} fontSize={7} fontFamily={mono}>{p.temp.toFixed(1)}°</text>
            <text x={xS(i)} y={PIH+14} textAnchor="middle" fill={T.dim} fontSize={7} fontFamily={mono} transform={`rotate(-35,${xS(i)},${PIH+14})`}>{p.run}</text>
          </g>);})}
        {['Lag','Exponential','Peak','Decline'].map((n,i)=><g key={n} transform={`translate(${innerW-100},${i*14})`}><rect width={10} height={10} fill={STAGE_CHART_COLORS[n]} rx={2}/><text x={14} y={9} fill={T.txt} fontSize={8} fontFamily={mono}>{n}</text></g>)}
        <text x={-PIH/2} y={-42} textAnchor="middle" fill={T.txt} fontSize={10} fontFamily={sans} transform="rotate(-90)">Duration (min)</text>
        {[0,.25,.5,.75,1].map(f=>{const v=Math.round(maxDur*1.15*(1-f));return<text key={f} x={-8} y={f*PIH+3} textAnchor="end" fill={T.dim} fontSize={9} fontFamily={mono}>{v}</text>;})}
      </g>
    </svg></div>
  );
}


/* ── Panel 4: Per-Stage Transition Errors ── */
function PanelPerStageErrors({ profiles, setTooltip, onCtx }) {
  const withErr = profiles.filter(p => p.expErr != null);
  if (!withErr.length) return null;
  const maxErr = Math.min(100, Math.max(...withErr.flatMap(p => [Math.abs(p.expErr||0), Math.abs(p.peakErr||0), Math.abs(p.decErr||0)]), 1));
  const barW = Math.min(10, PIW / withErr.length / 3 - 1);
  const xS = i => (i + 0.5) * (PIW / withErr.length);
  const yS = v => PIH - (Math.min(v, maxErr) / (maxErr * 1.05)) * PIH;
  const stages = [
    { key: 'expErr', label: 'Exponential', color: STAGE_CHART_COLORS.Exponential },
    { key: 'peakErr', label: 'Peak', color: STAGE_CHART_COLORS.Peak },
    { key: 'decErr', label: 'Decline', color: STAGE_CHART_COLORS.Decline },
  ];
  return (
    <div style={S.panel}><svg viewBox={`0 0 ${PW} ${PH}`} style={S.panelSvg}>
      <text x={PW/2} y={22} textAnchor="middle" fill={T.white} fontSize={13} fontWeight={700} fontFamily={sans}>Transition Error by Stage</text>
      <g transform={`translate(${PM.left},${PM.top})`}>
        {[0,.25,.5,.75,1].map(f=><line key={f} x1={0} y1={f*PIH} x2={PIW} y2={f*PIH} stroke={T.grid} strokeWidth={0.5}/>)}
        {withErr.map((p,i)=>(
          <g key={i} onContextMenu={e=>onCtx(e,p.run)}>
            {stages.map((s,si)=>{const val=Math.abs(p[s.key]||0);return(
              <rect key={s.key} x={xS(i)+(si-1)*barW-barW/2} y={yS(val)} width={barW} height={PIH-yS(val)} fill={s.color} opacity={0.8} rx={1}
                onMouseEnter={e=>setTooltip({text:`Run ${p.run}\n${s.label}: ${val.toFixed(1)} min`,x:e.clientX+12,y:e.clientY-20})}
                onMouseLeave={()=>setTooltip(null)}/>);})}
            <text x={xS(i)} y={PIH+12} textAnchor="middle" fill={T.dim} fontSize={7} fontFamily={mono}>{p.run}</text>
          </g>))}
        {stages.map((s,i)=><g key={s.key} transform={`translate(${PIW-100},${i*14})`}><rect width={10} height={10} fill={s.color} rx={2}/><text x={14} y={9} fill={T.txt} fontSize={8} fontFamily={mono}>{s.label}</text></g>)}
        <text x={PIW/2} y={PIH+38} textAnchor="middle" fill={T.txt} fontSize={10} fontFamily={sans}>Run</text>
        <text x={-PIH/2} y={-42} textAnchor="middle" fill={T.txt} fontSize={10} fontFamily={sans} transform="rotate(-90)">|Error| (min)</text>
        {[0,.25,.5,.75,1].map(f=>{const v=Math.round(maxErr*1.05*(1-f));return<text key={f} x={-8} y={f*PIH+3} textAnchor="end" fill={T.dim} fontSize={9} fontFamily={mono}>{v}</text>;})}
      </g>
    </svg></div>
  );
}


/* ── Panel: Max Transition Error by Run (LOOCV only) ── */
function PanelMaxErrorByRun({ profiles, setTooltip, onCtx }) {
  const data = useMemo(() => {
    return profiles
      .filter(p => p.worst != null)
      .map(p => {
        const errs = [
          { stage: 'Exponential', val: Math.abs(p.expErr || 0) },
          { stage: 'Peak',        val: Math.abs(p.peakErr || 0) },
          { stage: 'Decline',     val: Math.abs(p.decErr || 0) },
        ];
        const worst = errs.reduce((a, b) => b.val > a.val ? b : a, errs[0]);
        return { ...p, worstVal: worst.val, worstStage: worst.stage };
      })
      .sort((a, b) => a.temp - b.temp);
  }, [profiles]);

  if (!data.length) return null;

  const maxVal = Math.max(...data.map(p => p.worstVal), 1) * 1.1;
  const barW = Math.min(28, PIW / data.length - 4);
  const xS = i => (i + 0.5) * (PIW / data.length);
  const yS = v => PIH - (v / maxVal) * PIH;

  return (
    <div style={S.panel}><svg viewBox={`0 0 ${PW} ${PH}`} style={S.panelSvg}>
      <text x={PW/2} y={22} textAnchor="middle" fill={T.white} fontSize={13} fontWeight={700} fontFamily={sans}>Max Transition Error by Run</text>
      <g transform={`translate(${PM.left},${PM.top})`}>
        {[0,.25,.5,.75,1].map(f => <line key={f} x1={0} y1={f*PIH} x2={PIW} y2={f*PIH} stroke={T.grid} strokeWidth={0.5} />)}

        <line x1={0} y1={yS(15)} x2={PIW} y2={yS(15)} stroke={AMBER} strokeWidth={0.8} strokeDasharray="4 3" opacity={0.4} />
        <text x={PIW-4} y={yS(15)-4} textAnchor="end" fill={AMBER} fontSize={7} fontFamily={mono} opacity={0.6}>15 min</text>
        <line x1={0} y1={yS(30)} x2={PIW} y2={yS(30)} stroke={RED} strokeWidth={0.8} strokeDasharray="4 3" opacity={0.4} />
        <text x={PIW-4} y={yS(30)-4} textAnchor="end" fill={RED} fontSize={7} fontFamily={mono} opacity={0.6}>30 min</text>

        {data.map((p, i) => {
          const col = STAGE_CHART_COLORS[p.worstStage] || CYAN;
          return (
            <g key={i} onContextMenu={e => onCtx(e, p.run)}>
              <rect x={xS(i) - barW/2} y={yS(p.worstVal)} width={barW} height={PIH - yS(p.worstVal)}
                fill={col} opacity={0.85} rx={2}
                onMouseEnter={e => setTooltip({ text: `Run ${p.run}\nWorst stage: ${p.worstStage}\nMax error: ${p.worstVal.toFixed(1)} min\nMAE: ${p.mae?.toFixed(1)} min\nTemp: ${p.temp.toFixed(1)}°C`, x: e.clientX + 12, y: e.clientY - 20 })}
                onMouseLeave={() => setTooltip(null)} />
              <text x={xS(i)} y={yS(p.worstVal) - 4} textAnchor="middle" fill={col} fontSize={7} fontFamily={mono} fontWeight={600}>{p.worstVal.toFixed(0)}</text>
              <text x={xS(i)} y={PIH + 14} textAnchor="middle" fill={T.dim} fontSize={7} fontFamily={mono} transform={`rotate(-35,${xS(i)},${PIH + 14})`}>{p.run}</text>
            </g>
          );
        })}

        <text x={-PIH/2} y={-42} textAnchor="middle" fill={T.txt} fontSize={10} fontFamily={sans} transform="rotate(-90)">Max |Error| (min)</text>
        {[0,.25,.5,.75,1].map(f => { const v = Math.round(maxVal * (1 - f)); return <text key={f} x={-8} y={f*PIH + 3} textAnchor="end" fill={T.dim} fontSize={9} fontFamily={mono}>{v}</text>; })}

        {['Exponential', 'Peak', 'Decline'].map((name, i) => (
          <g key={name} transform={`translate(${PIW - 100}, ${i * 14})`}>
            <rect width={10} height={10} fill={STAGE_CHART_COLORS[name]} opacity={0.85} rx={2} />
            <text x={14} y={9} fill={T.txt} fontSize={7} fontFamily={mono}>{name}</text>
          </g>
        ))}
      </g>
    </svg></div>
  );
}


/* ── Panel 6: Temperature vs Duration ── */
function PanelTempVsDuration({ profiles, setTooltip, onCtx }) {
  const tMin = Math.min(...profiles.map(p => p.temp)) - 1, tMax = Math.max(...profiles.map(p => p.temp)) + 1;
  const durMax = Math.max(...profiles.map(p => p.duration)) * 1.1;
  const xS = t => ((t - tMin) / (tMax - tMin)) * PIW, yS = d => PIH - (d / durMax) * PIH;
  const trend = useMemo(() => {
    if (profiles.length < 3) return null;
    const xs = profiles.map(p => p.temp), ys = profiles.map(p => p.duration), n = xs.length;
    let s0=0,s1=0,s2=0,s3=0,s4=0,t0=0,t1=0,t2=0;
    for(let i=0;i<n;i++){const x=xs[i],y=ys[i];s0++;s1+=x;s2+=x*x;s3+=x*x*x;s4+=x*x*x*x;t0+=y;t1+=x*y;t2+=x*x*y;}
    const A=[[s4,s3,s2],[s3,s2,s1],[s2,s1,s0]],B=[t2,t1,t0];
    const det=m=>m[0][0]*(m[1][1]*m[2][2]-m[1][2]*m[2][1])-m[0][1]*(m[1][0]*m[2][2]-m[1][2]*m[2][0])+m[0][2]*(m[1][0]*m[2][1]-m[1][1]*m[2][0]);
    const D=det(A);if(Math.abs(D)<1e-10)return null;
    const rep=col=>A.map((row,i)=>row.map((v,j)=>j===col?B[i]:v));
    const a=det(rep(0))/D,b=det(rep(1))/D,c=det(rep(2))/D;
    const pts=[];for(let t=tMin;t<=tMax;t+=0.5)pts.push({x:xS(t),y:yS(a*t*t+b*t+c)});return pts;
  }, [profiles, tMin, tMax, xS, yS]);
  return (
    <div style={S.panel}><svg viewBox={`0 0 ${PW} ${PH}`} style={S.panelSvg}>
      <text x={PW/2} y={22} textAnchor="middle" fill={T.white} fontSize={13} fontWeight={700} fontFamily={sans}>Temperature vs Duration</text>
      <g transform={`translate(${PM.left},${PM.top})`}>
        {[0,.25,.5,.75,1].map(f=><line key={f} x1={0} y1={f*PIH} x2={PIW} y2={f*PIH} stroke={T.grid} strokeWidth={0.5}/>)}
        {trend&&<polyline points={trend.map(p=>`${p.x},${p.y}`).join(' ')} fill="none" stroke={CYAN} strokeWidth={1} strokeOpacity={0.3} strokeDasharray="4 3"/>}
        {profiles.map((p,i)=><circle key={`t${i}`} cx={xS(p.temp)} cy={yS(p.duration)} r={5} fill={CYAN} opacity={0.8} stroke={T.panel} strokeWidth={1} style={{cursor:'context-menu'}} onContextMenu={e=>onCtx(e,p.run)} onMouseEnter={e=>setTooltip({text:`Run ${p.run}\nTotal: ${fmtMin(p.duration)}\nExp: ${fmtMin(p.expDur)}\nPeak: ${fmtMin(p.peakDur)}\nTemp: ${p.temp.toFixed(1)}°C`,x:e.clientX+12,y:e.clientY-20})} onMouseLeave={()=>setTooltip(null)}/>)}
        {profiles.map((p,i)=><circle key={`e${i}`} cx={xS(p.temp)} cy={yS(p.expDur)} r={3.5} fill={STAGE_CHART_COLORS.Exponential} opacity={0.8} stroke={T.panel} strokeWidth={1} style={{cursor:'context-menu'}} onContextMenu={e=>onCtx(e,p.run)} onMouseEnter={e=>setTooltip({text:`Run ${p.run}\nExp: ${fmtMin(p.expDur)}`,x:e.clientX+12,y:e.clientY-20})} onMouseLeave={()=>setTooltip(null)}/>)}
        {profiles.map((p,i)=><circle key={`p${i}`} cx={xS(p.temp)} cy={yS(p.peakDur)} r={3.5} fill={STAGE_CHART_COLORS.Peak} opacity={0.8} stroke={T.panel} strokeWidth={1} style={{cursor:'context-menu'}} onContextMenu={e=>onCtx(e,p.run)} onMouseEnter={e=>setTooltip({text:`Run ${p.run}\nPeak: ${fmtMin(p.peakDur)}`,x:e.clientX+12,y:e.clientY-20})} onMouseLeave={()=>setTooltip(null)}/>)}
        {[{label:'Total',color:CYAN},{label:'Exp',color:STAGE_CHART_COLORS.Exponential},{label:'Peak',color:STAGE_CHART_COLORS.Peak}].map((l,i)=><g key={l.label} transform={`translate(${PIW-70},${i*14})`}><circle cx={5} cy={5} r={4} fill={l.color} opacity={0.8}/><text x={14} y={9} fill={T.txt} fontSize={8} fontFamily={mono}>{l.label}</text></g>)}
        {[22,24,26,28,30,32,34,36].filter(t=>t>=tMin&&t<=tMax).map(t=><text key={t} x={xS(t)} y={PIH+16} textAnchor="middle" fill={T.dim} fontSize={9} fontFamily={mono}>{t}°</text>)}
        <text x={PIW/2} y={PIH+38} textAnchor="middle" fill={T.txt} fontSize={10} fontFamily={sans}>Mean Temperature (°C)</text>
        <text x={-PIH/2} y={-42} textAnchor="middle" fill={T.txt} fontSize={10} fontFamily={sans} transform="rotate(-90)">Duration (min)</text>
        {[0,.25,.5,.75,1].map(f=>{const v=Math.round(durMax*(1-f));return<text key={f} x={-8} y={f*PIH+3} textAnchor="end" fill={T.dim} fontSize={9} fontFamily={mono}>{v}</text>;})}
      </g>
    </svg></div>
  );
}


/* ── Panel 7: CO₂ vs Temperature ── */
function PanelCO2VsTemp({ profiles, setTooltip, onCtx, hasLoocv }) {
  const tMin = Math.min(...profiles.map(p => p.temp)) - 1, tMax = Math.max(...profiles.map(p => p.temp)) + 1;
  const co2Max = Math.max(...profiles.map(p => p.co2Max / 1000)) * 1.1;
  const xS = t => ((t - tMin) / (tMax - tMin)) * PIW, yS = c => PIH - (c / co2Max) * PIH;
  return (
    <div style={S.panel}><svg viewBox={`0 0 ${PW} ${PH}`} style={S.panelSvg}>
      <text x={PW/2} y={22} textAnchor="middle" fill={T.white} fontSize={13} fontWeight={700} fontFamily={sans}>{hasLoocv ? 'Max CO₂ vs Temp (color = MAE)' : 'Max CO₂ vs Temperature'}</text>
      <g transform={`translate(${PM.left},${PM.top})`}>
        {[0,.25,.5,.75,1].map(f=><line key={f} x1={0} y1={f*PIH} x2={PIW} y2={f*PIH} stroke={T.grid} strokeWidth={0.5}/>)}
        <rect x={0} y={yS(20)} width={PIW} height={PIH-yS(20)} fill={RED} opacity={0.04}/>
        <text x={PIW-4} y={yS(18)} textAnchor="end" fill={RED} fontSize={7} fontFamily={mono} opacity={0.6}>Low CO₂ zone</text>
        {profiles.map((p,i)=>{const col=hasLoocv&&p.mae!=null?maeColor(p.mae):CYAN;return(
          <circle key={i} cx={xS(p.temp)} cy={yS(p.co2Max/1000)} r={6} fill={col} opacity={0.85} stroke={T.panel} strokeWidth={1} style={{cursor:'context-menu'}}
            onContextMenu={e=>onCtx(e,p.run)}
            onMouseEnter={e=>setTooltip({text:`Run ${p.run}\nMax CO₂: ${p.co2Max.toLocaleString()} ppm\nTemp: ${p.temp.toFixed(1)}°C${hasLoocv&&p.mae!=null?`\nMAE: ${p.mae.toFixed(1)} min`:''}`,x:e.clientX+12,y:e.clientY-20})}
            onMouseLeave={()=>setTooltip(null)}/>);})}
        {profiles.filter(p=>p.co2Max<20000||p.co2Max>43000).map((p,i)=><text key={i} x={xS(p.temp)+8} y={yS(p.co2Max/1000)+3} fill={T.dim} fontSize={7} fontFamily={mono}>Run {p.run}</text>)}
        {[22,24,26,28,30,32,34,36].filter(t=>t>=tMin&&t<=tMax).map(t=><text key={t} x={xS(t)} y={PIH+16} textAnchor="middle" fill={T.dim} fontSize={9} fontFamily={mono}>{t}°</text>)}
        <text x={PIW/2} y={PIH+38} textAnchor="middle" fill={T.txt} fontSize={10} fontFamily={sans}>Mean Temperature (°C)</text>
        <text x={-PIH/2} y={-42} textAnchor="middle" fill={T.txt} fontSize={10} fontFamily={sans} transform="rotate(-90)">Max CO₂ (×1000 ppm)</text>
        {[0,.25,.5,.75,1].map(f=>{const v=(co2Max*(1-f)).toFixed(0);return<text key={f} x={-8} y={f*PIH+3} textAnchor="end" fill={T.dim} fontSize={9} fontFamily={mono}>{v}</text>;})}
        {hasLoocv&&[{l:'MAE ≤ 15',c:GREEN},{l:'15 < MAE ≤ 30',c:AMBER},{l:'MAE > 30',c:RED}].map((e,i)=><g key={i} transform={`translate(4,${i*14})`}><circle cx={5} cy={5} r={4} fill={e.c}/><text x={14} y={9} fill={T.txt} fontSize={7} fontFamily={mono}>{e.l}</text></g>)}
      </g>
    </svg></div>
  );
}


const S = {
  root: { minHeight: '100vh', background: T.bg, color: T.bright, fontFamily: sans },
  landing: { minHeight: '100vh', background: T.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: sans, color: T.bright },
  landingInner: { textAlign: 'center', maxWidth: 460, padding: 40 },
  logoMark: { fontSize: 56, color: T.indigo, marginBottom: 16 },
  landingTitle: { fontSize: 40, fontWeight: 700, margin: 0, letterSpacing: '-0.03em' },
  landingSub: { fontSize: 16, color: 'rgba(255,255,255,0.4)', margin: '4px 0 24px', fontFamily: mono },
  landingDesc: { fontSize: 15, lineHeight: 1.6, color: 'rgba(255,255,255,0.55)', marginBottom: 32 },
  uploadBtn: { background: T.indigo, color: '#fff', border: 'none', borderRadius: 8, padding: '14px 36px', fontSize: 15, fontWeight: 600, cursor: 'pointer', fontFamily: sans },
  subHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)', flexWrap: 'wrap', gap: 8 },
  badge: { fontFamily: mono, fontSize: 11, color: 'rgba(255,255,255,0.4)', background: 'rgba(255,255,255,0.06)', padding: '3px 8px', borderRadius: 5 },
  hRight: { display: 'flex', gap: 6, flexWrap: 'wrap' },
  btnSec: { background: 'rgba(255,255,255,0.06)', color: T.bright, border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, padding: '6px 14px', fontSize: 12, cursor: 'pointer', fontFamily: sans },
  btnPri: { background: T.indigo, color: '#fff', border: 'none', borderRadius: 6, padding: '6px 14px', fontSize: 12, fontWeight: 600, cursor: 'pointer', fontFamily: sans },
  runList: { display: 'flex', gap: 6, padding: '10px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)', flexWrap: 'wrap' },
  runChip: { background: 'rgba(255,255,255,0.04)', color: T.txt, border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, padding: '4px 10px', fontSize: 11, fontFamily: mono, cursor: 'pointer' },
  panelGrid: { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10, padding: 14 },
  panel: { background: T.panel, borderRadius: 10, border: `1px solid ${T.grid}`, overflow: 'hidden' },
  panelSvg: { width: '100%', height: 'auto', display: 'block' },
  tooltip: { position: 'fixed', background: 'rgba(15,17,23,0.94)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 8, padding: '8px 12px', fontSize: 11, fontFamily: mono, color: T.bright, lineHeight: 1.6, pointerEvents: 'none', whiteSpace: 'pre-line', zIndex: 9999, backdropFilter: 'blur(8px)', maxWidth: 320 },
  ctxMenu: { position: 'fixed', background: T.panel, border: `1px solid ${T.grid}`, borderRadius: 8, padding: '6px 0', zIndex: 10000, boxShadow: '0 8px 32px rgba(0,0,0,0.5)', minWidth: 160 },
  ctxTitle: { padding: '6px 14px', fontSize: 12, fontFamily: mono, fontWeight: 700, color: T.white, borderBottom: `1px solid ${T.grid}` },
  ctxItem: { display: 'block', width: '100%', textAlign: 'left', background: 'none', border: 'none', color: T.bright, padding: '8px 14px', fontSize: 12, fontFamily: mono, cursor: 'pointer' },
};
