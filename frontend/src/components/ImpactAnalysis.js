import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { formatFilePath } from '../utils/formatters';

export default function ImpactAnalysis({ repoId }) {
  const [filePath, setFilePath] = useState('');
  const [changeType, setChangeType] = useState('modify');
  const [impact, setImpact] = useState(null);
  const [loading, setLoading] = useState(false);
  const [files, setFiles] = useState([]);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => { loadFiles(); }, []);

  const loadFiles = async () => {
    setLoadingFiles(true);
    try { const { data } = await api.getFiles(repoId); setFiles(data.files || []); }
    catch (error) { console.error('Failed to load files:', error); }
    setLoadingFiles(false);
  };

  const analyzeImpact = async () => {
    if (!filePath) return;
    setLoading(true); setError(null);
    try { const { data } = await api.analyzeImpact(filePath, changeType); setImpact(data); }
    catch (err) { console.error(err); setError(err.response?.data?.detail || err.message || 'Analysis failed'); }
    setLoading(false);
  };

  const formatExplanation = (text) => {
    if (!text) return null;
    return text.split('\n').map((line, idx) => {
      line = line.trim();
      if (!line) return null;
      if (line.endsWith(':')) return <div key={idx} style={styles.header}>{line}</div>;
      if (line.startsWith('-') || line.startsWith('•')) return <div key={idx} style={styles.bullet}>{line}</div>;
      if (/^\d+\./.test(line)) return <div key={idx} style={styles.numbered}>{line}</div>;
      return <div key={idx} style={styles.paragraph}>{line}</div>;
    });
  };

  const allAffected = impact ? [...(impact.direct_dependents || []), ...(impact.indirect_dependents || [])] : [];

  return (
    <div style={styles.container}>
      <div style={styles.titleSection}>
        <h2 style={styles.title}>Change Impact Analysis</h2>
        <p style={styles.subtitle}>Analyze the blast radius and risk of modifying a file</p>
      </div>

      <div style={styles.inputSection}>
        <label style={styles.label}>Select File:</label>
        <select value={filePath} onChange={(e) => setFilePath(e.target.value)} style={styles.select} disabled={loadingFiles}>
          <option value="">{loadingFiles ? 'Loading files…' : 'Select a file'}</option>
          {files.map((file, idx) => <option key={idx} value={file} title={file}>{formatFilePath(file, 3)}</option>)}
        </select>
        <label style={styles.label}>Change Type:</label>
        <div style={styles.changeTypeRow}>
          {['modify', 'delete', 'move'].map(type => (
            <button key={type} onClick={() => setChangeType(type)}
              style={{ ...styles.changeTypeBtn, ...(changeType === type ? styles.changeTypeBtnActive : {}) }}>
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </button>
          ))}
        </div>
        <button onClick={analyzeImpact} disabled={loading || !filePath}
          style={{ ...styles.button, ...(loading || !filePath ? styles.buttonDisabled : {}) }}>
          {loading ? 'Analyzing…' : 'Analyze Impact'}
        </button>
      </div>

      {error && <div style={styles.errorBox}><strong>Error:</strong> {error}</div>}

      {impact && (
        <div style={styles.result}>
          <div style={styles.resultHeader}><h3 style={styles.resultTitle}>Impact Analysis Results</h3></div>

          <div style={styles.infoGrid}>
            <div style={styles.infoCard}><div style={styles.infoLabel}>Target File</div><div style={styles.infoValue} title={impact.file}>{formatFilePath(impact.file, 2)}</div></div>
            <div style={styles.infoCard}><div style={styles.infoLabel}>Change Type</div><div style={styles.infoValue}>{(impact.change_type || changeType).toUpperCase()}</div></div>
            <div style={styles.infoCard}><div style={styles.infoLabel}>Risk Level</div><div style={{ ...styles.infoValue, ...getRiskStyle(impact.risk_level) }}>{(impact.risk_level || 'unknown').toUpperCase()}</div></div>
            <div style={styles.infoCard}><div style={styles.infoLabel}>Risk Score</div><div style={styles.infoValue}>{impact.risk_score || 0} / 100</div></div>
            <div style={styles.infoCard}><div style={styles.infoLabel}>Direct</div><div style={styles.infoValue}>{(impact.direct_dependents || []).length}</div></div>
            <div style={styles.infoCard}><div style={styles.infoLabel}>Total Affected</div><div style={styles.infoValue}>{impact.total_affected || allAffected.length}</div></div>
          </div>

          {impact.direct_dependents && impact.direct_dependents.length > 0 && (
            <div style={styles.directSection}>
              <h4 style={styles.sectionTitle}>Direct Dependents ({impact.direct_dependents.length})</h4>
              <div style={styles.fileGrid}>
                {impact.direct_dependents.slice(0, 20).map((file, idx) => <div key={idx} style={styles.directFile} title={file}>{formatFilePath(file, 2)}</div>)}
                {impact.direct_dependents.length > 20 && <div style={styles.moreFiles}>… and {impact.direct_dependents.length - 20} more</div>}
              </div>
            </div>
          )}

          {impact.indirect_dependents && impact.indirect_dependents.length > 0 && (
            <div style={styles.indirectSection}>
              <h4 style={styles.sectionTitle}>Indirect Dependents ({impact.indirect_dependents.length})</h4>
              <div style={styles.fileGrid}>
                {impact.indirect_dependents.slice(0, 20).map((file, idx) => <div key={idx} style={styles.indirectFile} title={file}>{formatFilePath(file, 2)}</div>)}
                {impact.indirect_dependents.length > 20 && <div style={styles.moreFiles}>… and {impact.indirect_dependents.length - 20} more</div>}
              </div>
            </div>
          )}

          {impact.functions_affected && impact.functions_affected.functions && impact.functions_affected.functions.length > 0 && (
            <div style={styles.functionsSection}>
              <h4 style={styles.sectionTitle}>Functions Affected ({impact.functions_affected.total_functions})</h4>
              <div style={styles.funcGrid}>
                {impact.functions_affected.functions.slice(0, 15).map((fn, idx) => (
                  <div key={idx} style={styles.funcCard}>
                    <div style={styles.funcName}>{fn.name}</div>
                    <div style={styles.funcCallers}>{fn.caller_count} callers</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {allAffected.length === 0 && (!impact.functions_affected || !impact.functions_affected.functions || impact.functions_affected.functions.length === 0) && (
            <div style={styles.emptySection}><p style={styles.emptyText}>No dependents found. Minimal blast radius.</p></div>
          )}

          {impact.explanation && (
            <div style={styles.explanation}>
              <h4 style={styles.sectionTitle}>AI Analysis</h4>
              <div style={styles.explanationContent}>{formatExplanation(impact.explanation)}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const getRiskStyle = (level) => {
  const riskStyles = {
    high: { color: '#f87171', background: 'var(--red-dim)', padding: '6px 14px', borderRadius: '14px', fontWeight: 700, display: 'inline-block', fontSize: '13px' },
    medium: { color: '#fbbf24', background: 'var(--amber-dim)', padding: '6px 14px', borderRadius: '14px', fontWeight: 700, display: 'inline-block', fontSize: '13px' },
    low: { color: '#4ade80', background: 'var(--green-dim)', padding: '6px 14px', borderRadius: '14px', fontWeight: 700, display: 'inline-block', fontSize: '13px' }
  };
  return riskStyles[level] || { color: 'var(--text-primary)', fontWeight: 700 };
};

const styles = {
  container: { padding: '28px', background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', marginBottom: '20px' },
  titleSection: { marginBottom: '24px', borderBottom: '1px solid var(--border)', paddingBottom: '16px' },
  title: { margin: '0 0 6px', fontSize: '20px', color: 'var(--text-primary)', fontWeight: 600 },
  subtitle: { margin: 0, fontSize: '13px', color: 'var(--text-muted)' },
  inputSection: { background: 'var(--bg-elevated)', padding: '20px', borderRadius: 'var(--radius-md)', marginBottom: '20px', border: '1px solid var(--border)' },
  label: { display: 'block', marginBottom: '8px', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' },
  select: { width: '100%', padding: '10px 14px', marginBottom: '14px', fontSize: '13px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', background: 'var(--bg-input)', color: 'var(--text-primary)' },
  changeTypeRow: { display: 'flex', gap: '8px', marginBottom: '14px' },
  changeTypeBtn: { padding: '8px 14px', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', background: 'var(--bg-card)', cursor: 'pointer', fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)', transition: 'all 0.2s' },
  changeTypeBtnActive: { borderColor: 'var(--text-primary)', background: 'var(--accent-glow)', color: 'var(--text-primary)', fontWeight: 700 },
  button: { padding: '10px 22px', background: 'var(--text-primary)', color: 'var(--bg-primary)', border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '13px', fontWeight: 600 },
  buttonDisabled: { background: 'var(--bg-elevated)', color: 'var(--text-dim)', cursor: 'not-allowed' },
  errorBox: { padding: '14px', background: 'var(--red-dim)', border: '1px solid rgba(248,113,113,0.15)', borderRadius: 'var(--radius-md)', color: 'var(--red)', marginBottom: '14px', fontSize: '13px' },
  result: { marginTop: '20px' },
  resultHeader: { background: 'var(--bg-elevated)', padding: '14px 20px', borderRadius: 'var(--radius-md) var(--radius-md) 0 0', border: '1px solid var(--border)', borderBottom: 'none', marginBottom: '0' },
  resultTitle: { margin: 0, color: 'var(--text-primary)', fontSize: '16px', fontWeight: 600 },
  infoGrid: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '20px', padding: '16px', background: 'var(--bg-elevated)', borderRadius: '0 0 var(--radius-md) var(--radius-md)', border: '1px solid var(--border)', borderTop: '1px solid var(--border)' },
  infoCard: { padding: '14px', background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' },
  infoLabel: { fontSize: '10px', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px' },
  infoValue: { fontSize: '16px', color: 'var(--text-primary)', fontWeight: 700, wordBreak: 'break-word', fontFamily: 'var(--font-mono)' },
  directSection: { marginTop: '16px', padding: '16px', background: 'var(--red-dim)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(248,113,113,0.15)' },
  indirectSection: { marginTop: '12px', padding: '16px', background: 'var(--amber-dim)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(251,191,36,0.12)' },
  functionsSection: { marginTop: '12px', padding: '16px', background: 'rgba(167,139,250,0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(167,139,250,0.12)' },
  emptySection: { marginTop: '16px', padding: '16px', background: 'var(--green-dim)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(74,222,128,0.12)', textAlign: 'center' },
  emptyText: { margin: 0, fontSize: '14px', color: 'var(--green)', fontWeight: 500 },
  sectionTitle: { margin: '0 0 12px', fontSize: '14px', color: 'var(--text-primary)', fontWeight: 600 },
  fileGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '8px' },
  directFile: { padding: '8px 12px', background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(248,113,113,0.15)', fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' },
  indirectFile: { padding: '8px 12px', background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(251,191,36,0.12)', fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' },
  funcGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '8px' },
  funcCard: { padding: '8px 12px', background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(167,139,250,0.12)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  funcName: { fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' },
  funcCallers: { fontSize: '10px', color: '#a78bfa', fontWeight: 600, background: 'rgba(167,139,250,0.12)', padding: '2px 8px', borderRadius: '10px', fontFamily: 'var(--font-mono)' },
  moreFiles: { padding: '8px', textAlign: 'center', color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '12px' },
  explanation: { marginTop: '16px', padding: '16px', background: 'var(--blue-dim)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(96,165,250,0.12)' },
  explanationContent: { fontSize: '13px', lineHeight: '1.8', color: 'var(--text-secondary)' },
  header: { fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', marginTop: '12px', marginBottom: '6px' },
  bullet: { paddingLeft: '16px', marginBottom: '4px', color: 'var(--text-secondary)' },
  numbered: { paddingLeft: '10px', marginBottom: '4px', color: 'var(--text-secondary)', fontWeight: 500 },
  paragraph: { marginBottom: '8px', color: 'var(--text-muted)' },
};
