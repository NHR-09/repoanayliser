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
        <h2>Repository Version Tracking</h2>
        <button onClick={loadRepositories} style={styles.refreshBtn}>
          Refresh
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
                <div onClick={() => selectRepository(repo)} style={{ cursor: 'pointer', flex: 1 }}>
                  <div style={styles.repoHeader}>
                    <h3 style={styles.repoName}>{repo.name}</h3>
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
                    <span>{repo.url}</span>
                    <span>{new Date(repo.last_analyzed).toLocaleString()}</span>
                  </div>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); deleteRepo(repo.repo_id); }}
                  disabled={deleting === repo.repo_id}
                  style={styles.deleteBtn}
                >
                  {deleting === repo.repo_id ? '...' : 'Del'}
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
                <h3>{selectedRepo.name}</h3>
                <p style={styles.repoUrl}>{selectedRepo.url}</p>
              </div>
              <button
                onClick={() => importGitHistory(selectedRepo.repo_id)}
                disabled={importingHistory}
                style={styles.importBtn}
              >
                {importingHistory ? 'Importing...' : 'Import Git History'}
              </button>
            </div>

            {importResult && (
              <div style={importResult.status === 'success' ? styles.successMsg : styles.errorMsg}>
                {importResult.status === 'success' ? (
                  <span>Imported {importResult.commits_processed} commits, created {importResult.versions_created} versions</span>
                ) : (
                  <span>{importResult.message}</span>
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
              style={{ ...styles.tab, ...(activeView === 'snapshots' ? styles.activeTab : {}) }}
            >
              📸 Snapshots
            </button>
            <button
              onClick={() => setActiveView('versions')}
              style={{ ...styles.tab, ...(activeView === 'versions' ? styles.activeTab : {}) }}
            >
              Version History
            </button>
            <button
              onClick={() => setActiveView('contributors')}
              style={{ ...styles.tab, ...(activeView === 'contributors' ? styles.activeTab : {}) }}
            >
              Contributors
            </button>
            <button
              onClick={() => setActiveView('filehistory')}
              style={{ ...styles.tab, ...(activeView === 'filehistory' ? styles.activeTab : {}) }}
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
                    <span style={styles.fileName} title={v.file}>{formatFilePath(v.file, 2)}</span>
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
  container: { background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', padding: '28px', border: '1px solid var(--border)' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' },
  refreshBtn: { padding: '8px 16px', background: 'var(--bg-elevated)', color: 'var(--text-secondary)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '13px' },
  loading: { textAlign: 'center', padding: '40px', color: 'var(--text-muted)' },
  empty: { textAlign: 'center', padding: '40px', color: 'var(--text-muted)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px dashed var(--border)' },
  repoList: { display: 'grid', gap: '12px' },
  repoCard: { border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '16px', transition: 'all 0.2s', display: 'flex', alignItems: 'flex-start', gap: '10px', background: 'var(--bg-elevated)' },
  repoHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' },
  repoName: { margin: 0, fontSize: '16px', color: 'var(--text-primary)', fontWeight: 600 },
  repoId: { fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', background: 'var(--bg-card)', padding: '2px 8px', borderRadius: '4px', border: '1px solid var(--border)' },
  repoStats: { display: 'flex', gap: '16px', marginBottom: '8px' },
  stat: { display: 'flex', gap: '5px' },
  statLabel: { color: 'var(--text-muted)', fontSize: '13px' },
  statValue: { fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' },
  repoMeta: { display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '11px', color: 'var(--text-dim)' },
  repoUrl: { color: 'var(--text-muted)', fontSize: '13px', marginTop: '4px' },
  repoDetailHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' },
  importBtn: { padding: '10px 20px', background: 'var(--green)', color: 'var(--bg-primary)', border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '13px', fontWeight: 600 },
  successMsg: { padding: '12px', background: 'var(--green-dim)', color: 'var(--green)', borderRadius: 'var(--radius-sm)', marginBottom: '14px', fontSize: '13px', border: '1px solid rgba(74,222,128,0.12)' },
  errorMsg: { padding: '12px', background: 'var(--red-dim)', color: 'var(--red)', borderRadius: 'var(--radius-sm)', marginBottom: '14px', fontSize: '13px', border: '1px solid rgba(248,113,113,0.15)' },
  statsBar: { display: 'flex', gap: '12px', marginTop: '16px' },
  statBox: { flex: 1, background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '16px', textAlign: 'center' },
  statNumber: { fontSize: '22px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px', fontFamily: 'var(--font-mono)' },
  deleteBtn: { padding: '8px 12px', background: 'var(--red-dim)', color: 'var(--red)', border: '1px solid rgba(248,113,113,0.15)', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '14px', minWidth: '40px' },
  backBtn: { padding: '8px 16px', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', cursor: 'pointer', marginBottom: '16px', color: 'var(--text-secondary)', fontSize: '13px' },
  repoDetail: { marginBottom: '20px' },
  tabs: { display: 'flex', gap: '4px', marginBottom: '20px', borderBottom: '1px solid var(--border)' },
  tab: { padding: '10px 16px', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '13px', borderBottom: '2px solid transparent', marginBottom: '-1px', color: 'var(--text-muted)' },
  activeTab: { borderBottom: '2px solid var(--text-primary)', color: 'var(--text-primary)', fontWeight: 600 },
  versionList: { maxHeight: '600px', overflowY: 'auto' },
  versionCard: { border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '12px', marginBottom: '8px', background: 'var(--bg-elevated)' },
  versionHeader: { display: 'flex', justifyContent: 'space-between', marginBottom: '8px' },
  fileName: { fontWeight: 600, color: 'var(--text-primary)', cursor: 'help', fontFamily: 'var(--font-mono)', fontSize: '13px' },
  timestamp: { fontSize: '11px', color: 'var(--text-dim)' },
  versionBody: { display: 'flex', gap: '16px', marginBottom: '6px', fontSize: '13px', color: 'var(--text-secondary)' },
  hash: { fontFamily: 'var(--font-mono)', fontSize: '12px' },
  author: { color: 'var(--text-muted)' },
  message: { color: 'var(--text-muted)', fontStyle: 'italic', flex: 1 },
  filePath: { fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' },
  contributorList: {},
  contributorCard: { border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '14px', marginBottom: '8px', background: 'var(--bg-elevated)' },
  contributorName: { fontSize: '15px', fontWeight: 600, marginBottom: '8px', color: 'var(--text-primary)' },
  contributorStats: { display: 'flex', gap: '16px', fontSize: '13px', color: 'var(--text-muted)' },
};

export default RepositoryManager;
