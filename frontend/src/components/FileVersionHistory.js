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
      <h3>File Version History</h3>

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
              <span style={styles.icon}>✓</span>
              <div>
                <strong>File Integrity: INTACT</strong>
                <div style={styles.hashText}>Hash: {integrity.hash.substring(0, 32)}...</div>
              </div>
            </>
          ) : integrity.status === 'tampered' ? (
            <>
              <span style={styles.icon}>✗</span>
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
  container: { marginTop: '20px', padding: '20px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' },
  inputGroup: { display: 'flex', gap: '10px', marginBottom: '20px' },
  input: { flex: 1, padding: '10px 14px', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', fontSize: '13px', background: 'var(--bg-input)', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' },
  btn: { padding: '10px 20px', background: 'var(--text-primary)', color: 'var(--bg-primary)', border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontWeight: 600, fontSize: '13px' },
  btnSecondary: { padding: '10px 20px', background: 'var(--green)', color: 'var(--bg-primary)', border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontWeight: 600, fontSize: '13px' },
  integrityBox: { padding: '14px', borderRadius: 'var(--radius-sm)', marginBottom: '20px', display: 'flex', gap: '12px', alignItems: 'center' },
  integrityIntact: { background: 'var(--green-dim)', border: '1px solid rgba(74,222,128,0.12)', color: 'var(--green)' },
  integrityTampered: { background: 'var(--red-dim)', border: '1px solid rgba(248,113,113,0.15)', color: 'var(--red)' },
  icon: { fontSize: '22px' },
  hashText: { fontSize: '11px', fontFamily: 'var(--font-mono)', marginTop: '4px' },
  historyList: { marginTop: '20px' },
  historyCard: { background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '14px', marginBottom: '8px' },
  versionNumber: { fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px', fontFamily: 'var(--font-mono)' },
  historyDetails: { display: 'flex', flexDirection: 'column', gap: '6px', color: 'var(--text-secondary)', fontSize: '13px' },
  historyRow: { display: 'flex', gap: '8px', fontSize: '13px' },
  code: { fontFamily: 'var(--font-mono)', background: 'var(--bg-elevated)', padding: '2px 6px', borderRadius: '3px', fontSize: '11px', color: 'var(--text-primary)' },
};

export default FileVersionHistory;
