import React, { useState } from 'react';
import { api } from '../services/api';

export default function ImpactAnalysis() {
  const [filePath, setFilePath] = useState('');
  const [impact, setImpact] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyzeImpact = async () => {
    if (!filePath) return;
    setLoading(true);
    try {
      const { data } = await api.analyzeImpact(filePath);
      setImpact(data);
    } catch (error) {
      console.error(error);
    }
    setLoading(false);
  };

  return (
    <div style={styles.container}>
      <h2>Change Impact Analysis</h2>
      <input
        type="text"
        placeholder="Enter file path (e.g., src/auth.py)"
        value={filePath}
        onChange={(e) => setFilePath(e.target.value)}
        style={styles.input}
      />
      <button onClick={analyzeImpact} disabled={loading} style={styles.button}>
        {loading ? 'Analyzing...' : 'Analyze Impact'}
      </button>

      {impact && (
        <div style={styles.result}>
          <h3>Impact Results</h3>
          <p><strong>File:</strong> {impact.file}</p>
          <p><strong>Risk Level:</strong> <span style={getRiskStyle(impact.risk_level)}>{impact.risk_level}</span></p>
          
          {impact.blast_radius && impact.blast_radius.length > 0 && (
            <div style={styles.blastRadius}>
              <h4>Affected Files ({impact.blast_radius.length})</h4>
              {impact.blast_radius.map((file, idx) => (
                <div key={idx} style={styles.affectedFile}>{file}</div>
              ))}
            </div>
          )}

          {impact.impact_explanation && (
            <div style={styles.explanation}>
              <h4>Explanation</h4>
              <p>{impact.impact_explanation}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const getRiskStyle = (level) => {
  const colors = { high: '#dc3545', medium: '#ffc107', low: '#28a745' };
  return { color: colors[level] || '#333', fontWeight: 'bold' };
};

const styles = {
  container: { padding: '20px', background: '#fff', borderRadius: '8px', marginBottom: '20px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' },
  input: { width: '100%', padding: '10px', marginBottom: '10px', fontSize: '14px', borderRadius: '4px', border: '1px solid #ddd' },
  button: { padding: '10px 20px', background: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' },
  result: { marginTop: '20px', padding: '15px', background: '#f9f9f9', borderRadius: '6px' },
  blastRadius: { marginTop: '15px' },
  affectedFile: { padding: '8px', background: '#fff', borderRadius: '4px', marginBottom: '5px', border: '1px solid #ddd' },
  explanation: { marginTop: '15px', padding: '10px', background: '#e7f3ff', borderRadius: '4px' }
};
