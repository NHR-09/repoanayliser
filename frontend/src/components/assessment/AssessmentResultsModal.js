import React, { useState, useEffect } from 'react';
import { assessmentApi } from '../../services/assessmentApi';
import CandidateScorecardModal from './CandidateScorecardModal';

export default function AssessmentResultsModal({ orgId, assessment, onClose }) {
  const [attempts, setAttempts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedAttemptId, setSelectedAttemptId] = useState(null);

  useEffect(() => {
    loadAttempts();
  }, [orgId, assessment.id]);

  const loadAttempts = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await assessmentApi.getAttempts(orgId, assessment.id);
      setAttempts(data || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load assessment attempts.');
    } finally {
      setLoading(false);
    }
  };

  const handleExportCsv = () => {
    const url = assessmentApi.exportResultsCsvUrl(orgId, assessment.id);
    window.open(url, '_blank');
  };

  // Metrics computation
  const totalAttempts = attempts.length;
  const completedAttempts = attempts.filter((a) => a.status === 'GRADED' || a.status === 'SUBMITTED');
  const passedCount = completedAttempts.filter((a) => a.passed === 1).length;
  const avgScore =
    completedAttempts.length > 0
      ? Math.round(
          completedAttempts.reduce((acc, curr) => acc + (curr.percentage_score || 0), 0) /
            completedAttempts.length
        )
      : 0;

  return (
    <div style={styles.backdrop}>
      <div style={styles.modal}>
        {/* Header */}
        <div style={styles.header}>
          <div>
            <div style={styles.badgeRow}>
              <span style={styles.tagBlue}>ASSESSMENT RESULTS & REPORTING</span>
              <span style={styles.tagZinc}>VERSION {assessment.version || 1}</span>
            </div>
            <h2 style={styles.title}>{assessment.title}</h2>
            <p style={styles.subtitle}>
              Monitor candidate performance, inspect individual scorecards, release results, and export sanitized reports.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <button onClick={handleExportCsv} style={styles.exportBtn}>
              📥 Export CSV
            </button>
            <button onClick={onClose} style={styles.closeBtn}>✕</button>
          </div>
        </div>

        {error && <div style={styles.errorBox}>{error}</div>}

        <div style={styles.body}>
          {/* Top Metrics Row */}
          <div style={styles.metricsRow}>
            <div style={styles.metricCard}>
              <div style={styles.metricLabel}>Total Attempts</div>
              <div style={styles.metricVal}>{totalAttempts}</div>
            </div>
            <div style={styles.metricCard}>
              <div style={styles.metricLabel}>Completed & Graded</div>
              <div style={styles.metricVal}>{completedAttempts.length}</div>
            </div>
            <div style={styles.metricCard}>
              <div style={styles.metricLabel}>Passing Rate</div>
              <div style={{ ...styles.metricVal, color: '#10b981' }}>
                {completedAttempts.length > 0
                  ? `${Math.round((passedCount / completedAttempts.length) * 100)}%`
                  : '—'}
              </div>
            </div>
            <div style={styles.metricCard}>
              <div style={styles.metricLabel}>Average Score</div>
              <div style={{ ...styles.metricVal, color: '#38bdf8' }}>
                {completedAttempts.length > 0 ? `${avgScore}%` : '—'}
              </div>
            </div>
          </div>

          {/* Table of Attempts */}
          {loading ? (
            <div style={styles.loadingBox}>Loading candidate attempts...</div>
          ) : attempts.length === 0 ? (
            <div style={styles.emptyBox}>No candidate attempts recorded for this assessment yet.</div>
          ) : (
            <div style={styles.tableWrap}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>Candidate</th>
                    <th style={styles.th}>Status</th>
                    <th style={styles.th}>Score</th>
                    <th style={styles.th}>Percentage</th>
                    <th style={styles.th}>Result</th>
                    <th style={styles.th}>Duration</th>
                    <th style={styles.th}>Submitted At</th>
                    <th style={styles.th}>Release</th>
                    <th style={styles.th}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {attempts.map((att) => {
                    const durationMins =
                      att.duration_seconds_used != null
                        ? `${Math.round(att.duration_seconds_used / 60)} min`
                        : '—';
                    const isPassed = att.passed === 1;

                    return (
                      <tr key={att.id} style={styles.tr}>
                        <td style={styles.td}>
                          <div style={{ fontWeight: '600', color: '#f8fafc' }}>
                            {att.candidate_name || att.candidate_email}
                          </div>
                          {att.candidate_name && (
                            <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                              {att.candidate_email || att.user_email}
                            </div>
                          )}
                        </td>
                        <td style={styles.td}>
                          <span
                            style={{
                              ...styles.statusTag,
                              backgroundColor:
                                att.status === 'GRADED'
                                  ? 'rgba(16, 185, 129, 0.15)'
                                  : att.status === 'IN_PROGRESS'
                                  ? 'rgba(56, 189, 248, 0.15)'
                                  : '#334155',
                              color:
                                att.status === 'GRADED'
                                  ? '#10b981'
                                  : att.status === 'IN_PROGRESS'
                                  ? '#38bdf8'
                                  : '#94a3b8',
                            }}
                          >
                            {att.status}
                          </span>
                        </td>
                        <td style={styles.td}>
                          {att.total_score != null ? `${att.total_score} / ${att.max_possible_score}` : '—'}
                        </td>
                        <td style={styles.td}>
                          {att.percentage_score != null ? (
                            <strong style={{ color: isPassed ? '#10b981' : '#f59e0b' }}>
                              {att.percentage_score}%
                            </strong>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td style={styles.td}>
                          {att.status === 'GRADED' ? (
                            <span
                              style={{
                                ...styles.resultBadge,
                                backgroundColor: isPassed ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                                color: isPassed ? '#10b981' : '#ef4444',
                              }}
                            >
                              {isPassed ? 'PASS' : 'FAIL'}
                            </span>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td style={styles.td}>{durationMins}</td>
                        <td style={styles.td}>
                          <span style={{ fontSize: '12px', color: '#94a3b8' }}>
                            {att.submitted_at ? new Date(att.submitted_at).toLocaleString() : '—'}
                          </span>
                        </td>
                        <td style={styles.td}>
                          {att.result_released ? (
                            <span style={{ color: '#10b981', fontSize: '12px' }}>✓ Released</span>
                          ) : (
                            <span style={{ color: '#f59e0b', fontSize: '12px' }}>🔒 Withheld</span>
                          )}
                        </td>
                        <td style={styles.td}>
                          <button
                            onClick={() => setSelectedAttemptId(att.id)}
                            style={styles.viewBtn}
                          >
                            Scorecard →
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Single Candidate Scorecard Modal */}
      {selectedAttemptId && (
        <CandidateScorecardModal
          orgId={orgId}
          attemptId={selectedAttemptId}
          onClose={() => setSelectedAttemptId(null)}
          onUpdated={loadAttempts}
        />
      )}
    </div>
  );
}

const styles = {
  backdrop: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(15, 23, 42, 0.85)',
    backdropFilter: 'blur(4px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 9998,
    padding: '20px',
  },
  modal: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '12px',
    width: '100%',
    maxWidth: '1050px',
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 20px 40px rgba(0, 0, 0, 0.4)',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: '20px 24px',
    borderBottom: '1px solid #334155',
  },
  badgeRow: {
    display: 'flex',
    gap: '8px',
    marginBottom: '6px',
  },
  tagBlue: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#38bdf8',
    backgroundColor: 'rgba(56, 189, 248, 0.12)',
    padding: '2px 8px',
    borderRadius: '4px',
  },
  tagZinc: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#94a3b8',
    backgroundColor: '#334155',
    padding: '2px 8px',
    borderRadius: '4px',
  },
  title: {
    margin: 0,
    fontSize: '18px',
    fontWeight: '700',
    color: '#f8fafc',
  },
  subtitle: {
    margin: '4px 0 0',
    fontSize: '13px',
    color: '#94a3b8',
  },
  exportBtn: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    color: '#f8fafc',
    padding: '8px 14px',
    borderRadius: '8px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: '#94a3b8',
    fontSize: '20px',
    cursor: 'pointer',
    padding: '4px',
  },
  body: {
    padding: '24px',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  metricsRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '14px',
  },
  metricCard: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '10px',
    padding: '14px',
  },
  metricLabel: {
    fontSize: '11px',
    fontWeight: '600',
    color: '#94a3b8',
    textTransform: 'uppercase',
  },
  metricVal: {
    fontSize: '22px',
    fontWeight: '700',
    color: '#f8fafc',
    marginTop: '4px',
  },
  tableWrap: {
    overflowX: 'auto',
    border: '1px solid #334155',
    borderRadius: '8px',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    textAlign: 'left',
    fontSize: '13px',
  },
  th: {
    padding: '12px 14px',
    borderBottom: '1px solid #334155',
    color: '#94a3b8',
    fontSize: '11px',
    fontWeight: '700',
    textTransform: 'uppercase',
    backgroundColor: '#0f172a',
  },
  tr: {
    borderBottom: '1px solid #334155',
    transition: 'background 0.15s ease',
  },
  td: {
    padding: '12px 14px',
    color: '#f8fafc',
  },
  statusTag: {
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '600',
  },
  resultBadge: {
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '700',
  },
  viewBtn: {
    backgroundColor: 'rgba(56, 189, 248, 0.12)',
    border: '1px solid rgba(56, 189, 248, 0.3)',
    color: '#38bdf8',
    padding: '5px 12px',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  loadingBox: {
    padding: '40px',
    textAlign: 'center',
    color: '#94a3b8',
  },
  emptyBox: {
    padding: '40px',
    textAlign: 'center',
    color: '#64748b',
    border: '1px dashed #334155',
    borderRadius: '8px',
  },
  errorBox: {
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    color: '#fca5a5',
    padding: '10px 14px',
    borderRadius: '8px',
    fontSize: '13px',
    margin: '16px 24px 0',
  },
};
