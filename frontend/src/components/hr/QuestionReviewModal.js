import React, { useState } from 'react';
import { hrApi } from '../../services/hrApi';

export default function QuestionReviewModal({
  orgId,
  question,
  onClose,
  onActionComplete,
  onOpenEdit,
}) {
  const [reviewerNotes, setReviewerNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleAction = async (action) => {
    setSubmitting(true);
    setError('');
    try {
      await hrApi.transitionQuestion(orgId, question.id, action, reviewerNotes.trim());
      onActionComplete();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || `Failed to execute ${action}.`);
    } finally {
      setSubmitting(false);
    }
  };

  const isApproved = question.review_status === 'APPROVED';
  const isPublished = question.review_status === 'PUBLISHED';
  const isArchived = question.review_status === 'ARCHIVED' || question.is_archived === 1;

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        {/* Header */}
        <div style={styles.header}>
          <div>
            <div style={styles.badge}>HR QUESTION REVIEW & LIFECYCLE</div>
            <h3 style={styles.title}>Review & Authorize Question (v{question.version})</h3>
            <p style={styles.subtext}>
              Review pedagogical accuracy, evidence grounding, and verify answer keys before publication.
            </p>
          </div>
          <button style={styles.closeBtn} onClick={onClose}>&times;</button>
        </div>

        {/* Content Body */}
        <div style={styles.body}>
          {error && <div style={styles.errorBox}>{error}</div>}

          {/* Status Bar */}
          <div style={styles.statusBar}>
            <div style={styles.statusItem}>
              <span style={styles.statusLabel}>Review Lifecycle:</span>
              <span
                style={{
                  ...styles.statusBadge,
                  backgroundColor: isPublished
                    ? 'rgba(16, 185, 129, 0.15)'
                    : isApproved
                    ? 'rgba(56, 189, 248, 0.15)'
                    : isArchived
                    ? 'rgba(100, 116, 139, 0.2)'
                    : 'rgba(245, 158, 11, 0.15)',
                  color: isPublished ? '#10b981' : isApproved ? '#38bdf8' : isArchived ? '#94a3b8' : '#f59e0b',
                }}
              >
                {question.review_status}
              </span>
            </div>

            <div style={styles.statusItem}>
              <span style={styles.statusLabel}>Automated Validation:</span>
              <span
                style={{
                  ...styles.statusBadge,
                  backgroundColor: question.validation_status === 'VALIDATED'
                    ? 'rgba(16, 185, 129, 0.15)'
                    : 'rgba(239, 68, 68, 0.15)',
                  color: question.validation_status === 'VALIDATED' ? '#10b981' : '#ef4444',
                }}
              >
                {question.validation_status || 'VALIDATED'}
              </span>
            </div>

            <div style={styles.statusItem}>
              <span style={styles.statusLabel}>Source:</span>
              <span style={{ ...styles.statusBadge, backgroundColor: 'rgba(148, 163, 184, 0.1)', color: '#cbd5e1' }}>
                {question.source_type}
              </span>
            </div>
          </div>

          {/* Question Text */}
          <div style={styles.sectionLabel}>QUESTION TEXT</div>
          <div style={styles.questionBox}>{question.question_text}</div>

          {/* Options & Key */}
          <div style={styles.sectionLabel}>OPTIONS & ANSWER KEY (HR VIEW)</div>
          <div style={styles.optionsList}>
            {question.options?.map((opt) => {
              const optKey = opt.id || opt.key;
              const isCorrect = (question.answer_key || []).includes(optKey);
              return (
                <div
                  key={optKey}
                  style={{
                    ...styles.optionRow,
                    borderColor: isCorrect ? '#10b981' : '#334155',
                    backgroundColor: isCorrect ? 'rgba(16, 185, 129, 0.08)' : '#1e293b',
                  }}
                >
                  <span
                    style={{
                      ...styles.optKeyBadge,
                      backgroundColor: isCorrect ? '#10b981' : '#334155',
                      color: isCorrect ? '#0f172a' : '#cbd5e1',
                    }}
                  >
                    {optKey}
                  </span>
                  <span style={styles.optText}>{opt.text}</span>
                  {isCorrect && (
                    <span style={styles.correctBadge}>
                      ✓ Keyed Answer
                    </span>
                  )}
                </div>
              );
            })}
          </div>

          {/* Explanation */}
          <div style={styles.sectionLabel}>EXPLANATION & RATIONALE</div>
          <div style={styles.explanationBox}>{question.explanation}</div>

          {/* Evidence References (Mode B) */}
          {question.evidence_references && question.evidence_references.length > 0 && (
            <div>
              <div style={styles.sectionLabel}>SOURCE EVIDENCE REFERENCES (GROUNDING)</div>
              <div style={styles.evidenceContainer}>
                {question.evidence_references.map((ev, i) => (
                  <div key={i} style={styles.evidenceCard}>
                    <div style={styles.evidenceTop}>
                      <span style={styles.evidencePath}>{ev.file_path || ev.target || 'Code File'}</span>
                      {ev.entity_name && (
                        <span style={styles.evidenceEntity}>{ev.entity_type || 'Symbol'}: {ev.entity_name}</span>
                      )}
                    </div>
                    {ev.snippet && (
                      <pre style={styles.evidenceSnippet}>{ev.snippet}</pre>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Reviewer Notes Field */}
          <div style={{ marginTop: '16px' }}>
            <label style={styles.sectionLabel}>ADD REVIEWER AUDIT NOTES</label>
            <input
              type="text"
              value={reviewerNotes}
              onChange={(e) => setReviewerNotes(e.target.value)}
              placeholder="e.g. Verified against architectural guidelines. Pedagogically solid."
              style={styles.notesInput}
            />
          </div>
        </div>

        {/* Footer Actions */}
        <div style={styles.footer}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              style={styles.editBtn}
              onClick={() => {
                onClose();
                onOpenEdit(question);
              }}
            >
              ✏️ Edit Draft
            </button>
            {!isArchived ? (
              <button
                style={styles.archiveBtn}
                disabled={submitting}
                onClick={() => handleAction('ARCHIVE')}
              >
                Archive
              </button>
            ) : (
              <button
                style={styles.restoreBtn}
                disabled={submitting}
                onClick={() => handleAction('RESTORE')}
              >
                Restore to Review
              </button>
            )}
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            {!isApproved && !isPublished && (
              <button
                style={styles.rejectBtn}
                disabled={submitting}
                onClick={() => handleAction('REJECT')}
              >
                Reject / Needs Revision
              </button>
            )}

            {!isApproved && !isPublished && (
              <button
                style={styles.approveBtn}
                disabled={submitting}
                onClick={() => handleAction('APPROVE')}
              >
                {submitting ? 'Processing...' : 'Approve Question'}
              </button>
            )}

            {isApproved && !isPublished && (
              <button
                style={styles.publishBtn}
                disabled={submitting}
                onClick={() => handleAction('PUBLISH')}
              >
                {submitting ? 'Publishing...' : 'Publish to Bank'}
              </button>
            )}

            {isPublished && (
              <div style={styles.publishedStatusBadge}>
                ✓ Published & Active in Question Bank
              </div>
            )}
          </div>
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
    maxWidth: '860px',
    maxHeight: '92vh',
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
    padding: '20px 24px',
    overflowY: 'auto',
    flex: 1,
  },
  statusBar: {
    display: 'flex',
    gap: '24px',
    padding: '12px 16px',
    backgroundColor: '#1e293b',
    borderRadius: '8px',
    marginBottom: '20px',
    border: '1px solid #334155',
  },
  statusItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  statusLabel: {
    fontSize: '12px',
    color: '#94a3b8',
  },
  statusBadge: {
    fontSize: '11px',
    fontWeight: '700',
    padding: '2px 8px',
    borderRadius: '4px',
  },
  sectionLabel: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#64748b',
    letterSpacing: '0.05em',
    marginBottom: '8px',
    display: 'block',
  },
  questionBox: {
    fontSize: '16px',
    fontWeight: '500',
    color: '#f8fafc',
    lineHeight: '1.6',
    backgroundColor: '#1e293b',
    padding: '16px',
    borderRadius: '8px',
    border: '1px solid #334155',
    marginBottom: '16px',
  },
  optionsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    marginBottom: '16px',
  },
  optionRow: {
    display: 'flex',
    alignItems: 'center',
    padding: '10px 14px',
    borderRadius: '6px',
    border: '1px solid #334155',
  },
  optKeyBadge: {
    width: '26px',
    height: '26px',
    borderRadius: '4px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '12px',
    fontWeight: '700',
    marginRight: '12px',
    flexShrink: 0,
  },
  optText: {
    fontSize: '14px',
    color: '#e2e8f0',
    flex: 1,
  },
  correctBadge: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#10b981',
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    padding: '3px 10px',
    borderRadius: '4px',
  },
  explanationBox: {
    fontSize: '14px',
    color: '#cbd5e1',
    lineHeight: '1.5',
    backgroundColor: '#1e293b',
    padding: '14px 16px',
    borderRadius: '8px',
    border: '1px solid #334155',
    marginBottom: '16px',
  },
  evidenceContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    marginBottom: '16px',
  },
  evidenceCard: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '6px',
    padding: '10px 14px',
  },
  evidenceTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '6px',
  },
  evidencePath: {
    fontSize: '12px',
    color: '#38bdf8',
    fontFamily: 'monospace',
  },
  evidenceEntity: {
    fontSize: '11px',
    color: '#94a3b8',
  },
  evidenceSnippet: {
    margin: 0,
    fontSize: '12px',
    fontFamily: 'monospace',
    color: '#94a3b8',
    backgroundColor: '#1e293b',
    padding: '8px',
    borderRadius: '4px',
    overflowX: 'auto',
  },
  notesInput: {
    width: '100%',
    padding: '10px 14px',
    borderRadius: '6px',
    border: '1px solid #334155',
    backgroundColor: '#1e293b',
    color: '#f8fafc',
    fontSize: '14px',
    outline: 'none',
    boxSizing: 'border-box',
  },
  errorBox: {
    padding: '12px 16px',
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid #ef4444',
    color: '#fca5a5',
    borderRadius: '6px',
    fontSize: '13px',
    marginBottom: '16px',
  },
  footer: {
    padding: '16px 24px',
    borderTop: '1px solid #1e293b',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  editBtn: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    color: '#f8fafc',
    padding: '8px 16px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  archiveBtn: {
    backgroundColor: 'transparent',
    border: '1px solid #64748b',
    color: '#94a3b8',
    padding: '8px 16px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  restoreBtn: {
    backgroundColor: 'transparent',
    border: '1px solid #38bdf8',
    color: '#38bdf8',
    padding: '8px 16px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  rejectBtn: {
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    border: '1px solid #ef4444',
    color: '#fca5a5',
    padding: '8px 18px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  approveBtn: {
    backgroundColor: '#38bdf8',
    border: 'none',
    color: '#0f172a',
    padding: '8px 20px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '700',
    cursor: 'pointer',
  },
  publishBtn: {
    backgroundColor: '#10b981',
    border: 'none',
    color: '#0f172a',
    padding: '8px 22px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '700',
    cursor: 'pointer',
  },
  publishedStatusBadge: {
    color: '#10b981',
    fontSize: '13px',
    fontWeight: '600',
    padding: '8px 12px',
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    borderRadius: '6px',
  },
};
