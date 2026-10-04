import React, { useState } from 'react';
import { api } from '../services/api';

export default function AnalyzeRepo({ onAnalysisComplete }) {
  const [mode, setMode] = useState('github'); // 'github' | 'local'
  const [repoUrl, setRepoUrl] = useState('');
  const [localPath, setLocalPath] = useState('');
  const [loading, setLoading] = useState(false);
  const [browsing, setBrowsing] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState('');

  const handleBrowse = async () => {
    setBrowsing(true);
    try {
      const { data } = await api.browseFolder();
      if (data.path) {
        setLocalPath(data.path);
      }
    } catch (error) {
      setStatus('Error opening folder dialog: ' + error.message);
    } finally {
      setBrowsing(false);
    }
  };

  const handleAnalyze = async () => {
    const isLocal = mode === 'local';
    const value = isLocal ? localPath : repoUrl;
    if (!value) return;

    setLoading(true);
    setStatus(isLocal ? 'Scanning local folder...' : 'Starting analysis...');

    try {
      const { data } = isLocal
        ? await api.analyzeLocal(value)
        : await api.analyzeRepo(value);
      setJobId(data.job_id);
      setStatus(isLocal
        ? 'Parsing files and building graph...'
        : 'Cloning repository and importing git history...');
      pollStatus(data.job_id);
    } catch (error) {
      setStatus('Error: ' + error.message);
      setLoading(false);
    }
  };

  const pollStatus = async (id) => {
    const interval = setInterval(async () => {
      try {
        const { data } = await api.getStatus(id);
        setStatus(data.status);
        if (data.status === 'completed') {
          clearInterval(interval);
          setLoading(false);
          onAnalysisComplete(data.result, mode === 'local' ? localPath : repoUrl);
        } else if (data.status === 'failed') {
          clearInterval(interval);
          setLoading(false);
          setStatus('Failed: ' + (data.error || 'Unknown error'));
        }
      } catch (error) {
        clearInterval(interval);
        setLoading(false);
      }
    }, 2000);
  };

  const isLocal = mode === 'local';
  const inputValue = isLocal ? localPath : repoUrl;
  const isReady = !!inputValue.trim() && !loading;

  return (
    <div style={styles.container}>
      <div style={styles.headerRow}>
        <div>
          <h2 style={styles.heading}>Analyze Repository</h2>
          <p style={styles.description}>
            {isLocal
              ? 'Analyze any local folder on this machine — no git required.'
              : 'Clone, parse, and build the architectural graph for any GitHub repo.'}
          </p>
        </div>
      </div>

      {/* Mode Toggle */}
      <div style={styles.modeToggle}>
        <button
          id="mode-github"
          onClick={() => { setMode('github'); setStatus(''); }}
          style={{ ...styles.modeBtn, ...(mode === 'github' ? styles.modeBtnActive : {}) }}
        >
          <span style={styles.modeIcon}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/></svg></span> GitHub URL
        </button>
        <button
          id="mode-local"
          onClick={() => { setMode('local'); setStatus(''); }}
          style={{ ...styles.modeBtn, ...(mode === 'local' ? styles.modeBtnActive : {}) }}
        >
          <span style={styles.modeIcon}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg></span> Local Folder
        </button>
      </div>

      <div style={styles.inputGroup}>
        {isLocal && (
          <button
            id="browse-btn"
            onClick={handleBrowse}
            disabled={browsing || loading}
            style={{
              ...styles.browseBtn,
              ...(browsing ? styles.browseBtnActive : {})
            }}
          >
            {browsing ? <span style={styles.spinner}></span> : <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>}
          </button>
        )}
        <input
          id={isLocal ? 'local-path-input' : 'github-url-input'}
          type="text"
          placeholder={isLocal
            ? 'Click folder icon to browse  or  paste path here'
            : 'https://github.com/user/repo'}
          value={inputValue}
          onChange={(e) => isLocal ? setLocalPath(e.target.value) : setRepoUrl(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && isReady && handleAnalyze()}
          style={styles.input}
          readOnly={browsing}
        />
        <button
          id="analyze-btn"
          onClick={handleAnalyze}
          disabled={!isReady}
          style={{
            ...styles.button,
            ...(loading ? styles.buttonLoading : {}),
            ...(!isReady && !loading ? styles.buttonDisabled : {})
          }}
        >
          {loading ? (
            <span style={styles.buttonInner}>
              <span style={styles.spinner}></span>
              Analyzing…
            </span>
          ) : (
            'Analyze'
          )}
        </button>
      </div>

      {isLocal && (
        <p style={styles.hint}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{flexShrink: 0, opacity: 0.6}}><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
          <span>Supports Python, JavaScript, TypeScript, and Java projects.</span>
        </p>
      )}

      {jobId && (
        <p style={styles.jobId}>
          Job: <code style={styles.code}>{jobId}</code>
        </p>
      )}

      {status && (
        <div style={status.includes('Error') || status.includes('Failed') ? styles.errorStatus : styles.statusBox}>
          <span style={styles.statusDot(status.includes('Error') || status.includes('Failed'))}></span>
          {status}
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    padding: '28px',
    background: 'var(--bg-card)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border)',
    marginBottom: '20px',
  },
  headerRow: {
    marginBottom: '20px',
  },
  heading: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  description: {
    color: 'var(--text-muted)',
    fontSize: '13px',
    marginTop: '4px',
    marginBottom: 0,
  },
  modeToggle: {
    display: 'flex',
    gap: '8px',
    marginBottom: '16px',
  },
  modeBtn: {
    padding: '8px 18px',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border)',
    background: 'var(--bg-elevated)',
    color: 'var(--text-muted)',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    transition: 'all 0.2s',
  },
  modeBtnActive: {
    background: 'var(--bg-card)',
    color: 'var(--text-primary)',
    border: '1px solid var(--text-primary)',
    boxShadow: '0 0 0 1px var(--text-primary)',
  },
  modeIcon: {
    fontSize: '11px',
    opacity: 0.75,
  },
  inputGroup: {
    display: 'flex',
    gap: '10px',
    marginBottom: '8px',
  },
  input: {
    flex: 1,
    padding: '12px 16px',
    fontSize: '14px',
    fontFamily: 'var(--font-mono)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border)',
    background: 'var(--bg-input)',
    color: 'var(--text-primary)',
    transition: 'border-color 0.2s',
  },
  button: {
    padding: '12px 28px',
    background: 'var(--text-primary)',
    color: 'var(--bg-primary)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 600,
    letterSpacing: '0.3px',
    transition: 'all 0.2s',
    whiteSpace: 'nowrap',
  },
  buttonLoading: {
    background: 'var(--bg-elevated)',
    color: 'var(--text-secondary)',
    cursor: 'wait',
  },
  buttonDisabled: {
    opacity: 0.4,
    cursor: 'not-allowed',
  },
  browseBtn: {
    padding: '12px 14px',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border)',
    background: 'var(--bg-elevated)',
    color: 'var(--text-secondary)',
    fontSize: '18px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    lineHeight: 1,
  },
  browseBtnActive: {
    background: 'var(--bg-card)',
    border: '1px solid var(--text-primary)',
    cursor: 'wait',
  },
  buttonInner: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  spinner: {
    display: 'inline-block',
    width: '14px',
    height: '14px',
    border: '2px solid var(--border)',
    borderTop: '2px solid var(--text-secondary)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  hint: {
    margin: '0 0 12px',
    fontSize: '12px',
    color: 'var(--text-dim)',
    fontFamily: 'var(--font-mono)',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  jobId: {
    padding: '10px 14px',
    background: 'var(--bg-elevated)',
    borderRadius: 'var(--radius-sm)',
    fontSize: '13px',
    color: 'var(--text-secondary)',
    border: '1px solid var(--border)',
    marginTop: '12px',
  },
  code: {
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-primary)',
  },
  statusBox: {
    marginTop: '12px',
    padding: '12px 16px',
    background: 'var(--blue-dim)',
    color: 'var(--blue)',
    borderRadius: 'var(--radius-md)',
    fontSize: '13px',
    border: '1px solid rgba(96, 165, 250, 0.15)',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  errorStatus: {
    marginTop: '12px',
    padding: '12px 16px',
    background: 'var(--red-dim)',
    color: 'var(--red)',
    borderRadius: 'var(--radius-md)',
    fontSize: '13px',
    border: '1px solid rgba(248, 113, 113, 0.15)',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  statusDot: (isError) => ({
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: isError ? 'var(--red)' : 'var(--blue)',
    flexShrink: 0,
  }),
};
