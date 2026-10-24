import React, { useState, useEffect } from 'react';
import { assessmentApi } from '../../services/assessmentApi';
import AssessmentWizardModal from './AssessmentWizardModal';
import CandidateAssignmentModal from './CandidateAssignmentModal';
import AssessmentResultsModal from './AssessmentResultsModal';

export default function AssessmentList({ orgId }) {
  const [assessments, setAssessments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Modals
  const [wizardOpen, setWizardOpen] = useState(false);
  const [editingAssessment, setEditingAssessment] = useState(null);
  const [assigningAssessment, setAssigningAssessment] = useState(null);
  const [resultsAssessment, setResultsAssessment] = useState(null);
  const [publishingId, setPublishingId] = useState(null);
  const [archivingId, setArchivingId] = useState(null);

  useEffect(() => {
    if (orgId) {
      loadAssessments();
    }
  }, [orgId, statusFilter]);

  const loadAssessments = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await assessmentApi.getAssessments(orgId, statusFilter === 'ALL' ? null : statusFilter);
      setAssessments(data || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load assessments.');
    } finally {
      setLoading(false);
    }
  };

  const handlePublish = async (assessment) => {
    const confirmed = window.confirm(
      `Are you sure you want to publish "${assessment.title}"? This freezes an immutable published version and allows candidate assignments.`
    );
    if (!confirmed) return;

    setPublishingId(assessment.id);
    try {
      await assessmentApi.publishAssessment(orgId, assessment.id);
      await loadAssessments();
    } catch (err) {
      alert(`Publishing failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setPublishingId(null);
    }
  };

  const handleArchive = async (assessment) => {
    const confirmed = window.confirm(
      `Archive "${assessment.title}"? Candidates will no longer be able to start new attempts.`
    );
    if (!confirmed) return;

    setArchivingId(assessment.id);
    try {
      await assessmentApi.archiveAssessment(orgId, assessment.id);
      await loadAssessments();
    } catch (err) {
      alert(`Archive failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setArchivingId(null);
    }
  };

  const filteredAssessments = assessments.filter((a) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      a.title?.toLowerCase().includes(q) ||
      a.job_role?.toLowerCase().includes(q) ||
      a.description?.toLowerCase().includes(q)
    );
  });

  const totalCount = assessments.length;
  const publishedCount = assessments.filter((a) => a.status === 'PUBLISHED').length;
  const draftCount = assessments.filter((a) => a.status === 'DRAFT').length;
  const totalAssigned = assessments.reduce((acc, curr) => acc + (curr.assigned_candidates_count || 0), 0);
  const totalCompleted = assessments.reduce((acc, curr) => acc + (curr.completed_attempts_count || 0), 0);

  return (
    <div style={styles.container}>
      {/* Metrics Banner */}
      <div style={styles.metricsGrid}>
        <div style={styles.metricCard}>
          <div style={styles.metricLabel}>TOTAL ASSESSMENTS</div>
          <div style={styles.metricValue}>{totalCount}</div>
          <div style={styles.metricSub}>All lifecycle states</div>
        </div>
        <div style={styles.metricCard}>
          <div style={styles.metricLabel}>ACTIVE PUBLISHED</div>
          <div style={{ ...styles.metricValue, color: '#10b981' }}>{publishedCount}</div>
          <div style={styles.metricSub}>Immutable versions live</div>
        </div>
        <div style={styles.metricCard}>
          <div style={styles.metricLabel}>IN DRAFT</div>
          <div style={{ ...styles.metricValue, color: '#f59e0b' }}>{draftCount}</div>
          <div style={styles.metricSub}>Pending review / publication</div>
        </div>
        <div style={styles.metricCard}>
          <div style={styles.metricLabel}>CANDIDATE ATTEMPTS</div>
          <div style={{ ...styles.metricValue, color: '#38bdf8' }}>
            {totalCompleted} <span style={{ fontSize: '14px', color: '#94a3b8' }}>/ {totalAssigned} assigned</span>
          </div>
          <div style={styles.metricSub}>Automated objective grading</div>
        </div>
      </div>

      {/* Action Bar */}
      <div style={styles.actionBar}>
        <div style={styles.searchGroup}>
          <input
            type="text"
            placeholder="Search by title, job role, or description..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={styles.searchInput}
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={styles.filterSelect}
          >
            <option value="ALL">All Statuses</option>
            <option value="PUBLISHED">Published</option>
            <option value="DRAFT">Draft</option>
            <option value="ARCHIVED">Archived</option>
          </select>
          <button onClick={loadAssessments} style={styles.refreshBtn} title="Reload assessments">
            🔄
          </button>
        </div>

        <button
          onClick={() => {
            setEditingAssessment(null);
            setWizardOpen(true);
          }}
          style={styles.createBtn}
        >
          <span style={{ fontSize: '16px', marginRight: '6px' }}>✨</span>
          Create Assessment
        </button>
      </div>

      {error && (
        <div style={styles.errorBox}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Assessments Table */}
      {loading ? (
        <div style={styles.loadingBox}>
          <div style={styles.spinner} />
          <p style={{ marginTop: '12px', color: '#94a3b8' }}>Loading organization assessments...</p>
        </div>
      ) : filteredAssessments.length === 0 ? (
        <div style={styles.emptyState}>
          <span style={{ fontSize: '36px' }}>🎯</span>
          <h3 style={{ margin: '12px 0 6px', color: '#f8fafc' }}>No Assessments Found</h3>
          <p style={{ margin: 0, color: '#94a3b8', fontSize: '14px', maxWidth: '440px' }}>
            {searchQuery || statusFilter !== 'ALL'
              ? 'No assessments match your current filters. Try resetting the search or status filter.'
              : 'Create a tailored technical assessment with curated questions or a randomized blueprint grounded in your codebase.'}
          </p>
          {!searchQuery && statusFilter === 'ALL' && (
            <button
              onClick={() => {
                setEditingAssessment(null);
                setWizardOpen(true);
              }}
              style={{ ...styles.createBtn, marginTop: '18px' }}
            >
              ✨ Create First Assessment
            </button>
          )}
        </div>
      ) : (
        <div style={styles.tableCard}>
          <table style={styles.table}>
            <thead>
              <tr style={styles.tableHeaderRow}>
                <th style={styles.th}>ASSESSMENT TITLE & ROLE</th>
                <th style={styles.th}>MODE & REPOSITORY</th>
                <th style={styles.th}>STATUS & VERSION</th>
                <th style={styles.th}>DURATION & PASS</th>
                <th style={styles.th}>QUESTIONS</th>
                <th style={styles.th}>CANDIDATES</th>
                <th style={{ ...styles.th, textAlign: 'right' }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {filteredAssessments.map((a) => {
                const isPublished = a.status === 'PUBLISHED';
                const isDraft = a.status === 'DRAFT';
                const isArchived = a.status === 'ARCHIVED';

                return (
                  <tr key={a.id} style={styles.tr}>
                    <td style={styles.td}>
                      <div style={styles.assessmentTitle}>{a.title}</div>
                      <div style={styles.roleSub}>Role: {a.job_role || 'General Software Engineering'}</div>
                      {a.description && (
                        <div style={styles.descSub}>
                          {a.description.length > 70 ? `${a.description.slice(0, 70)}...` : a.description}
                        </div>
                      )}
                    </td>

                    <td style={styles.td}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <span
                          style={{
                            ...styles.modeBadge,
                            backgroundColor: a.mode === 'RANDOMIZED' ? '#0284c7' : '#4f46e5',
                          }}
                        >
                          {a.mode === 'RANDOMIZED' ? '🎲 Randomized Blueprint' : '📋 Curated Selection'}
                        </span>
                        {a.repository_id ? (
                          <span style={styles.repoBadge}>
                            📦 Codebase Attached
                          </span>
                        ) : (
                          <span style={{ fontSize: '11px', color: '#64748b' }}>No repo attached</span>
                        )}
                      </div>
                    </td>

                    <td style={styles.td}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span
                          style={{
                            ...styles.statusBadge,
                            backgroundColor: isPublished
                              ? '#065f46'
                              : isDraft
                              ? '#78350f'
                              : '#334155',
                            color: isPublished
                              ? '#34d399'
                              : isDraft
                              ? '#fbbf24'
                              : '#94a3b8',
                          }}
                        >
                          {a.status}
                        </span>
                        <span style={styles.versionBadge}>v{a.active_version_number || a.version_number || 1}</span>
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
                        Release: {a.result_release_policy?.replace(/_/g, ' ') || 'Pending Review'}
                      </div>
                    </td>

                    <td style={styles.td}>
                      <div style={{ fontSize: '13px', color: '#f1f5f9' }}>⏱️ {a.duration_minutes} mins</div>
                      <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
                        Passing: {a.passing_score_pct ? `${a.passing_score_pct}%` : 'N/A'}
                      </div>
                    </td>

                    <td style={styles.td}>
                      <div style={{ fontSize: '13px', fontWeight: '600', color: '#38bdf8' }}>
                        {a.question_count || (a.questions ? a.questions.length : 0)} Qs
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                        Max Attempts: {a.max_attempts_per_candidate || 1}
                      </div>
                    </td>

                    <td style={styles.td}>
                      <div style={{ fontSize: '12px', color: '#e2e8f0' }}>
                        <strong>{a.completed_attempts_count || 0}</strong> completed
                      </div>
                      <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                        {a.assigned_candidates_count || 0} assigned
                      </div>
                    </td>

                    <td style={{ ...styles.td, textAlign: 'right' }}>
                      <div style={styles.actionBtnGroup}>
                        {isDraft && (
                          <>
                            <button
                              onClick={() => handlePublish(a)}
                              disabled={publishingId === a.id}
                              style={styles.publishBtn}
                              title="Freeze version and publish"
                            >
                              {publishingId === a.id ? 'Publishing...' : '🚀 Publish'}
                            </button>
                            <button
                              onClick={() => {
                                setEditingAssessment(a);
                                setWizardOpen(true);
                              }}
                              style={styles.editBtn}
                              title="Edit draft assessment"
                            >
                              ✏️ Edit
                            </button>
                          </>
                        )}

                        {isPublished && (
                          <>
                            <button
                              onClick={() => setAssigningAssessment(a)}
                              style={styles.assignBtn}
                              title="Assign candidates and generate invitation links"
                            >
                              👥 Assign
                            </button>
                            <button
                              onClick={() => setResultsAssessment(a)}
                              style={styles.resultsBtn}
                              title="View candidate scores and detailed review"
                            >
                              📊 Results ({a.completed_attempts_count || 0})
                            </button>
                            <button
                              onClick={() => {
                                setEditingAssessment(a);
                                setWizardOpen(true);
                              }}
                              style={styles.editBtn}
                              title="Create a new draft revision"
                            >
                              ✏️ Edit
                            </button>
                            <button
                              onClick={() => handleArchive(a)}
                              disabled={archivingId === a.id}
                              style={styles.archiveBtn}
                              title="Archive assessment"
                            >
                              📦
                            </button>
                          </>
                        )}

                        {isArchived && (
                          <button
                            onClick={() => setResultsAssessment(a)}
                            style={styles.resultsBtn}
                            title="View historical candidate results"
                          >
                            📊 Results
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Assessment Creation / Edit Wizard Modal */}
      {wizardOpen && (
        <AssessmentWizardModal
          orgId={orgId}
          initialAssessment={editingAssessment}
          onClose={() => {
            setWizardOpen(false);
            setEditingAssessment(null);
          }}
          onSaved={() => {
            setWizardOpen(false);
            setEditingAssessment(null);
            loadAssessments();
          }}
        />
      )}

      {/* Candidate Assignment Modal */}
      {assigningAssessment && (
        <CandidateAssignmentModal
          orgId={orgId}
          assessment={assigningAssessment}
          onClose={() => {
            setAssigningAssessment(null);
            loadAssessments();
          }}
        />
      )}

      {/* Results & Scorecards Modal */}
      {resultsAssessment && (
        <AssessmentResultsModal
          orgId={orgId}
          assessment={resultsAssessment}
          onClose={() => {
            setResultsAssessment(null);
            loadAssessments();
          }}
        />
      )}
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
    gap: '14px',
  },
  metricCard: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '10px',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  metricLabel: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#94a3b8',
    letterSpacing: '0.05em',
  },
  metricValue: {
    fontSize: '26px',
    fontWeight: '800',
    color: '#f8fafc',
  },
  metricSub: {
    fontSize: '12px',
    color: '#64748b',
  },
  actionBar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '12px',
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '10px',
    padding: '12px 16px',
  },
  searchGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    flex: '1 1 360px',
  },
  searchInput: {
    flex: 1,
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '6px',
    padding: '9px 12px',
    color: '#f8fafc',
    fontSize: '13px',
    outline: 'none',
  },
  filterSelect: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '6px',
    padding: '9px 12px',
    color: '#f8fafc',
    fontSize: '13px',
    cursor: 'pointer',
    outline: 'none',
  },
  refreshBtn: {
    backgroundColor: '#334155',
    border: 'none',
    borderRadius: '6px',
    padding: '9px 12px',
    cursor: 'pointer',
    color: '#f8fafc',
    fontSize: '13px',
  },
  createBtn: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    border: 'none',
    borderRadius: '6px',
    padding: '9px 16px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'background-color 0.15s ease',
  },
  errorBox: {
    backgroundColor: '#451a1a',
    border: '1px solid #ef4444',
    color: '#fca5a5',
    borderRadius: '8px',
    padding: '12px 16px',
    fontSize: '13px',
  },
  loadingBox: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 20px',
    backgroundColor: '#1e293b',
    borderRadius: '10px',
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
    borderRadius: '10px',
    border: '1px solid #334155',
  },
  tableCard: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '10px',
    overflowX: 'auto',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    textAlign: 'left',
  },
  tableHeaderRow: {
    backgroundColor: '#0f172a',
    borderBottom: '1px solid #334155',
  },
  th: {
    padding: '12px 16px',
    fontSize: '11px',
    fontWeight: '700',
    color: '#94a3b8',
    letterSpacing: '0.05em',
  },
  tr: {
    borderBottom: '1px solid #334155',
    transition: 'background-color 0.15s ease',
  },
  td: {
    padding: '14px 16px',
    verticalAlign: 'middle',
  },
  assessmentTitle: {
    fontSize: '14px',
    fontWeight: '700',
    color: '#f8fafc',
  },
  roleSub: {
    fontSize: '12px',
    color: '#38bdf8',
    marginTop: '2px',
  },
  descSub: {
    fontSize: '11px',
    color: '#64748b',
    marginTop: '3px',
  },
  modeBadge: {
    fontSize: '11px',
    fontWeight: '600',
    padding: '3px 8px',
    borderRadius: '12px',
    color: '#ffffff',
    display: 'inline-block',
    width: 'fit-content',
  },
  repoBadge: {
    fontSize: '11px',
    color: '#94a3b8',
  },
  statusBadge: {
    fontSize: '11px',
    fontWeight: '700',
    padding: '3px 8px',
    borderRadius: '12px',
    letterSpacing: '0.04em',
  },
  versionBadge: {
    fontSize: '11px',
    fontWeight: '600',
    padding: '2px 6px',
    backgroundColor: '#334155',
    color: '#94a3b8',
    borderRadius: '4px',
  },
  actionBtnGroup: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: '6px',
    flexWrap: 'wrap',
  },
  publishBtn: {
    backgroundColor: '#059669',
    color: '#ffffff',
    border: 'none',
    borderRadius: '6px',
    padding: '6px 10px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  assignBtn: {
    backgroundColor: '#2563eb',
    color: '#ffffff',
    border: 'none',
    borderRadius: '6px',
    padding: '6px 10px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  resultsBtn: {
    backgroundColor: '#0284c7',
    color: '#ffffff',
    border: 'none',
    borderRadius: '6px',
    padding: '6px 10px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  editBtn: {
    backgroundColor: '#334155',
    color: '#f8fafc',
    border: 'none',
    borderRadius: '6px',
    padding: '6px 10px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  archiveBtn: {
    backgroundColor: '#334155',
    color: '#ef4444',
    border: 'none',
    borderRadius: '6px',
    padding: '6px 10px',
    fontSize: '12px',
    cursor: 'pointer',
  },
};
