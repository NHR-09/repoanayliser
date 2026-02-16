import React, { useState } from 'react';
import { api } from '../services/api';
import { getFileName } from '../utils/formatters';

function FileVersionHistory({ repoId }) {
  const [filePath, setFilePath] = useState('');
  const [history, setHistory] = useState([]);
  const [integrity, setIntegrity] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadHistory = async () => {
    if (!filePath) return;
    try {
      setLoading(true);
      const response = await api.getFileHistory(repoId, filePath);
      setHistory(response.data.history || []);
    } catch (error) {
      console.error('Error loading history:', error);
    } finally {
      setLoading(false);
    }
  };

  const checkIntegrity = async () => {
    if (!filePath) return;
    try {
      const response = await api.checkFileIntegrity(repoId, filePath);
      setIntegrity(response.data);
    } catch (error) {
      console.error('Error checking integrity:', error);
    }
  };

  return (
    <div style={styles.container}>
      <h3>🔍 File Version History</h3>
      
      <div style={styles.inputGroup}>
        <input
          type="text"
          placeholder="Enter file path (e.g., workspace\repo\file.py)"
          value={filePath}
          onChange={(e) => setFilePath(e.target.value)}
          style={styles.input}
        />
        <button onClick={loadHistory} style={styles.btn} disabled={loading}>
          {loading ? 'Loading...' : 'Get History'}
        </button>
        <button onClick={checkIntegrity} style={styles.btnSecondary}>
          Check Integrity
        </button>
      </div>

      {integrity && (
        <div style={{
          ...styles.integrityBox,
          ...(integrity.status === 'intact' ? styles.integrityIntact : styles.integrityTampered)
        }}>
          {integrity.status === 'intact' ? (
            <>
              <span style={styles.icon}>✅</span>
              <div>
                <strong>File Integrity: INTACT</strong>
                <div style={styles.hashText}>Hash: {integrity.hash.substring(0, 32)}...</div>
              </div>
            </>
          ) : integrity.status === 'tampered' ? (
            <>
              <span style={styles.icon}>⚠️</span>
              <div>
                <strong>File Integrity: TAMPERED</strong>
                <div style={styles.hashText}>Stored: {integrity.stored_hash.substring(0, 16)}...</div>
                <div style={styles.hashText}>Current: {integrity.current_hash.substring(0, 16)}...</div>
              </div>
            </>
          ) : (
            <div>{integrity.status}</div>
          )}
        </div>
      )}

      {history.length > 0 && (
        <div style={styles.historyList}>
          <h4>Version Chain ({history.length} versions)</h4>
          {history.map((v, idx) => (
            <div key={idx} style={styles.historyCard}>
              <div style={styles.versionNumber}>Version {idx + 1}</div>
              <div style={styles.historyDetails}>
                <div style={styles.historyRow}>
                  <strong>Hash:</strong>
                  <code style={styles.code}>{v.hash.substring(0, 32)}...</code>
                </div>
                <div style={styles.historyRow}>
                  <strong>Timestamp:</strong>
                  <span>{new Date(v.timestamp).toLocaleString()}</span>
                </div>
                <div style={styles.historyRow}>
                  <strong>Author:</strong>
                  <span>{v.author}</span>
                </div>
                {v.previous_hash && (
                  <div style={styles.historyRow}>
                    <strong>Previous:</strong>
                    <code style={styles.code}>{v.previous_hash.substring(0, 16)}...</code>
                  </div>
                )}
              </div>
              <div style={styles.filePath} title={filePath}>
                {getFileName(filePath)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const styles = {
  container: { marginTop: '20px', padding: '20px', background: '#f9f9f9', borderRadius: '8px' },
  inputGroup: { display: 'flex', gap: '10px', marginBottom: '20px' },
  input: { flex: 1, padding: '10px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '14px' },
  btn: { padding: '10px 20px', background: '#667eea', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' },
  btnSecondary: { padding: '10px 20px', background: '#48bb78', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' },
  integrityBox: { padding: '15px', borderRadius: '6px', marginBottom: '20px', display: 'flex', gap: '15px', alignItems: 'center' },
  integrityIntact: { background: '#d4edda', border: '1px solid #c3e6cb', color: '#155724' },
  integrityTampered: { background: '#f8d7da', border: '1px solid #f5c6cb', color: '#721c24' },
  icon: { fontSize: '24px' },
  hashText: { fontSize: '12px', fontFamily: 'monospace', marginTop: '5px' },
  historyList: { marginTop: '20px' },
  historyCard: { background: 'white', border: '1px solid #e0e0e0', borderRadius: '6px', padding: '15px', marginBottom: '10px' },
  versionNumber: { fontSize: '16px', fontWeight: 'bold', color: '#667eea', marginBottom: '10px' },
  historyDetails: { display: 'flex', flexDirection: 'column', gap: '8px' },
  historyRow: { display: 'flex', gap: '10px', fontSize: '14px' },
  code: { fontFamily: 'monospace', background: '#f5f5f5', padding: '2px 6px', borderRadius: '3px', fontSize: '12px' }
};

export default FileVersionHistory;
