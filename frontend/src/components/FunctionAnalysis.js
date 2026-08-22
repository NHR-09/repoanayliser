import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function FunctionAnalysis({ repoId }) {
  const [functions, setFunctions] = useState([]);
  const [selectedFunction, setSelectedFunction] = useState('');
  const [functionInfo, setFunctionInfo] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadFunctions();
  }, []);

  const loadFunctions = async () => {
    try {
      const { data } = await api.getFunctions(repoId);
      setFunctions(data.functions || []);
    } catch (error) {
      console.error(error);
    }
  };

  const analyzeFunction = async () => {
    if (!selectedFunction) return;
    setLoading(true);
    try {
      const { data } = await api.getFunctionInfo(selectedFunction);
      setFunctionInfo(data);
    } catch (error) {
      console.error(error);
      setFunctionInfo({ error: error.message });
    }
    setLoading(false);
  };

  const formatExplanation = (text) => {
    if (!text) return null;
    return text.split('\n').map((line, idx) => {
      line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      line = line.replace(/__(.+?)__/g, '<strong>$1</strong>');
      line = line.replace(/`(.+?)`/g, '<code style="background:var(--bg-elevated);padding:2px 6px;border-radius:4px;font-family:var(--font-mono);font-size:12px;color:var(--text-primary)">$1</code>');
      if (line.startsWith('####')) return <h4 key={idx} style={styles.h4}>{line.replace(/####\s*/, '')}</h4>;
      if (line.startsWith('###')) return <h4 key={idx} style={styles.h4}>{line.replace(/###\s*/, '')}</h4>;
      if (line.startsWith('##')) return <h3 key={idx} style={styles.h3}>{line.replace(/##\s*/, '')}</h3>;
      if (line.startsWith('#')) return <h2 key={idx} style={styles.h2}>{line.replace(/#\s*/, '')}</h2>;
      if (/^\d+\.\s/.test(line)) return <div key={idx} style={styles.listItem} dangerouslySetInnerHTML={{ __html: line }} />;
      if (/^[-*]\s/.test(line)) return <div key={idx} style={styles.bulletItem} dangerouslySetInnerHTML={{ __html: line.replace(/^[-*]\s/, '• ') }} />;
      if (line.trim()) return <p key={idx} style={styles.paragraph} dangerouslySetInnerHTML={{ __html: line }} />;
      return <br key={idx} />;
    });
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.heading}>Function Analysis</h2>

      <div style={styles.inputSection}>
        <select
          value={selectedFunction}
          onChange={(e) => setSelectedFunction(e.target.value)}
          style={styles.select}
        >
          <option value="">Select a function…</option>
          {functions.map((fn, idx) => (
            <option key={idx} value={fn.name}>
              {fn.name} ({fn.file})
            </option>
          ))}
        </select>
        <button onClick={analyzeFunction} disabled={loading || !selectedFunction} style={styles.button}>
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>

      {functionInfo && !functionInfo.error && (
        <div style={styles.result}>
          <h3 style={styles.fnName}>{functionInfo.function_name}</h3>

          <div style={styles.section}>
            <span style={styles.label}>Location</span>
            <span style={styles.locationValue}>{functionInfo.file} : {functionInfo.line}</span>
          </div>

          <div style={styles.section}>
            <h4 style={styles.sectionTitle}>Called By ({functionInfo.usage_count} locations)</h4>
            {functionInfo.callers && functionInfo.callers.length > 0 ? (
              functionInfo.callers.map((caller, idx) => (
                <div key={idx} style={styles.caller}>
                  <strong style={{ color: 'var(--text-primary)' }}>{caller.caller_name}</strong>
                  <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}> in {caller.caller_file}{caller.line > 0 && ` :${caller.line}`}</span>
                </div>
              ))
            ) : (
              <p style={styles.noData}>No callers found</p>
            )}
          </div>

          <div style={styles.section}>
            <h4 style={styles.sectionTitle}>AI Explanation</h4>
            <div style={styles.explanation}>
              {formatExplanation(functionInfo.explanation)}
            </div>
          </div>

          {functionInfo.related_code && functionInfo.related_code.length > 0 && (
            <div style={styles.section}>
              <h4 style={styles.sectionTitle}>Related Code</h4>
              {functionInfo.related_code.map((code, idx) => (
                <div key={idx} style={styles.relatedCode}>
                  <div style={styles.codeHeader}>{code.metadata.file_path}</div>
                  <pre style={styles.code}>{code.code}</pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {functionInfo && functionInfo.error && (
        <div style={styles.error}>Error: {functionInfo.error}</div>
      )}
    </div>
  );
}

const styles = {
  container: { padding: '28px', background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', marginBottom: '20px' },
  heading: { margin: '0 0 20px', fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)' },
  inputSection: { display: 'flex', gap: '10px', marginBottom: '20px' },
  select: { flex: 1, padding: '10px 14px', fontSize: '13px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', background: 'var(--bg-input)', color: 'var(--text-primary)', fontFamily: 'var(--font-sans)' },
  button: { padding: '10px 22px', background: 'var(--text-primary)', color: 'var(--bg-primary)', border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontWeight: 600, fontSize: '13px' },
  result: { marginTop: '20px' },
  fnName: { fontSize: '16px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', marginBottom: '16px' },
  section: { marginBottom: '16px', padding: '16px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' },
  sectionTitle: { fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.5px' },
  label: { fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px', display: 'block', marginBottom: '4px' },
  locationValue: { fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)' },
  caller: { padding: '8px 12px', background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', marginBottom: '4px', border: '1px solid var(--border)', fontFamily: 'var(--font-mono)', fontSize: '13px' },
  noData: { color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '13px' },
  explanation: { padding: '16px', background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', lineHeight: '1.8', color: 'var(--text-secondary)', border: '1px solid var(--border)' },
  h2: { fontSize: '18px', fontWeight: 600, marginTop: '16px', marginBottom: '8px', color: 'var(--text-primary)' },
  h3: { fontSize: '16px', fontWeight: 600, marginTop: '12px', marginBottom: '6px', color: 'var(--text-primary)' },
  h4: { fontSize: '14px', fontWeight: 600, marginTop: '10px', marginBottom: '6px', color: 'var(--text-secondary)' },
  paragraph: { marginBottom: '8px', lineHeight: '1.7' },
  listItem: { marginLeft: '16px', marginBottom: '6px', lineHeight: '1.7' },
  bulletItem: { marginLeft: '16px', marginBottom: '4px', lineHeight: '1.7' },
  relatedCode: { marginBottom: '12px', borderRadius: 'var(--radius-sm)', overflow: 'hidden', border: '1px solid var(--border)' },
  codeHeader: { padding: '8px 14px', background: 'var(--bg-card)', fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', borderBottom: '1px solid var(--border)' },
  code: { background: 'var(--bg-primary)', padding: '14px', overflow: 'auto', fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', margin: 0, lineHeight: '1.6' },
  error: { padding: '14px', background: 'var(--red-dim)', color: 'var(--red)', borderRadius: 'var(--radius-sm)', marginTop: '20px', border: '1px solid rgba(248,113,113,0.15)' },
};
