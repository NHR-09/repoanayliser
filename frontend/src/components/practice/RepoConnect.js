import React, { useState, useEffect } from 'react';
import { practiceApi } from '../../services/practiceApi';

export default function RepoConnect({ onSelectRepo, selectedRepoId }) {
  const [repos, setRepos] = useState([]);
  const [repoUrl, setRepoUrl] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });

  useEffect(() => {
    loadRepositories();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadRepositories = async () => {
    setLoading(true);
    try {
      const data = await practiceApi.getRepositories();
      setRepos(data || []);
      // If none selected and repos exist, select first completed repo by default
      if (!selectedRepoId && data?.length > 0 && onSelectRepo) {
        onSelectRepo(data[0]);
      }
    } catch (err) {
      console.error('Failed to load repositories:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleConnectRepo = async (e) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;

    setSubmitting(true);
    setMessage({ text: '', type: '' });

    try {
      const newRepo = await practiceApi.registerRepository(repoUrl.trim(), displayName.trim());
      setMessage({ text: `Successfully registered "${newRepo.display_name}". Analysis started in background.`, type: 'success' });
      setRepoUrl('');
      setDisplayName('');
      await loadRepositories();
      if (onSelectRepo) onSelectRepo(newRepo);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || 'Failed to connect repository.';
      setMessage({ text: `Connection Error: ${detail}`, type: 'error' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleReanalyze = async (repoId) => {
    try {
      await practiceApi.triggerReanalysis(repoId);
      setMessage({ text: 'Re-analysis queued in background.', type: 'info' });
      await loadRepositories();
    } catch (err) {
      setMessage({ text: 'Failed to trigger re-analysis.', type: 'error' });
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'COMPLETED':
        return <span style={{ background: 'var(--green-dim)', color: 'var(--green)', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600 }}>COMPLETED</span>;
      case 'RUNNING':
        return <span style={{ background: 'var(--blue-dim)', color: 'var(--blue)', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600 }}>RUNNING</span>;
      case 'FAILED':
        return <span style={{ background: 'var(--red-dim)', color: 'var(--red)', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600 }}>FAILED</span>;
      default:
        return <span style={{ background: 'var(--amber-dim)', color: 'var(--amber)', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600 }}>PENDING</span>;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Alert Banner */}
      {message.text && (
        <div style={{
          padding: '12px 16px',
          borderRadius: 'var(--radius-md)',
          background: message.type === 'error' ? 'var(--red-dim)' : message.type === 'success' ? 'var(--green-dim)' : 'var(--blue-dim)',
          color: message.type === 'error' ? 'var(--red)' : message.type === 'success' ? 'var(--green)' : 'var(--blue)',
          border: `1px solid ${message.type === 'error' ? 'var(--red)' : message.type === 'success' ? 'var(--green)' : 'var(--blue)'}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>{message.text}</span>
          <button
            onClick={() => setMessage({ text: '', type: '' })}
            style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Connect Repo Form */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '24px'
      }}>
        <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
          Connect GitHub Repository
        </h3>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>
          Connect a public GitHub repository to enable repository-grounded quizzes and AST evidence mapping.
        </p>

        <form onSubmit={handleConnectRepo} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <div style={{ flex: 3, minWidth: '260px' }}>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                GitHub Repository URL
              </label>
              <input
                type="url"
                placeholder="https://github.com/owner/repository"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                required
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border)',
                  background: 'var(--bg-input)',
                  color: 'var(--text-primary)',
                  fontSize: '13px'
                }}
              />
            </div>
            <div style={{ flex: 2, minWidth: '180px' }}>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                Display Name (Optional)
              </label>
              <input
                type="text"
                placeholder="e.g. Core API Service"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border)',
                  background: 'var(--bg-input)',
                  color: 'var(--text-primary)',
                  fontSize: '13px'
                }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
            <button
              type="submit"
              disabled={submitting}
              style={{
                padding: '8px 20px',
                background: submitting ? 'var(--border)' : 'var(--accent)',
                color: '#09090b',
                fontWeight: 600,
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                cursor: submitting ? 'not-allowed' : 'pointer',
                fontSize: '13px'
              }}
            >
              {submitting ? 'Connecting...' : 'Connect & Analyze Repository'}
            </button>
          </div>
        </form>
      </div>

      {/* Connected Repositories List */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '24px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' }}>
              Connected Repositories ({repos.length})
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Select a repository to map code evidence and generate grounded questions.
            </p>
          </div>
          <button
            onClick={loadRepositories}
            style={{
              padding: '4px 10px',
              background: 'transparent',
              border: '1px solid var(--border)',
              color: 'var(--text-muted)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '12px',
              cursor: 'pointer'
            }}
          >
            ↻ Refresh
          </button>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>Loading repositories...</div>
        ) : repos.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
            No repositories connected yet. Add a GitHub repository above to start codebase practice.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {repos.map(r => {
              const isSelected = selectedRepoId === r.id;
              return (
                <div
                  key={r.id}
                  onClick={() => onSelectRepo && onSelectRepo(r)}
                  style={{
                    background: isSelected ? 'rgba(96, 165, 250, 0.08)' : 'var(--bg-elevated)',
                    border: `1px solid ${isSelected ? 'var(--blue)' : 'var(--border)'}`,
                    borderRadius: 'var(--radius-md)',
                    padding: '16px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease'
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '14px' }}>
                        {r.display_name}
                      </span>
                      {getStatusBadge(r.analysis_status)}
                      {isSelected && (
                        <span style={{ fontSize: '11px', color: 'var(--blue)', fontWeight: 600 }}>
                          • Active for Practice
                        </span>
                      )}
                    </div>
                    <a
                      href={r.repo_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      style={{ fontSize: '12px', color: 'var(--text-muted)', textDecoration: 'none' }}
                    >
                      🔗 {r.repo_url}
                    </a>
                    {r.last_analyzed_commit && (
                      <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                        Commit: {r.last_analyzed_commit.slice(0, 8)} • Analyzed: {new Date(r.last_analyzed_at || r.created_at).toLocaleString()}
                      </span>
                    )}
                    {r.analysis_error && (
                      <span style={{ fontSize: '11px', color: 'var(--red)', marginTop: '2px' }}>
                        Error: {r.analysis_error}
                      </span>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }} onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => handleReanalyze(r.id)}
                      style={{
                        padding: '6px 12px',
                        background: 'var(--bg-card)',
                        border: '1px solid var(--border-hover)',
                        color: 'var(--text-secondary)',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '12px',
                        cursor: 'pointer'
                      }}
                    >
                      ↻ Re-analyze
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
