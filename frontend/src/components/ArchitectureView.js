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
    if (confidence >= 0.8) return { bg: '#dcfce7', text: '#166534', bar: '#22c55e' };
    if (confidence >= 0.6) return { bg: '#fef3c7', text: '#92400e', bar: '#f59e0b' };
    return { bg: '#fee2e2', text: '#991b1b', bar: '#ef4444' };
  };

  const getPatternIcon = (name) => {
    const n = (name || '').toLowerCase();
    if (n.includes('layer')) return '🏗️';
    if (n.includes('mvc')) return '🔀';
    if (n.includes('hexagonal')) return '⬡';
    if (n.includes('event')) return '⚡';
    if (n.includes('modular')) return '📦';
    if (n.includes('monolith')) return '🧱';
    if (n.includes('micro')) return '🔬';
    return '📐';
  };

  const formatMarkdown = (text) => {
    if (!text) return null;
    text = formatEvidenceText(text);
    return text.split('\n').map((line, idx) => {
      line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      line = line.replace(/`(.+?)`/g, '<code style="background:#eef2ff;padding:2px 6px;border-radius:4px;font-size:12px;color:#4338ca;">$1</code>');
      if (line.startsWith('###')) return <h4 key={idx} style={s.h4} dangerouslySetInnerHTML={{ __html: line.replace(/###\s*/, '') }} />;
      if (line.startsWith('##'))  return <h3 key={idx} style={s.h3} dangerouslySetInnerHTML={{ __html: line.replace(/##\s*/, '') }} />;
      if (/^\d+\.\s/.test(line))  return <div key={idx} style={s.listItem} dangerouslySetInnerHTML={{ __html: line }} />;
      if (/^[-*]\s/.test(line))   return <div key={idx} style={s.bulletItem} dangerouslySetInnerHTML={{ __html: line.replace(/^[-*]\s/, '• ') }} />;
      if (line.trim())            return <p key={idx} style={s.paragraph} dangerouslySetInnerHTML={{ __html: line }} />;
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
          <p style={{ color: '#6b7280', marginTop: 15 }}>Generating architecture insights...</p>
        </div>
      </div>
    );
  }

  if (!architecture) return <div style={s.container}><p style={{ color: '#6b7280', textAlign: 'center', padding: 40 }}>No architecture data available</p></div>;
  if (architecture.error) return <div style={s.container}><div style={s.errorBox}>⚠️ {architecture.error}</div></div>;

  const sections = [
    { id: 'overview',  icon: '🏛️', label: 'System Overview',         content: architecture.overview },
    { id: 'modules',   icon: '📦', label: 'Module Responsibilities',  content: architecture.modules },
    { id: 'key_files', icon: '📄', label: 'Key Files',                content: architecture.key_files },
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
          {cached && <span style={s.cacheBadge}>⚡ Cached</span>}
          <button onClick={loadArchitecture} style={s.refreshBtn} disabled={loading}>
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Stats Banner */}
      {stats.total_files > 0 && (
        <div style={s.statsBanner}>
          <div style={s.statCard}>
            <div style={s.statIcon}>📁</div>
            <div style={s.statValue}>{stats.total_files}</div>
            <div style={s.statLabel}>Files</div>
          </div>
          <div style={s.statCard}>
            <div style={s.statIcon}>🔗</div>
            <div style={s.statValue}>{stats.total_dependencies}</div>
            <div style={s.statLabel}>Dependencies</div>
          </div>
          <div style={s.statCard}>
            <div style={s.statIcon}>📊</div>
            <div style={s.statValue}>{stats.avg_coupling || '—'}</div>
            <div style={s.statLabel}>Avg Coupling</div>
          </div>
          <div style={s.statCard}>
            <div style={{...s.statIcon, ...(stats.cycle_count > 0 ? {background:'#fef2f2'} : {})}}>
              {stats.cycle_count > 0 ? '⚠️' : '✅'}
            </div>
            <div style={{...s.statValue, ...(stats.cycle_count > 0 ? {color:'#ef4444'} : {color:'#10b981'})}}>{stats.cycle_count}</div>
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
                <div key={i} style={{...s.patternCard, borderColor: c.bar}}>
                  <div style={s.patternHeader}>
                    <span style={s.patternIcon}>{getPatternIcon(p.name)}</span>
                    <span style={s.patternName}>{p.name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                  </div>
                  <div style={s.patternBarTrack}>
                    <div style={{...s.patternBarFill, width: `${pct}%`, background: c.bar}} />
                  </div>
                  <div style={{...s.patternPct, color: c.text}}>{pct}% confidence</div>
                  {p.layers && p.layers.length > 0 && (
                    <div style={s.layerTags}>
                      {p.layers.map((l, j) => (
                        <span key={j} style={{...s.layerTag, background: c.bg, color: c.text}}>{l}</span>
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
                    <div style={{...s.dirBarFill, width: `${widthPct}%`}} />
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
                <span style={s.evidenceIcon}>📄</span>
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
  container: {
    padding: '24px',
    background: '#fff',
    borderRadius: '12px',
    marginBottom: '20px',
    boxShadow: '0 2px 12px rgba(0,0,0,0.08)'
  },

  // Header
  headerBar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '24px',
    borderBottom: '2px solid #667eea',
    paddingBottom: '16px'
  },
  headerRight: { display: 'flex', alignItems: 'center', gap: '10px' },
  title: { margin: '0 0 4px', fontSize: '26px', fontWeight: 'bold', color: '#1f2937' },
  subtitle: { margin: 0, fontSize: '14px', color: '#6b7280' },
  cacheBadge: { padding: '4px 12px', background: '#d1fae5', color: '#065f46', borderRadius: '12px', fontSize: '12px', fontWeight: 'bold' },
  refreshBtn: { padding: '8px 16px', background: 'linear-gradient(135deg, #667eea, #764ba2)', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontSize: '13px', fontWeight: '600', boxShadow: '0 2px 6px rgba(102,126,234,0.4)' },
  titleSection: { marginBottom: '20px', borderBottom: '2px solid #667eea', paddingBottom: '12px' },

  // Loading
  loadingBox: { textAlign: 'center', padding: '60px 20px' },
  spinner: { width: 40, height: 40, border: '4px solid #e5e7eb', borderTopColor: '#667eea', borderRadius: '50%', margin: '0 auto', animation: 'spin 0.8s linear infinite' },
  errorBox: { padding: '20px', background: '#fee2e2', border: '1px solid #ef4444', borderRadius: '8px', color: '#991b1b', fontSize: '14px' },

  // Stats Banner
  statsBanner: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '14px',
    marginBottom: '24px'
  },
  statCard: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '18px 12px',
    background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
    borderRadius: '12px',
    border: '1px solid #e2e8f0',
    transition: 'transform 0.2s, box-shadow 0.2s'
  },
  statIcon: { fontSize: '22px', marginBottom: '8px', width: '44px', height: '44px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#eef2ff', borderRadius: '10px' },
  statValue: { fontSize: '24px', fontWeight: 'bold', color: '#1f2937', lineHeight: 1 },
  statLabel: { fontSize: '11px', color: '#6b7280', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px', marginTop: '4px' },

  // Section Headers
  sectionHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', marginTop: '8px' },
  sectionTitle: { margin: 0, fontSize: '17px', fontWeight: 'bold', color: '#1f2937' },
  badge: { padding: '3px 10px', background: '#eef2ff', color: '#4338ca', borderRadius: '10px', fontSize: '12px', fontWeight: '600' },

  // Patterns
  patternsSection: { marginBottom: '24px' },
  patternsGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '12px' },
  patternCard: { padding: '16px', background: '#fff', borderRadius: '10px', border: '2px solid #e2e8f0', transition: 'border-color 0.2s' },
  patternHeader: { display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' },
  patternIcon: { fontSize: '20px' },
  patternName: { fontSize: '14px', fontWeight: '600', color: '#1f2937' },
  patternBarTrack: { height: '6px', background: '#f3f4f6', borderRadius: '3px', overflow: 'hidden', marginBottom: '6px' },
  patternBarFill: { height: '100%', borderRadius: '3px', transition: 'width 0.8s ease' },
  patternPct: { fontSize: '12px', fontWeight: '600' },
  layerTags: { display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '8px' },
  layerTag: { padding: '2px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: '500' },

  // Directories
  dirSection: { marginBottom: '24px' },
  dirGrid: { display: 'flex', flexDirection: 'column', gap: '6px' },
  dirRow: { display: 'flex', alignItems: 'center', gap: '10px', padding: '6px 0' },
  dirName: { fontSize: '13px', fontWeight: '500', color: '#374151', width: '140px', flexShrink: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  dirBarTrack: { flex: 1, height: '8px', background: '#f3f4f6', borderRadius: '4px', overflow: 'hidden' },
  dirBarFill: { height: '100%', borderRadius: '4px', background: 'linear-gradient(90deg, #667eea, #764ba2)', transition: 'width 0.6s ease' },
  dirCount: { fontSize: '13px', fontWeight: '600', color: '#4338ca', width: '35px', textAlign: 'right' },

  // LLM Section Tabs
  sectionTabs: { display: 'flex', gap: '6px', marginBottom: '14px' },
  sectionTab: {
    padding: '8px 16px',
    border: '1px solid #e2e8f0',
    background: '#f8fafc',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '500',
    color: '#6b7280',
    transition: 'all 0.2s'
  },
  sectionTabActive: {
    background: 'linear-gradient(135deg, #667eea, #764ba2)',
    color: 'white',
    border: '1px solid transparent',
    boxShadow: '0 2px 8px rgba(102,126,234,0.3)'
  },

  // LLM Card
  llmCard: {
    padding: '20px',
    background: 'linear-gradient(135deg, #fafbff 0%, #f5f3ff 100%)',
    borderRadius: '10px',
    border: '1px solid #e0e7ff',
    marginBottom: '24px'
  },
  llmContent: { lineHeight: '1.8', color: '#1f2937', fontSize: '14px' },

  // Text formatting
  h3: { fontSize: '17px', fontWeight: 'bold', marginTop: '14px', marginBottom: '8px', color: '#1f2937' },
  h4: { fontSize: '15px', fontWeight: 'bold', marginTop: '10px', marginBottom: '6px', color: '#374151' },
  paragraph: { marginBottom: '10px', lineHeight: '1.7' },
  listItem: { marginLeft: '20px', marginBottom: '6px', lineHeight: '1.7', paddingLeft: '4px' },
  bulletItem: { marginLeft: '20px', marginBottom: '5px', lineHeight: '1.7', paddingLeft: '4px' },

  // Evidence
  evidenceSection: { marginBottom: '8px' },
  evidenceGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '10px' },
  evidenceChip: {
    display: 'flex',
    gap: '10px',
    alignItems: 'flex-start',
    padding: '12px',
    background: '#f9fafb',
    borderRadius: '8px',
    border: '1px solid #e5e7eb',
    cursor: 'default'
  },
  evidenceIcon: { fontSize: '18px', flexShrink: 0, marginTop: '2px' },
  evidenceName: { fontSize: '13px', fontWeight: '600', color: '#1f2937', marginBottom: '2px' },
  evidenceReason: { fontSize: '12px', color: '#6b7280', lineHeight: '1.4' }
};
