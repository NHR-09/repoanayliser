import React, { useState, useEffect } from 'react';
import { hrApi } from '../../services/hrApi';
import QuestionEditorModal from './QuestionEditorModal';
import QuestionReviewModal from './QuestionReviewModal';
import QuestionPreviewModal from './QuestionPreviewModal';
import QuestionVersionHistoryModal from './QuestionVersionHistoryModal';
import QuestionGenerationModal from './QuestionGenerationModal';

export default function QuestionBankTable({
  orgId,
  initialOpenGen = false,
  initialGenRepoId = '',
  onClearGenTrigger = () => {},
}) {
  const [questions, setQuestions] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Search & Filter state
  const [search, setSearch] = useState('');
  const [competency, setCompetency] = useState('');
  const [difficulty, setDifficulty] = useState('');
  const [responseFormat, setResponseFormat] = useState('');
  const [sourceType, setSourceType] = useState('');
  const [reviewStatus, setReviewStatus] = useState('');
  const [validationStatus, setValidationStatus] = useState('');

  // Modals state
  const [editorQuestion, setEditorQuestion] = useState(null); // null = new, object = edit
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [reviewQuestion, setReviewQuestion] = useState(null);
  const [previewQuestionId, setPreviewQuestionId] = useState(null);
  const [historyQuestionId, setHistoryQuestionId] = useState(null);
  const [isGenerationOpen, setIsGenerationOpen] = useState(false);
  const [genRepoId, setGenRepoId] = useState(initialGenRepoId);

  useEffect(() => {
    if (initialOpenGen) {
      setIsGenerationOpen(true);
      setGenRepoId(initialGenRepoId);
      onClearGenTrigger();
    }
  }, [initialOpenGen, initialGenRepoId]);

  useEffect(() => {
    if (orgId) {
      loadQuestions();
    }
  }, [orgId, page, competency, difficulty, responseFormat, sourceType, reviewStatus, validationStatus]);

  const loadQuestions = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await hrApi.getQuestions(orgId, {
        page,
        pageSize,
        search,
        competency,
        difficulty,
        responseFormat,
        sourceType,
        reviewStatus,
        validationStatus,
      });
      setQuestions(data.items || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || 1);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load Question Bank.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    loadQuestions();
  };

  const handleClearFilters = () => {
    setSearch('');
    setCompetency('');
    setDifficulty('');
    setResponseFormat('');
    setSourceType('');
    setReviewStatus('');
    setValidationStatus('');
    setPage(1);
  };

  return (
    <div style={styles.container}>
      {/* Top Action Bar */}
      <div style={styles.topBar}>
        <div>
          <h2 style={styles.pageTitle}>HR Question Bank</h2>
          <p style={styles.subtext}>
            Curated library of technical questions with multi-version tracking and rigorous pedagogical validation.
          </p>
        </div>
        <div style={styles.actionButtons}>
          <button style={styles.secondaryBtn} onClick={() => setIsGenerationOpen(true)}>
            <span style={{ marginRight: '6px' }}>⚡</span>
            Generate AI Questions
          </button>
          <button
            style={styles.primaryBtn}
            onClick={() => {
              setEditorQuestion(null);
              setIsEditorOpen(true);
            }}
          >
            <span style={{ marginRight: '6px' }}>+</span>
            Author Question
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div style={styles.filterCard}>
        <form onSubmit={handleSearchSubmit} style={styles.searchForm}>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search questions or skill tags..."
            style={styles.searchInput}
          />
          <button type="submit" style={styles.searchBtn}>Search</button>
        </form>

        <div style={styles.filtersRow}>
          <select
            value={competency}
            onChange={(e) => { setCompetency(e.target.value); setPage(1); }}
            style={styles.filterSelect}
          >
            <option value="">All Competencies</option>
            <option value="CODE_COMPREHENSION">Code Comprehension</option>
            <option value="DEPENDENCY_TRACING">Dependency Tracing</option>
            <option value="ARCHITECTURE_REASONING">Architecture Reasoning</option>
            <option value="DEBUGGING">Debugging & Diagnostics</option>
            <option value="CHANGE_IMPACT">Change Impact</option>
          </select>

          <select
            value={difficulty}
            onChange={(e) => { setDifficulty(e.target.value); setPage(1); }}
            style={styles.filterSelect}
          >
            <option value="">All Difficulties</option>
            <option value="BEGINNER">Beginner</option>
            <option value="INTERMEDIATE">Intermediate</option>
            <option value="ADVANCED">Advanced</option>
          </select>

          <select
            value={responseFormat}
            onChange={(e) => { setResponseFormat(e.target.value); setPage(1); }}
            style={styles.filterSelect}
          >
            <option value="">All Formats</option>
            <option value="SINGLE_SELECT">Single Select</option>
            <option value="MULTI_SELECT">Multi Select</option>
            <option value="TRUE_FALSE">True / False</option>
          </select>

          <select
            value={sourceType}
            onChange={(e) => { setSourceType(e.target.value); setPage(1); }}
            style={styles.filterSelect}
          >
            <option value="">All Sources</option>
            <option value="SKILL_BASED">Skill-Based</option>
            <option value="REPOSITORY_BASED">Repository-Grounded</option>
          </select>

          <select
            value={reviewStatus}
            onChange={(e) => { setReviewStatus(e.target.value); setPage(1); }}
            style={styles.filterSelect}
          >
            <option value="">All Review Statuses</option>
            <option value="NEEDS_REVIEW">Needs Review</option>
            <option value="APPROVED">Approved</option>
            <option value="PUBLISHED">Published</option>
            <option value="ARCHIVED">Archived</option>
          </select>

          <select
            value={validationStatus}
            onChange={(e) => { setValidationStatus(e.target.value); setPage(1); }}
            style={styles.filterSelect}
          >
            <option value="">All Validations</option>
            <option value="VALIDATED">Validated</option>
            <option value="REJECTED">Rejected</option>
            <option value="PENDING">Pending</option>
          </select>

          {(search || competency || difficulty || responseFormat || sourceType || reviewStatus || validationStatus) && (
            <button type="button" onClick={handleClearFilters} style={styles.clearBtn}>
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {error && <div style={styles.errorBox}>{error}</div>}

      {/* Main Table */}
      <div style={styles.tableCard}>
        {loading ? (
          <div style={styles.loadingBox}>
            <div style={styles.spinner} />
            <p style={{ marginTop: '12px', color: '#94a3b8' }}>Loading question bank records...</p>
          </div>
        ) : questions.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={{ fontSize: '32px', marginBottom: '8px' }}>📋</div>
            <h4 style={{ margin: 0, color: '#f8fafc', fontSize: '16px' }}>No questions found</h4>
            <p style={{ margin: '6px 0 16px', color: '#94a3b8', fontSize: '13px' }}>
              No questions matched your filter criteria or none have been authored for this organization yet.
            </p>
            <button
              style={styles.primaryBtn}
              onClick={() => {
                setEditorQuestion(null);
                setIsEditorOpen(true);
              }}
            >
              Author First Question
            </button>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Question</th>
                  <th style={styles.th}>Competency</th>
                  <th style={styles.th}>Difficulty</th>
                  <th style={styles.th}>Format</th>
                  <th style={styles.th}>Source</th>
                  <th style={styles.th}>Lifecycle Status</th>
                  <th style={styles.th}>Version</th>
                  <th style={{ ...styles.th, textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {questions.map((q) => {
                  const isPublished = q.review_status === 'PUBLISHED';
                  const isApproved = q.review_status === 'APPROVED';
                  const isArchived = q.is_archived === 1 || q.review_status === 'ARCHIVED';

                  return (
                    <tr key={q.id} style={styles.tr}>
                      <td style={styles.tdQuestion}>
                        <div style={styles.questionTextPreview}>{q.question_text}</div>
                        <div style={styles.tagList}>
                          {q.skill_tags?.slice(0, 3).map((tag, idx) => (
                            <span key={idx} style={styles.tagBadge}>#{tag}</span>
                          ))}
                          {q.repo_name && (
                            <span style={styles.repoBadge}>📦 {q.repo_name}</span>
                          )}
                        </div>
                      </td>

                      <td style={styles.td}>
                        <span style={styles.competencyPill}>
                          {q.competency?.replace('_', ' ')}
                        </span>
                      </td>

                      <td style={styles.td}>
                        <span
                          style={{
                            ...styles.difficultyPill,
                            borderColor: q.difficulty === 'ADVANCED' ? '#f43f5e' : q.difficulty === 'INTERMEDIATE' ? '#38bdf8' : '#10b981',
                            color: q.difficulty === 'ADVANCED' ? '#f43f5e' : q.difficulty === 'INTERMEDIATE' ? '#38bdf8' : '#10b981',
                          }}
                        >
                          {q.difficulty}
                        </span>
                      </td>

                      <td style={styles.td}>
                        <span style={{ fontSize: '12px', color: '#94a3b8' }}>
                          {q.response_format?.replace('_', ' ')}
                        </span>
                      </td>

                      <td style={styles.td}>
                        <span style={{ fontSize: '12px', color: '#cbd5e1' }}>
                          {q.source_type === 'REPOSITORY_BASED' ? 'Repository' : 'Skill'}
                        </span>
                      </td>

                      <td style={styles.td}>
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
                          {q.review_status}
                        </span>
                      </td>

                      <td style={styles.td}>
                        <button
                          style={styles.versionBtn}
                          onClick={() => setHistoryQuestionId(q.id)}
                          title="View Version History"
                        >
                          v{q.version || 1} 📜
                        </button>
                      </td>

                      <td style={{ ...styles.td, textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '6px' }}>
                          <button
                            style={styles.rowActionBtn}
                            onClick={() => setReviewQuestion(q)}
                            title="Review and publish question"
                          >
                            Review
                          </button>
                          <button
                            style={styles.rowIconBtn}
                            onClick={() => setPreviewQuestionId(q.id)}
                            title="Candidate Mode Preview"
                          >
                            👁️
                          </button>
                          <button
                            style={styles.rowIconBtn}
                            onClick={() => {
                              setEditorQuestion(q);
                              setIsEditorOpen(true);
                            }}
                            title="Edit Question"
                          >
                            ✏️
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {!loading && questions.length > 0 && (
          <div style={styles.paginationRow}>
            <div style={{ fontSize: '13px', color: '#94a3b8' }}>
              Showing {questions.length} of {total} questions (Page {page} of {totalPages})
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                style={{
                  ...styles.pageBtn,
                  opacity: page <= 1 ? 0.4 : 1,
                  cursor: page <= 1 ? 'not-allowed' : 'pointer',
                }}
              >
                ← Previous
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
                style={{
                  ...styles.pageBtn,
                  opacity: page >= totalPages ? 0.4 : 1,
                  cursor: page >= totalPages ? 'not-allowed' : 'pointer',
                }}
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      {isEditorOpen && (
        <QuestionEditorModal
          orgId={orgId}
          existingQuestion={editorQuestion}
          onClose={() => setIsEditorOpen(false)}
          onSaved={loadQuestions}
        />
      )}

      {reviewQuestion && (
        <QuestionReviewModal
          orgId={orgId}
          question={reviewQuestion}
          onClose={() => setReviewQuestion(null)}
          onActionComplete={loadQuestions}
          onOpenEdit={(q) => {
            setEditorQuestion(q);
            setIsEditorOpen(true);
          }}
        />
      )}

      {previewQuestionId && (
        <QuestionPreviewModal
          orgId={orgId}
          questionId={previewQuestionId}
          onClose={() => setPreviewQuestionId(null)}
        />
      )}

      {historyQuestionId && (
        <QuestionVersionHistoryModal
          orgId={orgId}
          questionId={historyQuestionId}
          onClose={() => setHistoryQuestionId(null)}
        />
      )}

      {isGenerationOpen && (
        <QuestionGenerationModal
          orgId={orgId}
          initialMode={genRepoId ? 'REPOSITORY_BASED' : 'SKILL_BASED'}
          initialRepoId={genRepoId}
          onClose={() => {
            setIsGenerationOpen(false);
            setGenRepoId('');
          }}
          onGenerated={loadQuestions}
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
  topBar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  pageTitle: {
    margin: 0,
    fontSize: '22px',
    fontWeight: '700',
    color: '#f8fafc',
  },
  subtext: {
    margin: '4px 0 0',
    fontSize: '13px',
    color: '#94a3b8',
  },
  actionButtons: {
    display: 'flex',
    gap: '12px',
  },
  primaryBtn: {
    backgroundColor: '#38bdf8',
    color: '#0f172a',
    border: 'none',
    padding: '9px 18px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '700',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    transition: 'background-color 0.15s ease',
  },
  secondaryBtn: {
    backgroundColor: '#1e293b',
    color: '#f8fafc',
    border: '1px solid #334155',
    padding: '9px 16px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
  },
  filterCard: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '10px',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  searchForm: {
    display: 'flex',
    gap: '10px',
  },
  searchInput: {
    flex: 1,
    padding: '9px 14px',
    borderRadius: '6px',
    border: '1px solid #334155',
    backgroundColor: '#0f172a',
    color: '#f8fafc',
    fontSize: '13px',
    outline: 'none',
  },
  searchBtn: {
    backgroundColor: '#334155',
    color: '#f8fafc',
    border: 'none',
    padding: '0 18px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  filtersRow: {
    display: 'flex',
    gap: '10px',
    flexWrap: 'wrap',
    alignItems: 'center',
  },
  filterSelect: {
    padding: '8px 12px',
    borderRadius: '6px',
    border: '1px solid #334155',
    backgroundColor: '#0f172a',
    color: '#e2e8f0',
    fontSize: '12px',
    outline: 'none',
    cursor: 'pointer',
  },
  clearBtn: {
    background: 'none',
    border: 'none',
    color: '#f43f5e',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
    padding: '4px 8px',
  },
  tableCard: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '10px',
    overflow: 'hidden',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    textAlign: 'left',
  },
  th: {
    padding: '12px 16px',
    fontSize: '11px',
    fontWeight: '700',
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    borderBottom: '1px solid #334155',
    backgroundColor: '#0f172a',
  },
  tr: {
    borderBottom: '1px solid #1e293b',
    transition: 'background-color 0.15s ease',
  },
  td: {
    padding: '12px 16px',
    fontSize: '13px',
    verticalAlign: 'middle',
  },
  tdQuestion: {
    padding: '12px 16px',
    maxWidth: '340px',
  },
  questionTextPreview: {
    color: '#f8fafc',
    fontSize: '13px',
    fontWeight: '500',
    lineHeight: '1.4',
    marginBottom: '6px',
    overflow: 'hidden',
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
  },
  tagList: {
    display: 'flex',
    gap: '6px',
    flexWrap: 'wrap',
  },
  tagBadge: {
    fontSize: '11px',
    color: '#94a3b8',
    backgroundColor: '#0f172a',
    padding: '1px 6px',
    borderRadius: '4px',
  },
  repoBadge: {
    fontSize: '11px',
    color: '#38bdf8',
    backgroundColor: 'rgba(56, 189, 248, 0.1)',
    padding: '1px 6px',
    borderRadius: '4px',
  },
  competencyPill: {
    fontSize: '11px',
    fontWeight: '600',
    color: '#cbd5e1',
    backgroundColor: '#0f172a',
    padding: '3px 8px',
    borderRadius: '4px',
    border: '1px solid #334155',
    display: 'inline-block',
  },
  difficultyPill: {
    fontSize: '11px',
    fontWeight: '700',
    padding: '2px 8px',
    borderRadius: '10px',
    border: '1px solid',
    display: 'inline-block',
  },
  statusBadge: {
    fontSize: '11px',
    fontWeight: '700',
    padding: '3px 8px',
    borderRadius: '4px',
    textTransform: 'uppercase',
    display: 'inline-block',
  },
  versionBtn: {
    background: 'none',
    border: '1px solid #334155',
    color: '#38bdf8',
    fontSize: '12px',
    padding: '2px 8px',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  rowActionBtn: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    color: '#f8fafc',
    fontSize: '12px',
    fontWeight: '600',
    padding: '5px 12px',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  rowIconBtn: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    color: '#cbd5e1',
    fontSize: '13px',
    padding: '5px 8px',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  paginationRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '14px 16px',
    borderTop: '1px solid #334155',
    backgroundColor: '#0f172a',
  },
  pageBtn: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    color: '#f8fafc',
    padding: '5px 14px',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: '600',
  },
  loadingBox: {
    textAlign: 'center',
    padding: '60px',
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
  emptyState: {
    textAlign: 'center',
    padding: '60px 20px',
  },
  errorBox: {
    padding: '12px 16px',
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid #ef4444',
    color: '#fca5a5',
    borderRadius: '6px',
    fontSize: '13px',
  },
};
