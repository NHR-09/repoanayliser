import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

function SnapshotComparison({ repoId }) {
  const [snapshots, setSnapshots] = useState([]);
  const [selectedSnapshot1, setSelectedSnapshot1] = useState(null);
  const [selectedSnapshot2, setSelectedSnapshot2] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (repoId) loadSnapshots();
  }, [repoId]);

  const loadSnapshots = async () => {
    try {
      setLoading(true);
      const response = await api.getSnapshots(repoId);
      setSnapshots(response.data.snapshots || []);
    } catch (error) {
      console.error('Error loading snapshots:', error);
    } finally {
      setLoading(false);
    }
  };

  const deleteSnapshot = async (snapshotId) => {
    if (!window.confirm('Delete this snapshot?')) return;
    try {
      await api.deleteSnapshot(repoId, snapshotId);
      loadSnapshots();
    } catch (error) {
      console.error('Error deleting snapshot:', error);
    }
  };

  const compareSelected = async () => {
    if (!selectedSnapshot1 || !selectedSnapshot2) return;
    try {
      const response = await api.compareSnapshots(repoId, selectedSnapshot1, selectedSnapshot2);
      setComparison(response.data);
    } catch (error) {
      console.error('Error comparing snapshots:', error);
    }
  };

  if (loading) return <div style={styles.loading}>Loading snapshots...</div>;

  return (
    <div style={styles.container}>
      <h3>📸 Analysis Snapshots</h3>

      <div style={styles.snapshotList}>
        {snapshots.map((snapshot, idx) => (
          <div key={snapshot.snapshot_id} style={styles.snapshotCard}>
            <div style={styles.snapshotHeader}>
              <span style={styles.snapshotNumber}>#{snapshots.length - idx}</span>
              <span style={styles.snapshotDate}>
                {new Date(snapshot.created_at).toLocaleString()}
              </span>
            </div>
            <div style={styles.snapshotMetrics}>
              <div style={styles.metric}>
                <span>Files:</span> <strong>{snapshot.total_files || snapshot.file_count}</strong>
              </div>
              <div style={styles.metric}>
                <span>Deps:</span> <strong>{snapshot.total_deps || 0}</strong>
              </div>
              <div style={styles.metric}>
                <span>Coupling:</span> <strong>{snapshot.avg_coupling?.toFixed(2) || 'N/A'}</strong>
              </div>
              <div style={styles.metric}>
                <span>Cycles:</span> <strong>{snapshot.cycle_count || 0}</strong>
              </div>
            </div>
            <div style={styles.snapshotActions}>
              <button
                onClick={() => setSelectedSnapshot1(snapshot.snapshot_id)}
                style={{ ...styles.selectBtn, ...(selectedSnapshot1 === snapshot.snapshot_id ? styles.selected : {}) }}
              >
                {selectedSnapshot1 === snapshot.snapshot_id ? '✓ Snapshot 1' : 'Select as 1'}
              </button>
              <button
                onClick={() => setSelectedSnapshot2(snapshot.snapshot_id)}
                style={{ ...styles.selectBtn, ...(selectedSnapshot2 === snapshot.snapshot_id ? styles.selected : {}) }}
              >
                {selectedSnapshot2 === snapshot.snapshot_id ? '✓ Snapshot 2' : 'Select as 2'}
              </button>
              <button
                onClick={() => deleteSnapshot(snapshot.snapshot_id)}
                style={styles.deleteBtn}
              >
                Del
              </button>
            </div>
          </div>
        ))}
      </div>

      {selectedSnapshot1 && selectedSnapshot2 && (
        <div style={styles.compareSection}>
          <button onClick={compareSelected} style={styles.compareBtn}>
            Compare Snapshots
          </button>
        </div>
      )}

      {comparison && (
        <div style={styles.comparisonResult}>
          <h4>Comparison Results</h4>

          {/* Risk Assessment */}
          {comparison.risk_assessment && (
            <div style={{
              ...styles.riskBanner,
              background: getRiskColor(comparison.risk_assessment.risk_level)
            }}>
              <div style={styles.riskLevel}>
                {getRiskIcon(comparison.risk_assessment.risk_level)} Risk Level: {comparison.risk_assessment.risk_level.toUpperCase()}
              </div>
              {comparison.risk_assessment.risk_areas?.length > 0 && (
                <div style={styles.riskAreas}>
                  {comparison.risk_assessment.risk_areas.map((area, idx) => (
                    <div key={idx} style={styles.riskItem}>{area}</div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Summary */}
          {comparison.summary && (
            <div style={styles.summaryBox}>
              <strong>📝 Summary:</strong> {comparison.summary}
            </div>
          )}

          {/* Metrics Comparison */}
          <div style={styles.comparisonGrid}>
            <div style={styles.comparisonCard}>
              <h5>📸 Snapshot 1</h5>
              <div style={styles.comparisonDate}>{comparison.snapshot1.date}</div>
              <div style={styles.comparisonMetrics}>
                <div>Files: <strong>{comparison.snapshot1.files}</strong></div>
                <div>Dependencies: <strong>{comparison.snapshot1.dependencies}</strong></div>
                <div>Coupling: <strong>{comparison.snapshot1.avg_coupling?.toFixed(2)}</strong></div>
                <div>Cycles: <strong>{comparison.snapshot1.cycles}</strong></div>
              </div>
            </div>

            <div style={styles.deltaCard}>
              <h5>Changes (Δ)</h5>
              <div style={styles.deltaMetrics}>
                <div style={getDeltaStyle(comparison.changes.file_delta)}>
                  Files: <strong>{formatDelta(comparison.changes.file_delta)}</strong>
                </div>
                <div style={getDeltaStyle(comparison.changes.dependency_delta)}>
                  Deps: <strong>{formatDelta(comparison.changes.dependency_delta)}</strong>
                </div>
                <div style={getDeltaStyle(comparison.changes.coupling_delta)}>
                  Coupling: <strong>{formatDelta(comparison.changes.coupling_delta)}</strong>
                </div>
                <div style={getDeltaStyle(comparison.changes.cycle_delta)}>
                  Cycles: <strong>{formatDelta(comparison.changes.cycle_delta)}</strong>
                </div>
              </div>
            </div>

            <div style={styles.comparisonCard}>
              <h5>📸 Snapshot 2</h5>
              <div style={styles.comparisonDate}>{comparison.snapshot2.date}</div>
              <div style={styles.comparisonMetrics}>
                <div>Files: <strong>{comparison.snapshot2.files}</strong></div>
                <div>Dependencies: <strong>{comparison.snapshot2.dependencies}</strong></div>
                <div>Coupling: <strong>{comparison.snapshot2.avg_coupling?.toFixed(2)}</strong></div>
                <div>Cycles: <strong>{comparison.snapshot2.cycles}</strong></div>
              </div>
            </div>
          </div>

          {/* Pattern Changes */}
          {comparison.changes.pattern_changes && Object.keys(comparison.changes.pattern_changes).length > 0 && (
            <div style={styles.patternSection}>
              <h5>Architectural Pattern Changes</h5>
              <div style={styles.patternList}>
                {Object.entries(comparison.changes.pattern_changes).map(([pattern, change]) => (
                  <div key={pattern} style={styles.patternItem}>
                    <span style={styles.patternName}>{pattern}</span>
                    <span style={getPatternChangeStyle(change)}>{change}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* File Changes */}
          <div style={styles.fileChangesSection}>
            <div style={styles.fileChangeColumn}>
              <h5>➕ Files Added ({comparison.changes.files_added?.length || 0})</h5>
              <div style={styles.fileList}>
                {comparison.changes.files_added?.slice(0, 10).map((file, idx) => (
                  <div key={idx} style={styles.fileItem}>{file ? file.split(/[\\/]/).pop() : 'N/A'}</div>
                ))}
                {comparison.changes.files_added?.length > 10 && (
                  <div style={styles.moreFiles}>... and {comparison.changes.files_added.length - 10} more</div>
                )}
              </div>
            </div>
            <div style={styles.fileChangeColumn}>
              <h5>📝 Files Modified ({comparison.changes.files_modified?.length || 0})</h5>
              <div style={styles.fileList}>
                {comparison.changes.files_modified?.slice(0, 10).map((file, idx) => (
                  <div key={idx} style={styles.fileItem}>{file ? file.split(/[\\/]/).pop() : 'N/A'}</div>
                ))}
                {comparison.changes.files_modified?.length > 10 && (
                  <div style={styles.moreFiles}>... and {comparison.changes.files_modified.length - 10} more</div>
                )}
              </div>
            </div>
            <div style={styles.fileChangeColumn}>
              <h5>➖ Files Removed ({comparison.changes.files_removed?.length || 0})</h5>
              <div style={styles.fileList}>
                {comparison.changes.files_removed?.slice(0, 10).map((file, idx) => (
                  <div key={idx} style={styles.fileItem}>{file ? file.split(/[\\/]/).pop() : 'N/A'}</div>
                ))}
                {comparison.changes.files_removed?.length > 10 && (
                  <div style={styles.moreFiles}>... and {comparison.changes.files_removed.length - 10} more</div>
                )}
              </div>
            </div>
          </div>

          {/* Coupling Details */}
          <div style={styles.couplingSection}>
            <h5>Coupling Analysis</h5>
            <div style={styles.couplingGrid}>
              <div style={styles.couplingCard}>
                <div style={styles.couplingLabel}>High Coupling Files (Before)</div>
                <div style={styles.couplingValue}>{comparison.changes.high_coupling_before}</div>
              </div>
              <div style={styles.couplingCard}>
                <div style={styles.couplingLabel}>High Coupling Files (After)</div>
                <div style={styles.couplingValue}>{comparison.changes.high_coupling_after}</div>
              </div>
              <div style={styles.couplingCard}>
                <div style={styles.couplingLabel}>Change</div>
                <div style={{
                  ...styles.couplingValue,
                  color: comparison.changes.high_coupling_after > comparison.changes.high_coupling_before ? '#f87171' : '#4ade80'
                }}>
                  {formatDelta(comparison.changes.high_coupling_after - comparison.changes.high_coupling_before)}
                </div>
              </div>
            </div>
          </div>

          {/* Structural Risk — Changed Files */}
          {comparison.structural_risks && comparison.structural_risks.length > 0 && (
            <div style={styles.riskSection}>
              <h5>🎯 Structural Risk — Changed Files</h5>
              <div style={styles.riskDescription}>
                Files changed in this comparison ranked by structural risk (fan-in, fan-out, circular dependencies)
              </div>
              <div style={styles.riskFileList}>
                {comparison.structural_risks.map((risk, idx) => (
                  <div key={idx} style={styles.riskFileCard}>
                    <div style={styles.riskFileHeader}>
                      <span style={styles.riskFileName}>
                        {risk.file ? risk.file.split(/[\\/]/).slice(-2).join('/') : 'N/A'}
                      </span>
                      <span style={{
                        ...styles.riskBadge,
                        background: risk.level === 'critical' ? 'var(--red-dim)' : risk.level === 'high' ? 'var(--amber-dim)' : risk.level === 'medium' ? 'var(--blue-dim)' : 'var(--green-dim)',
                        color: risk.level === 'critical' ? '#f87171' : risk.level === 'high' ? '#fbbf24' : risk.level === 'medium' ? '#60a5fa' : '#4ade80'
                      }}>
                        {risk.level?.toUpperCase()} ({risk.score}/100)
                      </span>
                    </div>
                    <div style={styles.riskFileDetails}>
                      <span>Fan-in: <strong>{risk.fan_in}</strong></span>
                      <span>Fan-out: <strong>{risk.fan_out}</strong></span>
                      {risk.in_cycle && (
                        <span style={{ color: '#f87171', fontWeight: 'bold' }}>In Cycle</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const formatDelta = (value) => {
  if (value > 0) return `+${value}`;
  return value.toString();
};

const getDeltaStyle = (value) => {
  if (value > 0) return { color: '#f87171' };
  if (value < 0) return { color: '#4ade80' };
  return { color: 'var(--text-muted)' };
};

const getRiskColor = (level) => {
  if (level === 'high') return 'var(--red-dim)';
  if (level === 'medium') return 'var(--amber-dim)';
  return 'var(--green-dim)';
};

const getRiskIcon = (level) => {
  if (level === 'high') return '🔴';
  if (level === 'medium') return '🟡';
  return '🟢';
};

const getPatternChangeStyle = (change) => {
  if (change === 'newly_detected') return { color: '#4ade80', fontWeight: 'bold' };
  if (change === 'no_longer_detected') return { color: '#f87171', fontWeight: 'bold' };
  return { color: '#60a5fa', fontWeight: 'bold' };
};

const styles = {
  container: { padding: '20px' },
  loading: { textAlign: 'center', padding: '40px', color: 'var(--text-muted)' },
  snapshotList: { display: 'grid', gap: '12px', marginBottom: '20px' },
  snapshotCard: { border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '16px', background: 'var(--bg-elevated)', transition: 'all 0.2s' },
  snapshotHeader: { display: 'flex', justifyContent: 'space-between', marginBottom: '10px', alignItems: 'center' },
  snapshotNumber: { fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)', background: 'var(--bg-card)', padding: '4px 12px', borderRadius: '14px', border: '1px solid var(--border)', fontFamily: 'var(--font-mono)' },
  snapshotDate: { fontSize: '12px', color: 'var(--text-dim)' },
  snapshotMetrics: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '12px', padding: '10px', background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' },
  metric: { fontSize: '13px', color: 'var(--text-secondary)' },
  snapshotActions: { display: 'flex', gap: '8px' },
  selectBtn: { flex: 1, padding: '8px 14px', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '13px', transition: 'all 0.2s', color: 'var(--text-secondary)' },
  selected: { background: 'var(--text-primary)', color: 'var(--bg-primary)', border: '1px solid var(--text-primary)', fontWeight: 600 },
  deleteBtn: { padding: '8px 12px', background: 'var(--red-dim)', color: 'var(--red)', border: '1px solid rgba(248,113,113,0.15)', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '14px' },
  compareSection: { textAlign: 'center', padding: '20px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', marginBottom: '20px', border: '1px solid var(--border)' },
  compareBtn: { padding: '12px 28px', background: 'var(--green)', color: 'var(--bg-primary)', border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '14px', fontWeight: 600 },
  comparisonResult: { border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: '20px', background: 'var(--bg-card)' },
  riskBanner: { padding: '14px', borderRadius: 'var(--radius-md)', marginBottom: '20px', border: '1px solid var(--border)' },
  riskLevel: { fontSize: '16px', fontWeight: 700, marginBottom: '8px', color: 'var(--text-primary)' },
  riskAreas: { display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px', color: 'var(--text-secondary)' },
  riskItem: { padding: '4px 10px', background: 'var(--bg-card)', borderRadius: '4px', border: '1px solid var(--border)' },
  summaryBox: { padding: '14px', background: 'var(--blue-dim)', borderRadius: 'var(--radius-md)', marginBottom: '20px', fontSize: '13px', border: '1px solid rgba(96,165,250,0.12)', color: 'var(--text-secondary)' },
  comparisonGrid: { display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '16px', alignItems: 'center', marginBottom: '20px' },
  comparisonCard: { padding: '16px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' },
  deltaCard: { padding: '16px', background: 'var(--amber-dim)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(251,191,36,0.12)', minWidth: '180px' },
  comparisonDate: { fontSize: '11px', color: 'var(--text-dim)', marginBottom: '12px' },
  comparisonMetrics: { display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '13px', color: 'var(--text-secondary)' },
  deltaMetrics: { display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '14px', fontWeight: 700, fontFamily: 'var(--font-mono)' },
  patternSection: { marginTop: '16px', padding: '14px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' },
  patternList: { display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '10px' },
  patternItem: { display: 'flex', justifyContent: 'space-between', padding: '10px', background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' },
  patternName: { fontWeight: 600, textTransform: 'capitalize', color: 'var(--text-primary)' },
  fileChangesSection: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginTop: '16px' },
  fileChangeColumn: { padding: '14px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' },
  fileList: { marginTop: '8px', maxHeight: '200px', overflowY: 'auto' },
  fileItem: { padding: '6px 10px', background: 'var(--bg-card)', marginBottom: '4px', borderRadius: 'var(--radius-sm)', fontSize: '12px', border: '1px solid var(--border)', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' },
  moreFiles: { padding: '6px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px', fontStyle: 'italic' },
  couplingSection: { marginTop: '16px', padding: '14px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' },
  couplingGrid: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginTop: '10px' },
  couplingCard: { padding: '14px', background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', textAlign: 'center', border: '1px solid var(--border)' },
  couplingLabel: { fontSize: '10px', color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' },
  couplingValue: { fontSize: '22px', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' },
  riskSection: { marginTop: '16px', padding: '14px', background: 'rgba(167,139,250,0.06)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(167,139,250,0.12)' },
  riskDescription: { fontSize: '11px', color: 'var(--text-muted)', marginBottom: '10px', marginTop: '4px' },
  riskFileList: { display: 'flex', flexDirection: 'column', gap: '6px' },
  riskFileCard: { padding: '12px', background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' },
  riskFileHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' },
  riskFileName: { fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' },
  riskBadge: { padding: '3px 10px', borderRadius: '10px', fontSize: '10px', fontWeight: 700, fontFamily: 'var(--font-mono)' },
  riskFileDetails: { display: 'flex', gap: '14px', fontSize: '12px', color: 'var(--text-muted)' },
};

export default SnapshotComparison;
