import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function CouplingAnalysis() {
  const [coupling, setCoupling] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadCoupling = async () => {
    setLoading(true);
    try {
      const { data } = await api.getCoupling();
      setCoupling(data);
    } catch (error) {
      console.error(error);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadCoupling();
  }, []);

  if (loading) return <div style={styles.container}>Loading coupling analysis...</div>;
  if (!coupling) return <div style={styles.container}>No coupling data available</div>;

  return (
    <div style={styles.container}>
      <h2>Coupling Analysis</h2>
      
      {coupling.metrics && (
        <div style={styles.metrics}>
          <h3>Metrics</h3>
          <p>Total Files: {coupling.metrics.total_files}</p>
          <p>Average Coupling: {coupling.metrics.avg_coupling?.toFixed(2)}</p>
        </div>
      )}

      {coupling.high_coupling && coupling.high_coupling.length > 0 && (
        <div style={styles.section}>
          <h3>High Coupling Files</h3>
          {coupling.high_coupling.map((item, idx) => (
            <div key={idx} style={styles.item}>
              <strong>{item.file}</strong>
              <span style={styles.metric}>Fan-in: {item.fan_in} | Fan-out: {item.fan_out}</span>
            </div>
          ))}
        </div>
      )}

      {coupling.cycles && coupling.cycles.length > 0 && (
        <div style={styles.section}>
          <h3>Circular Dependencies</h3>
          {coupling.cycles.map((cycle, idx) => (
            <div key={idx} style={styles.cycle}>
              {cycle.join(' → ')}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const styles = {
  container: { padding: '20px', background: '#fff', borderRadius: '8px', marginBottom: '20px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' },
  metrics: { marginBottom: '20px', padding: '15px', background: '#e3f2fd', borderRadius: '6px' },
  section: { marginBottom: '20px' },
  item: { padding: '10px', background: '#fff3cd', borderRadius: '4px', marginBottom: '8px', display: 'flex', justifyContent: 'space-between' },
  metric: { color: '#856404' },
  cycle: { padding: '10px', background: '#f8d7da', borderRadius: '4px', marginBottom: '8px', color: '#721c24' }
};
