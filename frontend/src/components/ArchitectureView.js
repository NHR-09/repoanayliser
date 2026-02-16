import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { formatFilePath, formatEvidenceText } from '../utils/formatters';

export default function ArchitectureView({ repoId }) {
  const [architecture, setArchitecture] = useState(null);
  const [loading, setLoading] = useState(false);
  const [cached, setCached] = useState(false);

  const loadArchitecture = async () => {
    setLoading(true);
    setCached(false);
    try {
      const { data } = await api.getArchitecture(repoId);
      setArchitecture(data);
      if (data.cached) {
        setCached(true);
      }
    } catch (error) {
      console.error(error);
      setArchitecture({ error: 'Failed to load architecture explanation' });
    }
    setLoading(false);
  };

  useEffect(() => {
    loadArchitecture();
  }, [repoId]);

  const formatText = (text) => {
    if (!text) return null;
    
    // Format file paths in text
    text = formatEvidenceText(text);
    
    return text
      .split('\n')
      .map((line, idx) => {
        line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        line = line.replace(/`(.+?)`/g, '<code style="background:#f5f5f5;padding:2px 6px;border-radius:3px;">$1</code>');
        
        if (line.startsWith('###')) {
          return <h4 key={idx} style={styles.h4}>{line.replace(/###\s*/, '')}</h4>;
        } else if (line.startsWith('##')) {
          return <h3 key={idx} style={styles.h3}>{line.replace(/##\s*/, '')}</h3>;
        } else if (/^\d+\.\s/.test(line)) {
          return <div key={idx} style={styles.listItem} dangerouslySetInnerHTML={{ __html: line }} />;
        } else if (/^[-*]\s/.test(line)) {
          return <div key={idx} style={styles.bulletItem} dangerouslySetInnerHTML={{ __html: line.replace(/^[-*]\s/, '• ') }} />;
        } else if (line.trim()) {
          return <p key={idx} style={styles.paragraph} dangerouslySetInnerHTML={{ __html: line }} />;
        }
        return <br key={idx} />;
      });
  };

  if (loading) return <div style={styles.container}>Loading architecture...</div>;
  if (!architecture) return <div style={styles.container}>No architecture data available</div>;
  if (architecture.error) return <div style={styles.container}>{architecture.error}</div>;

  return (
    <div style={styles.container}>
      <div style={styles.headerBar}>
        <h2>Architecture Explanation</h2>
        {cached && <span style={styles.cacheBadge}>Cached</span>}
        <button onClick={loadArchitecture} style={styles.refreshBtn} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>
      
      {architecture.macro && (
        <div style={styles.section}>
          <h3>Macro Level (System Overview)</h3>
          <div style={styles.text}>{formatText(architecture.macro)}</div>
        </div>
      )}

      {architecture.meso && (
        <div style={styles.section}>
          <h3>Meso Level (Module Responsibilities)</h3>
          <div style={styles.text}>{formatText(architecture.meso)}</div>
        </div>
      )}

      {architecture.micro && (
        <div style={styles.section}>
          <h3>Micro Level (File/Function Details)</h3>
          <div style={styles.text}>{formatText(architecture.micro)}</div>
        </div>
      )}

      {architecture.evidence && architecture.evidence.length > 0 && (
        <div style={styles.section}>
          <h3>Evidence</h3>
          {architecture.evidence.map((item, idx) => (
            <div key={idx} style={styles.evidence}>
              <strong title={item.file || item.source}>
                {formatFilePath(item.file || item.source, 2)}
              </strong>
              <p>{formatEvidenceText(item.reason || item.content)}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const styles = {
  container: { padding: '20px', background: '#fff', borderRadius: '8px', marginBottom: '20px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' },
  headerBar: { display: 'flex', alignItems: 'center', gap: '15px', marginBottom: '20px' },
  cacheBadge: { padding: '4px 12px', background: '#d1fae5', color: '#065f46', borderRadius: '12px', fontSize: '12px', fontWeight: 'bold' },
  refreshBtn: { padding: '6px 12px', background: '#667eea', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '13px' },
  section: { marginBottom: '25px', padding: '15px', background: '#f9f9f9', borderRadius: '6px' },
  text: { lineHeight: '1.8', color: '#333' },
  h3: { fontSize: '18px', fontWeight: 'bold', marginTop: '12px', marginBottom: '8px', color: '#444' },
  h4: { fontSize: '16px', fontWeight: 'bold', marginTop: '10px', marginBottom: '6px', color: '#555' },
  paragraph: { marginBottom: '10px', lineHeight: '1.6' },
  listItem: { marginLeft: '20px', marginBottom: '8px', lineHeight: '1.6' },
  bulletItem: { marginLeft: '20px', marginBottom: '6px', lineHeight: '1.6' },
  evidence: { padding: '10px', background: '#fff', borderRadius: '4px', marginBottom: '10px', border: '1px solid #e0e0e0' }
};
