import React, { useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';
import MarkdownContent from './MarkdownContent';
import SearchableTreeSelect from './SearchableTreeSelect';

const functionValue = (fn) => `${fn.file || ''}::${fn.name}::${fn.line || 0}`;

export default function FunctionAnalysis({ repoId }) {
  const [functions, setFunctions] = useState([]);
  const [selectedFunction, setSelectedFunction] = useState('');
  const [functionInfo, setFunctionInfo] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setSelectedFunction('');
    setFunctionInfo(null);
    const loadFunctions = async () => {
      try {
        const { data } = await api.getFunctions(repoId);
        setFunctions(data.functions || []);
      } catch (error) {
        console.error(error);
      }
    };
    loadFunctions();
  }, [repoId]);

  const functionItems = useMemo(() => functions.map(fn => ({
    value: functionValue(fn),
    label: fn.name,
    path: fn.file || 'unknown',
    secondary: fn.line ? `L${fn.line}` : ''
  })), [functions]);

  const analyzeFunction = async () => {
    const selected = functions.find(fn => functionValue(fn) === selectedFunction);
    if (!selected) return;
    setLoading(true);
    try {
      const { data } = await api.getFunctionInfo(selected.name, repoId, selected.file);
      setFunctionInfo(data);
    } catch (error) {
      console.error(error);
      setFunctionInfo({ error: error.response?.data?.detail || error.message });
    }
    setLoading(false);
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.heading}>Function Analysis</h2>

      <div style={styles.inputSection}>
        <SearchableTreeSelect
          items={functionItems}
          value={selectedFunction}
          onChange={setSelectedFunction}
          placeholder="Select a function…"
          searchPlaceholder="Search functions or file paths…"
          groupByFile
        />
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
            {functionInfo.callers?.length > 0 ? functionInfo.callers.map((caller, idx) => (
              <div key={`${caller.caller_file}-${caller.caller_name}-${idx}`} style={styles.caller}>
                <strong style={{ color: 'var(--text-primary)' }}>{caller.caller_name}</strong>
                <span style={styles.callerLocation}> in {caller.caller_file}{caller.line > 0 && ` :${caller.line}`}</span>
              </div>
            )) : <p style={styles.noData}>No callers found</p>}
          </div>

          <div style={styles.section}>
            <h4 style={styles.sectionTitle}>AI Explanation</h4>
            <div style={styles.explanation}>
              <MarkdownContent>{functionInfo.explanation}</MarkdownContent>
            </div>
          </div>

          {functionInfo.related_code?.length > 0 && (
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

      {functionInfo?.error && <div style={styles.error}>Error: {functionInfo.error}</div>}
    </div>
  );
}

const styles = {
  container: { padding: '28px', background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', marginBottom: '20px' },
  heading: { margin: '0 0 20px', fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)' },
  inputSection: { display: 'flex', gap: '10px', marginBottom: '20px', alignItems: 'flex-start' },
  button: { minHeight: '40px', padding: '10px 22px', background: 'var(--text-primary)', color: 'var(--bg-primary)', border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontWeight: 600, fontSize: '13px' },
  result: { marginTop: '20px' },
  fnName: { fontSize: '16px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', marginBottom: '16px' },
  section: { marginBottom: '16px', padding: '16px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' },
  sectionTitle: { fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', margin: '0 0 10px', textTransform: 'uppercase', letterSpacing: '0.5px' },
  label: { fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px', display: 'block', marginBottom: '4px' },
  locationValue: { fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-primary)', overflowWrap: 'anywhere' },
  caller: { padding: '8px 12px', background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', marginBottom: '4px', border: '1px solid var(--border)', fontFamily: 'var(--font-mono)', fontSize: '13px' },
  callerLocation: { color: 'var(--text-muted)', fontSize: '12px', overflowWrap: 'anywhere' },
  noData: { color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '13px' },
  explanation: { padding: '16px', background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', lineHeight: '1.8', color: 'var(--text-secondary)', border: '1px solid var(--border)' },
  relatedCode: { marginBottom: '12px', borderRadius: 'var(--radius-sm)', overflow: 'hidden', border: '1px solid var(--border)' },
  codeHeader: { padding: '8px 14px', background: 'var(--bg-card)', fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', borderBottom: '1px solid var(--border)' },
  code: { background: 'var(--bg-primary)', padding: '14px', overflow: 'auto', fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', margin: 0, lineHeight: '1.6' },
  error: { padding: '14px', background: 'var(--red-dim)', color: 'var(--red)', borderRadius: 'var(--radius-sm)', marginTop: '20px', border: '1px solid rgba(248,113,113,0.15)' }
};
