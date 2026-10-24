import React, { useState, useEffect } from 'react';
import { hrApi } from '../../services/hrApi';

export default function QuestionPreviewModal({ orgId, questionId, onClose }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [preview, setPreview] = useState(null);
  const [selectedAnswers, setSelectedAnswers] = useState([]);

  useEffect(() => {
    loadPreview();
  }, [orgId, questionId]);

  const loadPreview = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await hrApi.previewQuestion(orgId, questionId);
      setPreview(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load question preview.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectOption = (key) => {
    if (preview?.response_format === 'MULTI_SELECT') {
      if (selectedAnswers.includes(key)) {
        setSelectedAnswers(selectedAnswers.filter((k) => k !== key));
      } else {
        setSelectedAnswers([...selectedAnswers, key]);
      }
    } else {
      setSelectedAnswers([key]);
    }
  };

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        {/* Header */}
        <div style={styles.header}>
          <div>
            <div style={styles.badge}>CANDIDATE MODE PREVIEW</div>
            <h3 style={styles.title}>Simulated Candidate Experience</h3>
            <p style={styles.subtext}>
              Answer keys, evidence citations, and explanations are strictly redacted to simulate exam conditions.
            </p>
          </div>
          <button style={styles.closeBtn} onClick={onClose}>&times;</button>
        </div>

        {/* Content */}
        <div style={styles.body}>
          {loading && (
            <div style={styles.loadingBox}>
              <div style={styles.spinner} />
              <p style={{ marginTop: '12px', color: '#94a3b8' }}>Loading preview...</p>
            </div>
          )}

          {error && <div style={styles.errorBox}>{error}</div>}

          {preview && (
            <div style={styles.previewCard}>
              <div style={styles.metaRow}>
                <span style={styles.metaPill}>{preview.competency?.replace('_', ' ')}</span>
                <span style={{ ...styles.metaPill, borderColor: '#38bdf8', color: '#38bdf8' }}>
                  {preview.difficulty}
                </span>
                <span style={styles.metaPill}>{preview.response_format?.replace('_', ' ')}</span>
              </div>

              <div style={styles.questionText}>
                {preview.question_text}
              </div>

              {preview.skill_tags && preview.skill_tags.length > 0 && (
                <div style={styles.tagsRow}>
                  {preview.skill_tags.map((tag, idx) => (
                    <span key={idx} style={styles.tag}>#{tag}</span>
                  ))}
                </div>
              )}

              <div style={styles.optionsContainer}>
                {preview.options?.map((opt) => {
                  const optKey = opt.id || opt.key;
                  const isSelected = selectedAnswers.includes(optKey);
                  return (
                    <div
                      key={optKey}
                      onClick={() => handleSelectOption(optKey)}
                      style={{
                        ...styles.optionRow,
                        borderColor: isSelected ? '#38bdf8' : '#334155',
                        backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.08)' : '#1e293b',
                      }}
                    >
                      <div
                        style={{
                          ...styles.optionIndicator,
                          borderColor: isSelected ? '#38bdf8' : '#64748b',
                          backgroundColor: isSelected ? '#38bdf8' : 'transparent',
                          color: isSelected ? '#0f172a' : '#94a3b8',
                        }}
                      >
                        {optKey}
                      </div>
                      <div style={styles.optionText}>{opt.text}</div>
                    </div>
                  );
                })}
              </div>

              <div style={styles.securityNotice}>
                <span style={{ marginRight: '6px' }}>🔒</span>
                <strong>Integrity Verification:</strong> Answer key is securely hidden from candidate view.
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={styles.footer}>
          <button style={styles.doneBtn} onClick={onClose}>
            Close Preview
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
    maxWidth: '720px',
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
    display: 'inline-block',
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
  loadingBox: {
    textAlign: 'center',
    padding: '40px',
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
    borderRadius: '8px',
    fontSize: '14px',
  },
  previewCard: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '10px',
    padding: '24px',
  },
  metaRow: {
    display: 'flex',
    gap: '8px',
    marginBottom: '16px',
    flexWrap: 'wrap',
  },
  metaPill: {
    fontSize: '11px',
    fontWeight: '600',
    padding: '3px 10px',
    borderRadius: '12px',
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    color: '#cbd5e1',
    textTransform: 'uppercase',
  },
  questionText: {
    fontSize: '16px',
    fontWeight: '500',
    color: '#f8fafc',
    lineHeight: '1.6',
    marginBottom: '16px',
  },
  tagsRow: {
    display: 'flex',
    gap: '6px',
    marginBottom: '20px',
    flexWrap: 'wrap',
  },
  tag: {
    fontSize: '12px',
    color: '#94a3b8',
    backgroundColor: '#0f172a',
    padding: '2px 8px',
    borderRadius: '4px',
  },
  optionsContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    marginBottom: '20px',
  },
  optionRow: {
    display: 'flex',
    alignItems: 'center',
    padding: '12px 16px',
    borderRadius: '8px',
    border: '1px solid #334155',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  optionIndicator: {
    width: '28px',
    height: '28px',
    borderRadius: '6px',
    border: '1px solid #64748b',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '13px',
    fontWeight: '700',
    marginRight: '14px',
    flexShrink: 0,
  },
  optionText: {
    fontSize: '14px',
    color: '#e2e8f0',
    lineHeight: '1.5',
  },
  securityNotice: {
    fontSize: '12px',
    color: '#10b981',
    display: 'flex',
    alignItems: 'center',
    padding: '8px 12px',
    backgroundColor: 'rgba(16, 185, 129, 0.08)',
    borderRadius: '6px',
    border: '1px solid rgba(16, 185, 129, 0.2)',
  },
  footer: {
    padding: '16px 24px',
    borderTop: '1px solid #1e293b',
    display: 'flex',
    justifyContent: 'flex-end',
  },
  doneBtn: {
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
