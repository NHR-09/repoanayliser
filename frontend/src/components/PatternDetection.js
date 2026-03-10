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

  useEffect(() => {
    loadPatterns();
  }, [repoId]);

  if (loading) return <div style={styles.container}><span style={styles.loadingText}>Loading patterns…</span></div>;
  if (!patterns) return <div style={styles.container}><span style={styles.loadingText}>No patterns detected yet</span></div>;

  return (
    <div style={styles.container}>
      <div style={styles.headerBar}>
        <h2 style={styles.heading}>Detected Patterns</h2>
        <button onClick={loadPatterns} style={styles.refreshBtn} disabled={loading}>
          {loading ? 'Refreshing…' : '↻ Refresh'}
        </button>
      </div>

      <div style={styles.terminal}>
        <div style={styles.terminalHeader}>
          <div style={styles.terminalButtons}>
            <span style={{ ...styles.terminalButton, background: '#ff5f56' }}></span>
            <span style={{ ...styles.terminalButton, background: '#ffbd2e' }}></span>
            <span style={{ ...styles.terminalButton, background: '#27c93f' }}></span>
          </div>
          <div style={styles.terminalTitle}>architech — patterns</div>
        </div>
        <div style={styles.terminalBody}>
          {terminalLines.map((line, idx) => {
            const isPatternName = line === line.toUpperCase() && line.length > 0 && /^[A-Z_]+$/.test(line);
            const isDetected = line.includes('✓ Detected');
            const isNotDetected = line.includes('Not detected');

            return (
              <div key={idx} style={styles.terminalLine}>
                {isPatternName ? (
                  <Highlighter color="#fbbf24">{line}</Highlighter>
                ) : isDetected ? (
                  <Highlighter color="#4ade80">{line}</Highlighter>
                ) : isNotDetected ? (
                  <Highlighter color="#f87171">{line}</Highlighter>
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
  container: {
    padding: '28px',
    background: 'var(--bg-card)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border)',
    marginBottom: '20px',
  },
  loadingText: {
    color: 'var(--text-muted)',
    fontSize: '14px',
  },
  headerBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '20px',
  },
  heading: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  refreshBtn: {
    padding: '6px 14px',
    background: 'var(--bg-elevated)',
    color: 'var(--text-secondary)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 500,
  },
  terminal: {
    borderRadius: 'var(--radius-md)',
    overflow: 'hidden',
    border: '1px solid var(--border)',
  },
  terminalHeader: {
    background: 'var(--bg-elevated)',
    padding: '10px 15px',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    borderBottom: '1px solid var(--border)',
  },
  terminalButtons: { display: 'flex', gap: '7px' },
  terminalButton: { width: '11px', height: '11px', borderRadius: '50%' },
  terminalTitle: {
    color: 'var(--text-muted)',
    fontSize: '12px',
    fontFamily: 'var(--font-mono)',
    fontWeight: 500,
  },
  terminalBody: {
    background: 'var(--bg-primary)',
    color: 'var(--text-secondary)',
    fontFamily: 'var(--font-mono)',
    fontSize: '13px',
    padding: '20px',
    minHeight: '280px',
    maxHeight: '500px',
    overflowY: 'auto',
    lineHeight: '1.9',
  },
  terminalLine: { marginBottom: '1px' },
};
