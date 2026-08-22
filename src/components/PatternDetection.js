import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function PatternDetection({ repoId }) {
  const [patterns, setPatterns] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadPatterns = async () => {
    setLoading(true);
    try {
      const { data } = await api.getPatterns(repoId);
      setPatterns(data);
    } catch (error) {
      console.error(error);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadPatterns();
  }, [repoId]);

  if (loading) return <div style={styles.container}><span style={styles.loadingText}>Analyzing architecture patterns…</span></div>;
  if (!patterns) return <div style={styles.container}><span style={styles.loadingText}>No patterns detected yet</span></div>;

  const formatName = (key) => {
    const names = {
        layered: 'Layered (N-tier)',
        mvc: 'Model-View-Controller',
        hexagonal: 'Hexagonal Architecture',
        event_driven: 'Event-Driven',
        pipe_filter: 'Pipe & Filter',
        client_server: 'Client-Server',
        microkernel: 'Microkernel (Plug-in)',
        microservices: 'Microservices'
    };
    return names[key] || key.toUpperCase().replace('_', ' ');
  };

  const renderDetails = (p) => {
    const details = [];
    if (p.layers) details.push({ label: 'Layers', value: p.layers.join(', ') });
    if (p.controllers !== undefined) details.push({ label: 'Controllers', value: p.controllers });
    if (p.models !== undefined) details.push({ label: 'Models', value: p.models });
    if (p.views !== undefined) details.push({ label: 'Views', value: p.views });
    if (p.ports !== undefined) details.push({ label: 'Ports', value: p.ports });
    if (p.adapters !== undefined) details.push({ label: 'Adapters', value: p.adapters });
    if (p.domain !== undefined) details.push({ label: 'Domain', value: p.domain });
    if (p.events !== undefined) details.push({ label: 'Events', value: p.events });
    if (p.publishers !== undefined) details.push({ label: 'Publishers', value: p.publishers });
    if (p.subscribers !== undefined) details.push({ label: 'Subscribers', value: p.subscribers });
    if (p.pipes !== undefined) details.push({ label: 'Pipes', value: p.pipes });
    if (p.filters !== undefined) details.push({ label: 'Filters', value: p.filters });
    if (p.clients !== undefined) details.push({ label: 'Clients', value: p.clients });
    if (p.servers !== undefined) details.push({ label: 'Servers', value: p.servers });
    if (p.core_modules !== undefined) details.push({ label: 'Core Modules', value: p.core_modules });
    if (p.plugins !== undefined) details.push({ label: 'Plugins', value: p.plugins });
    if (p.services !== undefined) details.push({ label: 'Services', value: p.services });
    if (p.gateways !== undefined) details.push({ label: 'Gateways', value: p.gateways || 0 });

    return details.map((d, i) => (
      <div key={i} style={styles.detailItem}>
        <span style={styles.detailLabel}>{d.label}</span>
        <span style={styles.detailValue}>{d.value}</span>
      </div>
    ));
  };

  // Sort so detected patterns show up first
  const sortedPatterns = Object.entries(patterns).sort((a, b) => {
    if (a[1].detected === b[1].detected) return 0;
    return a[1].detected ? -1 : 1;
  });

  return (
    <div style={styles.container}>
      <div style={styles.headerBar}>
        <div style={styles.headerLeft}>
          <div style={styles.headerIcon}>🧩</div>
          <h2 style={styles.heading}>Architecture Patterns</h2>
        </div>
        <button onClick={loadPatterns} style={styles.refreshBtn} disabled={loading}>
          {loading ? 'Refreshing…' : '↻ Refresh'}
        </button>
      </div>

      <div style={styles.grid}>
        {sortedPatterns.map(([key, p]) => (
          <div key={key} style={p.detected ? styles.cardDetected : styles.cardInactive}>
            <div style={styles.cardHeader}>
              <h3 style={p.detected ? styles.cardTitle : styles.cardTitleInactive}>{formatName(key)}</h3>
              {p.detected ? (
                <div style={styles.badgeDetected}>✓ Active</div>
              ) : (
                <div style={styles.badgeInactive}>Not Found</div>
              )}
            </div>

            {p.detected && (
              <div style={styles.cardBody}>
                <div style={styles.confidenceWrapper}>
                  <div style={styles.confidenceHeader}>
                    <span style={styles.confidenceLabel}>Detection Confidence</span>
                    <span style={styles.confidenceValue}>{(p.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div style={styles.progressTrack}>
                    <div style={{ ...styles.progressFill, width: `${p.confidence * 100}%` }}></div>
                  </div>
                </div>

                <div style={styles.detailsGrid}>
                  {renderDetails(p)}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
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
    boxShadow: 'var(--shadow-sm)',
  },
  loadingText: {
    color: 'var(--text-muted)',
    fontSize: '14px',
  },
  headerBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '24px',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  headerIcon: {
    fontSize: '20px',
    background: 'rgba(251, 191, 36, 0.1)',
    padding: '8px',
    borderRadius: '8px',
  },
  heading: {
    margin: 0,
    fontSize: '20px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    letterSpacing: '-0.02em',
  },
  refreshBtn: {
    padding: '8px 16px',
    background: 'var(--bg-elevated)',
    color: 'var(--text-secondary)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 500,
    transition: 'all 0.2s ease',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
    gap: '20px',
  },
  cardDetected: {
    background: 'var(--bg-elevated)',
    border: '1px solid rgba(74, 222, 128, 0.25)',
    borderRadius: '12px',
    padding: '20px',
    boxShadow: '0 4px 20px -4px rgba(74, 222, 128, 0.08)',
    display: 'flex',
    flexDirection: 'column',
    transition: 'transform 0.2s',
  },
  cardInactive: {
    background: 'var(--bg-primary)',
    border: '1px dashed var(--border)',
    borderRadius: '12px',
    padding: '16px 20px',
    opacity: 0.6,
    display: 'flex',
    flexDirection: 'column',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  cardBody: {
    marginTop: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    flex: 1,
  },
  cardTitle: {
    margin: 0,
    fontSize: '16px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    lineHeight: 1.3,
  },
  cardTitleInactive: {
    margin: 0,
    fontSize: '15px',
    fontWeight: 500,
    color: 'var(--text-muted)',
  },
  badgeDetected: {
    background: 'rgba(74, 222, 128, 0.15)',
    color: '#4ade80',
    padding: '4px 10px',
    borderRadius: '20px',
    fontSize: '11px',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  badgeInactive: {
    background: 'var(--bg-card)',
    color: 'var(--text-muted)',
    border: '1px solid var(--border)',
    padding: '3px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: 500,
  },
  confidenceWrapper: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  confidenceHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  confidenceLabel: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
    fontWeight: 500,
  },
  confidenceValue: {
    fontSize: '13px',
    color: '#fbbf24',
    fontWeight: 700,
  },
  progressTrack: {
    height: '6px',
    background: 'var(--bg-primary)',
    borderRadius: '3px',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    background: 'linear-gradient(90deg, #fbbf24, #f59e0b)',
    borderRadius: '3px',
    transition: 'width 0.5s ease-out',
  },
  detailsGrid: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '10px',
    background: 'var(--bg-primary)',
    padding: '12px',
    borderRadius: '8px',
    border: '1px solid var(--border)',
    marginTop: 'auto',
  },
  detailItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    background: 'var(--bg-card)',
    padding: '4px 10px',
    borderRadius: '6px',
    border: '1px solid var(--border-light)',
    fontSize: '12px',
  },
  detailLabel: {
    color: 'var(--text-muted)',
    fontWeight: 500,
  },
  detailValue: {
    color: 'var(--text-primary)',
    fontWeight: 600,
  }
};

