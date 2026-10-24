import React, { useState, useEffect } from 'react';
import { hrApi } from '../../services/hrApi';

export default function QuestionVersionHistoryModal({ orgId, questionId, onClose }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [versions, setVersions] = useState([]);
  const [selectedVersion, setSelectedVersion] = useState(null);

  useEffect(() => {
    loadVersions();
  }, [orgId, questionId]);

  const loadVersions = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await hrApi.getQuestionVersions(orgId, questionId);
      setVersions(data);
      if (data.length > 0) {
        setSelectedVersion(data[0]);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load version history.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        {/* Header */}
        <div style={styles.header}>
          <div>
            <div style={styles.badge}>PROVENANCE & AUDIT TRAIL</div>
            <h3 style={styles.title}>Immutable Question Version History</h3>
            <p style={styles.subtext}>
              Every published update generates a new immutable snapshot to preserve candidate attempt integrity.
            </p>
          </div>
          <button style={styles.closeBtn} onClick={onClose}>&times;</button>
        </div>

        {/* Content */}
        <div style={styles.body}>
          {loading && (
            <div style={styles.loadingBox}>
              <div style={styles.spinner} />
              <p style={{ marginTop: '12px', color: '#94a3b8' }}>Loading version snapshots...</p>
            </div>
          )}

          {error && <div style={styles.errorBox}>{error}</div>}

          {!loading && versions.length === 0 && (
            <div style={{ textAlign: 'center', padding: '30px', color: '#94a3b8' }}>
              No version history records found.
            </div>
          )}

          {!loading && versions.length > 0 && (
            <div style={styles.columns}>
              {/* Version List Sidebar */}
              <div style={styles.sidebar}>
                <div style={styles.sidebarTitle}>VERSIONS ({versions.length})</div>
                <div style={styles.versionList}>
                  {versions.map((v) => {
                    const isSelected = selectedVersion?.version === v.version;
                    return (
                      <div
                        key={v.id || v.version}
                        onClick={() => setSelectedVersion(v)}
                        style={{
                          ...styles.versionCard,
                          borderColor: isSelected ? '#38bdf8' : '#334155',
                          backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.08)' : '#1e293b',
                        }}
                      >
                        <div style={styles.versionTop}>
                          <span style={styles.versionNumber}>Version {v.version}</span>
                          <span
                            style={{
                              ...styles.statusBadge,
                              backgroundColor: v.review_status === 'PUBLISHED' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                              color: v.review_status === 'PUBLISHED' ? '#10b981' : '#f59e0b',
                            }}
                          >
                            {v.review_status}
                          </span>
                        </div>
                        <div style={styles.versionDate}>
                          {v.created_at ? new Date(v.created_at).toLocaleString() : 'N/A'}
                        </div>
                        {v.reviewer_notes && (
                          <div style={styles.versionNotes}>"{v.reviewer_notes}"</div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Version Details View */}
              <div style={styles.detailPane}>
                {selectedVersion && (
                  <div>
                    <div style={styles.detailHeader}>
                      <h4 style={styles.detailTitle}>Version {selectedVersion.version} Snapshot</h4>
                      <div style={styles.metaRow}>
                        <span style={styles.metaPill}>Author: {selectedVersion.author_name || 'HR Author'}</span>
                        <span style={styles.metaPill}>Format: {selectedVersion.response_format}</span>
                        <span style={styles.metaPill}>Difficulty: {selectedVersion.difficulty}</span>
                      </div>
                    </div>

                    <div style={styles.sectionLabel}>QUESTION TEXT</div>
                    <div style={styles.sectionBox}>{selectedVersion.question_text}</div>

                    <div style={styles.sectionLabel}>OPTIONS & ANSWER KEY</div>
                    <div style={styles.optionsList}>
                      {selectedVersion.options?.map((opt) => {
                        const optKey = opt.id || opt.key;
                        const isCorrect = (selectedVersion.answer_key || []).includes(optKey);
                        return (
                          <div
                            key={optKey}
                            style={{
                              ...styles.optionItem,
                              borderColor: isCorrect ? '#10b981' : '#334155',
                              backgroundColor: isCorrect ? 'rgba(16, 185, 129, 0.08)' : '#0f172a',
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
                            {isCorrect && <span style={styles.correctLabel}>Correct Answer</span>}
                          </div>
                        );
                      })}
                    </div>

                    <div style={styles.sectionLabel}>EXPLANATION</div>
                    <div style={styles.sectionBox}>{selectedVersion.explanation}</div>

                    {selectedVersion.reviewer_notes && (
                      <>
                        <div style={styles.sectionLabel}>REVIEWER AUDIT NOTES</div>
                        <div style={{ ...styles.sectionBox, color: '#f59e0b', fontStyle: 'italic' }}>
                          {selectedVersion.reviewer_notes}
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
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
    maxWidth: '960px',
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
    padding: '20px 24px',
    overflowY: 'auto',
    flex: 1,
  },
  columns: {
    display: 'flex',
    gap: '20px',
  },
  sidebar: {
    width: '280px',
    flexShrink: 0,
    borderRight: '1px solid #1e293b',
    paddingRight: '16px',
  },
  sidebarTitle: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#64748b',
    letterSpacing: '0.05em',
    marginBottom: '12px',
  },
  versionList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  versionCard: {
    padding: '12px 14px',
    borderRadius: '8px',
    border: '1px solid #334155',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  versionTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '6px',
  },
  versionNumber: {
    fontSize: '13px',
    fontWeight: '700',
    color: '#f8fafc',
  },
  statusBadge: {
    fontSize: '10px',
    fontWeight: '700',
    padding: '2px 6px',
    borderRadius: '4px',
    textTransform: 'uppercase',
  },
  versionDate: {
    fontSize: '11px',
    color: '#94a3b8',
  },
  versionNotes: {
    fontSize: '11px',
    color: '#cbd5e1',
    marginTop: '6px',
    fontStyle: 'italic',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  detailPane: {
    flex: 1,
    overflowY: 'auto',
  },
  detailHeader: {
    marginBottom: '16px',
    paddingBottom: '12px',
    borderBottom: '1px solid #1e293b',
  },
  detailTitle: {
    margin: '0 0 8px',
    color: '#f8fafc',
    fontSize: '16px',
  },
  metaRow: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
  },
  metaPill: {
    fontSize: '11px',
    color: '#94a3b8',
    backgroundColor: '#1e293b',
    padding: '3px 8px',
    borderRadius: '4px',
    border: '1px solid #334155',
  },
  sectionLabel: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#64748b',
    letterSpacing: '0.05em',
    margin: '14px 0 6px',
  },
  sectionBox: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '6px',
    padding: '12px 14px',
    fontSize: '14px',
    color: '#e2e8f0',
    lineHeight: '1.5',
  },
  optionsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  optionItem: {
    display: 'flex',
    alignItems: 'center',
    padding: '10px 14px',
    borderRadius: '6px',
    border: '1px solid #334155',
  },
  optKeyBadge: {
    width: '24px',
    height: '24px',
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
    fontSize: '13px',
    color: '#e2e8f0',
    flex: 1,
  },
  correctLabel: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#10b981',
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    padding: '2px 8px',
    borderRadius: '4px',
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
