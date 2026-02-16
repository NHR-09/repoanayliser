import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { formatFilePath } from '../utils/formatters';
import FileVersionHistory from './FileVersionHistory';
import SnapshotComparison from './SnapshotComparison';

function RepositoryManager(props) {
  const [repositories, setRepositories] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [versions, setVersions] = useState([]);
  const [contributors, setContributors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState('list');
  const [importingHistory, setImportingHistory] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [deleting, setDeleting] = useState(null);

  useEffect(() => {
    loadRepositories();
  }, []);

  const loadRepositories = async () => {
    try {
      setLoading(true);
      const response = await api.getRepositories();
      setRepositories(response.data.repositories || []);
    } catch (error) {
      console.error('Error loading repositories:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadVersions = async (repoId) => {
    try {
      const response = await api.getRepositoryVersions(repoId);
      setVersions(response.data.versions || []);
    } catch (error) {
      console.error('Error loading versions:', error);
    }
  };

  const loadContributors = async (repoId) => {
    try {
      const response = await api.getContributors(repoId);
      setContributors(response.data.contributors || []);
    } catch (error) {
      console.error('Error loading contributors:', error);
    }
  };

  const selectRepository = (repo) => {
    setSelectedRepo(repo);
    setActiveView('versions');
    setImportResult(null);
    loadVersions(repo.repo_id);
    loadContributors(repo.repo_id);
    // Load repository analysis in backend and notify parent
    api.loadRepository(repo.repo_id)
      .then(() => {
        if (props.onRepoSelect) {
          props.onRepoSelect(repo);
        }
      })
      .catch(err => console.error('Failed to load repository:', err));
  };

  const importGitHistory = async (repoId) => {
    try {
      setImportingHistory(true);
      setImportResult(null);
      const response = await api.importGitHistory(repoId);
      setImportResult(response.data);
      await loadVersions(repoId);
      await loadRepositories();
    } catch (error) {
      setImportResult({ status: 'error', message: error.message });
    } finally {
      setImportingHistory(false);
    }
  };

  const deleteRepo = async (repoId) => {
    if (!window.confirm('Delete this repository and all its data?')) return;
    try {
      setDeleting(repoId);
      await api.deleteRepository(repoId);
      await loadRepositories();
      if (selectedRepo?.repo_id === repoId) {
        setSelectedRepo(null);
        setActiveView('list');
      }
    } catch (error) {
      alert('Failed to delete: ' + error.message);
    } finally {
      setDeleting(null);
    }
  };

  if (loading) {
    return <div style={styles.loading}>Loading repositories...</div>;
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2>📦 Repository Version Tracking</h2>
        <button onClick={loadRepositories} style={styles.refreshBtn}>
          🔄 Refresh
        </button>
      </div>

      {activeView === 'list' && (
        <div style={styles.repoList}>
          {repositories.length === 0 ? (
            <div style={styles.empty}>
              No repositories analyzed yet. Go to Analyze tab to start.
            </div>
          ) : (
            repositories.map(repo => (
              <div key={repo.repo_id} style={styles.repoCard}>
                <div onClick={() => selectRepository(repo)} style={{cursor: 'pointer', flex: 1}}>
                  <div style={styles.repoHeader}>
                    <h3 style={styles.repoName}>📁 {repo.name}</h3>
                    <span style={styles.repoId}>{repo.repo_id.substring(0, 8)}...</span>
                  </div>
                  <div style={styles.repoStats}>
                    <div style={styles.stat}>
                      <span style={styles.statLabel}>Files:</span>
                      <span style={styles.statValue}>{repo.file_count}</span>
                    </div>
                    <div style={styles.stat}>
                      <span style={styles.statLabel}>Snapshots:</span>
                      <span style={styles.statValue}>{repo.version_count}</span>
                    </div>
                  </div>
                  <div style={styles.repoMeta}>
                    <span>🔗 {repo.url}</span>
                    <span>🕒 {new Date(repo.last_analyzed).toLocaleString()}</span>
                  </div>
                </div>
                <button 
                  onClick={(e) => { e.stopPropagation(); deleteRepo(repo.repo_id); }}
                  disabled={deleting === repo.repo_id}
                  style={styles.deleteBtn}
                >
                  {deleting === repo.repo_id ? '⏳' : '🗑️'}
                </button>
              </div>
            ))
          )}
        </div>
      )}

      {activeView === 'versions' && selectedRepo && (
        <div>
          <button onClick={() => setActiveView('list')} style={styles.backBtn}>
            ← Back to Repositories
          </button>
          
          <div style={styles.repoDetail}>
            <div style={styles.repoDetailHeader}>
              <div>
                <h3>📦 {selectedRepo.name}</h3>
                <p style={styles.repoUrl}>{selectedRepo.url}</p>
              </div>
              <button 
                onClick={() => importGitHistory(selectedRepo.repo_id)} 
                disabled={importingHistory}
                style={styles.importBtn}
              >
                {importingHistory ? '⏳ Importing...' : '📥 Import Git History'}
              </button>
            </div>
            
            {importResult && (
              <div style={importResult.status === 'success' ? styles.successMsg : styles.errorMsg}>
                {importResult.status === 'success' ? (
                  <span>✅ Imported {importResult.commits_processed} commits, created {importResult.versions_created} versions</span>
                ) : (
                  <span>❌ {importResult.message}</span>
                )}
              </div>
            )}
            
            <div style={styles.statsBar}>
              <div style={styles.statBox}>
                <div style={styles.statNumber}>{selectedRepo.file_count}</div>
                <div style={styles.statLabel}>Files</div>
              </div>
              <div style={styles.statBox}>
                <div style={styles.statNumber}>{selectedRepo.version_count}</div>
                <div style={styles.statLabel}>Snapshots</div>
              </div>
              <div style={styles.statBox}>
                <div style={styles.statNumber}>
                  {selectedRepo.version_count > 0 ? selectedRepo.version_count : 'N/A'}
                </div>
                <div style={styles.statLabel}>Analysis Runs</div>
              </div>
            </div>
          </div>

          <div style={styles.tabs}>
            <button 
              onClick={() => setActiveView('snapshots')} 
              style={{...styles.tab, ...(activeView === 'snapshots' ? styles.activeTab : {})}}
            >
              📸 Snapshots
            </button>
            <button 
              onClick={() => setActiveView('versions')} 
              style={{...styles.tab, ...(activeView === 'versions' ? styles.activeTab : {})}}
            >
              Version History
            </button>
            <button 
              onClick={() => setActiveView('contributors')} 
              style={{...styles.tab, ...(activeView === 'contributors' ? styles.activeTab : {})}}
            >
              Contributors
            </button>
            <button 
              onClick={() => setActiveView('filehistory')} 
              style={{...styles.tab, ...(activeView === 'filehistory' ? styles.activeTab : {})}}
            >
              File History
            </button>
          </div>

          {activeView === 'snapshots' && (
            <SnapshotComparison repoId={selectedRepo.repo_id} />
          )}

          {activeView === 'versions' && (
            <div style={styles.versionList}>
              <h4>📜 Version History ({versions.length} versions)</h4>
              {versions.slice(0, 20).map((v, idx) => (
                <div key={idx} style={styles.versionCard}>
                  <div style={styles.versionHeader}>
                    <span style={styles.fileName} title={v.file}>📄 {formatFilePath(v.file, 2)}</span>
                    <span style={styles.timestamp}>{new Date(v.timestamp).toLocaleString()}</span>
                  </div>
                  <div style={styles.versionBody}>
                    <div style={styles.hash}>
                      <strong>Hash:</strong> <code>{v.hash.substring(0, 16)}...</code>
                    </div>
                    <div style={styles.author}>
                      <strong>Author:</strong> {v.author || 'system'}
                    </div>
                    {v.message && v.message !== 'Auto-tracked' && (
                      <div style={styles.message}>
                        <strong>Message:</strong> {v.message}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeView === 'contributors' && (
            <div style={styles.contributorList}>
              <h4>👥 Contributors ({contributors.length})</h4>
              {contributors.map((c, idx) => (
                <div key={idx} style={styles.contributorCard}>
                  <div style={styles.contributorName}>👤 {c.developer}</div>
                  <div style={styles.contributorStats}>
                    <span>Files Modified: <strong>{c.files_modified}</strong></span>
                    <span>Total Versions: <strong>{c.total_versions}</strong></span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeView === 'filehistory' && (
            <FileVersionHistory repoId={selectedRepo.repo_id} />
          )}
        </div>
      )}
    </div>
  );
}

const styles = {
  container: { background: 'white', borderRadius: '8px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' },
  refreshBtn: { padding: '8px 16px', background: '#667eea', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' },
  loading: { textAlign: 'center', padding: '40px', color: '#666' },
  empty: { textAlign: 'center', padding: '40px', color: '#999', background: '#f9f9f9', borderRadius: '8px' },
  repoList: { display: 'grid', gap: '15px' },
  repoCard: { border: '1px solid #e0e0e0', borderRadius: '8px', padding: '15px', transition: 'all 0.3s', display: 'flex', alignItems: 'flex-start', gap: '10px' },
  repoHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' },
  repoName: { margin: 0, fontSize: '18px', color: '#333' },
  repoId: { fontSize: '12px', color: '#999', fontFamily: 'monospace', background: '#f5f5f5', padding: '2px 8px', borderRadius: '4px' },
  repoStats: { display: 'flex', gap: '20px', marginBottom: '10px' },
  stat: { display: 'flex', gap: '5px' },
  statLabel: { color: '#666', fontSize: '14px' },
  statValue: { fontWeight: 'bold', color: '#667eea' },
  repoMeta: { display: 'flex', flexDirection: 'column', gap: '5px', fontSize: '12px', color: '#666' },
  repoUrl: { color: '#666', fontSize: '14px', marginTop: '5px' },
  repoDetailHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '15px' },
  importBtn: { padding: '10px 20px', background: '#10b981', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px', fontWeight: 'bold', ':disabled': { opacity: 0.6, cursor: 'not-allowed' } },
  successMsg: { padding: '12px', background: '#d1fae5', color: '#065f46', borderRadius: '6px', marginBottom: '15px', fontSize: '14px' },
  errorMsg: { padding: '12px', background: '#fee2e2', color: '#991b1b', borderRadius: '6px', marginBottom: '15px', fontSize: '14px' },
  statsBar: { display: 'flex', gap: '15px', marginTop: '15px' },
  statBox: { flex: 1, background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: '8px', padding: '15px', textAlign: 'center' },
  statNumber: { fontSize: '24px', fontWeight: 'bold', color: '#667eea', marginBottom: '5px' },
  statLabel: { fontSize: '12px', color: '#6b7280', textTransform: 'uppercase' },
  deleteBtn: { padding: '8px 12px', background: '#ef4444', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '16px', minWidth: '45px' },
  backBtn: { padding: '8px 16px', background: '#f0f0f0', border: 'none', borderRadius: '4px', cursor: 'pointer', marginBottom: '15px' },
  repoDetail: { marginBottom: '20px' },
  tabs: { display: 'flex', gap: '10px', marginBottom: '20px', borderBottom: '2px solid #e0e0e0' },
  tab: { padding: '10px 20px', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '14px', borderBottom: '2px solid transparent', marginBottom: '-2px' },
  activeTab: { borderBottom: '2px solid #667eea', color: '#667eea', fontWeight: 'bold' },
  versionList: { maxHeight: '600px', overflowY: 'auto' },
  versionCard: { border: '1px solid #e0e0e0', borderRadius: '6px', padding: '12px', marginBottom: '10px', background: '#fafafa' },
  versionHeader: { display: 'flex', justifyContent: 'space-between', marginBottom: '8px' },
  fileName: { fontWeight: 'bold', color: '#333', cursor: 'help' },
  timestamp: { fontSize: '12px', color: '#999' },
  versionBody: { display: 'flex', gap: '20px', marginBottom: '8px', fontSize: '14px' },
  hash: { fontFamily: 'monospace', fontSize: '13px' },
  author: { color: '#666' },
  message: { color: '#666', fontStyle: 'italic', flex: 1 },
  filePath: { fontSize: '11px', color: '#999', marginTop: '5px' },
  contributorList: {},
  contributorCard: { border: '1px solid #e0e0e0', borderRadius: '6px', padding: '15px', marginBottom: '10px', background: '#fafafa' },
  contributorName: { fontSize: '16px', fontWeight: 'bold', marginBottom: '10px', color: '#333' },
  contributorStats: { display: 'flex', gap: '20px', fontSize: '14px', color: '#666' }
};

export default RepositoryManager;
