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
    try {
      const { data } = await api.analyzeRepo(repoUrl);
      setJobId(data.job_id);
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
          onAnalysisComplete();
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
      <input
        type="text"
        placeholder="Enter GitHub repository URL"
        value={repoUrl}
        onChange={(e) => setRepoUrl(e.target.value)}
        style={styles.input}
      />
      <button onClick={handleAnalyze} disabled={loading} style={styles.button}>
        {loading ? 'Analyzing...' : 'Analyze'}
      </button>
      {jobId && <p>Job ID: {jobId}</p>}
      {status && <p>Status: {status}</p>}
    </div>
  );
}

const styles = {
  container: { padding: '20px', background: '#f5f5f5', borderRadius: '8px', marginBottom: '20px' },
  input: { width: '100%', padding: '10px', marginBottom: '10px', fontSize: '14px', borderRadius: '4px', border: '1px solid #ddd' },
  button: { padding: '10px 20px', background: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }
};
