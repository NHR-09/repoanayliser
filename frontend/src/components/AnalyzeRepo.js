import React, { useState } from 'react';
import { api } from '../services/api';

export default function AnalyzeRepo({ onAnalysisComplete }) {
  const [repoUrl, setRepoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState('');

  const handleAnalyze = async () => {
    if (!repoUrl) return;
    setLoading(true);
    setStatus('Starting analysis...');
    try {
      const { data } = await api.analyzeRepo(repoUrl);
      setJobId(data.job_id);
      setStatus('Cloning repository and importing git history...');
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
          onAnalysisComplete(data.result);
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

  return (
    <div style={styles.container}>
      <div style={styles.headerRow}>
        <div>
          <h2 style={styles.heading}>Analyze Repository</h2>
          <p style={styles.description}>
            Clone, parse, and build the architectural graph for any GitHub repo.
          </p>
        </div>
      </div>

      <div style={styles.inputGroup}>
        <input
          type="text"
          placeholder="https://github.com/user/repo"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          style={styles.input}
        />
        <button
          onClick={handleAnalyze}
          disabled={loading || !repoUrl}
          style={{
            ...styles.button,
            ...(loading ? styles.buttonLoading : {})
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

      {jobId && (
        <p style={styles.jobId}>
          Job: <code style={styles.code}>{jobId}</code>
        </p>
      )}

      {status && (
        <div style={status.includes('Error') || status.includes('Failed') ? styles.errorStatus : styles.status}>
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
  inputGroup: {
    display: 'flex',
    gap: '10px',
    marginBottom: '16px',
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
  jobId: {
    padding: '10px 14px',
    background: 'var(--bg-elevated)',
    borderRadius: 'var(--radius-sm)',
    fontSize: '13px',
    color: 'var(--text-secondary)',
    border: '1px solid var(--border)',
  },
  code: {
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-primary)',
  },
  status: {
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
