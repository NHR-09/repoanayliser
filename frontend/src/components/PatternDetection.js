import React, { useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';

const PATTERNS = {
  layered: {
    name: 'Layered (N-tier)',
    description: 'Organizes the system into presentation, business, and data responsibilities.',
    color: '#10b981',
    groups: p => [
      ['Presentation', p.layer_files?.presentation, p.layer_counts?.presentation],
      ['Business', p.layer_files?.business, p.layer_counts?.business],
      ['Data', p.layer_files?.data, p.layer_counts?.data]
    ]
  },
  mvc: {
    name: 'Model-View-Controller',
    description: 'Separates request handling, domain data, and presentation concerns.',
    color: '#8b5cf6',
    groups: p => [
      ['Controllers', p.controller_files, p.controllers],
      ['Models', p.model_files, p.models],
      ['Views', p.view_files, p.views]
    ]
  },
  event_driven: {
    name: 'Event-Driven',
    description: 'Coordinates work through events, publishers, and subscribers.',
    color: '#f59e0b',
    groups: p => [
      ['Events', p.event_files, p.events],
      ['Publishers', p.publisher_files, p.publishers],
      ['Subscribers', p.subscriber_files, p.subscribers]
    ]
  },
  client_server: {
    name: 'Client-Server',
    description: 'Separates API or server providers from network clients.',
    color: '#3b82f6',
    groups: p => [
      ['Clients', p.client_files, p.clients],
      ['Servers', p.server_files, p.servers]
    ]
  },
  microkernel: {
    name: 'Microkernel (Plug-in)',
    description: 'Keeps a stable core that is extended through plug-ins or adapters.',
    color: '#14b8a6',
    groups: p => [
      ['Core modules', p.core_module_files, p.core_modules],
      ['Plug-ins', p.plugin_files, p.plugins]
    ]
  },
  hexagonal: {
    name: 'Hexagonal Architecture',
    description: 'Protects domain logic behind ports and infrastructure adapters.',
    color: '#ec4899',
    groups: p => [
      ['Ports', p.port_files, p.ports],
      ['Adapters', p.adapter_files, p.adapters],
      ['Domain', p.domain_files, p.domain]
    ]
  },
  pipe_filter: {
    name: 'Pipe & Filter',
    description: 'Transforms data through composable processing stages.',
    color: '#06b6d4',
    groups: p => [
      ['Pipes / stages', p.pipe_files, p.pipes],
      ['Filters', p.filter_files, p.filters]
    ]
  },
  microservices: {
    name: 'Microservices',
    description: 'Splits capabilities into service modules with gateway or service-to-service links.',
    color: '#818cf8',
    groups: p => [
      ['Services', p.service_files, p.services],
      ['Gateways', p.gateway_files, p.gateways]
    ]
  }
};

const shortPath = path => {
  const parts = String(path || '').replace(/\\/g, '/').split('/').filter(Boolean);
  return parts.slice(-3).join('/');
};

function ComponentList({ groups, color }) {
  const normalized = groups
    .map(([label, items, count]) => ({ label, items: Array.isArray(items) ? items : [], count: count || 0 }))
    .filter(group => group.count > 0 || group.items.length > 0);
  const total = normalized.reduce((sum, group) => sum + Math.max(group.count, group.items.length), 0);

  if (!normalized.length) return null;

  return (
    <div>
      <div style={styles.metricGrid}>
        {normalized.map(group => (
          <div key={group.label} style={styles.metric}>
            <span style={styles.metricLabel}>{group.label}</span>
            <strong style={{ ...styles.metricCount, color }}>{Math.max(group.count, group.items.length)}</strong>
          </div>
        ))}
      </div>
      <details style={styles.details}>
        <summary style={styles.summary}>Browse {total} detected component{total === 1 ? '' : 's'}</summary>
        <div style={styles.componentPanel}>
          {normalized.map(group => (
            <div key={group.label} style={styles.componentGroup}>
              <div style={styles.componentHeading}>{group.label}</div>
              {group.items.length ? (
                <div style={styles.chipList}>
                  {group.items.map(path => (
                    <span key={path} title={path} style={styles.pathChip}>{shortPath(path)}</span>
                  ))}
                </div>
              ) : (
                <div style={styles.unavailable}>Names are available after re-analyzing this repository.</div>
              )}
            </div>
          ))}
        </div>
      </details>
    </div>
  );
}

export default function PatternDetection({ repoId }) {
  const [patterns, setPatterns] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    api.getPatterns(repoId)
      .then(({ data }) => {
        if (cancelled) return;
        if (data?.error) throw new Error(data.error);
        setPatterns(data || {});
      })
      .catch(err => !cancelled && setError(err.message || 'Failed to load patterns'))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [repoId]);

  const cards = useMemo(() => Object.keys(PATTERNS)
    .map(key => ({ key, meta: PATTERNS[key], result: patterns?.[key] || {} }))
    .sort((a, b) => {
      const confidenceDiff = (b.result.confidence || 0) - (a.result.confidence || 0);
      return confidenceDiff || a.meta.name.localeCompare(b.meta.name);
    }), [patterns]);

  if (loading) return <div style={styles.state}>Analyzing architecture patterns…</div>;
  if (error) return <div style={{ ...styles.state, color: '#f87171' }}>{error}</div>;
  if (!patterns) return <div style={styles.state}>Analyze a repository to detect architecture patterns.</div>;

  const detected = cards.filter(card => card.result.detected);
  const average = detected.length
    ? Math.round(detected.reduce((sum, card) => sum + (card.result.confidence || 0), 0) / detected.length * 100)
    : 0;

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>Architecture Patterns</h2>
          <p style={styles.subtitle}>Ranked by detection confidence. Expand a card to see the files behind each count.</p>
        </div>
        <div style={styles.summaryStats}>
          <div><strong style={styles.summaryNumber}>{detected.length}</strong><span style={styles.summaryLabel}> detected</span></div>
          <div style={styles.divider} />
          <div><strong style={styles.summaryNumber}>{average}%</strong><span style={styles.summaryLabel}> avg. confidence</span></div>
        </div>
      </div>

      <div style={styles.grid}>
        {cards.map(({ key, meta, result }) => {
          const confidence = Math.round((result.confidence || 0) * 100);
          const groups = meta.groups(result);
          return (
            <article key={key} style={{ ...styles.card, ...(result.detected ? {} : styles.inactiveCard) }}>
              <div style={styles.cardHeader}>
                <div style={{ ...styles.icon, color: meta.color, background: `${meta.color}18` }}>◇</div>
                <div style={styles.cardHeading}>
                  <h3 style={styles.cardTitle}>{meta.name}</h3>
                  <p style={styles.description}>{meta.description}</p>
                </div>
                <div style={styles.confidence}>
                  <strong style={{ ...styles.confidenceValue, color: result.detected ? meta.color : '#64748b' }}>{confidence}%</strong>
                  <span style={styles.confidenceLabel}>confidence</span>
                </div>
              </div>

              {result.detected ? (
                <ComponentList groups={groups} color={meta.color} />
              ) : (
                <div style={styles.notDetected}>Not enough structural evidence was found for this pattern.</div>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}

const styles = {
  page: { padding: '4px 0 32px' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: '24px', marginBottom: '22px' },
  title: { margin: 0, color: 'var(--text-primary)', fontSize: '22px' },
  subtitle: { margin: '6px 0 0', color: 'var(--text-muted)', fontSize: '13px' },
  summaryStats: { display: 'flex', alignItems: 'center', gap: '18px', padding: '12px 16px', border: '1px solid var(--border)', borderRadius: '12px', background: 'var(--bg-card)', whiteSpace: 'nowrap' },
  summaryNumber: { color: 'var(--text-primary)', fontSize: '17px' },
  summaryLabel: { color: 'var(--text-muted)', fontSize: '12px' },
  divider: { width: '1px', height: '24px', background: 'var(--border)' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(390px, 1fr))', gap: '18px', alignItems: 'start' },
  card: { padding: '20px', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '14px', minWidth: 0 },
  inactiveCard: { opacity: 0.66, background: 'var(--bg-primary)' },
  cardHeader: { display: 'flex', alignItems: 'flex-start', gap: '12px' },
  icon: { width: '38px', height: '38px', borderRadius: '11px', display: 'grid', placeItems: 'center', flexShrink: 0, fontSize: '21px' },
  cardHeading: { flex: 1, minWidth: 0 },
  cardTitle: { margin: '1px 0 5px', fontSize: '16px', color: 'var(--text-primary)' },
  description: { margin: 0, color: 'var(--text-muted)', fontSize: '12.5px', lineHeight: 1.5 },
  confidence: { display: 'flex', flexDirection: 'column', alignItems: 'flex-end', flexShrink: 0 },
  confidenceValue: { fontSize: '20px', fontFamily: 'var(--font-mono)' },
  confidenceLabel: { color: 'var(--text-dim)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.06em' },
  metricGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(112px, 1fr))', gap: '8px', marginTop: '18px' },
  metric: { display: 'flex', justifyContent: 'space-between', gap: '8px', padding: '9px 11px', border: '1px solid var(--border)', borderRadius: '9px', background: 'var(--bg-elevated)' },
  metricLabel: { color: 'var(--text-secondary)', fontSize: '12px' },
  metricCount: { fontFamily: 'var(--font-mono)', fontSize: '13px' },
  details: { marginTop: '10px', borderTop: '1px solid var(--border)', paddingTop: '10px' },
  summary: { cursor: 'pointer', color: 'var(--text-secondary)', fontSize: '12px', userSelect: 'none' },
  componentPanel: { maxHeight: '260px', overflowY: 'auto', marginTop: '12px', padding: '12px', background: 'var(--bg-primary)', borderRadius: '10px' },
  componentGroup: { marginBottom: '12px' },
  componentHeading: { marginBottom: '7px', color: 'var(--text-muted)', fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' },
  chipList: { display: 'flex', flexWrap: 'wrap', gap: '6px' },
  pathChip: { maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', padding: '5px 8px', border: '1px solid var(--border)', borderRadius: '7px', background: 'var(--bg-elevated)', color: 'var(--text-secondary)', fontSize: '11px', fontFamily: 'var(--font-mono)' },
  unavailable: { color: 'var(--text-dim)', fontSize: '11px', fontStyle: 'italic' },
  notDetected: { marginTop: '20px', padding: '12px', color: 'var(--text-dim)', fontSize: '12px', borderTop: '1px solid var(--border)' },
  state: { minHeight: '360px', display: 'grid', placeItems: 'center', color: 'var(--text-muted)', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '14px' }
};
