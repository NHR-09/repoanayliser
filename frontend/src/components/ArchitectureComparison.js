import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { formatFilePath } from '../utils/formatters';

function ArchitectureComparison() {
  const [repos, setRepos] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState('');
  const [commits, setCommits] = useState([]);
  const [commit1, setCommit1] = useState('');
  const [commit2, setCommit2] = useState('');
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadRepositories();
  }, []);

  const loadRepositories = async () => {
    try {
      const res = await api.getRepositories();
      setRepos(res.data.repositories);
    } catch (err) {
      console.error('Failed to load repositories:', err);
    }
  };

  const loadCommits = async (repoId) => {
    try {
      const res = await api.getCommits(repoId);
      const commitList = res.data || [];
      setCommits(commitList);
      if (commitList.length >= 2) {
        setCommit1(commitList[commitList.length - 1].hash);
        setCommit2(commitList[0].hash);
      } else if (commitList.length === 0) {
        alert('No commits found. Import git history first.');
      }
    } catch (err) {
      console.error('Failed to load commits:', err);
      alert('Failed to load commits. Import git history first.');
    }
  };

  const handleRepoChange = (repoId) => {
    setSelectedRepo(repoId);
    setComparison(null);
    if (repoId) loadCommits(repoId);
  };

  const compareCommits = async () => {
    if (!selectedRepo || !commit1 || !commit2) return;
    setLoading(true);
    try {
      const res = await api.compareArchitecture(selectedRepo, commit1, commit2);
      setComparison(res.data);
    } catch (err) {
      alert('Comparison failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>🔄 Architecture Comparison</h2>
      
      <div style={styles.controls}>
        <select value={selectedRepo} onChange={(e) => handleRepoChange(e.target.value)} style={styles.select}>
          <option value="">Select Repository</option>
          {repos.map(r => <option key={r.repo_id} value={r.repo_id}>{r.name}</option>)}
        </select>

        {commits.length === 0 && selectedRepo && (
        <div style={styles.warning}>
          ⚠️ No commits found. Click "Import Git History" in Repository Manager first.
        </div>
      )}

      {commits.length >= 2 && (
          <>
            <select value={commit1} onChange={(e) => setCommit1(e.target.value)} style={styles.select}>
              {commits.map(c => <option key={c.hash} value={c.hash}>{c.hash.slice(0,8)} - {c.message.slice(0,50)}</option>)}
            </select>
            <span style={styles.arrow}>→</span>
            <select value={commit2} onChange={(e) => setCommit2(e.target.value)} style={styles.select}>
              {commits.map(c => <option key={c.hash} value={c.hash}>{c.hash.slice(0,8)} - {c.message.slice(0,50)}</option>)}
            </select>
            <button onClick={compareCommits} disabled={loading} style={styles.button}>
              {loading ? 'Comparing...' : 'Compare'}
            </button>
          </>
        )}
      </div>

      {comparison && (
        <div style={styles.results}>
          <div style={styles.section}>
            <h3>📊 Dependency Changes</h3>
            <div style={styles.metrics}>
              <div style={styles.metric}>
                <span style={styles.label}>Added:</span>
                <span style={styles.value}>{comparison.added_dependencies.length}</span>
              </div>
              <div style={styles.metric}>
                <span style={styles.label}>Removed:</span>
                <span style={styles.value}>{comparison.removed_dependencies.length}</span>
              </div>
              <div style={styles.metric}>
                <span style={styles.label}>Net Change:</span>
                <span style={{...styles.value, color: comparison.dependency_delta > 0 ? '#e74c3c' : '#27ae60'}}>
                  {comparison.dependency_delta > 0 ? '+' : ''}{comparison.dependency_delta}
                </span>
              </div>
            </div>
          </div>

          <div style={styles.section}>
            <h3>🔗 Coupling Metrics</h3>
            <div style={styles.metrics}>
              <div style={styles.metric}>
                <span style={styles.label}>Before:</span>
                <span style={styles.value}>{comparison.coupling_before?.toFixed(2) || 0}</span>
              </div>
              <div style={styles.metric}>
                <span style={styles.label}>After:</span>
                <span style={styles.value}>{comparison.coupling_after?.toFixed(2) || 0}</span>
              </div>
              <div style={styles.metric}>
                <span style={styles.label}>Delta:</span>
                <span style={{...styles.value, color: comparison.coupling_delta > 0 ? '#e74c3c' : '#27ae60'}}>
                  {comparison.coupling_delta > 0 ? '+' : ''}{comparison.coupling_delta}
                </span>
              </div>
            </div>
          </div>

          <div style={styles.section}>
            <h3>🔄 Circular Dependencies</h3>
            <div style={styles.metrics}>
              <div style={styles.metric}>
                <span style={styles.label}>Before:</span>
                <span style={styles.value}>{comparison.cycles_before}</span>
              </div>
              <div style={styles.metric}>
                <span style={styles.label}>After:</span>
                <span style={styles.value}>{comparison.cycles_after}</span>
              </div>
            </div>
          </div>

          {comparison.risk_areas.length > 0 && (
            <div style={styles.risks}>
              <h3>⚠️ Risk Areas</h3>
              {comparison.risk_areas.map((risk, i) => <div key={i} style={styles.risk}>• {risk}</div>)}
            </div>
          )}

          {comparison.added_dependencies.length > 0 && (
            <details style={styles.details}>
              <summary style={styles.summary}>➕ Added Dependencies ({comparison.added_dependencies.length})</summary>
              {comparison.added_dependencies.slice(0, 10).map((dep, i) => (
                <div key={i} style={styles.dep} title={`${dep[0]} → ${dep[1]}`}>
                  {formatFilePath(dep[0], 1)} → {formatFilePath(dep[1], 1)}
                </div>
              ))}
            </details>
          )}

          {comparison.removed_dependencies.length > 0 && (
            <details style={styles.details}>
              <summary style={styles.summary}>➖ Removed Dependencies ({comparison.removed_dependencies.length})</summary>
              {comparison.removed_dependencies.slice(0, 10).map((dep, i) => (
                <div key={i} style={styles.dep} title={`${dep[0]} → ${dep[1]}`}>
                  {formatFilePath(dep[0], 1)} → {formatFilePath(dep[1], 1)}
                </div>
              ))}
            </details>
          )}
        </div>
      )}
    </div>
  );
}

const styles = {
  container: { background: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' },
  title: { margin: '0 0 20px 0', color: '#2c3e50' },
  controls: { display: 'flex', gap: '10px', marginBottom: '20px', alignItems: 'center', flexWrap: 'wrap' },
  select: { padding: '8px', borderRadius: '4px', border: '1px solid #ddd', flex: '1', minWidth: '200px' },
  arrow: { fontSize: '20px', color: '#667eea' },
  button: { padding: '8px 20px', background: '#667eea', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' },
  results: { marginTop: '20px' },
  section: { marginBottom: '20px', padding: '15px', background: '#f8f9fa', borderRadius: '6px' },
  metrics: { display: 'flex', gap: '20px', flexWrap: 'wrap' },
  metric: { display: 'flex', flexDirection: 'column', gap: '5px' },
  label: { fontSize: '12px', color: '#666' },
  value: { fontSize: '24px', fontWeight: 'bold', color: '#2c3e50' },
  risks: { padding: '15px', background: '#fff3cd', borderRadius: '6px', borderLeft: '4px solid #ffc107' },
  risk: { padding: '5px 0', color: '#856404' },
  warning: { padding: '15px', background: '#fff3cd', color: '#856404', borderRadius: '6px', marginBottom: '20px', border: '1px solid #ffc107' },
  details: { marginTop: '15px', padding: '10px', background: '#f8f9fa', borderRadius: '6px' },
  summary: { cursor: 'pointer', fontWeight: 'bold', padding: '5px' },
  dep: { padding: '5px 20px', fontSize: '14px', color: '#555' }
};

export default ArchitectureComparison;
