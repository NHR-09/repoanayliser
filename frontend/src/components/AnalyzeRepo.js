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
      <h2>Analyze Repository</h2>
      <p style={styles.description}>
        Analyzes repository structure, imports git commit history, and tracks file versions.
      </p>
      <input
        type="text"
        placeholder="Enter GitHub repository URL (e.g., https://github.com/user/repo)"
        value={repoUrl}
        onChange={(e) => setRepoUrl(e.target.value)}
        style={styles.input}
      />
      <button onClick={handleAnalyze} disabled={loading} style={styles.button}>
        {loading ? 'Analyzing...' : 'Analyze'}
      </button>
      {jobId && <p style={styles.jobId}>Job ID: <code>{jobId}</code></p>}
      {status && (
        <div style={status.includes('Error') || status.includes('Failed') ? styles.errorStatus : styles.status}>
          {status}
        </div>
      )}
    </div>
  );
}

const styles = {
  container: { padding: '20px', background: 'white', borderRadius: '8px', marginBottom: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' },
  description: { color: '#666', fontSize: '14px', marginBottom: '15px' },
  input: { width: '100%', padding: '12px', marginBottom: '10px', fontSize: '14px', borderRadius: '6px', border: '1px solid #ddd', boxSizing: 'border-box' },
  button: { padding: '12px 24px', background: '#667eea', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px', fontWeight: 'bold' },
  jobId: { marginTop: '15px', padding: '10px', background: '#f9fafb', borderRadius: '4px', fontSize: '13px' },
  status: { marginTop: '10px', padding: '12px', background: '#dbeafe', color: '#1e40af', borderRadius: '6px', fontSize: '14px' },
  errorStatus: { marginTop: '10px', padding: '12px', background: '#fee2e2', color: '#991b1b', borderRadius: '6px', fontSize: '14px' }
};
