import React, { useState, useEffect } from 'react';
import { getConfidenceReport } from '../services/api';

const ConfidenceReport = ({ repoId }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedClaim, setExpandedClaim] = useState(null);

  useEffect(() => { if (repoId) fetchReport(); }, [repoId]);

  const fetchReport = async () => {
    setLoading(true); setError(null);
    try { const data = await getConfidenceReport(repoId); setReport(data); }
    catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  const getConfidenceColor = (c) => c >= 0.8 ? '#4ade80' : c >= 0.6 ? '#fbbf24' : '#f87171';
  const getConfidenceLabel = (c) => c >= 0.8 ? 'High' : c >= 0.6 ? 'Medium' : 'Low';
  const getConfidenceEmoji = (c) => c >= 0.8 ? 'HIGH' : c >= 0.6 ? 'MED' : 'LOW';
  const getClaimIcon = (claim) => {
    const c = claim.toLowerCase();
    if (c.includes('layered')) return '—';
    if (c.includes('mvc')) return '—';
    if (c.includes('hexagonal')) return '—';
    if (c.includes('event')) return '—';
    if (c.includes('coupling')) return '—';
    if (c.includes('circular')) return '—';
    return '—';
  };

  const ConfidenceRing = ({ value, size = 80, strokeWidth = 6 }) => {
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (value * circumference);
    const color = getConfidenceColor(value);
    const pct = Math.round(value * 100);
    return (
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--border)" strokeWidth={strokeWidth} />
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={color} strokeWidth={strokeWidth}
          strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.8s ease' }} />
        <text x={size / 2} y={size / 2} textAnchor="middle" dominantBaseline="central"
          style={{ transform: 'rotate(90deg)', transformOrigin: 'center', fontSize: size > 60 ? '18px' : '13px', fontWeight: 'bold', fill: color, fontFamily: 'var(--font-mono)' }}>
          {pct}%
        </text>
      </svg>
    );
  };

  const ConfidenceBar = ({ value }) => {
    const pct = Math.round(value * 100);
    const color = getConfidenceColor(value);
    return (
      <div style={s.barTrack}>
        <div style={{ ...s.barFill, width: `${pct}%`, background: color }} />
      </div>
    );
  };

  if (loading) return (
    <div style={s.container}>
      <div style={s.titleSection}><h2 style={s.title}>Confidence & Limitations</h2><p style={s.subtitle}>How reliable is our analysis?</p></div>
      <div style={s.loadingBox}><div style={s.spinner} /><p style={{ color: 'var(--text-muted)', marginTop: 15 }}>Evaluating analysis reliability…</p></div>
    </div>
  );

  if (error) return (
    <div style={s.container}>
      <div style={s.titleSection}><h2 style={s.title}>Confidence & Limitations</h2></div>
      <div style={s.errorBox}><strong>Error:</strong> {error}</div>
    </div>
  );

  if (!report || !report.claims || report.claims.length === 0) return (
    <div style={s.container}>
      <div style={s.titleSection}><h2 style={s.title}>Confidence & Limitations</h2><p style={s.subtitle}>How reliable is our analysis?</p></div>
      <div style={s.emptyBox}>
        <div style={{ fontSize: 40, marginBottom: 12 }}>◉</div>
        <h3 style={{ margin: '0 0 8px', color: 'var(--text-secondary)' }}>No analysis data yet</h3>
        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: 13 }}>Analyze a repository first to see confidence results.</p>
      </div>
    </div>
  );

  const avgConfidence = report.claims.reduce((sum, c) => sum + c.confidence, 0) / report.claims.length;
  const highCount = report.claims.filter(c => c.confidence >= 0.8).length;
  const medCount = report.claims.filter(c => c.confidence >= 0.6 && c.confidence < 0.8).length;
  const lowCount = report.claims.filter(c => c.confidence < 0.6).length;

  return (
    <div style={s.container}>
      <div style={s.titleSection}><h2 style={s.title}>Confidence & Limitations</h2>
        <p style={s.subtitle}>How reliable is our architectural analysis? Each claim is scored based on evidence strength.</p>
      </div>

      <div style={s.summaryBanner}>
        <div style={s.summaryLeft}>
          <ConfidenceRing value={avgConfidence} size={100} strokeWidth={8} />
          <div style={s.summaryText}>
            <div style={s.summaryLabel}>Overall Confidence</div>
            <div style={{ ...s.summaryValue, color: getConfidenceColor(avgConfidence) }}>{getConfidenceLabel(avgConfidence)}</div>
            <div style={s.summaryDesc}>{report.summary || `Based on ${report.claims.length} architectural claims`}</div>
          </div>
        </div>
        <div style={s.summaryStats}>
          <div style={s.statChip}><span style={{ ...s.statDot, background: '#4ade80' }} /><span style={s.statCount}>{highCount}</span><span style={s.statLabel}>High</span></div>
          <div style={s.statChip}><span style={{ ...s.statDot, background: '#fbbf24' }} /><span style={s.statCount}>{medCount}</span><span style={s.statLabel}>Med</span></div>
          <div style={s.statChip}><span style={{ ...s.statDot, background: '#f87171' }} /><span style={s.statCount}>{lowCount}</span><span style={s.statLabel}>Low</span></div>
        </div>
      </div>

      <div style={s.explainerBox}>
        <div style={s.explainerIcon}></div>
        <div>
          <strong style={{ color: 'var(--blue)' }}>What does this mean?</strong>
          <p style={s.explainerText}>
            ARCHITECH makes claims about your codebase's architecture. Each claim is scored on evidence strength. We also show when our analysis might be wrong.
          </p>
        </div>
      </div>

      <div style={s.claimsHeader}>
        <h3 style={s.claimsTitle}>Architectural Claims</h3>
        <span style={s.claimsCount}>{report.claims.length} claims</span>
      </div>

      <div style={s.claimsList}>
        {report.claims.map((claim, index) => {
          const isExpanded = expandedClaim === index;
          const color = getConfidenceColor(claim.confidence);
          return (
            <div key={index} style={{ ...s.claimCard, borderLeftColor: color, ...(isExpanded ? { boxShadow: '0 4px 20px rgba(0,0,0,0.3)' } : {}) }}
              onClick={() => setExpandedClaim(isExpanded ? null : index)}>
              <div style={s.claimRow}>
                <div style={s.claimLeft}>
                  <span style={s.claimIcon}>{getClaimIcon(claim.claim)}</span>
                  <div>
                    <div style={s.claimName}>{claim.claim}</div>
                    <div style={s.claimMeta}>{getConfidenceEmoji(claim.confidence)} {getConfidenceLabel(claim.confidence)} confidence</div>
                  </div>
                </div>
                <div style={s.claimRight}>
                  <ConfidenceRing value={claim.confidence} size={48} strokeWidth={4} />
                  <span style={{ ...s.expandArrow, transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>▾</span>
                </div>
              </div>
              <ConfidenceBar value={claim.confidence} />
              {isExpanded && (
                <div style={s.claimDetails}>
                  <div style={s.detailSection}>
                    <div style={s.detailLabel}>🧠 Why We Think This</div>
                    <p style={s.detailText}>{claim.reasoning || claim.explanation || 'Pattern detected via structural analysis'}</p>
                  </div>
                  <div style={{ ...s.detailSection, ...s.warningSection }}>
                    <div style={s.detailLabel}>When This Could Be Wrong</div>
                    <p style={s.detailText}>{claim.failure_scenario || 'No specific failure scenario identified'}</p>
                  </div>
                  {claim.evidence && claim.evidence.length > 0 && (
                    <div style={s.detailSection}>
                      <div style={s.detailLabel}>Evidence ({claim.evidence.length} files)</div>
                      <div style={s.evidenceGrid}>
                        {claim.evidence.slice(0, 6).map((file, i) => {
                          const name = file.split('/').pop() || file.split('\\').pop();
                          return <div key={i} style={s.evidenceChip} title={file}>{name}</div>;
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

const s = {
  container: { padding: '28px', background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', marginBottom: '20px' },
  titleSection: { marginBottom: '24px', borderBottom: '1px solid var(--border)', paddingBottom: '16px' },
  title: { margin: '0 0 6px', fontSize: '20px', color: 'var(--text-primary)', fontWeight: 600 },
  subtitle: { margin: 0, fontSize: '13px', color: 'var(--text-muted)', lineHeight: '1.5' },
  loadingBox: { textAlign: 'center', padding: '60px 20px' },
  spinner: { width: 36, height: 36, border: '3px solid var(--border)', borderTopColor: 'var(--text-secondary)', borderRadius: '50%', margin: '0 auto', animation: 'spin 0.8s linear infinite' },
  errorBox: { padding: '16px', background: 'var(--red-dim)', border: '1px solid rgba(248,113,113,0.15)', borderRadius: 'var(--radius-md)', color: 'var(--red)', fontSize: '13px' },
  emptyBox: { textAlign: 'center', padding: '60px 20px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px dashed var(--border)' },
  summaryBanner: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '24px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', marginBottom: '20px', flexWrap: 'wrap', gap: '20px' },
  summaryLeft: { display: 'flex', alignItems: 'center', gap: '20px' },
  summaryText: { display: 'flex', flexDirection: 'column', gap: '3px' },
  summaryLabel: { fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px' },
  summaryValue: { fontSize: '22px', fontWeight: 700, fontFamily: 'var(--font-mono)' },
  summaryDesc: { fontSize: '12px', color: 'var(--text-muted)', maxWidth: '320px', lineHeight: '1.4' },
  summaryStats: { display: 'flex', gap: '10px' },
  statChip: { display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 14px', background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' },
  statDot: { width: 7, height: 7, borderRadius: '50%', display: 'inline-block' },
  statCount: { fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' },
  statLabel: { fontSize: '11px', color: 'var(--text-muted)' },
  explainerBox: { display: 'flex', gap: '12px', padding: '14px 16px', background: 'var(--blue-dim)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(96,165,250,0.12)', marginBottom: '24px', alignItems: 'flex-start' },
  explainerIcon: { fontSize: '18px', flexShrink: 0, marginTop: '1px' },
  explainerText: { margin: '4px 0 0', fontSize: '12px', color: 'var(--blue)', lineHeight: '1.6' },
  claimsHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' },
  claimsTitle: { margin: 0, fontSize: '16px', color: 'var(--text-primary)', fontWeight: 600 },
  claimsCount: { fontSize: '12px', color: 'var(--text-muted)', background: 'var(--bg-elevated)', padding: '4px 12px', borderRadius: '10px', border: '1px solid var(--border)', fontFamily: 'var(--font-mono)' },
  claimsList: { display: 'flex', flexDirection: 'column', gap: '10px' },
  claimCard: { padding: '16px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', borderLeft: '3px solid var(--border)', cursor: 'pointer', transition: 'all 0.2s ease' },
  claimRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' },
  claimLeft: { display: 'flex', alignItems: 'center', gap: '12px', flex: 1 },
  claimIcon: { fontSize: '20px', width: '36px', height: '36px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', flexShrink: 0 },
  claimName: { fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '2px' },
  claimMeta: { fontSize: '11px', color: 'var(--text-muted)' },
  claimRight: { display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 },
  expandArrow: { fontSize: '14px', color: 'var(--text-dim)', transition: 'transform 0.2s ease' },
  barTrack: { height: '4px', background: 'var(--bg-card)', borderRadius: '2px', overflow: 'hidden' },
  barFill: { height: '100%', borderRadius: '2px', transition: 'width 0.8s ease' },
  claimDetails: { marginTop: '14px', display: 'flex', flexDirection: 'column', gap: '10px', paddingTop: '14px', borderTop: '1px solid var(--border)' },
  detailSection: { padding: '12px', background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' },
  warningSection: { background: 'var(--amber-dim)', border: '1px solid rgba(251,191,36,0.12)' },
  detailLabel: { fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' },
  detailText: { margin: 0, fontSize: '12px', color: 'var(--text-muted)', lineHeight: '1.7' },
  evidenceGrid: { display: 'flex', flexWrap: 'wrap', gap: '6px' },
  evidenceChip: { padding: '5px 10px', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '180px' },
};

export default ConfidenceReport;
