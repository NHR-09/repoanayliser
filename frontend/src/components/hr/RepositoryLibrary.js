import React, { useState, useEffect, useCallback } from 'react';
import { hrApi } from '../../services/hrApi';
import RepositoryCoverageModal from './RepositoryCoverageModal';

export default function RepositoryLibrary({ orgId, onOpenGenerateForRepo }) {
  const [repositories, setRepositories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Register Modal state
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [repoUrl, setRepoUrl] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [description, setDescription] = useState('');
  const [intendedEvaluations, setIntendedEvaluations] = useState('');
  const [registering, setRegistering] = useState(false);
  const [registerError, setRegisterError] = useState('');

  // Coverage Modal state
  const [coverageRepo, setCoverageRepo] = useState(null);

  const loadRepositories = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await hrApi.getRepositories(orgId, { pageSize: 50 });
      setRepositories(data.items || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load Approved Repository Library.');
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    if (orgId) {
      loadRepositories();
    }
  }, [orgId, loadRepositories]);

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setRegisterError('');

    if (!repoUrl.trim().startsWith('https://github.com/')) {
      setRegisterError("Only official HTTPS GitHub repository URLs ('https://github.com/owner/repo') are supported.");
      return;
    }

    setRegistering(true);
    try {
      await hrApi.registerRepository(orgId, {
        repo_url: repoUrl.trim(),
        display_name: displayName.trim() || undefined,
        description: description.trim() || undefined,
        intended_evaluations: intendedEvaluations.trim() || undefined,
      });
      setIsRegisterOpen(false);
      setRepoUrl('');
      setDisplayName('');
      setDescription('');
      setIntendedEvaluations('');
      loadRepositories();
    } catch (err) {
      setRegisterError(err.response?.data?.detail || err.message || 'Registration failed.');
    } finally {
      setRegistering(false);
    }
  };

  const handleTransitionApproval = async (repoId, action) => {
    try {
      await hrApi.transitionRepository(orgId, repoId, action);
      loadRepositories();
    } catch (err) {
      alert(err.response?.data?.detail || err.message || `Failed to ${action} repository.`);
    }
  };

  const handleReanalyze = async (repoId) => {
    try {
      await hrApi.reanalyzeRepository(orgId, repoId);
      alert('Repository re-analysis queued in background.');
      loadRepositories();
    } catch (err) {
      alert(err.response?.data?.detail || err.message || 'Failed to queue re-analysis.');
    }
  };

  return (
    <div style={styles.container}>
      {/* Top Header */}
      <div style={styles.topBar}>
        <div>
          <h2 style={styles.pageTitle}>Approved Repository Library</h2>
          <p style={styles.subtext}>
            Curated repositories approved for technical assessment preparation, revision tracking, and question coverage analysis.
          </p>
        </div>
        <button style={styles.primaryBtn} onClick={() => setIsRegisterOpen(true)}>
          <span style={{ marginRight: '6px' }}>+</span>
          Register Repository
        </button>
      </div>

      {error && <div style={styles.errorBox}>{error}</div>}

      {/* Main Table */}
      <div style={styles.tableCard}>
        {loading ? (
          <div style={styles.loadingBox}>
            <div style={styles.spinner} />
            <p style={{ marginTop: '12px', color: '#94a3b8' }}>Loading repository records...</p>
          </div>
        ) : repositories.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={{ fontSize: '32px', marginBottom: '8px' }}>📦</div>
            <h4 style={{ margin: 0, color: '#f8fafc', fontSize: '16px' }}>No repositories registered</h4>
            <p style={{ margin: '6px 0 16px', color: '#94a3b8', fontSize: '13px' }}>
              Register a public GitHub repository to analyze its code graph and build grounded technical assessments.
            </p>
            <button style={styles.primaryBtn} onClick={() => setIsRegisterOpen(true)}>
              Register Repository
            </button>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Repository</th>
                  <th style={styles.th}>Branch / Commit</th>
                  <th style={styles.th}>Analysis State</th>
                  <th style={styles.th}>Approval Lifecycle</th>
                  <th style={styles.th}>Intended Purpose</th>
                  <th style={{ ...styles.th, textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {repositories.map((repo) => {
                  const isApproved = repo.approval_status === 'APPROVED';
                  const isArchived = repo.approval_status === 'ARCHIVED' || repo.is_archived === 1;
                  const isAnalysisCompleted = repo.analysis_status === 'COMPLETED';

                  return (
                    <tr key={repo.id} style={styles.tr}>
                      <td style={styles.td}>
                        <div style={{ fontWeight: '600', color: '#f8fafc', fontSize: '14px' }}>
                          {repo.display_name}
                        </div>
                        <a
                          href={repo.repo_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={styles.repoLink}
                        >
                          {repo.repo_url} ↗
                        </a>
                      </td>

                      <td style={styles.td}>
                        <div style={{ fontSize: '12px', color: '#cbd5e1' }}>
                          {repo.default_branch || 'main'}
                        </div>
                        <div style={{ fontSize: '11px', color: '#64748b', fontFamily: 'monospace' }}>
                          {repo.last_analyzed_commit ? repo.last_analyzed_commit.substring(0, 8) : 'PENDING'}
                        </div>
                      </td>

                      <td style={styles.td}>
                        <span
                          style={{
                            ...styles.statusBadge,
                            backgroundColor: isAnalysisCompleted
                              ? 'rgba(16, 185, 129, 0.15)'
                              : repo.analysis_status === 'FAILED'
                              ? 'rgba(239, 68, 68, 0.15)'
                              : 'rgba(245, 158, 11, 0.15)',
                            color: isAnalysisCompleted
                              ? '#10b981'
                              : repo.analysis_status === 'FAILED'
                              ? '#ef4444'
                              : '#f59e0b',
                          }}
                        >
                          {repo.analysis_status}
                        </span>
                      </td>

                      <td style={styles.td}>
                        <span
                          style={{
                            ...styles.statusBadge,
                            backgroundColor: isApproved
                              ? 'rgba(16, 185, 129, 0.15)'
                              : isArchived
                              ? 'rgba(100, 116, 139, 0.2)'
                              : 'rgba(56, 189, 248, 0.15)',
                            color: isApproved ? '#10b981' : isArchived ? '#94a3b8' : '#38bdf8',
                          }}
                        >
                          {repo.approval_status}
                        </span>
                      </td>

                      <td style={{ ...styles.td, maxWidth: '240px' }}>
                        <div style={styles.purposeText}>
                          {repo.intended_evaluations || repo.description || 'General assessment preparation'}
                        </div>
                      </td>

                      <td style={{ ...styles.td, textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '6px' }}>
                          <button
                            style={styles.coverageBtn}
                            onClick={() => setCoverageRepo(repo)}
                            title="Inspect Question Coverage"
                          >
                            📊 Coverage
                          </button>

                          {!isApproved && !isArchived && isAnalysisCompleted && (
                            <button
                              style={styles.approveBtn}
                              onClick={() => handleTransitionApproval(repo.id, 'APPROVE')}
                              title="Approve repository for technical assessments"
                            >
                              Approve
                            </button>
                          )}

                          <button
                            style={styles.iconBtn}
                            onClick={() => handleReanalyze(repo.id)}
                            title="Trigger Static Code Re-analysis"
                          >
                            🔄
                          </button>

                          {!isArchived ? (
                            <button
                              style={styles.archiveBtn}
                              onClick={() => handleTransitionApproval(repo.id, 'ARCHIVE')}
                              title="Archive Repository"
                            >
                              Archive
                            </button>
                          ) : (
                            <button
                              style={styles.restoreBtn}
                              onClick={() => handleTransitionApproval(repo.id, 'RESTORE')}
                              title="Restore Repository"
                            >
                              Restore
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Register Repository Modal */}
      {isRegisterOpen && (
        <div style={styles.modalOverlay}>
          <div style={styles.modal}>
            <div style={styles.modalHeader}>
              <div>
                <div style={styles.badge}>REPOSITORY REGISTRATION</div>
                <h3 style={styles.modalTitle}>Register GitHub Repository</h3>
              </div>
              <button style={styles.closeBtn} onClick={() => setIsRegisterOpen(false)}>&times;</button>
            </div>

            <form onSubmit={handleRegisterSubmit} style={styles.modalBody}>
              {registerError && <div style={styles.errorBox}>{registerError}</div>}

              <div style={styles.infoBanner}>
                🔒 <strong>Security & SSRF Verification:</strong> Only verified, public HTTPS GitHub repositories
                are accepted. Private network addresses and loopback URLs are rejected.
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>GitHub Repository URL *</label>
                <input
                  type="url"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  placeholder="https://github.com/owner/repository"
                  style={styles.input}
                  required
                />
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Display Name (Optional)</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="e.g. Core Platform Backend"
                  style={styles.input}
                />
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Description</label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Brief summary of codebase architecture and purpose..."
                  style={styles.textarea}
                />
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Intended Assessment Purpose</label>
                <input
                  type="text"
                  value={intendedEvaluations}
                  onChange={(e) => setIntendedEvaluations(e.target.value)}
                  placeholder="e.g. Senior Backend Engineer dependency tracing evaluation"
                  style={styles.input}
                />
              </div>

              <div style={styles.modalFooter}>
                <button
                  type="button"
                  onClick={() => setIsRegisterOpen(false)}
                  style={styles.cancelBtn}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={registering}
                  style={styles.submitBtn}
                >
                  {registering ? 'Registering & Queuing Analysis...' : 'Register Repository'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Coverage Modal */}
      {coverageRepo && (
        <RepositoryCoverageModal
          orgId={orgId}
          repoId={coverageRepo.id}
          repoName={coverageRepo.display_name}
          onClose={() => setCoverageRepo(null)}
          onOpenGenerate={onOpenGenerateForRepo}
        />
      )}
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  topBar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  pageTitle: {
    margin: 0,
    fontSize: '22px',
    fontWeight: '700',
    color: '#f8fafc',
  },
  subtext: {
    margin: '4px 0 0',
    fontSize: '13px',
    color: '#94a3b8',
  },
  primaryBtn: {
    backgroundColor: '#38bdf8',
    color: '#0f172a',
    border: 'none',
    padding: '9px 18px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '700',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
  },
  tableCard: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '10px',
    overflow: 'hidden',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    textAlign: 'left',
  },
  th: {
    padding: '12px 16px',
    fontSize: '11px',
    fontWeight: '700',
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    borderBottom: '1px solid #334155',
    backgroundColor: '#0f172a',
  },
  tr: {
    borderBottom: '1px solid #1e293b',
  },
  td: {
    padding: '14px 16px',
    fontSize: '13px',
    verticalAlign: 'middle',
  },
  repoLink: {
    fontSize: '12px',
    color: '#38bdf8',
    textDecoration: 'none',
    marginTop: '2px',
    display: 'inline-block',
  },
  purposeText: {
    fontSize: '12px',
    color: '#94a3b8',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  statusBadge: {
    fontSize: '11px',
    fontWeight: '700',
    padding: '3px 8px',
    borderRadius: '4px',
    textTransform: 'uppercase',
    display: 'inline-block',
  },
  coverageBtn: {
    backgroundColor: '#0f172a',
    border: '1px solid #38bdf8',
    color: '#38bdf8',
    fontSize: '12px',
    fontWeight: '600',
    padding: '5px 10px',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  approveBtn: {
    backgroundColor: '#10b981',
    border: 'none',
    color: '#0f172a',
    fontSize: '12px',
    fontWeight: '700',
    padding: '5px 12px',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  iconBtn: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    color: '#f8fafc',
    fontSize: '13px',
    padding: '5px 8px',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  archiveBtn: {
    backgroundColor: 'transparent',
    border: '1px solid #64748b',
    color: '#94a3b8',
    fontSize: '12px',
    padding: '5px 10px',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  restoreBtn: {
    backgroundColor: 'transparent',
    border: '1px solid #38bdf8',
    color: '#38bdf8',
    fontSize: '12px',
    padding: '5px 10px',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  loadingBox: {
    textAlign: 'center',
    padding: '60px',
  },
  spinner: {
    width: '32px',
    height: '32px',
    border: '3px solid #334155',
    borderTopColor: '#38bdf8',
    borderRadius: '50%',
    margin: '0 auto',
    animation: 'spin 1s linear infinite',
  },
  emptyState: {
    textAlign: 'center',
    padding: '60px 20px',
  },
  errorBox: {
    padding: '12px 16px',
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid #ef4444',
    color: '#fca5a5',
    borderRadius: '6px',
    fontSize: '13px',
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: '20px',
  },
  modal: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '12px',
    width: '100%',
    maxWidth: '560px',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
  },
  modalHeader: {
    padding: '18px 22px',
    borderBottom: '1px solid #1e293b',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  badge: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#38bdf8',
    letterSpacing: '0.05em',
    marginBottom: '4px',
  },
  modalTitle: {
    margin: 0,
    color: '#f8fafc',
    fontSize: '17px',
    fontWeight: '600',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: '#94a3b8',
    fontSize: '26px',
    cursor: 'pointer',
    lineHeight: 1,
  },
  modalBody: {
    padding: '20px 22px',
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  infoBanner: {
    padding: '10px 14px',
    backgroundColor: 'rgba(56, 189, 248, 0.08)',
    border: '1px solid rgba(56, 189, 248, 0.2)',
    borderRadius: '6px',
    fontSize: '12px',
    color: '#cbd5e1',
    lineHeight: '1.4',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '5px',
  },
  label: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#cbd5e1',
  },
  input: {
    padding: '9px 12px',
    borderRadius: '6px',
    border: '1px solid #334155',
    backgroundColor: '#1e293b',
    color: '#f8fafc',
    fontSize: '13px',
    outline: 'none',
  },
  textarea: {
    padding: '9px 12px',
    borderRadius: '6px',
    border: '1px solid #334155',
    backgroundColor: '#1e293b',
    color: '#f8fafc',
    fontSize: '13px',
    outline: 'none',
    resize: 'vertical',
    fontFamily: 'inherit',
  },
  modalFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '10px',
    marginTop: '10px',
    paddingTop: '14px',
    borderTop: '1px solid #1e293b',
  },
  cancelBtn: {
    backgroundColor: 'transparent',
    border: '1px solid #334155',
    color: '#cbd5e1',
    padding: '8px 16px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  submitBtn: {
    backgroundColor: '#38bdf8',
    border: 'none',
    color: '#0f172a',
    padding: '8px 20px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '700',
    cursor: 'pointer',
  },
};
