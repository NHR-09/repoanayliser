import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { formatFilePath } from '../utils/formatters';

export default function ImpactAnalysis() {
  const [filePath, setFilePath] = useState('');
  const [changeType, setChangeType] = useState('modify');
  const [impact, setImpact] = useState(null);
  const [loading, setLoading] = useState(false);
  const [files, setFiles] = useState([]);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadFiles();
  }, []);

  const loadFiles = async () => {
    setLoadingFiles(true);
    try {
      const { data } = await api.getFiles();
      setFiles(data.files || []);
    } catch (error) {
      console.error('Failed to load files:', error);
    }
    setLoadingFiles(false);
  };

  const analyzeImpact = async () => {
    if (!filePath) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.analyzeImpact(filePath, changeType);
      setImpact(data);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || 'Analysis failed');
    }
    setLoading(false);
  };

  const formatExplanation = (text) => {
    if (!text) return null;
    return text.split('\n').map((line, idx) => {
      line = line.trim();
      if (!line) return null;
      if (line.endsWith(':')) {
        return <div key={idx} style={styles.header}>{line}</div>;
      }
      if (line.startsWith('-') || line.startsWith('•')) {
        return <div key={idx} style={styles.bullet}>{line}</div>;
      }
      if (/^\d+\./.test(line)) {
        return <div key={idx} style={styles.numbered}>{line}</div>;
      }
      return <div key={idx} style={styles.paragraph}>{line}</div>;
    });
  };

  // Combine direct + indirect dependents as the full blast radius
  const allAffected = impact ? [
    ...(impact.direct_dependents || []),
    ...(impact.indirect_dependents || [])
  ] : [];

  return (
    <div style={styles.container}>
      <div style={styles.titleSection}>
        <h2 style={styles.title}>Change Impact Analysis</h2>
        <p style={styles.subtitle}>Analyze the blast radius and risk of modifying a file</p>
      </div>

      <div style={styles.inputSection}>
        <label style={styles.label}>Select File to Analyze:</label>
        <select
          value={filePath}
          onChange={(e) => setFilePath(e.target.value)}
          style={styles.select}
          disabled={loadingFiles}
        >
          <option value="">{loadingFiles ? 'Loading files...' : 'Select a file'}</option>
          {files.map((file, idx) => (
            <option key={idx} value={file} title={file}>
              {formatFilePath(file, 3)}
            </option>
          ))}
        </select>

        <label style={styles.label}>Change Type:</label>
        <div style={styles.changeTypeRow}>
          {['modify', 'delete', 'move'].map(type => (
            <button
              key={type}
              onClick={() => setChangeType(type)}
              style={{
                ...styles.changeTypeBtn,
                ...(changeType === type ? styles.changeTypeBtnActive : {})
              }}
            >
              {type === 'modify' ? '✏️' : type === 'delete' ? '🗑️' : '📦'} {type.charAt(0).toUpperCase() + type.slice(1)}
            </button>
          ))}
        </div>

        <button 
          onClick={analyzeImpact} 
          disabled={loading || !filePath} 
          style={{
            ...styles.button,
            ...(loading || !filePath ? styles.buttonDisabled : {})
          }}
        >
          {loading ? '⏳ Analyzing...' : '🔍 Analyze Impact'}
        </button>
      </div>

      {error && (
        <div style={styles.errorBox}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {impact && (
        <div style={styles.result}>
          <div style={styles.resultHeader}>
            <h3 style={styles.resultTitle}>Impact Analysis Results</h3>
          </div>

          <div style={styles.infoGrid}>
            <div style={styles.infoCard}>
              <div style={styles.infoLabel}>Target File</div>
              <div style={styles.infoValue} title={impact.file}>
                {formatFilePath(impact.file, 2)}
              </div>
            </div>

            <div style={styles.infoCard}>
              <div style={styles.infoLabel}>Change Type</div>
              <div style={styles.infoValue}>
                {(impact.change_type || changeType).toUpperCase()}
              </div>
            </div>

            <div style={styles.infoCard}>
              <div style={styles.infoLabel}>Risk Level</div>
              <div style={{...styles.infoValue, ...getRiskStyle(impact.risk_level)}}>
                {(impact.risk_level || 'unknown').toUpperCase()}
              </div>
            </div>

            <div style={styles.infoCard}>
              <div style={styles.infoLabel}>Risk Score</div>
              <div style={styles.infoValue}>
                {impact.risk_score || 0} / 100
              </div>
            </div>

            <div style={styles.infoCard}>
              <div style={styles.infoLabel}>Direct Dependents</div>
              <div style={styles.infoValue}>
                {(impact.direct_dependents || []).length}
              </div>
            </div>

            <div style={styles.infoCard}>
              <div style={styles.infoLabel}>Total Affected</div>
              <div style={styles.infoValue}>
                {impact.total_affected || allAffected.length}
              </div>
            </div>
          </div>

          {/* Direct Dependents */}
          {impact.direct_dependents && impact.direct_dependents.length > 0 && (
            <div style={styles.directSection}>
              <h4 style={styles.sectionTitle}>🔴 Direct Dependents ({impact.direct_dependents.length} files)</h4>
              <div style={styles.fileGrid}>
                {impact.direct_dependents.slice(0, 20).map((file, idx) => (
                  <div key={idx} style={styles.directFile} title={file}>
                    {formatFilePath(file, 2)}
                  </div>
                ))}
                {impact.direct_dependents.length > 20 && (
                  <div style={styles.moreFiles}>
                    ... and {impact.direct_dependents.length - 20} more files
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Indirect Dependents */}
          {impact.indirect_dependents && impact.indirect_dependents.length > 0 && (
            <div style={styles.indirectSection}>
              <h4 style={styles.sectionTitle}>🟡 Indirect Dependents ({impact.indirect_dependents.length} files)</h4>
              <div style={styles.fileGrid}>
                {impact.indirect_dependents.slice(0, 20).map((file, idx) => (
                  <div key={idx} style={styles.indirectFile} title={file}>
                    {formatFilePath(file, 2)}
                  </div>
                ))}
                {impact.indirect_dependents.length > 20 && (
                  <div style={styles.moreFiles}>
                    ... and {impact.indirect_dependents.length - 20} more files
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Functions Affected */}
          {impact.functions_affected && impact.functions_affected.functions && impact.functions_affected.functions.length > 0 && (
            <div style={styles.functionsSection}>
              <h4 style={styles.sectionTitle}>⚡ Functions Affected ({impact.functions_affected.total_functions})</h4>
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

          {/* No dependents found */}
          {allAffected.length === 0 && (!impact.functions_affected || !impact.functions_affected.functions || impact.functions_affected.functions.length === 0) && (
            <div style={styles.emptySection}>
              <p style={styles.emptyText}>
                ✅ No dependents found. This file appears to have minimal blast radius.
              </p>
            </div>
          )}

          {/* Explanation from LLM */}
          {impact.explanation && (
            <div style={styles.explanation}>
              <h4 style={styles.sectionTitle}>📝 AI Analysis</h4>
              <div style={styles.explanationContent}>
                {formatExplanation(impact.explanation)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const getRiskStyle = (level) => {
  const riskStyles = {
    high: { 
      color: '#dc3545', 
      background: '#fee2e2',
      padding: '8px 16px',
      borderRadius: '20px',
      fontWeight: 'bold',
      display: 'inline-block'
    },
    medium: { 
      color: '#f59e0b', 
      background: '#fef3c7',
      padding: '8px 16px',
      borderRadius: '20px',
      fontWeight: 'bold',
      display: 'inline-block'
    },
    low: { 
      color: '#10b981', 
      background: '#d1fae5',
      padding: '8px 16px',
      borderRadius: '20px',
      fontWeight: 'bold',
      display: 'inline-block'
    }
  };
  return riskStyles[level] || { color: '#333', fontWeight: 'bold' };
};

const styles = {
  container: { 
    padding: '20px', 
    background: '#fff', 
    borderRadius: '12px', 
    marginBottom: '20px', 
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)' 
  },
  titleSection: {
    marginBottom: '30px',
    borderBottom: '2px solid #667eea',
    paddingBottom: '15px'
  },
  title: {
    margin: '0 0 8px 0',
    fontSize: '28px',
    color: '#1f2937',
    fontWeight: 'bold'
  },
  subtitle: {
    margin: 0,
    fontSize: '14px',
    color: '#6b7280'
  },
  inputSection: {
    background: '#f9fafb',
    padding: '20px',
    borderRadius: '8px',
    marginBottom: '20px'
  },
  label: {
    display: 'block',
    marginBottom: '8px',
    fontSize: '14px',
    fontWeight: '600',
    color: '#374151'
  },
  select: { 
    width: '100%', 
    padding: '12px', 
    marginBottom: '15px', 
    fontSize: '14px', 
    borderRadius: '6px', 
    border: '2px solid #e5e7eb', 
    background: '#fff',
    transition: 'border-color 0.2s'
  },
  changeTypeRow: {
    display: 'flex',
    gap: '10px',
    marginBottom: '15px'
  },
  changeTypeBtn: {
    padding: '8px 16px',
    border: '2px solid #e5e7eb',
    borderRadius: '6px',
    background: '#fff',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '500',
    transition: 'all 0.2s'
  },
  changeTypeBtnActive: {
    borderColor: '#667eea',
    background: '#eff6ff',
    color: '#667eea',
    fontWeight: '700'
  },
  button: { 
    padding: '12px 24px', 
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 
    color: 'white', 
    border: 'none', 
    borderRadius: '6px', 
    cursor: 'pointer',
    fontSize: '15px',
    fontWeight: '600',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    transition: 'transform 0.2s, box-shadow 0.2s'
  },
  buttonDisabled: {
    background: '#d1d5db',
    cursor: 'not-allowed',
    boxShadow: 'none'
  },
  errorBox: {
    padding: '15px',
    background: '#fee2e2',
    border: '1px solid #dc3545',
    borderRadius: '8px',
    color: '#dc3545',
    marginBottom: '15px',
    fontSize: '14px'
  },
  result: { 
    marginTop: '20px', 
    padding: '0'
  },
  resultHeader: {
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    padding: '15px 20px',
    borderRadius: '8px 8px 0 0',
    marginBottom: '20px'
  },
  resultTitle: {
    margin: 0,
    color: 'white',
    fontSize: '20px',
    fontWeight: 'bold'
  },
  infoGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '15px',
    marginBottom: '25px'
  },
  infoCard: {
    background: '#f9fafb',
    padding: '15px',
    borderRadius: '8px',
    border: '1px solid #e5e7eb'
  },
  infoLabel: {
    fontSize: '12px',
    color: '#6b7280',
    marginBottom: '8px',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  infoValue: {
    fontSize: '18px',
    color: '#1f2937',
    fontWeight: 'bold',
    wordBreak: 'break-word'
  },
  directSection: { 
    marginTop: '25px',
    padding: '20px',
    background: '#fee2e2',
    borderRadius: '8px',
    border: '2px solid #f87171'
  },
  indirectSection: { 
    marginTop: '15px',
    padding: '20px',
    background: '#fef3c7',
    borderRadius: '8px',
    border: '2px solid #fbbf24'
  },
  functionsSection: { 
    marginTop: '15px',
    padding: '20px',
    background: '#ede9fe',
    borderRadius: '8px',
    border: '2px solid #8b5cf6'
  },
  emptySection: {
    marginTop: '25px',
    padding: '20px',
    background: '#d1fae5',
    borderRadius: '8px',
    border: '2px solid #10b981',
    textAlign: 'center'
  },
  emptyText: {
    margin: 0,
    fontSize: '16px',
    color: '#065f46',
    fontWeight: '500'
  },
  sectionTitle: {
    margin: '0 0 15px 0',
    fontSize: '18px',
    color: '#1f2937',
    fontWeight: 'bold'
  },
  fileGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
    gap: '10px'
  },
  directFile: { 
    padding: '10px 12px', 
    background: '#fff', 
    borderRadius: '6px', 
    border: '1px solid #f87171',
    fontSize: '13px',
    transition: 'all 0.2s',
    cursor: 'default'
  },
  indirectFile: { 
    padding: '10px 12px', 
    background: '#fff', 
    borderRadius: '6px', 
    border: '1px solid #fbbf24',
    fontSize: '13px',
    transition: 'all 0.2s',
    cursor: 'default'
  },
  funcGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: '10px'
  },
  funcCard: {
    padding: '10px 12px',
    background: '#fff',
    borderRadius: '6px',
    border: '1px solid #8b5cf6',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  funcName: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#1f2937'
  },
  funcCallers: {
    fontSize: '11px',
    color: '#8b5cf6',
    fontWeight: '600',
    background: '#ede9fe',
    padding: '3px 8px',
    borderRadius: '10px'
  },
  moreFiles: {
    padding: '10px',
    textAlign: 'center',
    color: '#6b7280',
    fontStyle: 'italic',
    fontSize: '13px'
  },
  explanation: { 
    marginTop: '25px', 
    padding: '20px', 
    background: '#eff6ff', 
    borderRadius: '8px',
    border: '2px solid #3b82f6'
  },
  explanationContent: {
    fontSize: '14px',
    lineHeight: '1.8',
    color: '#1f2937'
  },
  header: {
    fontSize: '16px',
    fontWeight: 'bold',
    color: '#1f2937',
    marginTop: '15px',
    marginBottom: '8px'
  },
  bullet: {
    paddingLeft: '20px',
    marginBottom: '6px',
    color: '#374151'
  },
  numbered: {
    paddingLeft: '10px',
    marginBottom: '6px',
    color: '#374151',
    fontWeight: '500'
  },
  paragraph: {
    marginBottom: '10px',
    color: '#4b5563'
  }
};
