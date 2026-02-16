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
                <span>📁 Files:</span> <strong>{snapshot.total_files || snapshot.file_count}</strong>
              </div>
              <div style={styles.metric}>
                <span>🔗 Deps:</span> <strong>{snapshot.total_deps || 0}</strong>
              </div>
              <div style={styles.metric}>
                <span>📊 Coupling:</span> <strong>{snapshot.avg_coupling?.toFixed(2) || 'N/A'}</strong>
              </div>
              <div style={styles.metric}>
                <span>🔄 Cycles:</span> <strong>{snapshot.cycle_count || 0}</strong>
              </div>
            </div>
            <div style={styles.snapshotActions}>
              <button 
                onClick={() => setSelectedSnapshot1(snapshot.snapshot_id)}
                style={{...styles.selectBtn, ...(selectedSnapshot1 === snapshot.snapshot_id ? styles.selected : {})}}
              >
                {selectedSnapshot1 === snapshot.snapshot_id ? '✓ Snapshot 1' : 'Select as 1'}
              </button>
              <button 
                onClick={() => setSelectedSnapshot2(snapshot.snapshot_id)}
                style={{...styles.selectBtn, ...(selectedSnapshot2 === snapshot.snapshot_id ? styles.selected : {})}}
              >
                {selectedSnapshot2 === snapshot.snapshot_id ? '✓ Snapshot 2' : 'Select as 2'}
              </button>
              <button 
                onClick={() => deleteSnapshot(snapshot.snapshot_id)}
                style={styles.deleteBtn}
              >
                🗑️
              </button>
            </div>
          </div>
        ))}
      </div>

      {selectedSnapshot1 && selectedSnapshot2 && (
        <div style={styles.compareSection}>
          <button onClick={compareSelected} style={styles.compareBtn}>
            🔍 Compare Snapshots
          </button>
        </div>
      )}

      {comparison && (
        <div style={styles.comparisonResult}>
          <h4>📊 Comparison Results</h4>
          
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
                    <div key={idx} style={styles.riskItem}>⚠️ {area}</div>
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
              <h5>🔄 Changes (Δ)</h5>
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
              <h5>🏗️ Architectural Pattern Changes</h5>
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
            <h5>📈 Coupling Analysis</h5>
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
                  color: comparison.changes.high_coupling_after > comparison.changes.high_coupling_before ? '#ef4444' : '#10b981'
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
                        background: risk.level === 'critical' ? '#fee2e2' : risk.level === 'high' ? '#fef3c7' : risk.level === 'medium' ? '#e0f2fe' : '#d1fae5',
                        color: risk.level === 'critical' ? '#991b1b' : risk.level === 'high' ? '#92400e' : risk.level === 'medium' ? '#0c4a6e' : '#065f46'
                      }}>
                        {risk.level?.toUpperCase()} ({risk.score}/100)
                      </span>
                    </div>
                    <div style={styles.riskFileDetails}>
                      <span>📥 Fan-in: <strong>{risk.fan_in}</strong></span>
                      <span>📤 Fan-out: <strong>{risk.fan_out}</strong></span>
                      {risk.in_cycle && (
                        <span style={{color: '#ef4444', fontWeight: 'bold'}}>🔄 In Cycle</span>
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
  if (value > 0) return { color: '#ef4444' };
  if (value < 0) return { color: '#10b981' };
  return { color: '#6b7280' };
};

const getRiskColor = (level) => {
  if (level === 'high') return '#fee2e2';
  if (level === 'medium') return '#fef3c7';
  return '#d1fae5';
};

const getRiskIcon = (level) => {
  if (level === 'high') return '🔴';
  if (level === 'medium') return '🟡';
  return '🟢';
};

const getPatternChangeStyle = (change) => {
  if (change === 'newly_detected') return { color: '#10b981', fontWeight: 'bold' };
  if (change === 'no_longer_detected') return { color: '#ef4444', fontWeight: 'bold' };
  return { color: '#3b82f6', fontWeight: 'bold' };
};

const styles = {
  container: { padding: '20px' },
  loading: { textAlign: 'center', padding: '40px', color: '#666' },
  snapshotList: { display: 'grid', gap: '15px', marginBottom: '20px' },
  snapshotCard: { 
    border: '1px solid #e0e0e0', 
    borderRadius: '8px', 
    padding: '15px', 
    background: '#fafafa',
    transition: 'all 0.3s'
  },
  snapshotHeader: { 
    display: 'flex', 
    justifyContent: 'space-between', 
    marginBottom: '10px',
    alignItems: 'center'
  },
  snapshotNumber: { 
    fontSize: '18px', 
    fontWeight: 'bold', 
    color: '#667eea',
    background: '#eef2ff',
    padding: '4px 12px',
    borderRadius: '20px'
  },
  snapshotDate: { fontSize: '13px', color: '#666' },
  snapshotMetrics: { 
    display: 'grid', 
    gridTemplateColumns: 'repeat(4, 1fr)', 
    gap: '10px', 
    marginBottom: '15px',
    padding: '10px',
    background: 'white',
    borderRadius: '6px'
  },
  metric: { fontSize: '14px', color: '#333' },
  snapshotActions: { display: 'flex', gap: '10px' },
  selectBtn: { 
    flex: 1,
    padding: '8px 16px', 
    background: '#f0f0f0', 
    border: '1px solid #d0d0d0',
    borderRadius: '6px', 
    cursor: 'pointer',
    fontSize: '14px',
    transition: 'all 0.2s'
  },
  selected: { 
    background: '#667eea', 
    color: 'white',
    border: '1px solid #667eea',
    fontWeight: 'bold'
  },
  deleteBtn: {
    padding: '8px 12px',
    background: '#ef4444',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '16px'
  },
  compareSection: { 
    textAlign: 'center', 
    padding: '20px',
    background: '#f9fafb',
    borderRadius: '8px',
    marginBottom: '20px'
  },
  compareBtn: { 
    padding: '12px 32px', 
    background: '#10b981', 
    color: 'white', 
    border: 'none', 
    borderRadius: '8px', 
    cursor: 'pointer',
    fontSize: '16px',
    fontWeight: 'bold',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
  },
  comparisonResult: { 
    border: '2px solid #667eea', 
    borderRadius: '12px', 
    padding: '20px',
    background: 'white'
  },
  riskBanner: {
    padding: '15px',
    borderRadius: '8px',
    marginBottom: '20px',
    border: '2px solid rgba(0,0,0,0.1)'
  },
  riskLevel: {
    fontSize: '18px',
    fontWeight: 'bold',
    marginBottom: '10px'
  },
  riskAreas: {
    display: 'flex',
    flexDirection: 'column',
    gap: '5px',
    fontSize: '14px'
  },
  riskItem: {
    padding: '5px 10px',
    background: 'rgba(255,255,255,0.5)',
    borderRadius: '4px'
  },
  summaryBox: {
    padding: '15px',
    background: '#f0f9ff',
    borderRadius: '8px',
    marginBottom: '20px',
    fontSize: '15px',
    border: '1px solid #bae6fd'
  },
  comparisonGrid: { 
    display: 'grid', 
    gridTemplateColumns: '1fr auto 1fr', 
    gap: '20px',
    alignItems: 'center',
    marginBottom: '20px'
  },
  comparisonCard: { 
    padding: '20px', 
    background: '#f9fafb', 
    borderRadius: '8px',
    border: '1px solid #e5e7eb'
  },
  deltaCard: { 
    padding: '20px', 
    background: '#fef3c7', 
    borderRadius: '8px',
    border: '2px solid #fbbf24',
    minWidth: '200px'
  },
  comparisonDate: { 
    fontSize: '12px', 
    color: '#666', 
    marginBottom: '15px' 
  },
  comparisonMetrics: { 
    display: 'flex', 
    flexDirection: 'column', 
    gap: '8px',
    fontSize: '14px'
  },
  deltaMetrics: { 
    display: 'flex', 
    flexDirection: 'column', 
    gap: '8px',
    fontSize: '15px',
    fontWeight: 'bold'
  },
  patternSection: {
    marginTop: '20px',
    padding: '15px',
    background: '#f9fafb',
    borderRadius: '8px',
    border: '1px solid #e5e7eb'
  },
  patternList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    marginTop: '10px'
  },
  patternItem: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '10px',
    background: 'white',
    borderRadius: '6px',
    border: '1px solid #e5e7eb'
  },
  patternName: {
    fontWeight: 'bold',
    textTransform: 'capitalize'
  },
  fileChangesSection: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: '20px',
    marginTop: '20px'
  },
  fileChangeColumn: {
    padding: '15px',
    background: '#f9fafb',
    borderRadius: '8px',
    border: '1px solid #e5e7eb'
  },
  fileList: {
    marginTop: '10px',
    maxHeight: '200px',
    overflowY: 'auto'
  },
  fileItem: {
    padding: '8px',
    background: 'white',
    marginBottom: '5px',
    borderRadius: '4px',
    fontSize: '13px',
    border: '1px solid #e5e7eb'
  },
  moreFiles: {
    padding: '8px',
    textAlign: 'center',
    color: '#666',
    fontSize: '13px',
    fontStyle: 'italic'
  },
  couplingSection: {
    marginTop: '20px',
    padding: '15px',
    background: '#f9fafb',
    borderRadius: '8px',
    border: '1px solid #e5e7eb'
  },
  couplingGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '15px',
    marginTop: '10px'
  },
  couplingCard: {
    padding: '15px',
    background: 'white',
    borderRadius: '6px',
    textAlign: 'center',
    border: '1px solid #e5e7eb'
  },
  couplingLabel: {
    fontSize: '12px',
    color: '#666',
    marginBottom: '8px'
  },
  couplingValue: {
    fontSize: '24px',
    fontWeight: 'bold'
  },
  riskSection: {
    marginTop: '20px',
    padding: '15px',
    background: '#fef7ff',
    borderRadius: '8px',
    border: '1px solid #e8b4f8'
  },
  riskDescription: {
    fontSize: '12px',
    color: '#666',
    marginBottom: '12px',
    marginTop: '4px'
  },
  riskFileList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px'
  },
  riskFileCard: {
    padding: '12px',
    background: 'white',
    borderRadius: '6px',
    border: '1px solid #e5e7eb'
  },
  riskFileHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '6px'
  },
  riskFileName: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#1f2937'
  },
  riskBadge: {
    padding: '3px 10px',
    borderRadius: '10px',
    fontSize: '11px',
    fontWeight: 'bold'
  },
  riskFileDetails: {
    display: 'flex',
    gap: '16px',
    fontSize: '12px',
    color: '#4b5563'
  }
};

export default SnapshotComparison;
