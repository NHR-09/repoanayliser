import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import Highlighter from './Highlighter';

export default function PatternDetection({ repoId }) {
  const [patterns, setPatterns] = useState(null);
  const [loading, setLoading] = useState(false);
  const [terminalLines, setTerminalLines] = useState([]);

  const loadPatterns = async () => {
    setLoading(true);
    setTerminalLines([]);
    
    try {
      const { data } = await api.getPatterns(repoId);
      setPatterns(data);
      
      const lines = [];
      // Display results in terminal
      Object.entries(data).forEach(([name, patternData]) => {
        lines.push(name.toUpperCase());
        if (patternData.detected) {
          lines.push('✓ Detected');
          lines.push(`Confidence: ${(patternData.confidence * 100).toFixed(0)}%`);
          lines.push('');
          if (patternData.layers) {
            lines.push(`Layers: ${patternData.layers.join(', ')}`);
          }
          if (patternData.controllers !== undefined) {
            lines.push(`Controllers: ${patternData.controllers}`);
          }
          if (patternData.models !== undefined) {
            lines.push(`Models: ${patternData.models}`);
          }
        } else {
          lines.push('Not detected.');
        }
        lines.push('');
      });
      setTerminalLines(lines);
    } catch (error) {
      setTerminalLines(['Error: Failed to load patterns']);
      console.error(error);
    }
    setLoading(false);
  };

  const addTerminalLine = (line) => {
    setTerminalLines(prev => [...prev, line]);
  };

  useEffect(() => {
    loadPatterns();
  }, [repoId]);

  if (loading) return <div style={styles.container}>Loading patterns...</div>;
  if (!patterns) return <div style={styles.container}>No patterns detected yet</div>;

  return (
    <div style={styles.container}>
      <div style={styles.headerBar}>
        <h2>Detected Patterns</h2>
        <button onClick={loadPatterns} style={styles.refreshBtn} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
      
      {/* Terminal Window */}
      <div style={styles.terminal}>
        <div style={styles.terminalHeader}>
          <div style={styles.terminalButtons}>
            <span style={{...styles.terminalButton, background: '#ff5f56'}}></span>
            <span style={{...styles.terminalButton, background: '#ffbd2e'}}></span>
            <span style={{...styles.terminalButton, background: '#27c93f'}}></span>
          </div>
          <div style={styles.terminalTitle}>architech — patterns</div>
        </div>
        <div style={styles.terminalBody}>
          {terminalLines.map((line, idx) => {
            const isPatternName = line === line.toUpperCase() && line.length > 0 && /^[A-Z]+$/.test(line);
            const isDetected = line.includes('✓ Detected');
            const isNotDetected = line.includes('Not detected');
            
            return (
              <div key={idx} style={styles.terminalLine}>
                {isPatternName ? (
                  <Highlighter color="#FFED4A">{line}</Highlighter>
                ) : isDetected ? (
                  <Highlighter color="#82FFAD">{line}</Highlighter>
                ) : isNotDetected ? (
                  <Highlighter color="#FF8282">{line}</Highlighter>
                ) : (
                  line
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: { padding: '20px', background: '#fff', borderRadius: '8px', marginBottom: '20px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' },
  headerBar: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' },
  refreshBtn: { padding: '6px 12px', background: '#667eea', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '13px' },
  terminal: { marginBottom: '30px', borderRadius: '8px', overflow: 'hidden', boxShadow: '0 4px 12px rgba(0,0,0,0.15)' },
  terminalHeader: { background: '#e8e8e8', padding: '10px 15px', display: 'flex', alignItems: 'center', gap: '10px' },
  terminalButtons: { display: 'flex', gap: '8px' },
  terminalButton: { width: '12px', height: '12px', borderRadius: '50%' },
  terminalTitle: { color: '#666', fontSize: '13px', fontWeight: '500' },
  terminalBody: { background: '#f5f5f5', color: '#333', fontFamily: 'Monaco, Menlo, monospace', fontSize: '14px', padding: '20px', minHeight: '300px', maxHeight: '500px', overflowY: 'auto', lineHeight: '1.8' },
  terminalLine: { marginBottom: '2px' }
};
