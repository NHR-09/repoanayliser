import React, { useState, useEffect } from 'react';
import { getConfidenceReport } from '../services/api';

const ConfidenceReport = ({ repoId }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedClaim, setExpandedClaim] = useState(null);

  useEffect(() => {
    if (repoId) {
      fetchReport();
    }
  }, [repoId]);

  const fetchReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getConfidenceReport(repoId);
      setReport(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceColor = (c) => {
    if (c >= 0.8) return '#10b981';
    if (c >= 0.6) return '#f59e0b';
    return '#ef4444';
  };

  const getConfidenceLabel = (c) => {
    if (c >= 0.8) return 'High';
    if (c >= 0.6) return 'Medium';
    return 'Low';
  };

  const getConfidenceEmoji = (c) => {
    if (c >= 0.8) return '✅';
    if (c >= 0.6) return '⚠️';
    return '❌';
  };

  const getClaimIcon = (claim) => {
    const c = claim.toLowerCase();
    if (c.includes('layered')) return '🏗️';
    if (c.includes('mvc')) return '🔀';
    if (c.includes('hexagonal')) return '⬡';
    if (c.includes('event')) return '⚡';
    if (c.includes('coupling')) return '🔗';
    if (c.includes('circular')) return '🔄';
    return '📋';
  };

  // Circular progress ring component
  const ConfidenceRing = ({ value, size = 80, strokeWidth = 6 }) => {
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (value * circumference);
    const color = getConfidenceColor(value);
    const pct = Math.round(value * 100);

    return (
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke="#e5e7eb" strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke={color} strokeWidth={strokeWidth}
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
        <text
          x={size / 2} y={size / 2}
          textAnchor="middle" dominantBaseline="central"
          style={{
            transform: 'rotate(90deg)',
            transformOrigin: 'center',
            fontSize: size > 60 ? '18px' : '13px',
            fontWeight: 'bold',
            fill: color
          }}
        >
          {pct}%
        </text>
      </svg>
    );
  };

  // Horizontal confidence bar
  const ConfidenceBar = ({ value }) => {
    const pct = Math.round(value * 100);
    const color = getConfidenceColor(value);
    return (
      <div style={s.barTrack}>
        <div style={{ ...s.barFill, width: `${pct}%`, background: color }} />
      </div>
    );
  };

  if (loading) {
    return (
      <div style={s.container}>
        <div style={s.titleSection}>
          <h2 style={s.title}>Confidence & Limitations</h2>
          <p style={s.subtitle}>How reliable is our analysis?</p>
        </div>
        <div style={s.loadingBox}>
          <div style={s.spinner} />
          <p style={{ color: '#6b7280', marginTop: 15 }}>Evaluating analysis reliability...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={s.container}>
        <div style={s.titleSection}>
          <h2 style={s.title}>Confidence & Limitations</h2>
        </div>
        <div style={s.errorBox}>
          <strong>⚠️ Error:</strong> {error}
        </div>
      </div>
    );
  }

  if (!report || !report.claims || report.claims.length === 0) {
    return (
      <div style={s.container}>
        <div style={s.titleSection}>
          <h2 style={s.title}>Confidence & Limitations</h2>
          <p style={s.subtitle}>How reliable is our analysis?</p>
        </div>
        <div style={s.emptyBox}>
          <div style={{ fontSize: 48, marginBottom: 15 }}>🔍</div>
          <h3 style={{ margin: '0 0 8px', color: '#374151' }}>No analysis data yet</h3>
          <p style={{ margin: 0, color: '#6b7280', fontSize: 14 }}>
            Analyze a repository first to see how confident we are in the results.
          </p>
        </div>
      </div>
    );
  }

  // Compute stats
  const avgConfidence = report.claims.reduce((sum, c) => sum + c.confidence, 0) / report.claims.length;
  const highCount = report.claims.filter(c => c.confidence >= 0.8).length;
  const medCount = report.claims.filter(c => c.confidence >= 0.6 && c.confidence < 0.8).length;
  const lowCount = report.claims.filter(c => c.confidence < 0.6).length;

  return (
    <div style={s.container}>
      {/* Title */}
      <div style={s.titleSection}>
        <h2 style={s.title}>Confidence & Limitations</h2>
        <p style={s.subtitle}>
          How reliable is our architectural analysis? Each claim is scored based on the strength of evidence found.
        </p>
      </div>

      {/* Summary Banner */}
      <div style={s.summaryBanner}>
        <div style={s.summaryLeft}>
          <ConfidenceRing value={avgConfidence} size={100} strokeWidth={8} />
          <div style={s.summaryText}>
            <div style={s.summaryLabel}>Overall Confidence</div>
            <div style={{ ...s.summaryValue, color: getConfidenceColor(avgConfidence) }}>
              {getConfidenceLabel(avgConfidence)}
            </div>
            <div style={s.summaryDesc}>
              {report.summary || `Based on ${report.claims.length} architectural claims`}
            </div>
          </div>
        </div>
        <div style={s.summaryStats}>
          <div style={s.statChip}>
            <span style={{ ...s.statDot, background: '#10b981' }} />
            <span style={s.statCount}>{highCount}</span>
            <span style={s.statLabel}>High</span>
          </div>
          <div style={s.statChip}>
            <span style={{ ...s.statDot, background: '#f59e0b' }} />
            <span style={s.statCount}>{medCount}</span>
            <span style={s.statLabel}>Medium</span>
          </div>
          <div style={s.statChip}>
            <span style={{ ...s.statDot, background: '#ef4444' }} />
            <span style={s.statCount}>{lowCount}</span>
            <span style={s.statLabel}>Low</span>
          </div>
        </div>
      </div>

      {/* What does this mean? */}
      <div style={s.explainerBox}>
        <div style={s.explainerIcon}>💡</div>
        <div>
          <strong style={{ color: '#1e40af' }}>What does this mean?</strong>
          <p style={s.explainerText}>
            ARCHITECH makes claims about your codebase's architecture (e.g. "uses MVC pattern"). 
            Each claim is scored on how much evidence supports it. We also show when our analysis 
            might be wrong — so you know what to double check.
          </p>
        </div>
      </div>

      {/* Claims */}
      <div style={s.claimsHeader}>
        <h3 style={s.claimsTitle}>Architectural Claims</h3>
        <span style={s.claimsCount}>{report.claims.length} claims</span>
      </div>

      <div style={s.claimsList}>
        {report.claims.map((claim, index) => {
          const isExpanded = expandedClaim === index;
          const color = getConfidenceColor(claim.confidence);
          const pct = Math.round(claim.confidence * 100);

          return (
            <div
              key={index}
              style={{
                ...s.claimCard,
                borderLeftColor: color,
                ...(isExpanded ? { boxShadow: '0 4px 20px rgba(0,0,0,0.12)' } : {})
              }}
              onClick={() => setExpandedClaim(isExpanded ? null : index)}
            >
              {/* Claim header row */}
              <div style={s.claimRow}>
                <div style={s.claimLeft}>
                  <span style={s.claimIcon}>{getClaimIcon(claim.claim)}</span>
                  <div>
                    <div style={s.claimName}>{claim.claim}</div>
                    <div style={s.claimMeta}>
                      {getConfidenceEmoji(claim.confidence)} {getConfidenceLabel(claim.confidence)} confidence
                    </div>
                  </div>
                </div>
                <div style={s.claimRight}>
                  <ConfidenceRing value={claim.confidence} size={52} strokeWidth={4} />
                  <span style={{
                    ...s.expandArrow,
                    transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)'
                  }}>▾</span>
                </div>
              </div>

              {/* Confidence bar */}
              <ConfidenceBar value={claim.confidence} />

              {/* Expanded details */}
              {isExpanded && (
                <div style={s.claimDetails}>
                  {/* Why we think this */}
                  <div style={s.detailSection}>
                    <div style={s.detailLabel}>🧠 Why We Think This</div>
                    <p style={s.detailText}>
                      {claim.reasoning || claim.explanation || 'Pattern detected via structural analysis'}
                    </p>
                  </div>

                  {/* When it could be wrong */}
                  <div style={{ ...s.detailSection, ...s.warningSection }}>
                    <div style={s.detailLabel}>⚠️ When This Could Be Wrong</div>
                    <p style={s.detailText}>
                      {claim.failure_scenario || 'No specific failure scenario identified'}
                    </p>
                  </div>

                  {/* Evidence files */}
                  {claim.evidence && claim.evidence.length > 0 && (
                    <div style={s.detailSection}>
                      <div style={s.detailLabel}>📁 Evidence ({claim.evidence.length} files)</div>
                      <div style={s.evidenceGrid}>
                        {claim.evidence.slice(0, 6).map((file, i) => {
                          const name = file.split('/').pop() || file.split('\\').pop();
                          return (
                            <div key={i} style={s.evidenceChip} title={file}>
                              📄 {name}
                            </div>
                          );
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
  container: {
    padding: '20px',
    background: '#fff',
    borderRadius: '12px',
    marginBottom: '20px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
  },
  titleSection: {
    marginBottom: '25px',
    borderBottom: '2px solid #667eea',
    paddingBottom: '15px'
  },
  title: {
    margin: '0 0 8px 0',
    fontSize: '28px',
    color: '#1f2937',
    fontWeight: 'bold'
  },
  subtitle: {
    margin: 0,
    fontSize: '14px',
    color: '#6b7280',
    lineHeight: '1.5'
  },

  // Loading
  loadingBox: {
    textAlign: 'center',
    padding: '60px 20px'
  },
  spinner: {
    width: 40, height: 40,
    border: '4px solid #e5e7eb',
    borderTopColor: '#667eea',
    borderRadius: '50%',
    margin: '0 auto',
    animation: 'spin 0.8s linear infinite'
  },

  // Error
  errorBox: {
    padding: '20px',
    background: '#fee2e2',
    border: '1px solid #ef4444',
    borderRadius: '8px',
    color: '#991b1b',
    fontSize: '14px'
  },

  // Empty
  emptyBox: {
    textAlign: 'center',
    padding: '60px 20px',
    background: '#f9fafb',
    borderRadius: '8px',
    border: '2px dashed #e5e7eb'
  },

  // Summary Banner
  summaryBanner: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '25px',
    background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
    borderRadius: '12px',
    border: '1px solid #e2e8f0',
    marginBottom: '20px',
    flexWrap: 'wrap',
    gap: '20px'
  },
  summaryLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '20px'
  },
  summaryText: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px'
  },
  summaryLabel: {
    fontSize: '12px',
    color: '#6b7280',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  summaryValue: {
    fontSize: '24px',
    fontWeight: 'bold'
  },
  summaryDesc: {
    fontSize: '13px',
    color: '#6b7280',
    maxWidth: '350px',
    lineHeight: '1.4'
  },
  summaryStats: {
    display: 'flex',
    gap: '12px'
  },
  statChip: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 14px',
    background: '#fff',
    borderRadius: '8px',
    border: '1px solid #e5e7eb',
    boxShadow: '0 1px 2px rgba(0,0,0,0.04)'
  },
  statDot: {
    width: 8, height: 8,
    borderRadius: '50%',
    display: 'inline-block'
  },
  statCount: {
    fontSize: '16px',
    fontWeight: 'bold',
    color: '#1f2937'
  },
  statLabel: {
    fontSize: '12px',
    color: '#6b7280'
  },

  // Explainer
  explainerBox: {
    display: 'flex',
    gap: '12px',
    padding: '16px',
    background: '#eff6ff',
    borderRadius: '8px',
    border: '1px solid #bfdbfe',
    marginBottom: '25px',
    alignItems: 'flex-start'
  },
  explainerIcon: {
    fontSize: '20px',
    flexShrink: 0,
    marginTop: '2px'
  },
  explainerText: {
    margin: '5px 0 0',
    fontSize: '13px',
    color: '#1e40af',
    lineHeight: '1.6'
  },

  // Claims header
  claimsHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '15px'
  },
  claimsTitle: {
    margin: 0,
    fontSize: '18px',
    color: '#1f2937',
    fontWeight: 'bold'
  },
  claimsCount: {
    fontSize: '13px',
    color: '#6b7280',
    background: '#f3f4f6',
    padding: '4px 12px',
    borderRadius: '12px'
  },

  // Claim Cards
  claimsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px'
  },
  claimCard: {
    padding: '18px',
    background: '#fff',
    borderRadius: '10px',
    border: '1px solid #e5e7eb',
    borderLeft: '4px solid #667eea',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    boxShadow: '0 1px 3px rgba(0,0,0,0.06)'
  },
  claimRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '10px'
  },
  claimLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    flex: 1
  },
  claimIcon: {
    fontSize: '24px',
    width: '40px',
    height: '40px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#f9fafb',
    borderRadius: '8px',
    flexShrink: 0
  },
  claimName: {
    fontSize: '15px',
    fontWeight: '600',
    color: '#1f2937',
    marginBottom: '3px'
  },
  claimMeta: {
    fontSize: '12px',
    color: '#6b7280'
  },
  claimRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexShrink: 0
  },
  expandArrow: {
    fontSize: '16px',
    color: '#9ca3af',
    transition: 'transform 0.2s ease'
  },

  // Confidence bar
  barTrack: {
    height: '6px',
    background: '#f3f4f6',
    borderRadius: '3px',
    overflow: 'hidden',
    marginBottom: '2px'
  },
  barFill: {
    height: '100%',
    borderRadius: '3px',
    transition: 'width 0.8s ease'
  },

  // Expanded details
  claimDetails: {
    marginTop: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    paddingTop: '16px',
    borderTop: '1px solid #f3f4f6'
  },
  detailSection: {
    padding: '14px',
    background: '#f9fafb',
    borderRadius: '8px'
  },
  warningSection: {
    background: '#fffbeb',
    border: '1px solid #fde68a'
  },
  detailLabel: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#374151',
    marginBottom: '8px'
  },
  detailText: {
    margin: 0,
    fontSize: '13px',
    color: '#4b5563',
    lineHeight: '1.7'
  },

  // Evidence
  evidenceGrid: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px'
  },
  evidenceChip: {
    padding: '6px 12px',
    background: '#fff',
    border: '1px solid #e5e7eb',
    borderRadius: '6px',
    fontSize: '12px',
    color: '#374151',
    fontFamily: 'monospace',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    maxWidth: '200px'
  }
};

export default ConfidenceReport;
