import React, { useState, useEffect } from 'react';
import { assessmentApi } from '../../services/assessmentApi';

export default function CandidateScorecardModal({ orgId, attemptId, onClose, onUpdated }) {
  const [scorecard, setScorecard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Manual Override Form
  const [isOverrideOpen, setIsOverrideOpen] = useState(false);
  const [newScore, setNewScore] = useState('');
  const [overrideReason, setOverrideReason] = useState('');
  const [overrideSubmitting, setOverrideSubmitting] = useState(false);
  const [overrideError, setOverrideError] = useState('');

  // Releasing result
  const [releasing, setReleasing] = useState(false);

  useEffect(() => {
    if (attemptId) {
      loadScorecard();
    }
  }, [orgId, attemptId]);

  const loadScorecard = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await assessmentApi.getScorecard(orgId, attemptId);
      setScorecard(data);
      setNewScore(data?.total_score != null ? String(data.total_score) : '');
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load candidate scorecard.');
    } finally {
      setLoading(false);
    }
  };

  const handleOverrideSubmit = async (e) => {
    e.preventDefault();
    setOverrideError('');
    const scoreVal = parseFloat(newScore);
    if (isNaN(scoreVal) || scoreVal < 0 || scoreVal > (scorecard?.max_possible_score || 100)) {
      setOverrideError(`Score must be between 0 and ${scorecard?.max_possible_score || 100}.`);
      return;
    }
    if (!overrideReason.trim() || overrideReason.trim().length < 5) {
      setOverrideError('A defensible reason (at least 5 characters) is required for audit trails.');
      return;
    }

    setOverrideSubmitting(true);
    try {
      const updated = await assessmentApi.manualScoreOverride(orgId, attemptId, scoreVal, overrideReason.trim());
      setScorecard(updated);
      setIsOverrideOpen(false);
      setOverrideReason('');
      if (onUpdated) onUpdated();
    } catch (err) {
      setOverrideError(err.response?.data?.detail || err.message || 'Failed to apply score override.');
    } finally {
      setOverrideSubmitting(false);
    }
  };

  const handleReleaseResult = async () => {
    if (!window.confirm('Release assessment results to this candidate now?')) return;
    setReleasing(true);
    try {
      await assessmentApi.releaseResult(orgId, attemptId);
      loadScorecard();
      if (onUpdated) onUpdated();
    } catch (err) {
      alert(err.response?.data?.detail || err.message || 'Failed to release result.');
    } finally {
      setReleasing(false);
    }
  };

  if (loading) {
    return (
      <div style={styles.backdrop}>
        <div style={styles.modal}>
          <div style={styles.loadingBox}>Loading candidate scorecard...</div>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.backdrop}>
      <div style={styles.modal}>
        {/* Header */}
        <div style={styles.header}>
          <div>
            <div style={styles.badgeRow}>
              <span style={styles.tagBlue}>CANDIDATE SCORECARD</span>
              <span style={styles.tagZinc}>VERSION {scorecard?.assessment_version || 1}</span>
              <span
                style={{
                  ...styles.statusTag,
                  backgroundColor: scorecard?.passed ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                  color: scorecard?.passed ? '#10b981' : '#ef4444',
                }}
              >
                {scorecard?.passed ? 'PASSED' : 'NOT MET'}
              </span>
            </div>
            <h2 style={styles.title}>{scorecard?.candidate_name || scorecard?.candidate_email}</h2>
            <p style={styles.subtitle}>
              Assessment: <strong>{scorecard?.assessment_title}</strong> • Candidate Email: <code>{scorecard?.candidate_email || scorecard?.candidate_user_email}</code>
            </p>
          </div>
          <button onClick={onClose} style={styles.closeBtn}>✕</button>
        </div>

        {error && <div style={styles.errorBox}>{error}</div>}

        <div style={styles.body}>
          {/* Top Score Summary Banner */}
          <div style={styles.summaryGrid}>
            <div style={styles.metricCard}>
              <div style={styles.metricLabel}>Total Score</div>
              <div style={styles.metricVal}>
                {scorecard?.total_score} <span style={styles.metricSub}>/ {scorecard?.max_possible_score}</span>
              </div>
            </div>

            <div style={styles.metricCard}>
              <div style={styles.metricLabel}>Percentage</div>
              <div style={{ ...styles.metricVal, color: scorecard?.passed ? '#10b981' : '#f59e0b' }}>
                {scorecard?.percentage_score}%
              </div>
            </div>

            <div style={styles.metricCard}>
              <div style={styles.metricLabel}>Result Release Status</div>
              <div style={{ marginTop: '4px' }}>
                {scorecard?.result_released ? (
                  <span style={{ color: '#10b981', fontWeight: '600', fontSize: '14px' }}>✓ Released</span>
                ) : (
                  <button
                    onClick={handleReleaseResult}
                    disabled={releasing}
                    style={styles.releaseBtn}
                  >
                    {releasing ? 'Releasing...' : '🚀 Release to Candidate'}
                  </button>
                )}
              </div>
            </div>

            <div style={styles.metricCard}>
              <div style={styles.metricLabel}>Manual Score Override</div>
              <div style={{ marginTop: '4px' }}>
                <button
                  onClick={() => setIsOverrideOpen(!isOverrideOpen)}
                  style={styles.overrideBtn}
                >
                  ✎ Edit Score
                </button>
              </div>
            </div>
          </div>

          {/* Override Form */}
          {isOverrideOpen && (
            <div style={styles.overrideCard}>
              <h4 style={{ margin: '0 0 10px', fontSize: '14px', color: '#f8fafc' }}>
                Audited Manual Score Override
              </h4>
              {overrideError && <div style={styles.errorBox}>{overrideError}</div>}
              <form onSubmit={handleOverrideSubmit} style={styles.overrideForm}>
                <div style={{ display: 'flex', gap: '14px' }}>
                  <div style={{ width: '140px' }}>
                    <label style={styles.label}>New Score</label>
                    <input
                      type="number"
                      step="0.1"
                      value={newScore}
                      onChange={(e) => setNewScore(e.target.value)}
                      style={styles.input}
                      required
                    />
                  </div>
                  <div style={{ flex: 1 }}>
                    <label style={styles.label}>Reason for Override (Audited)</label>
                    <input
                      type="text"
                      value={overrideReason}
                      onChange={(e) => setOverrideReason(e.target.value)}
                      placeholder="e.g. Defensible alternate implementation in AST analysis..."
                      style={styles.input}
                      required
                    />
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                  <button
                    type="button"
                    onClick={() => setIsOverrideOpen(false)}
                    style={styles.cancelBtn}
                  >
                    Cancel
                  </button>
                  <button type="submit" disabled={overrideSubmitting} style={styles.saveBtn}>
                    {overrideSubmitting ? 'Saving...' : 'Apply & Audit Override'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Competency & Skill Breakdowns */}
          {scorecard?.competency_breakdown && Object.keys(scorecard.competency_breakdown).length > 0 && (
            <div style={styles.section}>
              <h3 style={styles.sectionTitle}>Competency Breakdown</h3>
              <div style={styles.breakdownGrid}>
                {Object.entries(scorecard.competency_breakdown).map(([comp, val]) => {
                  const pct = val.total > 0 ? Math.round((val.earned / val.total) * 100) : 0;
                  return (
                    <div key={comp} style={styles.breakdownItem}>
                      <div style={styles.breakdownHeader}>
                        <span style={styles.breakdownName}>{comp.replace(/_/g, ' ')}</span>
                        <span style={styles.breakdownVal}>
                          {val.earned}/{val.total} ({pct}%)
                        </span>
                      </div>
                      <div style={styles.progressBarBg}>
                        <div style={{ ...styles.progressBarFill, width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Question-by-Question Review */}
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>Question-Level Candidate Responses & Grading</h3>
            <div style={styles.questionsList}>
              {scorecard?.questions?.map((q, idx) => {
                const isFullCorrect = q.is_correct === 1;
                const isPartial = q.is_correct === 2;
                return (
                  <div key={q.question_id || idx} style={styles.questionCard}>
                    <div style={styles.qHeader}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={styles.qIndex}>#{idx + 1}</span>
                        <span style={styles.tagZinc}>{q.competency}</span>
                        <span style={styles.tagBlue}>{q.response_format}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span
                          style={{
                            ...styles.qScoreBadge,
                            color: isFullCorrect ? '#10b981' : isPartial ? '#38bdf8' : '#ef4444',
                            borderColor: isFullCorrect ? '#10b981' : isPartial ? '#38bdf8' : '#ef4444',
                          }}
                        >
                          {q.awarded_points} / {q.points} pts
                        </span>
                      </div>
                    </div>

                    <div style={styles.qText}>{q.question_text}</div>

                    {/* Candidate Response vs Key */}
                    <div style={styles.compareGrid}>
                      <div style={styles.compareBox}>
                        <div style={styles.compareLabel}>Candidate Response:</div>
                        <div style={styles.compareVal}>
                          {Array.isArray(q.candidate_response)
                            ? q.candidate_response.join(', ') || 'No answer submitted'
                            : q.candidate_response || 'No answer submitted'}
                        </div>
                      </div>

                      <div style={styles.compareBox}>
                        <div style={styles.compareLabel}>Correct Answer Key:</div>
                        <div style={{ ...styles.compareVal, color: '#10b981' }}>
                          {q.answer_key?.correct_option ||
                            q.answer_key?.correct_value ||
                            q.answer_key?.correct_options?.join(', ') ||
                            JSON.stringify(q.answer_key)}
                        </div>
                      </div>
                    </div>

                    {/* Explanation */}
                    {q.explanation && (
                      <div style={styles.explanationBox}>
                        <strong>Pedagogical Explanation:</strong> {q.explanation}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
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
    zIndex: 9999,
    padding: '20px',
  },
  modal: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '12px',
    width: '100%',
    maxWidth: '920px',
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
    alignItems: 'center',
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
  statusTag: {
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '700',
    letterSpacing: '0.05em',
  },
  title: {
    margin: 0,
    fontSize: '20px',
    fontWeight: '700',
    color: '#f8fafc',
  },
  subtitle: {
    margin: '4px 0 0',
    fontSize: '13px',
    color: '#94a3b8',
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
    gap: '24px',
  },
  summaryGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '14px',
  },
  metricCard: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '10px',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
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
  metricSub: {
    fontSize: '14px',
    color: '#64748b',
    fontWeight: '400',
  },
  releaseBtn: {
    backgroundColor: '#38bdf8',
    color: '#0f172a',
    border: 'none',
    padding: '6px 12px',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  overrideBtn: {
    backgroundColor: '#334155',
    color: '#f8fafc',
    border: '1px solid #475569',
    padding: '6px 12px',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  overrideCard: {
    backgroundColor: '#0f172a',
    border: '1px solid #f59e0b',
    borderRadius: '10px',
    padding: '16px',
  },
  overrideForm: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  label: {
    display: 'block',
    fontSize: '11px',
    fontWeight: '600',
    color: '#94a3b8',
    marginBottom: '4px',
    textTransform: 'uppercase',
  },
  input: {
    width: '100%',
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '6px',
    color: '#f8fafc',
    padding: '8px 12px',
    fontSize: '13px',
    outline: 'none',
  },
  cancelBtn: {
    backgroundColor: '#334155',
    color: '#f8fafc',
    border: 'none',
    padding: '6px 14px',
    borderRadius: '6px',
    fontSize: '12px',
    cursor: 'pointer',
  },
  saveBtn: {
    backgroundColor: '#f59e0b',
    color: '#0f172a',
    border: 'none',
    padding: '6px 14px',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  section: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  sectionTitle: {
    margin: 0,
    fontSize: '15px',
    fontWeight: '700',
    color: '#f8fafc',
  },
  breakdownGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
    gap: '12px',
  },
  breakdownItem: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '8px',
    padding: '12px',
  },
  breakdownHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '12px',
    fontWeight: '600',
    color: '#f8fafc',
    marginBottom: '6px',
  },
  breakdownName: {
    textTransform: 'capitalize',
  },
  breakdownVal: {
    color: '#38bdf8',
  },
  progressBarBg: {
    height: '6px',
    backgroundColor: '#1e293b',
    borderRadius: '3px',
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: '#38bdf8',
    borderRadius: '3px',
  },
  questionsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  questionCard: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '10px',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  qHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  qIndex: {
    fontSize: '13px',
    fontWeight: '700',
    color: '#94a3b8',
  },
  qScoreBadge: {
    fontSize: '12px',
    fontWeight: '700',
    border: '1px solid',
    borderRadius: '4px',
    padding: '2px 8px',
  },
  qText: {
    fontSize: '14px',
    color: '#f8fafc',
    lineHeight: '1.5',
  },
  compareGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
  },
  compareBox: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '6px',
    padding: '10px 12px',
  },
  compareLabel: {
    fontSize: '11px',
    fontWeight: '600',
    color: '#94a3b8',
    marginBottom: '4px',
  },
  compareVal: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#f8fafc',
  },
  explanationBox: {
    backgroundColor: 'rgba(56, 189, 248, 0.08)',
    border: '1px solid rgba(56, 189, 248, 0.25)',
    borderRadius: '6px',
    padding: '10px 12px',
    fontSize: '12px',
    color: '#cbd5e1',
    lineHeight: '1.5',
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
  loadingBox: {
    padding: '40px',
    textAlign: 'center',
    color: '#94a3b8',
  },
};
