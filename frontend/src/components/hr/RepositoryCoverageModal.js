import React, { useState, useEffect } from 'react';
import { hrApi } from '../../services/hrApi';

export default function RepositoryCoverageModal({
  orgId,
  repoId,
  repoName,
  onClose,
  onOpenGenerate,
}) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [coverage, setCoverage] = useState(null);

  useEffect(() => {
    loadCoverage();
  }, [orgId, repoId]);

  const loadCoverage = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await hrApi.getRepositoryCoverage(orgId, repoId);
      setCoverage(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to calculate repository coverage.');
    } finally {
      setLoading(false);
    }
  };

  const totals = coverage?.totals || {};
  const compStats = coverage?.by_competency || {};
  const gaps = coverage?.coverage_gaps || [];

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        {/* Header */}
        <div style={styles.header}>
          <div>
            <div style={styles.badge}>REPOSITORY QUESTION COVERAGE ANALYTICS</div>
            <h3 style={styles.title}>{coverage?.display_name || repoName || 'Repository'} Coverage</h3>
            <p style={styles.subtext}>
              Revision {coverage?.analysis_version?.substring(0, 8) || 'HEAD'} &bull; Status: {coverage?.approval_status}
            </p>
          </div>
          <button style={styles.closeBtn} onClick={onClose}>&times;</button>
        </div>

        {/* Content Body */}
        <div style={styles.body}>
          {loading && (
            <div style={styles.loadingBox}>
              <div style={styles.spinner} />
              <p style={{ marginTop: '12px', color: '#94a3b8' }}>Analyzing question coverage...</p>
            </div>
          )}

          {error && <div style={styles.errorBox}>{error}</div>}

          {coverage && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* Summary Cards */}
              <div style={styles.summaryGrid}>
                <div style={styles.summaryCard}>
                  <div style={styles.summaryValue}>{totals.total_questions || 0}</div>
                  <div style={styles.summaryLabel}>Total Questions</div>
                </div>
                <div style={styles.summaryCard}>
                  <div style={{ ...styles.summaryValue, color: '#10b981' }}>{totals.published || 0}</div>
                  <div style={styles.summaryLabel}>Published</div>
                </div>
                <div style={styles.summaryCard}>
                  <div style={{ ...styles.summaryValue, color: '#38bdf8' }}>{totals.approved || 0}</div>
                  <div style={styles.summaryLabel}>Approved Drafts</div>
                </div>
                <div style={styles.summaryCard}>
                  <div style={{ ...styles.summaryValue, color: '#f59e0b' }}>{totals.needs_review || 0}</div>
                  <div style={styles.summaryLabel}>Needs Review</div>
                </div>
              </div>

              {/* Assessment Readiness Notice */}
              <div
                style={{
                  ...styles.readinessBanner,
                  borderColor: coverage.is_ready_for_assessments ? '#10b981' : '#f59e0b',
                  backgroundColor: coverage.is_ready_for_assessments ? 'rgba(16, 185, 129, 0.08)' : 'rgba(245, 158, 11, 0.08)',
                }}
              >
                <div style={{ fontSize: '18px', marginRight: '12px' }}>
                  {coverage.is_ready_for_assessments ? '✅' : '⚠️'}
                </div>
                <div>
                  <div style={{ fontWeight: '700', fontSize: '13px', color: '#f8fafc' }}>
                    {coverage.is_ready_for_assessments
                      ? 'Approved & Ready for Candidate Assessment Quizzes'
                      : 'Preparation Required for Formal Assessments'}
                  </div>
                  <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
                    {coverage.is_ready_for_assessments
                      ? 'Repository is approved with sufficient published technical questions across core competencies.'
                      : 'To qualify for formal assessment blueprints, repository must be approved and have at least 5 published questions.'}
                  </div>
                </div>
              </div>

              {/* Competency Breakdown */}
              <div>
                <div style={styles.sectionLabel}>COVERAGE BY ARCHITECTURAL COMPETENCY</div>
                <div style={styles.competencyList}>
                  {Object.entries(compStats).map(([compKey, stats]) => {
                    const isMissing = stats.total === 0;
                    return (
                      <div
                        key={compKey}
                        style={{
                          ...styles.compRow,
                          borderColor: isMissing ? '#ef4444' : '#334155',
                          backgroundColor: isMissing ? 'rgba(239, 68, 68, 0.05)' : '#1e293b',
                        }}
                      >
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: '13px', fontWeight: '600', color: '#f8fafc' }}>
                            {compKey.replace('_', ' ')}
                          </div>
                          <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>
                            {stats.published} Published &bull; {stats.approved} Approved &bull; {stats.total} Total
                          </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {isMissing ? (
                            <span style={styles.gapTag}>0 Questions (Gap)</span>
                          ) : (
                            <span style={styles.coveredTag}>{stats.total} Covered</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Identified Coverage Gaps Callout */}
              {gaps.length > 0 && (
                <div style={styles.gapBox}>
                  <div style={{ fontWeight: '700', fontSize: '13px', color: '#f87171', marginBottom: '4px' }}>
                    Identified Assessment Coverage Gaps ({gaps.length})
                  </div>
                  <p style={{ margin: 0, fontSize: '12px', color: '#cbd5e1', lineHeight: '1.4' }}>
                    The following competencies have 0 published questions for this codebase:{' '}
                    <strong>{gaps.map((g) => g.replace('_', ' ')).join(', ')}</strong>.
                  </p>
                  <button
                    style={styles.generateForRepoBtn}
                    onClick={() => {
                      onClose();
                      onOpenGenerate(repoId);
                    }}
                  >
                    ⚡ Generate Grounded Questions for This Repository
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={styles.footer}>
          <button style={styles.closeModalBtn} onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

const styles = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: '20px',
  },
  modal: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '12px',
    width: '100%',
    maxWidth: '820px',
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
  },
  header: {
    padding: '20px 24px',
    borderBottom: '1px solid #1e293b',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  badge: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#38bdf8',
    letterSpacing: '0.05em',
    marginBottom: '6px',
  },
  title: {
    margin: 0,
    color: '#f8fafc',
    fontSize: '18px',
    fontWeight: '600',
  },
  subtext: {
    margin: '4px 0 0',
    color: '#94a3b8',
    fontSize: '13px',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: '#94a3b8',
    fontSize: '28px',
    cursor: 'pointer',
    padding: '0 8px',
    lineHeight: 1,
  },
  body: {
    padding: '24px',
    overflowY: 'auto',
    flex: 1,
  },
  summaryGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '12px',
  },
  summaryCard: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '8px',
    padding: '16px',
    textAlign: 'center',
  },
  summaryValue: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#f8fafc',
    marginBottom: '4px',
  },
  summaryLabel: {
    fontSize: '11px',
    fontWeight: '600',
    color: '#94a3b8',
    textTransform: 'uppercase',
  },
  readinessBanner: {
    display: 'flex',
    alignItems: 'center',
    padding: '14px 18px',
    borderRadius: '8px',
    border: '1px solid',
  },
  sectionLabel: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#64748b',
    letterSpacing: '0.05em',
    marginBottom: '10px',
  },
  competencyList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  compRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 16px',
    borderRadius: '8px',
    border: '1px solid #334155',
  },
  coveredTag: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#38bdf8',
    backgroundColor: 'rgba(56, 189, 248, 0.1)',
    padding: '3px 10px',
    borderRadius: '4px',
  },
  gapTag: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#ef4444',
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    padding: '3px 10px',
    borderRadius: '4px',
  },
  gapBox: {
    backgroundColor: '#1e293b',
    border: '1px solid #ef4444',
    borderRadius: '8px',
    padding: '16px',
  },
  generateForRepoBtn: {
    marginTop: '12px',
    backgroundColor: '#38bdf8',
    border: 'none',
    color: '#0f172a',
    padding: '8px 16px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '700',
    cursor: 'pointer',
  },
  loadingBox: {
    textAlign: 'center',
    padding: '50px',
  },
  spinner: {
    width: '32px',
    height: '32px',
    border: '3px solid #334155',
    borderTopColor: '#38bdf8',
    borderRadius: '50%',
    margin: '0 auto',
    animation: 'spin 1s linear infinite',
  },
  errorBox: {
    padding: '12px 16px',
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid #ef4444',
    color: '#fca5a5',
    borderRadius: '6px',
    fontSize: '13px',
  },
  footer: {
    padding: '16px 24px',
    borderTop: '1px solid #1e293b',
    display: 'flex',
    justifyContent: 'flex-end',
  },
  closeModalBtn: {
    backgroundColor: '#334155',
    color: '#f8fafc',
    border: 'none',
    padding: '8px 20px',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
  },
};
