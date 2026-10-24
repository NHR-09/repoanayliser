import React, { useState, useEffect, useCallback } from 'react';
import { assessmentApi } from '../../services/assessmentApi';

export default function CandidateAssignmentModal({ orgId, assessment, onClose }) {
  const [activeTab, setActiveTab] = useState('new'); // 'new' | 'existing'
  const [candidateEmails, setCandidateEmails] = useState('');
  const [expiresDays, setExpiresDays] = useState(7);
  const [maxAttempts, setMaxAttempts] = useState(assessment?.max_attempts_per_candidate || 1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [generatedInvitations, setGeneratedInvitations] = useState([]);
  const [existingAssignments, setExistingAssignments] = useState([]);
  const [loadingExisting, setLoadingExisting] = useState(false);
  const [copiedToken, setCopiedToken] = useState(null);

  const loadExistingAssignments = useCallback(async () => {
    setLoadingExisting(true);
    try {
      const data = await assessmentApi.getAssignments(orgId, assessment?.id);
      setExistingAssignments(data || []);
    } catch (err) {
      console.error('Failed to load assignments:', err);
    } finally {
      setLoadingExisting(false);
    }
  }, [orgId, assessment?.id]);

  useEffect(() => {
    if (activeTab === 'existing') {
      loadExistingAssignments();
    }
  }, [activeTab, loadExistingAssignments]);

  const handleAssignSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const emails = candidateEmails
      .split(/[\n,;]+/)
      .map((e) => e.trim())
      .filter((e) => e.includes('@'));

    if (emails.length === 0) {
      setError('Please provide at least one valid candidate email address.');
      return;
    }

    setLoading(true);
    try {
      const res = await assessmentApi.assignAssessment(orgId, assessment.id, {
        candidate_emails: emails,
        expires_days: Number(expiresDays),
        max_attempts: Number(maxAttempts),
      });
      setGeneratedInvitations(res.invitations || []);
      setCandidateEmails('');
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to create assessment invitations.');
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async (assignmentId) => {
    if (!window.confirm('Are you sure you want to revoke this candidate invitation?')) return;
    try {
      await assessmentApi.revokeAssignment(orgId, assignmentId, 'Revoked by recruiter');
      loadExistingAssignments();
    } catch (err) {
      alert(err.response?.data?.detail || err.message || 'Failed to revoke assignment.');
    }
  };

  const copyToClipboard = (text, tokenKey) => {
    const fullUrl = `${window.location.origin}${text}`;
    navigator.clipboard.writeText(fullUrl);
    setCopiedToken(tokenKey);
    setTimeout(() => setCopiedToken(null), 2500);
  };

  return (
    <div style={styles.backdrop}>
      <div style={styles.modal}>
        {/* Header */}
        <div style={styles.header}>
          <div>
            <div style={styles.badgeRow}>
              <span style={styles.tagBlue}>CANDIDATE ASSIGNMENT</span>
              <span style={styles.tagZinc}>VERSION {assessment.version || 1}</span>
            </div>
            <h2 style={styles.title}>{assessment.title}</h2>
            <p style={styles.subtitle}>
              Generate expiring, single-use invitation links for candidate assessment evaluation.
            </p>
          </div>
          <button onClick={onClose} style={styles.closeBtn}>✕</button>
        </div>

        {/* Tab switcher */}
        <div style={styles.tabBar}>
          <button
            onClick={() => setActiveTab('new')}
            style={{
              ...styles.tabBtn,
              ...(activeTab === 'new' ? styles.tabBtnActive : {}),
            }}
          >
            ✉️ Issue New Invitations
          </button>
          <button
            onClick={() => setActiveTab('existing')}
            style={{
              ...styles.tabBtn,
              ...(activeTab === 'existing' ? styles.tabBtnActive : {}),
            }}
          >
            📋 Manage Assigned Candidates ({existingAssignments.length || assessment.assigned_candidates_count || 0})
          </button>
        </div>

        {/* Tab 1: Issue New Invitations */}
        {activeTab === 'new' && (
          <div style={styles.body}>
            {error && <div style={styles.errorBox}>{error}</div>}

            <form onSubmit={handleAssignSubmit} style={styles.form}>
              <div style={styles.formGroup}>
                <label style={styles.label}>
                  Candidate Email Addresses <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <textarea
                  value={candidateEmails}
                  onChange={(e) => setCandidateEmails(e.target.value)}
                  placeholder="Enter one email per line (e.g. alice@example.com, bob@company.org)..."
                  rows={4}
                  style={styles.textarea}
                  required
                />
                <span style={styles.hint}>Comma, semicolon, or newline separated.</span>
              </div>

              <div style={styles.rowTwo}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>Invitation Expiry (Days)</label>
                  <input
                    type="number"
                    min="1"
                    max="60"
                    value={expiresDays}
                    onChange={(e) => setExpiresDays(e.target.value)}
                    style={styles.input}
                  />
                </div>
                <div style={styles.formGroup}>
                  <label style={styles.label}>Max Attempts Allowed</label>
                  <input
                    type="number"
                    min="1"
                    max="5"
                    value={maxAttempts}
                    onChange={(e) => setMaxAttempts(e.target.value)}
                    style={styles.input}
                  />
                </div>
              </div>

              <div style={styles.actionsBar}>
                <button type="button" onClick={onClose} style={styles.cancelBtn}>
                  Cancel
                </button>
                <button type="submit" disabled={loading} style={styles.primaryBtn}>
                  {loading ? 'Generating Secure Tokens...' : 'Generate Invitations'}
                </button>
              </div>
            </form>

            {/* Generated links showcase */}
            {generatedInvitations.length > 0 && (
              <div style={styles.invitationListCard}>
                <div style={styles.invListHeader}>
                  <span style={{ fontSize: '18px' }}>🎉</span>
                  <h4 style={styles.invListTitle}>
                    {generatedInvitations.length} Invitation Link(s) Generated
                  </h4>
                </div>
                <p style={styles.invListDesc}>
                  Share these private invitation links with your candidates. Raw tokens are never stored in plaintext.
                </p>

                <div style={styles.invitationItems}>
                  {generatedInvitations.map((inv) => {
                    const isCopied = copiedToken === inv.invitation_token;
                    return (
                      <div key={inv.assignment_id} style={styles.invitationRow}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={styles.invEmail}>{inv.candidate_email}</div>
                          <code style={styles.invUrl}>{`${window.location.origin}${inv.invitation_url}`}</code>
                        </div>
                        <button
                          type="button"
                          onClick={() => copyToClipboard(inv.invitation_url, inv.invitation_token)}
                          style={{
                            ...styles.copyBtn,
                            backgroundColor: isCopied ? 'rgba(16, 185, 129, 0.2)' : '#334155',
                            borderColor: isCopied ? '#10b981' : '#475569',
                            color: isCopied ? '#10b981' : '#f8fafc',
                          }}
                        >
                          {isCopied ? '✓ Copied!' : 'Copy Link'}
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Existing Assignments */}
        {activeTab === 'existing' && (
          <div style={styles.body}>
            {loadingExisting ? (
              <div style={styles.loadingBox}>Loading candidate assignments...</div>
            ) : existingAssignments.length === 0 ? (
              <div style={styles.emptyBox}>No candidates have been assigned to this assessment yet.</div>
            ) : (
              <div style={styles.tableWrap}>
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th style={styles.th}>Candidate</th>
                      <th style={styles.th}>Status</th>
                      <th style={styles.th}>Attempts</th>
                      <th style={styles.th}>Score</th>
                      <th style={styles.th}>Expires</th>
                      <th style={styles.th}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {existingAssignments.map((a) => (
                      <tr key={a.id} style={styles.tr}>
                        <td style={styles.td}>
                          <div style={{ fontWeight: '600', color: '#f8fafc' }}>
                            {a.candidate_name || a.candidate_email}
                          </div>
                          {a.candidate_name && (
                            <div style={{ fontSize: '11px', color: '#94a3b8' }}>{a.candidate_email}</div>
                          )}
                        </td>
                        <td style={styles.td}>
                          <span
                            style={{
                              ...styles.statusTag,
                              backgroundColor:
                                a.status === 'COMPLETED'
                                  ? 'rgba(16, 185, 129, 0.15)'
                                  : a.status === 'IN_PROGRESS'
                                  ? 'rgba(56, 189, 248, 0.15)'
                                  : a.status === 'REVOKED'
                                  ? 'rgba(239, 68, 68, 0.15)'
                                  : '#334155',
                              color:
                                a.status === 'COMPLETED'
                                  ? '#10b981'
                                  : a.status === 'IN_PROGRESS'
                                  ? '#38bdf8'
                                  : a.status === 'REVOKED'
                                  ? '#ef4444'
                                  : '#94a3b8',
                            }}
                          >
                            {a.status}
                          </span>
                        </td>
                        <td style={styles.td}>
                          {a.attempts_used || 0} / {a.max_attempts || 1}
                        </td>
                        <td style={styles.td}>
                          {a.latest_attempt_score != null ? `${a.latest_attempt_score}%` : '—'}
                        </td>
                        <td style={styles.td}>
                          <span style={{ fontSize: '12px', color: '#94a3b8' }}>
                            {a.expires_at ? new Date(a.expires_at).toLocaleDateString() : '—'}
                          </span>
                        </td>
                        <td style={styles.td}>
                          {a.status !== 'REVOKED' && a.status !== 'COMPLETED' && (
                            <button
                              onClick={() => handleRevoke(a.id)}
                              style={styles.revokeBtn}
                              title="Revoke invitation"
                            >
                              Revoke
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
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
    maxWidth: '780px',
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
  closeBtn: {
    background: 'none',
    border: 'none',
    color: '#94a3b8',
    fontSize: '20px',
    cursor: 'pointer',
    padding: '4px',
  },
  tabBar: {
    display: 'flex',
    borderBottom: '1px solid #334155',
    backgroundColor: '#0f172a',
  },
  tabBtn: {
    flex: 1,
    padding: '12px',
    backgroundColor: 'transparent',
    border: 'none',
    borderBottom: '2px solid transparent',
    color: '#94a3b8',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
    textAlign: 'center',
  },
  tabBtnActive: {
    color: '#38bdf8',
    borderBottomColor: '#38bdf8',
    backgroundColor: '#1e293b',
  },
  body: {
    padding: '24px',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  rowTwo: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '16px',
  },
  label: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#94a3b8',
    textTransform: 'uppercase',
  },
  input: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '8px',
    color: '#f8fafc',
    padding: '10px 14px',
    fontSize: '14px',
    outline: 'none',
  },
  textarea: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '8px',
    color: '#f8fafc',
    padding: '12px 14px',
    fontSize: '13px',
    lineHeight: '1.5',
    outline: 'none',
    fontFamily: 'monospace',
    resize: 'vertical',
  },
  hint: {
    fontSize: '11px',
    color: '#64748b',
  },
  actionsBar: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    marginTop: '8px',
  },
  cancelBtn: {
    backgroundColor: '#334155',
    color: '#f8fafc',
    border: 'none',
    padding: '9px 18px',
    borderRadius: '8px',
    fontSize: '13px',
    cursor: 'pointer',
  },
  primaryBtn: {
    backgroundColor: '#38bdf8',
    color: '#0f172a',
    border: 'none',
    padding: '9px 20px',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  errorBox: {
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    color: '#fca5a5',
    padding: '10px 14px',
    borderRadius: '8px',
    fontSize: '13px',
  },
  invitationListCard: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '10px',
    padding: '18px',
  },
  invListHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  invListTitle: {
    margin: 0,
    fontSize: '15px',
    fontWeight: '600',
    color: '#f8fafc',
  },
  invListDesc: {
    margin: '4px 0 14px',
    fontSize: '12px',
    color: '#94a3b8',
  },
  invitationItems: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  invitationRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '8px',
    padding: '10px 14px',
    gap: '12px',
  },
  invEmail: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#38bdf8',
    marginBottom: '2px',
  },
  invUrl: {
    fontSize: '11px',
    color: '#94a3b8',
    wordBreak: 'break-all',
  },
  copyBtn: {
    border: '1px solid',
    borderRadius: '6px',
    padding: '6px 12px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    transition: 'all 0.15s ease',
  },
  tableWrap: {
    overflowX: 'auto',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    textAlign: 'left',
    fontSize: '13px',
  },
  th: {
    padding: '10px 12px',
    borderBottom: '1px solid #334155',
    color: '#94a3b8',
    fontSize: '11px',
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  tr: {
    borderBottom: '1px solid #1e293b',
  },
  td: {
    padding: '12px',
    color: '#f8fafc',
  },
  statusTag: {
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '600',
  },
  revokeBtn: {
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    color: '#ef4444',
    padding: '4px 10px',
    borderRadius: '6px',
    fontSize: '11px',
    cursor: 'pointer',
  },
  loadingBox: {
    padding: '30px',
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
};
