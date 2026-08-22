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
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCoupling();
  }, [repoId]);

  const getCouplingTier = (score) => {
    if (score >= 3.2) return { label: 'Critical', color: '#ef4444', rankBg: 'rgba(239, 68, 68, 0.15)', rankBorder: 'rgba(239, 68, 68, 0.35)', rankText: '#f87171' };
    if (score >= 2.0) return { label: 'Medium', color: '#f59e0b', rankBg: 'rgba(245, 158, 11, 0.15)', rankBorder: 'rgba(245, 158, 11, 0.35)', rankText: '#fbbf24' };
    return { label: 'Good', color: '#22c55e', rankBg: 'rgba(34, 197, 94, 0.15)', rankBorder: 'rgba(34, 197, 94, 0.35)', rankText: '#4ade80' };
  };

  const getOverallLevel = (avg) => {
    if (avg >= 4.0) return { label: 'Critical', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.12)', border: 'rgba(239, 68, 68, 0.3)' };
    if (avg >= 2.5) return { label: 'High', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.12)', border: 'rgba(245, 158, 11, 0.3)' };
    if (avg >= 1.5) return { label: 'Moderate', color: '#2dd4bf', bg: 'rgba(45, 212, 191, 0.12)', border: 'rgba(45, 212, 191, 0.3)' };
    return { label: 'Low', color: '#22c55e', bg: 'rgba(34, 197, 94, 0.12)', border: 'rgba(34, 197, 94, 0.3)' };
  };

  if (loading) {
    return (
      <div style={s.container}>
        <div style={s.loadingWrap}>
          <div style={s.spinner}></div>
          <p style={s.loadingText}>Analyzing module coupling and structural health…</p>
        </div>
      </div>
    );
  }

  if (!coupling || !coupling.metrics) {
    return (
      <div style={s.container}>
        <div style={s.emptyWrap}>
          <span style={{ fontSize: '36px', display: 'block', marginBottom: '12px' }}>🔗</span>
          <p style={s.emptyTitle}>No Coupling Data Available</p>
          <p style={s.emptyHint}>Analyze a repository first to view coupling metrics</p>
        </div>
      </div>
    );
  }

  const { metrics, high_coupling = [], cycles = [] } = coupling;
  const avgCoupling = metrics.avg_coupling || 0;
  const overallTier = getOverallLevel(avgCoupling);

  const maxTotal = high_coupling.length > 0
    ? Math.max(...high_coupling.map(item => (item.fan_in || 0) + (item.fan_out || 0)), 1)
    : 1;

  // Process items with scores and ranking
  const itemsWithScores = high_coupling.map((item, idx) => {
    const fanIn = item.fan_in || 0;
    const fanOut = item.fan_out || 0;
    const total = fanIn + fanOut;

    let scoreVal;
    if (typeof item.score === 'number') {
      scoreVal = item.score;
    } else if (typeof item.coupling_score === 'number') {
      scoreVal = item.coupling_score;
    } else {
      scoreVal = Math.min(4.0, (fanIn * 0.25 + fanOut * 0.75) / Math.max(1, (maxTotal / 3.8)));
      if (scoreVal < 0.75 && total > 0) scoreVal = 0.75 + (fanIn * 0.05);
    }

    const tier = getCouplingTier(scoreVal);
    const barTotalPct = Math.min(100, Math.max(12, (total / maxTotal) * 100));
    const fanInSegmentPct = total > 0 ? (fanIn / total) * 100 : 50;

    return {
      ...item,
      rank: String(idx + 1).padStart(2, '0'),
      fanIn,
      fanOut,
      total,
      score: scoreVal.toFixed(2),
      tier,
      barTotalPct,
      fanInSegmentPct,
    };
  });

  return (
    <div style={s.container}>
      {/* Page Header */}
      <div style={s.header}>
        <div>
          <h1 style={s.title}>Coupling Analysis</h1>
          <p style={s.subtitle}>Module interdependency and structural health</p>
        </div>
        <button onClick={loadCoupling} style={s.refreshBtn} disabled={loading} title="Refresh analysis">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px' }}>
            <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
          </svg>
          Refresh
        </button>
      </div>

      {/* Hero Overview Card */}
      <div style={s.heroCard}>
        {/* Left: Overall Score */}
        <div style={s.heroLeft}>
          <div style={s.kicker}>OVERALL COUPLING SCORE</div>
          <div style={s.scoreRow}>
            <div style={s.bigScore}>{avgCoupling.toFixed(2)}</div>
            <div style={{ ...s.levelPill, color: overallTier.color, background: overallTier.bg, borderColor: overallTier.border }}>
              {overallTier.label}
            </div>
          </div>
          <div style={s.gaugeTrack}>
            <div style={{
              ...s.gaugeFill,
              width: `${Math.min(100, (avgCoupling / 4.5) * 100)}%`,
              background: `linear-gradient(90deg, #22d3ee, ${overallTier.color})`
            }} />
          </div>
          <div style={s.gaugeCaption}>Average coupling score across all modules</div>
        </div>

        {/* Right: 4 Stat KPIs */}
        <div style={s.heroRight}>
          {/* Total Files */}
          <div style={s.kpiItem}>
            <div style={{ ...s.kpiIconWrap, color: '#38bdf8' }}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
              </svg>
            </div>
            <div style={s.kpiValue}>{metrics.total_files ?? 0}</div>
            <div style={s.kpiLabel}>Total Files</div>
          </div>

          {/* Dependencies */}
          <div style={s.kpiItem}>
            <div style={{ ...s.kpiIconWrap, color: '#c084fc' }}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="18" cy="18" r="3"/>
                <circle cx="6" cy="6" r="3"/>
                <circle cx="6" cy="18" r="3"/>
                <path d="M6 9v6M9 6h6M8.5 15.5l7-7"/>
              </svg>
            </div>
            <div style={s.kpiValue}>{metrics.total_dependencies ?? 0}</div>
            <div style={s.kpiLabel}>Dependencies</div>
          </div>

          {/* Circular Deps */}
          <div style={s.kpiItem}>
            <div style={{ ...s.kpiIconWrap, color: cycles.length > 0 ? '#4ade80' : '#4ade80' }}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
              </svg>
            </div>
            <div style={s.kpiValue}>{cycles.length}</div>
            <div style={s.kpiLabel}>Circular Deps</div>
          </div>

          {/* Hot Files */}
          <div style={s.kpiItem}>
            <div style={{ ...s.kpiIconWrap, color: '#fb923c' }}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>
              </svg>
            </div>
            <div style={s.kpiValue}>{high_coupling.length}</div>
            <div style={s.kpiLabel}>Hot Files</div>
          </div>
        </div>
      </div>

      {/* Main Card: High Coupling Files */}
      {itemsWithScores.length > 0 && (
        <div style={s.listCard}>
          {/* Card Header */}
          <div style={s.listHeader}>
            <div style={s.listTitleRow}>
              <h2 style={s.listTitle}>High Coupling Files</h2>
              <span style={s.countBadge}>{itemsWithScores.length}</span>
            </div>

            <div style={s.legendWrap}>
              <div style={s.legendItem}>
                <span style={{ ...s.legendDot, background: '#22c55e' }} />
                <span>Good</span>
              </div>
              <div style={s.legendItem}>
                <span style={{ ...s.legendDot, background: '#f59e0b' }} />
                <span>Medium</span>
              </div>
              <div style={s.legendItem}>
                <span style={{ ...s.legendDot, background: '#ef4444' }} />
                <span>Critical</span>
              </div>
            </div>
          </div>

          {/* Files List */}
          <div style={s.filesContainer}>
            {itemsWithScores.map((item) => (
              <div key={item.rank} style={s.fileRow}>
                {/* 1. Rank Badge */}
                <div style={{
                  ...s.rankBadge,
                  background: item.tier.rankBg,
                  borderColor: item.tier.rankBorder,
                  color: item.tier.rankText,
                }}>
                  {item.rank}
                </div>

                {/* 2. File Path & Proportion Bar */}
                <div style={s.fileCenter}>
                  <div style={s.fileName} title={item.file}>
                    {formatFilePath(item.file, 2)}
                  </div>
                  <div style={s.barTrack}>
                    <div style={{ ...s.barFill, width: `${item.barTotalPct}%` }}>
                      {/* Fan-in segment (Green) */}
                      {item.fanIn > 0 && (
                        <div style={{
                          ...s.barGreenSegment,
                          width: item.fanOut === 0 ? '100%' : `${item.fanInSegmentPct}%`,
                        }} />
                      )}
                      {/* Fan-out segment (Red/Amber) */}
                      {item.fanOut > 0 && (
                        <div style={{
                          ...s.barRedSegment,
                          width: item.fanIn === 0 ? '100%' : `${100 - item.fanInSegmentPct}%`,
                        }} />
                      )}
                    </div>
                  </div>
                </div>

                {/* 3. Fan-in (Inward / Incoming) */}
                <div style={s.metricIn} title="Incoming dependencies (used by)">
                  <span style={s.arrowGreen}>↓</span> {item.fanIn}
                </div>

                {/* 4. Fan-out (Outward / Outgoing) */}
                <div style={s.metricOut} title="Outgoing dependencies (depends on)">
                  <span style={item.fanOut > 0 ? s.arrowRed : s.arrowMuted}>↑</span> {item.fanOut}
                </div>

                {/* 5. Score Pill */}
                <div style={s.scoreBox}>
                  {item.score}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Circular Dependencies Card (If present) */}
      {cycles && cycles.length > 0 && (
        <div style={s.cycleCard}>
          <div style={s.cycleHeader}>
            <h3 style={s.cycleTitle}>Circular Dependencies</h3>
            <span style={s.cycleCountBadge}>{cycles.length} detected</span>
          </div>
          <div style={s.cycleList}>
            {cycles.map((cycle, idx) => (
              <div key={idx} style={s.cycleRow}>
                <span style={s.cycleIndex}>#{idx + 1}</span>
                <div style={s.cycleChain}>
                  {cycle.map((f, i) => (
                    <React.Fragment key={i}>
                      <span style={s.cycleFile}>{formatFilePath(f, 1)}</span>
                      {i < cycle.length - 1 && <span style={s.cycleArrow}>→</span>}
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
  container: {
    padding: '4px 0 32px',
    color: '#f1f5f9',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '24px',
  },
  title: {
    margin: 0,
    fontSize: '24px',
    fontWeight: '700',
    color: '#ffffff',
    letterSpacing: '-0.02em',
  },
  subtitle: {
    margin: '4px 0 0',
    fontSize: '14px',
    color: '#94a3b8',
  },
  refreshBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '8px 16px',
    background: 'rgba(255, 255, 255, 0.04)',
    color: '#94a3b8',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '500',
    transition: 'all 0.2s ease',
  },

  // Hero Card
  heroCard: {
    display: 'flex',
    flexDirection: 'row',
    alignItems: 'center',
    background: 'radial-gradient(ellipse 90% 70% at 20% 30%, rgba(14, 116, 144, 0.12), rgba(15, 23, 42, 0.85) 60%, rgba(8, 14, 26, 0.95))',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '16px',
    padding: '28px 36px',
    marginBottom: '24px',
    gap: '40px',
    backdropFilter: 'blur(16px)',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.36)',
  },
  heroLeft: {
    flex: '0 0 320px',
  },
  kicker: {
    fontSize: '11px',
    fontWeight: '700',
    letterSpacing: '1.5px',
    color: '#38bdf8',
    marginBottom: '10px',
  },
  scoreRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    marginBottom: '14px',
  },
  bigScore: {
    fontSize: '54px',
    fontWeight: '700',
    color: '#ffffff',
    lineHeight: '1',
    letterSpacing: '-0.03em',
  },
  levelPill: {
    display: 'inline-block',
    padding: '4px 14px',
    borderRadius: '9999px',
    fontSize: '12px',
    fontWeight: '600',
    border: '1px solid',
  },
  gaugeTrack: {
    width: '100%',
    height: '6px',
    borderRadius: '9999px',
    background: 'rgba(255, 255, 255, 0.08)',
    overflow: 'hidden',
    marginBottom: '8px',
  },
  gaugeFill: {
    height: '100%',
    borderRadius: '9999px',
    transition: 'width 0.6s ease',
  },
  gaugeCaption: {
    fontSize: '12px',
    color: '#64748b',
  },

  // Hero Right (KPIs)
  heroRight: {
    flex: 1,
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '16px',
    borderLeft: '1px solid rgba(255, 255, 255, 0.07)',
    paddingLeft: '36px',
  },
  kpiItem: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    textAlign: 'center',
  },
  kpiIconWrap: {
    marginBottom: '10px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  kpiValue: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#f8fafc',
    lineHeight: '1.2',
    marginBottom: '4px',
  },
  kpiLabel: {
    fontSize: '12px',
    color: '#64748b',
    fontWeight: '500',
  },

  // Main List Card
  listCard: {
    background: 'rgba(13, 19, 31, 0.85)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '16px',
    padding: '24px 28px',
    backdropFilter: 'blur(12px)',
    boxShadow: '0 8px 24px rgba(0, 0, 0, 0.25)',
  },
  listHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
    paddingBottom: '16px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
  },
  listTitleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  listTitle: {
    margin: 0,
    fontSize: '16px',
    fontWeight: '600',
    color: '#ffffff',
  },
  countBadge: {
    background: 'rgba(30, 58, 77, 0.7)',
    color: '#38bdf8',
    fontSize: '12px',
    fontWeight: '600',
    padding: '2px 9px',
    borderRadius: '12px',
  },
  legendWrap: {
    display: 'flex',
    alignItems: 'center',
    gap: '20px',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '12px',
    color: '#94a3b8',
    fontWeight: '500',
  },
  legendDot: {
    width: '7px',
    height: '7px',
    borderRadius: '50%',
    display: 'inline-block',
  },

  // File Rows
  filesContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  fileRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '6px 4px',
  },
  rankBadge: {
    width: '26px',
    height: '26px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '11px',
    fontWeight: '700',
    border: '1px solid',
    flexShrink: 0,
    fontFamily: "'JetBrains Mono', monospace",
  },
  fileCenter: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    minWidth: 0,
  },
  fileName: {
    fontSize: '13px',
    color: '#e2e8f0',
    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    fontWeight: '500',
  },
  barTrack: {
    width: '100%',
    height: '3.5px',
    borderRadius: '2px',
    background: 'rgba(255, 255, 255, 0.05)',
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    display: 'flex',
    borderRadius: '2px',
    overflow: 'hidden',
  },
  barGreenSegment: {
    height: '100%',
    background: '#22c55e',
  },
  barRedSegment: {
    height: '100%',
    background: '#ef4444',
  },
  metricIn: {
    width: '48px',
    textAlign: 'right',
    fontSize: '13px',
    fontWeight: '600',
    color: '#22c55e',
    fontFamily: "'JetBrains Mono', monospace",
    flexShrink: 0,
  },
  arrowGreen: {
    color: '#22c55e',
    marginRight: '2px',
  },
  metricOut: {
    width: '48px',
    textAlign: 'right',
    fontSize: '13px',
    fontWeight: '600',
    color: '#ef4444',
    fontFamily: "'JetBrains Mono', monospace",
    flexShrink: 0,
  },
  arrowRed: {
    color: '#ef4444',
    marginRight: '2px',
  },
  arrowMuted: {
    color: '#64748b',
    marginRight: '2px',
  },
  scoreBox: {
    background: 'rgba(255, 255, 255, 0.03)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '6px',
    padding: '4px 10px',
    fontSize: '12px',
    fontWeight: '600',
    color: '#cbd5e1',
    minWidth: '52px',
    textAlign: 'center',
    fontFamily: "'JetBrains Mono', monospace",
    flexShrink: 0,
  },

  // Circular dependencies
  cycleCard: {
    marginTop: '20px',
    background: 'rgba(13, 19, 31, 0.85)',
    border: '1px solid rgba(239, 68, 68, 0.2)',
    borderRadius: '16px',
    padding: '20px 24px',
  },
  cycleHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
  },
  cycleTitle: {
    margin: 0,
    fontSize: '15px',
    fontWeight: '600',
    color: '#f87171',
  },
  cycleCountBadge: {
    background: 'rgba(239, 68, 68, 0.15)',
    color: '#f87171',
    fontSize: '11px',
    fontWeight: '600',
    padding: '2px 8px',
    borderRadius: '8px',
  },
  cycleList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  cycleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    background: 'rgba(255, 255, 255, 0.02)',
    padding: '8px 12px',
    borderRadius: '8px',
  },
  cycleIndex: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#f87171',
    fontFamily: "'JetBrains Mono', monospace",
  },
  cycleChain: {
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: '6px',
  },
  cycleFile: {
    fontSize: '12px',
    color: '#e2e8f0',
    fontFamily: "'JetBrains Mono', monospace",
  },
  cycleArrow: {
    color: '#ef4444',
    fontSize: '12px',
  },

  // Loading & Empty
  loadingWrap: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '340px',
  },
  spinner: {
    width: '38px',
    height: '38px',
    border: '3px solid rgba(255, 255, 255, 0.1)',
    borderTop: '3px solid #38bdf8',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  loadingText: {
    marginTop: '16px',
    color: '#94a3b8',
    fontSize: '14px',
  },
  emptyWrap: {
    textAlign: 'center',
    padding: '60px 20px',
  },
  emptyTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#cbd5e1',
    marginBottom: '6px',
  },
  emptyHint: {
    fontSize: '13px',
    color: '#64748b',
    margin: 0,
  },
};
