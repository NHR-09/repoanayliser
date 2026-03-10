import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { formatFilePath, formatEvidenceText } from '../utils/formatters';

export default function ArchitectureView({ repoId }) {
  const [architecture, setArchitecture] = useState(null);
  const [loading, setLoading] = useState(false);
  const [cached, setCached] = useState(false);
  const [expandedSection, setExpandedSection] = useState('overview');

  const loadArchitecture = async () => {
    setLoading(true);
    setCached(false);
    try {
      const { data } = await api.getArchitecture(repoId);
      setArchitecture(data);
      if (data.cached) setCached(true);
    } catch (error) {
      console.error(error);
      setArchitecture({ error: 'Failed to load architecture explanation' });
    }
    setLoading(false);
  };

  useEffect(() => { loadArchitecture(); }, [repoId]);

  const stats = architecture?.stats || {};
  const patterns = stats.detected_patterns || [];
  const topDirs = stats.top_directories || [];

  // — Helpers —

  const getPatternColor = (confidence) => {
    if (confidence >= 0.8) return { bg: 'var(--green-dim)', text: '#4ade80', bar: '#4ade80' };
    if (confidence >= 0.6) return { bg: 'var(--amber-dim)', text: '#fbbf24', bar: '#fbbf24' };
    return { bg: 'var(--red-dim)', text: '#f87171', bar: '#f87171' };
  };

  const getPatternIcon = (name) => {
    const n = (name || '').toLowerCase();
    if (n.includes('layer')) return '—';
    if (n.includes('mvc')) return '—';
    if (n.includes('hexagonal')) return '—';
    if (n.includes('event')) return '—';
    if (n.includes('modular')) return '—';
    if (n.includes('monolith')) return '—';
    if (n.includes('micro')) return '—';
    return '—';
  };

  const formatMarkdown = (text) => {
    if (!text) return null;
    text = formatEvidenceText(text);
    return text.split('\n').map((line, idx) => {
      line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      line = line.replace(/`(.+?)`/g, '<code style="background:var(--bg-elevated);padding:2px 6px;border-radius:4px;font-size:12px;color:var(--text-primary);font-family:var(--font-mono)">$1</code>');
      if (line.startsWith('###')) return <h4 key={idx} style={s.h4} dangerouslySetInnerHTML={{ __html: line.replace(/###\s*/, '') }} />;
      if (line.startsWith('##')) return <h3 key={idx} style={s.h3} dangerouslySetInnerHTML={{ __html: line.replace(/##\s*/, '') }} />;
      if (/^\d+\.\s/.test(line)) return <div key={idx} style={s.listItem} dangerouslySetInnerHTML={{ __html: line }} />;
      if (/^[-*]\s/.test(line)) return <div key={idx} style={s.bulletItem} dangerouslySetInnerHTML={{ __html: line.replace(/^[-*]\s/, '• ') }} />;
      if (line.trim()) return <p key={idx} style={s.paragraph} dangerouslySetInnerHTML={{ __html: line }} />;
      return null;
    });
  };

  // — Loading / Error / Empty —

  if (loading) {
    return (
      <div style={s.container}>
        <div style={s.titleSection}>
          <h2 style={s.title}>Architecture Report</h2>
          <p style={s.subtitle}>Analyzing repository structure...</p>
        </div>
        <div style={s.loadingBox}>
          <div style={s.spinner} />
          <p style={{ color: 'var(--text-muted)', marginTop: 15 }}>Generating architecture insights…</p>
        </div>
      </div>
    );
  }

  if (!architecture) return <div style={s.container}><p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>No architecture data available</p></div>;
  if (architecture.error) return <div style={s.container}><div style={s.errorBox}>{architecture.error}</div></div>;

  const sections = [
    { id: 'overview', icon: '', label: 'System Overview', content: architecture.overview },
    { id: 'modules', icon: '', label: 'Module Responsibilities', content: architecture.modules },
    { id: 'key_files', icon: '', label: 'Key Files', content: architecture.key_files },
  ];

  return (
    <div style={s.container}>
      {/* Header */}
      <div style={s.headerBar}>
        <div>
          <h2 style={s.title}>Architecture Report</h2>
          <p style={s.subtitle}>Structural analysis and LLM-powered insights</p>
        </div>
        <div style={s.headerRight}>
          {cached && <span style={s.cacheBadge}>Cached</span>}
          <button onClick={loadArchitecture} style={s.refreshBtn} disabled={loading}>
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Banner */}
      {stats.total_files > 0 && (
        <div style={s.statsBanner}>
          <div style={s.statCard}>
            <div style={s.statIcon}></div>
            <div style={s.statValue}>{stats.total_files}</div>
            <div style={s.statLabel}>Files</div>
          </div>
          <div style={s.statCard}>
            <div style={s.statIcon}></div>
            <div style={s.statValue}>{stats.total_dependencies}</div>
            <div style={s.statLabel}>Dependencies</div>
          </div>
          <div style={s.statCard}>
            <div style={s.statIcon}></div>
            <div style={s.statValue}>{stats.avg_coupling || '—'}</div>
            <div style={s.statLabel}>Avg Coupling</div>
          </div>
          <div style={s.statCard}>
            <div style={{ ...s.statIcon, ...(stats.cycle_count > 0 ? { background: 'var(--red-dim)' } : {}) }}>
              {stats.cycle_count > 0 ? '—' : '—'}
            </div>
            <div style={{ ...s.statValue, ...(stats.cycle_count > 0 ? { color: '#f87171' } : { color: '#4ade80' }) }}>{stats.cycle_count}</div>
            <div style={s.statLabel}>Cycles</div>
          </div>
        </div>
      )}

      {/* Detected Patterns */}
      {patterns.length > 0 && (
        <div style={s.patternsSection}>
          <div style={s.sectionHeader}>
            <h3 style={s.sectionTitle}>Detected Patterns</h3>
            <span style={s.badge}>{patterns.length} found</span>
          </div>
          <div style={s.patternsGrid}>
            {patterns.map((p, i) => {
              const c = getPatternColor(p.confidence);
              const pct = Math.round(p.confidence * 100);
              return (
                <div key={i} style={{ ...s.patternCard, borderColor: c.bar }}>
                  <div style={s.patternHeader}>
                    <span style={s.patternIcon}>{getPatternIcon(p.name)}</span>
                    <span style={s.patternName}>{p.name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                  </div>
                  <div style={s.patternBarTrack}>
                    <div style={{ ...s.patternBarFill, width: `${pct}%`, background: c.bar }} />
                  </div>
                  <div style={{ ...s.patternPct, color: c.text }}>{pct}% confidence</div>
                  {p.layers && p.layers.length > 0 && (
                    <div style={s.layerTags}>
                      {p.layers.map((l, j) => (
                        <span key={j} style={{ ...s.layerTag, background: c.bg, color: c.text }}>{l}</span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Top Directories */}
      {topDirs.length > 0 && (
        <div style={s.dirSection}>
          <div style={s.sectionHeader}>
            <h3 style={s.sectionTitle}>Directory Breakdown</h3>
          </div>
          <div style={s.dirGrid}>
            {topDirs.map((d, i) => {
              const maxCount = topDirs[0]?.count || 1;
              const widthPct = Math.max(8, Math.round((d.count / maxCount) * 100));
              return (
                <div key={i} style={s.dirRow}>
                  <span style={s.dirName}>📂 {d.name}/</span>
                  <div style={s.dirBarTrack}>
                    <div style={{ ...s.dirBarFill, width: `${widthPct}%` }} />
                  </div>
                  <span style={s.dirCount}>{d.count}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* LLM Sections */}
      <div style={s.sectionHeader}>
        <h3 style={s.sectionTitle}>AI Analysis</h3>
        <span style={s.badge}>Powered by LLM</span>
      </div>

      <div style={s.sectionTabs}>
        {sections.map(sec => (
          <button
            key={sec.id}
            onClick={() => setExpandedSection(sec.id)}
            style={{
              ...s.sectionTab,
              ...(expandedSection === sec.id ? s.sectionTabActive : {})
            }}
          >
            {sec.icon} {sec.label}
          </button>
        ))}
      </div>

      {sections.map(sec => expandedSection === sec.id && sec.content && (
        <div key={sec.id} style={s.llmCard}>
          <div style={s.llmContent}>
            {formatMarkdown(sec.content)}
          </div>
        </div>
      ))}

      {/* Evidence */}
      {architecture.evidence && architecture.evidence.length > 0 && (
        <div style={s.evidenceSection}>
          <div style={s.sectionHeader}>
            <h3 style={s.sectionTitle}>Evidence Sources</h3>
            <span style={s.badge}>{architecture.evidence.length} files</span>
          </div>
          <div style={s.evidenceGrid}>
            {architecture.evidence.map((item, idx) => (
              <div key={idx} style={s.evidenceChip} title={item.file || item.source}>
                <span style={s.evidenceIcon}></span>
                <div>
                  <div style={s.evidenceName}>
                    {formatFilePath(item.file || item.source, 2)}
                  </div>
                  <div style={s.evidenceReason}>
                    {(formatEvidenceText(item.reason || item.content) || '').slice(0, 100)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const s = {
  container: { padding: '28px', background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', marginBottom: '20px' },
  headerBar: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px', borderBottom: '1px solid var(--border)', paddingBottom: '16px' },
  headerRight: { display: 'flex', alignItems: 'center', gap: '10px' },
  title: { margin: '0 0 4px', fontSize: '20px', fontWeight: 600, color: 'var(--text-primary)' },
  subtitle: { margin: 0, fontSize: '13px', color: 'var(--text-muted)' },
  cacheBadge: { padding: '4px 12px', background: 'var(--green-dim)', color: 'var(--green)', borderRadius: '12px', fontSize: '11px', fontWeight: 600 },
  refreshBtn: { padding: '8px 16px', background: 'var(--bg-elevated)', color: 'var(--text-secondary)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '13px', fontWeight: 500 },
  titleSection: { marginBottom: '20px', borderBottom: '1px solid var(--border)', paddingBottom: '12px' },
  loadingBox: { textAlign: 'center', padding: '60px 20px' },
  spinner: { width: 36, height: 36, border: '3px solid var(--border)', borderTopColor: 'var(--text-secondary)', borderRadius: '50%', margin: '0 auto', animation: 'spin 0.8s linear infinite' },
  errorBox: { padding: '16px', background: 'var(--red-dim)', border: '1px solid rgba(248,113,113,0.15)', borderRadius: 'var(--radius-md)', color: 'var(--red)', fontSize: '13px' },
  statsBanner: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '24px' },
  statCard: { display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '16px 12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', transition: 'transform 0.2s' },
  statIcon: { fontSize: '20px', marginBottom: '8px', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' },
  statValue: { fontSize: '22px', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1, fontFamily: 'var(--font-mono)' },
  statLabel: { fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', marginTop: '4px' },
  sectionHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', marginTop: '8px' },
  sectionTitle: { margin: 0, fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' },
  badge: { padding: '3px 10px', background: 'var(--bg-elevated)', color: 'var(--text-muted)', borderRadius: '10px', fontSize: '11px', fontWeight: 600, border: '1px solid var(--border)', fontFamily: 'var(--font-mono)' },
  patternsSection: { marginBottom: '24px' },
  patternsGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '10px' },
  patternCard: { padding: '14px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', transition: 'border-color 0.2s' },
  patternHeader: { display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' },
  patternIcon: { fontSize: '18px' },
  patternName: { fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' },
  patternBarTrack: { height: '4px', background: 'var(--bg-card)', borderRadius: '2px', overflow: 'hidden', marginBottom: '6px' },
  patternBarFill: { height: '100%', borderRadius: '2px', transition: 'width 0.8s ease' },
  patternPct: { fontSize: '11px', fontWeight: 600 },
  layerTags: { display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '8px' },
  layerTag: { padding: '2px 8px', borderRadius: '6px', fontSize: '10px', fontWeight: 500 },
  dirSection: { marginBottom: '24px' },
  dirGrid: { display: 'flex', flexDirection: 'column', gap: '4px' },
  dirRow: { display: 'flex', alignItems: 'center', gap: '10px', padding: '6px 0' },
  dirName: { fontSize: '12px', fontWeight: 500, color: 'var(--text-secondary)', width: '140px', flexShrink: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'var(--font-mono)' },
  dirBarTrack: { flex: 1, height: '6px', background: 'var(--bg-primary)', borderRadius: '3px', overflow: 'hidden' },
  dirBarFill: { height: '100%', borderRadius: '3px', background: 'linear-gradient(90deg, var(--text-muted), var(--text-secondary))', transition: 'width 0.6s ease' },
  dirCount: { fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', width: '30px', textAlign: 'right', fontFamily: 'var(--font-mono)' },
  sectionTabs: { display: 'flex', gap: '4px', marginBottom: '14px' },
  sectionTab: { padding: '8px 14px', border: '1px solid var(--border)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '13px', fontWeight: 500, color: 'var(--text-muted)', transition: 'all 0.2s' },
  sectionTabActive: { background: 'var(--text-primary)', color: 'var(--bg-primary)', border: '1px solid var(--text-primary)' },
  llmCard: { padding: '20px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', marginBottom: '24px' },
  llmContent: { lineHeight: '1.8', color: 'var(--text-secondary)', fontSize: '13px' },
  h3: { fontSize: '16px', fontWeight: 600, marginTop: '14px', marginBottom: '8px', color: 'var(--text-primary)' },
  h4: { fontSize: '14px', fontWeight: 600, marginTop: '10px', marginBottom: '6px', color: 'var(--text-secondary)' },
  paragraph: { marginBottom: '8px', lineHeight: '1.7' },
  listItem: { marginLeft: '16px', marginBottom: '5px', lineHeight: '1.7', paddingLeft: '4px' },
  bulletItem: { marginLeft: '16px', marginBottom: '4px', lineHeight: '1.7', paddingLeft: '4px' },
  evidenceSection: { marginBottom: '8px' },
  evidenceGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '8px' },
  evidenceChip: { display: 'flex', gap: '10px', alignItems: 'flex-start', padding: '12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', cursor: 'default' },
  evidenceIcon: { fontSize: '16px', flexShrink: 0, marginTop: '2px' },
  evidenceName: { fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '2px', fontFamily: 'var(--font-mono)' },
  evidenceReason: { fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1.4' },
};
