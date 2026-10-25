import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { formatFilePath } from '../utils/formatters';
import FileVersionHistory from './FileVersionHistory';
import SnapshotComparison from './SnapshotComparison';
import {
  IconCamera,
  IconScroll,
  IconUsers,
  IconUser,
  IconX,
  IconGlobe,
  IconFolder,
  IconFileText,
  IconHistory,
  IconArrowRight,
  IconArrowLeft,
  IconTrash,
  IconDatabase,
  IconRefresh,
  IconGitCommit
} from './Icons';
import './RepositoryManager.css';

const parseRepoInfo = (repo) => {
  const rawName = repo.name || repo.repo_id || 'Repository';
  const rawUrl = repo.url || '';
  const isRemote = rawUrl.startsWith('http://') || rawUrl.startsWith('https://') || rawUrl.includes('github.com');

  let displayName = rawName;
  let displayPath = rawUrl || rawName;

  if (rawName.includes('\\') || rawName.includes('/')) {
    const parts = rawName.replace(/\\/g, '/').split('/').filter(Boolean);
    displayName = parts[parts.length - 1] || rawName;
  }

  if (displayPath.includes('\\') || displayPath.includes('/')) {
    const parts = displayPath.replace(/\\/g, '/').split('/').filter(Boolean);
    if (parts.length > 3) {
      displayPath = '.../' + parts.slice(-3).join('/');
    }
  }

  return { displayName, displayPath, isRemote };
};

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
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);

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
    try {
      setDeleting(repoId);
      await api.deleteRepository(repoId);
      await loadRepositories();
      if (selectedRepo?.repo_id === repoId) {
        setSelectedRepo(null);
        setActiveView('list');
      }
      if (props.onRepoDelete) {
        props.onRepoDelete(repoId);
      }
    } catch (error) {
      alert('Failed to delete: ' + error.message);
    } finally {
      setDeleting(null);
      setConfirmDeleteId(null);
    }
  };

  if (loading) {
    return <div style={styles.loading}>Loading repositories...</div>;
  }

  const totalFiles = repositories.reduce((sum, r) => sum + (r.file_count || 0), 0);
  const totalSnapshots = repositories.reduce((sum, r) => sum + (r.version_count || 0), 0);

  return (
    <div className="repo-manager-container">
      {activeView === 'list' && (
        <>
          <div className="repo-hero">
            <div className="repo-hero-main">
              <div className="repo-hero-badge">
                <span className="repo-hero-badge-dot" />
                <IconDatabase size={12} />
                <span>ACTIVE TOPOLOGY REGISTRY</span>
              </div>
              <h2 className="repo-hero-title">Repository Version Tracking</h2>
              <p className="repo-hero-subtitle">
                Indexed codebases, historical commit streams, and architectural snapshot graphs.
              </p>
            </div>

            <div className="repo-hero-stats">
              <div className="repo-telemetry-chip">
                <span className="repo-telemetry-val">{repositories.length}</span>
                <span className="repo-telemetry-lbl">Repositories</span>
              </div>
              <div className="repo-telemetry-chip">
                <span className="repo-telemetry-val">{totalFiles}</span>
                <span className="repo-telemetry-lbl">Files Tracked</span>
              </div>
              <div className="repo-telemetry-chip">
                <span className="repo-telemetry-val">{totalSnapshots}</span>
                <span className="repo-telemetry-lbl">Snapshots</span>
              </div>
              <button
                onClick={loadRepositories}
                className="repo-refresh-btn"
                title="Refresh active repositories list"
              >
                <IconRefresh size={14} />
                <span>Refresh</span>
              </button>
            </div>
          </div>

          <div className="repo-unconventional-grid">
            {repositories.length === 0 ? (
              <div style={styles.empty}>
                No repositories analyzed yet. Go to the Analyze tab to index your first repository.
              </div>
            ) : (
              repositories.map((repo, idx) => {
                const { displayName, displayPath, isRemote } = parseRepoInfo(repo);
                return (
                  <div
                    key={repo.repo_id}
                    className="repo-dossier-card"
                    onClick={() => selectRepository(repo)}
                  >
                    <span className="repo-dossier-watermark">// {String(idx + 1).padStart(2, '0')}</span>

                    <div>
                      <div className="repo-dossier-top">
                        <span className="repo-source-pill">
                          {isRemote ? <IconGlobe size={12} /> : <IconFolder size={12} />}
                          <span>{isRemote ? 'Remote GitHub' : 'Local Workspace'}</span>
                        </span>
                        <span className="repo-hash-badge" title={repo.repo_id}>
                          {repo.repo_id.substring(0, 8)}
                        </span>
                      </div>

                      <div className="repo-dossier-name-row">
                        <h3 className="repo-dossier-title">{displayName}</h3>
                      </div>

                      <div className="repo-dossier-path" title={repo.url || repo.name}>
                        {displayPath}
                      </div>

                      <div className="repo-dossier-metrics">
                        <div className="repo-metric-badge">
                          <IconFileText size={13} />
                          <span>Files: <strong>{repo.file_count || 0}</strong></span>
                        </div>
                        <div className="repo-metric-badge">
                          <IconCamera size={13} />
                          <span>Snapshots: <strong>{repo.version_count || 0}</strong></span>
                        </div>
                      </div>
                    </div>

                    <div className="repo-dossier-footer">
                      <span className="repo-timestamp">
                        <IconHistory size={11} />
                        {new Date(repo.last_analyzed).toLocaleDateString([], {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </span>

                      <div className="repo-action-group">
                        <span className="repo-inspect-cue">
                          Explore <IconArrowRight size={13} />
                        </span>

                        {confirmDeleteId === repo.repo_id ? (
                          <div className="repo-delete-confirm-box" onClick={(e) => e.stopPropagation()}>
                            <button
                              onClick={() => deleteRepo(repo.repo_id)}
                              disabled={deleting === repo.repo_id}
                              className="repo-confirm-btn"
                            >
                              {deleting === repo.repo_id ? '...' : 'Confirm'}
                            </button>
                            <button
                              onClick={() => setConfirmDeleteId(null)}
                              className="repo-cancel-btn"
                            >
                              <IconX size={11} />
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setConfirmDeleteId(repo.repo_id);
                            }}
                            disabled={deleting === repo.repo_id}
                            className="repo-trash-btn"
                            title="Delete from tracking"
                          >
                            <IconTrash size={13} />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </>
      )}

      {activeView === 'versions' && selectedRepo && (
        <div className="repo-detail-container">
          <button onClick={() => setActiveView('list')} className="repo-back-btn">
            <IconArrowLeft size={14} />
            <span>Back to Repositories</span>
          </button>

          <div className="repo-detail-dossier">
            <div className="repo-detail-top-row">
              <div className="repo-detail-meta">
                <div className="repo-detail-pills">
                  <span className="repo-source-pill">
                    {parseRepoInfo(selectedRepo).isRemote ? <IconGlobe size={12} /> : <IconFolder size={12} />}
                    <span>{parseRepoInfo(selectedRepo).isRemote ? 'Remote GitHub' : 'Local Workspace'}</span>
                  </span>
                  <span className="repo-hash-badge" title={selectedRepo.repo_id}>
                    {selectedRepo.repo_id.substring(0, 8)}
                  </span>
                </div>
                <h3 className="repo-detail-title">{parseRepoInfo(selectedRepo).displayName}</h3>
                <div className="repo-detail-url" title={selectedRepo.url || selectedRepo.name}>
                  {selectedRepo.url || selectedRepo.name}
                </div>
              </div>

              <button
                onClick={() => importGitHistory(selectedRepo.repo_id)}
                disabled={importingHistory}
                className="repo-import-action-btn"
              >
                <IconRefresh size={14} className={importingHistory ? 'spin' : ''} />
                <span>{importingHistory ? 'Importing Streams...' : 'Import Git History'}</span>
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

            <div className="repo-stats-trio">
              <div className="repo-stat-card">
                <div className="repo-stat-card-val">{selectedRepo.file_count || 0}</div>
                <div className="repo-stat-card-lbl">Files Tracked</div>
              </div>
              <div className="repo-stat-card">
                <div className="repo-stat-card-val">{selectedRepo.version_count || 0}</div>
                <div className="repo-stat-card-lbl">Total Snapshots</div>
              </div>
              <div className="repo-stat-card">
                <div className="repo-stat-card-val">
                  {selectedRepo.version_count > 0 ? selectedRepo.version_count : 'N/A'}
                </div>
                <div className="repo-stat-card-lbl">Analysis Sequences</div>
              </div>
            </div>
          </div>

          <div className="repo-subnav-tabs">
            <button
              onClick={() => setActiveView('snapshots')}
              className={`repo-subnav-tab ${activeView === 'snapshots' ? 'active' : ''}`}
            >
              <IconCamera size={14} />
              <span>Snapshots</span>
            </button>
            <button
              onClick={() => setActiveView('versions')}
              className={`repo-subnav-tab ${activeView === 'versions' ? 'active' : ''}`}
            >
              <IconScroll size={14} />
              <span>Version History</span>
            </button>
            <button
              onClick={() => setActiveView('contributors')}
              className={`repo-subnav-tab ${activeView === 'contributors' ? 'active' : ''}`}
            >
              <IconUsers size={14} />
              <span>Contributors</span>
            </button>
            <button
              onClick={() => setActiveView('filehistory')}
              className={`repo-subnav-tab ${activeView === 'filehistory' ? 'active' : ''}`}
            >
              <IconHistory size={14} />
              <span>File History</span>
            </button>
          </div>

          {activeView === 'snapshots' && (
            <SnapshotComparison repoId={selectedRepo.repo_id} />
          )}

          {activeView === 'versions' && (
            <div style={styles.versionList}>
              <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <IconScroll size={16} /> Version History ({versions.length} versions)
              </h4>
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
              <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <IconUsers size={16} /> Contributors ({contributors.length})
              </h4>
              {contributors.map((c, idx) => (
                <div key={idx} style={styles.contributorCard}>
                  <div style={{ ...styles.contributorName, display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <IconUser size={14} /> {c.developer}
                  </div>
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
  deleteBtn: { padding: '8px 14px', background: 'var(--red-dim)', color: 'var(--red)', border: '1px solid rgba(248,113,113,0.15)', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '13px', fontWeight: 600 },
  deleteConfirmBtn: { padding: '8px 12px', background: 'var(--red)', color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '12px', fontWeight: 700 },
  deleteCancelBtn: { padding: '8px 10px', background: 'var(--bg-elevated)', color: 'var(--text-muted)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '12px' },
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
