import React, { useState, useEffect, useCallback } from 'react';
import { assessmentApi } from '../../services/assessmentApi';

export default function CandidateAssignedAssessments({ onStartAttempt, onViewResult }) {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [claimToken, setClaimToken] = useState('');
  const [claiming, setClaiming] = useState(false);
  const [claimMessage, setClaimMessage] = useState('');
  const [startingId, setStartingId] = useState(null);

  const loadAssignments = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await assessmentApi.getCandidateAssigned();
      setAssignments(data || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load assigned assessments.');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleAutoClaim = useCallback(async (token) => {
    setClaiming(true);
    setClaimMessage('');
    try {
      await assessmentApi.claimInvitation(token);
      setClaimMessage('🎉 Assessment invitation claimed successfully!');
      // Clean up URL parameter
      window.history.replaceState({}, document.title, window.location.pathname);
      await loadAssignments();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to claim invitation.');
      await loadAssignments();
    } finally {
      setClaiming(false);
    }
  }, [loadAssignments]);

  // Auto-check for invite token in URL (?invite=...)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const inviteParam = params.get('invite');
    if (inviteParam) {
      setClaimToken(inviteParam);
      handleAutoClaim(inviteParam);
    } else {
      loadAssignments();
    }
  }, [handleAutoClaim, loadAssignments]);

  const handleManualClaim = async (e) => {
    e.preventDefault();
    if (!claimToken.trim()) return;
    setClaiming(true);
    setError('');
    setClaimMessage('');
    try {
      await assessmentApi.claimInvitation(claimToken.trim());
      setClaimMessage('🎉 Assessment invitation claimed successfully!');
      setClaimToken('');
      await loadAssignments();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to claim invitation.');
    } finally {
      setClaiming(false);
    }
  };

  const handleStart = async (assignment) => {
    const isResume = assignment.status === 'IN_PROGRESS';
    const confirmMsg = isResume
      ? `Resume your in-progress assessment "${assignment.assessment_title}"? Your timer is continuing.`
      : `Ready to start "${assignment.assessment_title}"?\n\n• Duration: ${assignment.duration_minutes} minutes\n• Timer is server-authoritative and starts immediately\n• All answers are autosaved\n\nClick OK to begin.`;

    if (!window.confirm(confirmMsg)) return;

    setStartingId(assignment.id);
    try {
      const attemptView = await assessmentApi.startAttempt(assignment.id);
      if (onStartAttempt) {
        onStartAttempt(attemptView);
      }
    } catch (err) {
      alert(`Could not start assessment: ${err.response?.data?.detail || err.message}`);
    } finally {
      setStartingId(null);
    }
  };

  return (
    <div style={styles.container}>
      {/* Top Banner */}
      <div style={styles.bannerCard}>
        <div style={styles.bannerLeft}>
          <div style={styles.iconCircle}>📝</div>
          <div>
            <div style={styles.tagRow}>
              <span style={styles.tagBlue}>ENTERPRISE ASSESSMENTS</span>
              <span style={styles.tagGreen}>SERVER-TIMED & SECURE</span>
            </div>
            <h1 style={styles.bannerTitle}>My Assigned Technical Assessments</h1>
            <p style={styles.bannerSubtitle}>
              Take repository-aware evaluations assigned by hiring organizations. Codebase exploration, autosave durability, and explainable scorecards.
            </p>
          </div>
        </div>

        {/* Claim Invitation Form */}
        <form onSubmit={handleManualClaim} style={styles.claimForm}>
          <input
            type="text"
            placeholder="Paste invitation token (e.g. inv_...)"
            value={claimToken}
            onChange={(e) => setClaimToken(e.target.value)}
            style={styles.claimInput}
          />
          <button type="submit" disabled={claiming || !claimToken.trim()} style={styles.claimBtn}>
            {claiming ? 'Claiming...' : 'Claim Invitation'}
          </button>
        </form>
      </div>

      {claimMessage && <div style={styles.successBox}>{claimMessage}</div>}
      {error && (
        <div style={styles.errorBox}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Assignments List */}
      {loading ? (
        <div style={styles.loadingBox}>
          <div style={styles.spinner} />
          <p style={{ marginTop: '12px', color: '#94a3b8' }}>Loading your assigned assessments...</p>
        </div>
      ) : assignments.length === 0 ? (
        <div style={styles.emptyState}>
          <span style={{ fontSize: '40px' }}>📭</span>
          <h3 style={{ margin: '14px 0 6px', color: '#f8fafc' }}>No Assessments Assigned Yet</h3>
          <p style={{ margin: 0, color: '#94a3b8', fontSize: '14px', maxWidth: '460px' }}>
            If a recruiter or hiring team invited you to an assessment, paste your invitation token in the box above to claim it.
          </p>
        </div>
      ) : (
        <div style={styles.cardsGrid}>
          {assignments.map((a) => {
            const isCompleted = a.status === 'COMPLETED';
            const isInProgress = a.status === 'IN_PROGRESS';
            const isRevoked = a.status === 'REVOKED';
            const isExpired = a.status === 'EXPIRED';
            const isReady = a.status === 'PENDING' || a.status === 'AVAILABLE' || isInProgress;

            return (
              <div key={a.id} style={styles.card}>
                <div style={styles.cardHeader}>
                  <div style={styles.orgBadge}>
                    🏢 {a.organization_name || 'Hiring Organization'}
                  </div>
                  <span
                    style={{
                      ...styles.statusBadge,
                      backgroundColor: isInProgress
                        ? '#0284c7'
                        : isCompleted
                        ? '#065f46'
                        : isRevoked
                        ? '#7f1d1d'
                        : isExpired
                        ? '#334155'
                        : '#1e3a8a',
                      color: isInProgress
                        ? '#38bdf8'
                        : isCompleted
                        ? '#34d399'
                        : isRevoked
                        ? '#fca5a5'
                        : isExpired
                        ? '#94a3b8'
                        : '#93c5fd',
                    }}
                  >
                    {a.status}
                  </span>
                </div>

                <h3 style={styles.cardTitle}>{a.assessment_title}</h3>
                <div style={styles.roleSub}>Role: {a.job_role || 'Software Engineering'}</div>

                {a.instructions && (
                  <p style={styles.instructionsText}>
                    {a.instructions.length > 140 ? `${a.instructions.slice(0, 140)}...` : a.instructions}
                  </p>
                )}

                <div style={styles.specsRow}>
                  <div style={styles.specItem}>
                    <span style={styles.specLabel}>Duration</span>
                    <span style={styles.specVal}>⏱️ {a.duration_minutes} mins</span>
                  </div>
                  <div style={styles.specItem}>
                    <span style={styles.specLabel}>Questions</span>
                    <span style={styles.specVal}>📋 {a.question_count || '~'} Qs</span>
                  </div>
                  <div style={styles.specItem}>
                    <span style={styles.specLabel}>Pass Threshold</span>
                    <span style={styles.specVal}>{a.passing_score_pct ? `${a.passing_score_pct}%` : 'N/A'}</span>
                  </div>
                </div>

                {/* Expiry and attempts metadata */}
                <div style={styles.metaRow}>
                  {a.expires_at && (
                    <span style={{ fontSize: '12px', color: '#94a3b8' }}>
                      Expires: {new Date(a.expires_at).toLocaleDateString()}
                    </span>
                  )}
                  {a.last_attempt_status && (
                    <span style={{ fontSize: '12px', color: '#38bdf8' }}>
                      Last Attempt: {a.last_attempt_status}
                    </span>
                  )}
                </div>

                {/* Actions */}
                <div style={styles.cardFooter}>
                  {isReady && (
                    <button
                      onClick={() => handleStart(a)}
                      disabled={startingId === a.id}
                      style={{
                        ...styles.startBtn,
                        backgroundColor: isInProgress ? '#0284c7' : '#2563eb',
                      }}
                    >
                      {startingId === a.id
                        ? 'Preparing workspace...'
                        : isInProgress
                        ? '⚡ Resume Assessment'
                        : '🚀 Start Assessment'}
                    </button>
                  )}

                  {isCompleted && (
                    <button
                      onClick={() => onViewResult && onViewResult(a)}
                      style={styles.viewResultBtn}
                    >
                      📊 View Results & Feedback
                    </button>
                  )}

                  {(isRevoked || isExpired) && (
                    <span style={{ fontSize: '13px', color: '#94a3b8', fontStyle: 'italic' }}>
                      {isRevoked ? 'Invitation was revoked by hiring team' : 'Assessment window expired'}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
    maxWidth: '1200px',
    margin: '0 auto',
  },
  bannerCard: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '12px',
    padding: '24px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '20px',
  },
  bannerLeft: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '16px',
    maxWidth: '650px',
  },
  iconCircle: {
    fontSize: '28px',
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '10px',
    width: '52px',
    height: '52px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  tagRow: {
    display: 'flex',
    gap: '8px',
    marginBottom: '6px',
  },
  tagBlue: {
    fontSize: '10px',
    fontWeight: '700',
    backgroundColor: '#0284c7',
    color: '#ffffff',
    padding: '2px 8px',
    borderRadius: '4px',
    letterSpacing: '0.04em',
  },
  tagGreen: {
    fontSize: '10px',
    fontWeight: '700',
    backgroundColor: '#065f46',
    color: '#34d399',
    padding: '2px 8px',
    borderRadius: '4px',
  },
  bannerTitle: {
    fontSize: '22px',
    fontWeight: '800',
    color: '#f8fafc',
    margin: '0 0 6px',
  },
  bannerSubtitle: {
    fontSize: '13px',
    color: '#94a3b8',
    margin: 0,
    lineHeight: '1.5',
  },
  claimForm: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  claimInput: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '6px',
    padding: '10px 14px',
    color: '#f8fafc',
    fontSize: '13px',
    width: '260px',
    outline: 'none',
  },
  claimBtn: {
    backgroundColor: '#2563eb',
    color: '#ffffff',
    border: 'none',
    borderRadius: '6px',
    padding: '10px 16px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  successBox: {
    backgroundColor: '#064e3b',
    border: '1px solid #059669',
    color: '#6ee7b7',
    padding: '12px 16px',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '600',
  },
  errorBox: {
    backgroundColor: '#451a1a',
    border: '1px solid #ef4444',
    color: '#fca5a5',
    padding: '12px 16px',
    borderRadius: '8px',
    fontSize: '13px',
  },
  loadingBox: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 20px',
    backgroundColor: '#1e293b',
    borderRadius: '12px',
    border: '1px solid #334155',
  },
  spinner: {
    width: '32px',
    height: '32px',
    border: '3px solid #334155',
    borderTopColor: '#38bdf8',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    textAlign: 'center',
    padding: '60px 20px',
    backgroundColor: '#1e293b',
    borderRadius: '12px',
    border: '1px solid #334155',
  },
  cardsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
    gap: '20px',
  },
  card: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '12px',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    transition: 'transform 0.15s ease, border-color 0.15s ease',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  orgBadge: {
    fontSize: '12px',
    color: '#94a3b8',
    fontWeight: '600',
  },
  statusBadge: {
    fontSize: '11px',
    fontWeight: '700',
    padding: '3px 8px',
    borderRadius: '12px',
  },
  cardTitle: {
    fontSize: '17px',
    fontWeight: '700',
    color: '#f8fafc',
    margin: 0,
  },
  roleSub: {
    fontSize: '12px',
    color: '#38bdf8',
  },
  instructionsText: {
    fontSize: '13px',
    color: '#cbd5e1',
    lineHeight: '1.4',
    margin: 0,
    backgroundColor: '#0f172a',
    padding: '10px 12px',
    borderRadius: '6px',
    border: '1px solid #334155',
  },
  specsRow: {
    display: 'flex',
    justifyContent: 'space-between',
    backgroundColor: '#0f172a',
    borderRadius: '8px',
    padding: '10px 14px',
    border: '1px solid #334155',
  },
  specItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  specLabel: {
    fontSize: '10px',
    color: '#94a3b8',
    textTransform: 'uppercase',
    fontWeight: '700',
  },
  specVal: {
    fontSize: '13px',
    color: '#f8fafc',
    fontWeight: '600',
  },
  metaRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cardFooter: {
    marginTop: 'auto',
    paddingTop: '8px',
    borderTop: '1px solid #334155',
  },
  startBtn: {
    width: '100%',
    padding: '11px',
    border: 'none',
    borderRadius: '6px',
    color: '#ffffff',
    fontSize: '14px',
    fontWeight: '700',
    cursor: 'pointer',
    transition: 'background-color 0.15s ease',
  },
  viewResultBtn: {
    width: '100%',
    padding: '11px',
    backgroundColor: '#059669',
    border: 'none',
    borderRadius: '6px',
    color: '#ffffff',
    fontSize: '14px',
    fontWeight: '700',
    cursor: 'pointer',
  },
};
