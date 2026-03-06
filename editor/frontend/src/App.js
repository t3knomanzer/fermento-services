/* App.js — Two modes: Report and Editor. Edit-from-report loads into Editor tab. */
import React, { useState, useCallback, useRef } from 'react';
import Editor from './Editor';
import Report from './Report';
import { T, mono, sans, ensureStage, addGrowth } from './shared';

export default function App() {
  const [mode, setMode] = useState('report');
  const [runs, setRuns] = useState({});

  // Editor state — persisted across tab switches
  // This is the single source of truth for what the Editor is showing.
  const [editorState, setEditorState] = useState(null);
  // { filename, data, headers, fromReport: bool }

  const prepareRun = useCallback((filename, headers, data) => {
    let rows = [...data];
    const hdrs = [...headers];
    if (!hdrs.includes('stage')) { rows = ensureStage(rows, 4); hdrs.push('stage'); }
    else { rows = ensureStage(rows, 4); }
    if (hdrs.includes('distance')) {
      rows = addGrowth(rows);
      if (!hdrs.includes('growth')) hdrs.push('growth');
    }
    return { filename, headers: hdrs, data: rows };
  }, []);

  const handleMultiUpload = useCallback((newRuns) => {
    const prepared = {};
    for (const r of newRuns) prepared[r.filename] = prepareRun(r.filename, r.headers, r.data);
    setRuns(prev => ({ ...prev, ...prepared }));
  }, [prepareRun]);

  /* Report context menu → edit a run: load into Editor and switch tab */
  const handleEditRun = useCallback((filename) => {
    const run = runs[filename];
    if (!run) return;
    setEditorState({
      filename: run.filename,
      data: run.data,
      headers: run.headers,
      fromReport: true,
    });
    setMode('editor');
  }, [runs]);

  /* Editor saves data — update runs if it came from report, always update editorState */
  const handleEditorSave = useCallback((filename, data, headers) => {
    setEditorState(prev => {
      const next = { ...prev, filename, data, headers };
      // If this run came from report, sync back to runs
      if (next.fromReport) {
        setRuns(r => ({ ...r, [filename]: { ...r[filename], data, headers, filename } }));
      }
      return next;
    });
  }, []);

  /* Editor uploaded a new file (standalone) */
  const handleEditorUploadSave = useCallback((filename, data, headers) => {
    setEditorState({ filename, data, headers, fromReport: false });
  }, []);

  return (
    <div style={{ minHeight: '100vh', background: T.bg, fontFamily: sans, color: T.bright }}>
      <nav style={S.nav}>
        <div style={S.navLeft}>
          <span style={S.logo}>⬡</span>
          <span style={S.brand}>Fermento</span>
        </div>
        <div style={S.tabs}>
          <button
            style={{ ...S.tab, ...(mode === 'report' ? S.tabActive : {}) }}
            onClick={() => setMode('report')}
          >
            Report
          </button>
          <button
            style={{ ...S.tab, ...(mode === 'editor' ? S.tabActive : {}) }}
            onClick={() => setMode('editor')}
          >
            Editor
          </button>
          {mode === 'editor' && editorState?.fromReport && (
            <span style={S.tabBadge}>
              {editorState.filename.replace(/\.csv$/i, '')}
            </span>
          )}
        </div>
      </nav>

      {/* Report — always mounted but hidden when not active, to preserve scroll */}
      <div style={{ display: mode === 'report' ? 'block' : 'none' }}>
        <Report runs={runs} onMultiUpload={handleMultiUpload} onEditRun={handleEditRun} />
      </div>

      {/* Editor — always mounted but hidden when not active, to preserve state */}
      <div style={{ display: mode === 'editor' ? 'block' : 'none' }}>
        <Editor
          initialData={editorState?.data}
          initialHeaders={editorState?.headers}
          initialFilename={editorState?.filename}
          onSave={editorState?.fromReport ? handleEditorSave : handleEditorUploadSave}
          onClose={editorState?.fromReport ? () => setMode('report') : null}
          embedded={!!editorState?.fromReport}
        />
      </div>
    </div>
  );
}

const S = {
  nav: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 20px', height: 44, background: 'rgba(15,17,23,0.98)', borderBottom: '1px solid rgba(255,255,255,0.06)', position: 'sticky', top: 0, zIndex: 200 },
  navLeft: { display: 'flex', alignItems: 'center', gap: 8 },
  logo: { fontSize: 20, color: T.indigo },
  brand: { fontWeight: 700, fontSize: 16, letterSpacing: '-0.02em' },
  tabs: { display: 'flex', gap: 2, alignItems: 'center' },
  tab: { background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)', padding: '8px 16px', fontSize: 13, fontFamily: mono, cursor: 'pointer', borderRadius: '6px 6px 0 0' },
  tabActive: { color: T.white, background: 'rgba(99,102,241,0.15)', borderBottom: `2px solid ${T.indigo}` },
  tabBadge: { color: T.amber, fontSize: 12, fontFamily: mono, marginLeft: 8, padding: '3px 8px', background: 'rgba(245,158,11,0.1)', borderRadius: 6 },
};
