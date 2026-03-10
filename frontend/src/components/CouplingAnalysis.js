import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { formatFilePath } from '../utils/formatters';

export default function CouplingAnalysis({ repoId }) {
  const [coupling, setCoupling] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadCoupling = async () => {
    setLoading(true);
    try {
      const { data } = await api.getCoupling(repoId);
      setCoupling(data);
    } catch (error) {
      console.error(error);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadCoupling();
  }, [repoId]);

  const getCouplingLevel = (avg) => {
    if (avg >= 5) return { label: 'Critical', color: '#f87171', bg: 'var(--red-dim)', icon: '🔴' };
    if (avg >= 3) return { label: 'High', color: '#fbbf24', bg: 'var(--amber-dim)', icon: '🟡' };
    if (avg >= 1.5) return { label: 'Moderate', color: '#60a5fa', bg: 'var(--blue-dim)', icon: '🔵' };
    return { label: 'Low', color: '#4ade80', bg: 'var(--green-dim)', icon: '🟢' };
  };

  const getCouplingBarWidth = (fanIn, fanOut, maxVal) => {
    const total = fanIn + fanOut;
    return Math.min(100, Math.max(8, (total / maxVal) * 100));
  };

  if (loading) return (
    <div style={s.container}>
      <div style={s.loadingWrap}>
        <div style={s.spinner}></div>
        <p style={s.loadingText}>Analyzing coupling relationships…</p>
      </div>
    </div>
  );

  if (!coupling) return (
    <div style={s.container}>
      <div style={s.emptyWrap}>
        <span style={{ fontSize: '36px', display: 'block', marginBottom: '12px' }}></span>
        <p style={s.emptyTitle}>No Coupling Data</p>
        <p style={s.emptyHint}>Analyze a repository first to view coupling metrics</p>
      </div>
    </div>
  );

  const level = coupling.metrics ? getCouplingLevel(coupling.metrics.avg_coupling) : null;
  const maxCoupling = coupling.high_coupling?.length > 0
    ? Math.max(...coupling.high_coupling.map(item => (item.fan_in || 0) + (item.fan_out || 0)))
    : 1;

  return (
    <div style={s.container}>
      {/* Header */}
      <div style={s.header}>
        <div>
          <h2 style={s.title}>Coupling Analysis</h2>
          <p style={s.subtitle}>Module interdependency and structural health</p>
        </div>
        <button onClick={loadCoupling} style={s.refreshBtn} disabled={loading}>
          ↻ Refresh
        </button>
      </div>

      {/* Bento Metrics Grid */}
      {coupling.metrics && (
        <div style={s.bentoGrid}>
          {/* Health Score — Large Card */}
          <div style={{ ...s.bentoCard, ...s.bentoLarge, background: level.bg, borderColor: `${level.color}22` }}>
            <div style={s.healthHeader}>
              <span style={s.healthIcon}>{level.icon}</span>
              <span style={{ ...s.healthLabel, color: level.color }}>{level.label} Coupling</span>
            </div>
            <div style={{ ...s.healthScore, color: level.color }}>
              {coupling.metrics.avg_coupling?.toFixed(2)}
            </div>
            <div style={s.healthBar}>
              <div style={{
                ...s.healthBarFill,
                width: `${Math.min(100, (coupling.metrics.avg_coupling / 8) * 100)}%`,
                background: `linear-gradient(90deg, ${level.color}88, ${level.color})`
              }}></div>
            </div>
            <p style={s.healthDesc}>average coupling score across all modules</p>
          </div>

          {/* Stat Cards */}
          <div style={s.bentoCard}>
            <div style={s.statIcon}></div>
            <div style={s.statValue}>{coupling.metrics.total_files}</div>
            <div style={s.statLabel}>Total Files</div>
          </div>

          <div style={s.bentoCard}>
            <div style={s.statIcon}></div>
            <div style={s.statValue}>{coupling.metrics.total_dependencies}</div>
            <div style={s.statLabel}>Dependencies</div>
          </div>

          <div style={{ ...s.bentoCard, ...(coupling.cycles && coupling.cycles.length > 0 ? { borderColor: 'rgba(248,113,113,0.2)' } : {}) }}>
            <div style={s.statIcon}>{coupling.cycles && coupling.cycles.length > 0 ? '—' : '—'}</div>
            <div style={{
              ...s.statValue,
              color: coupling.cycles && coupling.cycles.length > 0 ? '#f87171' : '#4ade80'
            }}>
              {coupling.cycles?.length || 0}
            </div>
            <div style={s.statLabel}>Circular Deps</div>
          </div>

          <div style={s.bentoCard}>
            <div style={s.statIcon}></div>
            <div style={s.statValue}>
              {coupling.high_coupling?.length || 0}
            </div>
            <div style={s.statLabel}>Hot Files</div>
          </div>
        </div>
      )}

      {/* High Coupling Files — Visual Bar Chart */}
      {coupling.high_coupling && coupling.high_coupling.length > 0 && (
        <div style={s.section}>
          <div style={s.sectionHeader}>
            <div style={s.sectionTitleRow}>
              <h3 style={s.sectionTitle}>High Coupling Files</h3>
              <span style={s.countBadge}>{coupling.high_coupling.length}</span>
            </div>
            <div style={s.legendRow}>
              <span style={s.legendItem}><span style={{ ...s.legendDot, background: '#4ade80' }}></span> Fan-in</span>
              <span style={s.legendItem}><span style={{ ...s.legendDot, background: '#f87171' }}></span> Fan-out</span>
            </div>
          </div>

          <div style={s.couplingList}>
            {coupling.high_coupling.map((item, idx) => {
              const total = (item.fan_in || 0) + (item.fan_out || 0);
              const barWidth = getCouplingBarWidth(item.fan_in || 0, item.fan_out || 0, maxCoupling);
              const fanInPct = total > 0 ? ((item.fan_in || 0) / total) * 100 : 50;
              const severity = total >= 10 ? 'critical' : total >= 6 ? 'high' : 'moderate';
              const sevColor = severity === 'critical' ? '#f87171' : severity === 'high' ? '#fbbf24' : '#60a5fa';

              return (
                <div key={idx} style={s.couplingRow}>
                  <div style={s.couplingRowTop}>
                    <div style={s.fileInfo}>
                      <span style={{ ...s.fileRank, color: sevColor }}>#{idx + 1}</span>
                      <span style={s.fileName} title={item.file}>{formatFilePath(item.file, 2)}</span>
                    </div>
                    <div style={s.couplingBadges}>
                      <span style={s.badgeIn} title="Fan-in (dependencies on this file)">
                        ↓ {item.fan_in || 0}
                      </span>
                      <span style={s.badgeOut} title="Fan-out (this file depends on)">
                        ↑ {item.fan_out || 0}
                      </span>
                      <span style={{ ...s.totalBadge, color: sevColor, borderColor: `${sevColor}33` }}>
                        Σ {total}
                      </span>
                    </div>
                  </div>
                  <div style={s.barTrack}>
                    <div style={{ ...s.barFill, width: `${barWidth}%` }}>
                      <div style={{
                        ...s.barSegmentIn,
                        width: `${fanInPct}%`,
                      }}></div>
                      <div style={{
                        ...s.barSegmentOut,
                        width: `${100 - fanInPct}%`,
                      }}></div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Circular Dependencies */}
      {coupling.cycles && coupling.cycles.length > 0 && (
        <div style={s.section}>
          <div style={s.sectionHeader}>
            <div style={s.sectionTitleRow}>
              <h3 style={{ ...s.sectionTitle, color: '#f87171' }}>Circular Dependencies</h3>
              <span style={{ ...s.countBadge, background: 'var(--red-dim)', color: '#f87171', borderColor: 'rgba(248,113,113,0.15)' }}>
                {coupling.cycles.length}
              </span>
            </div>
          </div>

          <div style={s.cycleList}>
            {coupling.cycles.map((cycle, idx) => (
              <div key={idx} style={s.cycleCard}>
                <div style={s.cycleNumber}>Cycle {idx + 1}</div>
                <div style={s.cycleChain}>
                  {cycle.map((file, fIdx) => (
                    <React.Fragment key={fIdx}>
                      <span style={s.cycleFile} title={file}>{formatFilePath(file, 1)}</span>
                      {fIdx < cycle.length - 1 && <span style={s.cycleArrow}>→</span>}
                    </React.Fragment>
                  ))}
                  <span style={s.cycleArrow}>↩</span>
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
  // Container
  container: { padding: '28px', background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', marginBottom: '20px' },

  // Loading
  loadingWrap: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '300px' },
  spinner: { width: '36px', height: '36px', border: '3px solid var(--border)', borderTop: '3px solid var(--text-secondary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' },
  loadingText: { marginTop: '16px', color: 'var(--text-muted)', fontSize: '14px' },

  // Empty
  emptyWrap: { textAlign: 'center', padding: '60px 20px' },
  emptyTitle: { fontSize: '16px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' },
  emptyHint: { fontSize: '13px', color: 'var(--text-muted)', margin: 0 },

  // Header
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px', paddingBottom: '16px', borderBottom: '1px solid var(--border)' },
  title: { margin: '0 0 4px', fontSize: '20px', fontWeight: 600, color: 'var(--text-primary)' },
  subtitle: { margin: 0, fontSize: '13px', color: 'var(--text-muted)' },
  refreshBtn: { padding: '8px 16px', background: 'var(--bg-elevated)', color: 'var(--text-secondary)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '13px', fontWeight: 500 },

  // Bento Grid
  bentoGrid: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gridTemplateRows: 'auto auto', gap: '10px', marginBottom: '28px' },
  bentoCard: { padding: '18px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '6px', textAlign: 'center', transition: 'border-color 0.2s' },
  bentoLarge: { gridColumn: '1 / 3', gridRow: '1 / 3', alignItems: 'flex-start', justifyContent: 'flex-start', padding: '24px' },

  // Health card
  healthHeader: { display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' },
  healthIcon: { fontSize: '18px' },
  healthLabel: { fontSize: '13px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px' },
  healthScore: { fontSize: '52px', fontWeight: 800, fontFamily: 'var(--font-mono)', lineHeight: 1, marginBottom: '12px' },
  healthBar: { width: '100%', height: '8px', background: 'var(--bg-card)', borderRadius: '4px', overflow: 'hidden', marginBottom: '10px' },
  healthBarFill: { height: '100%', borderRadius: '4px', transition: 'width 1s ease' },
  healthDesc: { margin: 0, fontSize: '11px', color: 'var(--text-dim)', fontStyle: 'italic' },

  // Stat cards
  statIcon: { fontSize: '20px', marginBottom: '4px' },
  statValue: { fontSize: '26px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', lineHeight: 1 },
  statLabel: { fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1.2px', fontWeight: 600, marginTop: '2px' },

  // Section
  section: { marginBottom: '24px' },
  sectionHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' },
  sectionTitleRow: { display: 'flex', alignItems: 'center', gap: '10px' },
  sectionTitle: { margin: 0, fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)' },
  countBadge: { padding: '2px 10px', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: '10px', fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' },

  // Legend
  legendRow: { display: 'flex', gap: '14px', fontSize: '11px', color: 'var(--text-dim)' },
  legendItem: { display: 'flex', alignItems: 'center', gap: '5px' },
  legendDot: { width: '8px', height: '8px', borderRadius: '50%', display: 'inline-block' },

  // Coupling file rows
  couplingList: { display: 'flex', flexDirection: 'column', gap: '6px' },
  couplingRow: { padding: '14px 16px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', transition: 'border-color 0.2s' },
  couplingRowTop: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' },
  fileInfo: { display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: 0 },
  fileRank: { fontSize: '12px', fontWeight: 700, fontFamily: 'var(--font-mono)', flexShrink: 0, width: '28px' },
  fileName: { color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  couplingBadges: { display: 'flex', gap: '6px', flexShrink: 0 },
  badgeIn: { padding: '3px 10px', background: 'var(--green-dim)', borderRadius: '10px', fontSize: '11px', color: '#4ade80', fontFamily: 'var(--font-mono)', fontWeight: 600, border: '1px solid rgba(74,222,128,0.12)' },
  badgeOut: { padding: '3px 10px', background: 'var(--red-dim)', borderRadius: '10px', fontSize: '11px', color: '#f87171', fontFamily: 'var(--font-mono)', fontWeight: 600, border: '1px solid rgba(248,113,113,0.12)' },
  totalBadge: { padding: '3px 10px', borderRadius: '10px', fontSize: '11px', fontFamily: 'var(--font-mono)', fontWeight: 700, border: '1px solid', background: 'var(--bg-card)' },

  // Bar chart
  barTrack: { height: '6px', background: 'var(--bg-card)', borderRadius: '3px', overflow: 'hidden' },
  barFill: { height: '100%', borderRadius: '3px', display: 'flex', transition: 'width 0.8s ease' },
  barSegmentIn: { height: '100%', background: '#4ade80', borderRadius: '3px 0 0 3px' },
  barSegmentOut: { height: '100%', background: '#f87171', borderRadius: '0 3px 3px 0' },

  // Cycles
  cycleList: { display: 'flex', flexDirection: 'column', gap: '8px' },
  cycleCard: { padding: '14px 16px', background: 'var(--red-dim)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(248,113,113,0.12)' },
  cycleNumber: { fontSize: '10px', fontWeight: 700, color: '#f87171', textTransform: 'uppercase', letterSpacing: '1.5px', marginBottom: '8px', fontFamily: 'var(--font-mono)' },
  cycleChain: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '6px' },
  cycleFile: { padding: '4px 10px', background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', fontWeight: 500 },
  cycleArrow: { color: '#f87171', fontSize: '14px', fontWeight: 700 },
};
