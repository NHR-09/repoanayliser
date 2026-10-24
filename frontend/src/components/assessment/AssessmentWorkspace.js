import React, { useState, useEffect, useRef } from 'react';
import { assessmentApi } from '../../services/assessmentApi';

export default function AssessmentWorkspace({ initialAttempt, onExit }) {
  const attempt = initialAttempt;
  const questions = initialAttempt?.questions || [];
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState(initialAttempt?.persisted_answers || {});
  const [saveStatus, setSaveStatus] = useState('saved'); // 'saved' | 'saving' | 'error'

  // Server-authoritative timer (in seconds)
  const [remainingSeconds, setRemainingSeconds] = useState(
    Math.max(0, Math.floor(initialAttempt?.remaining_seconds || 0))
  );
  const [isTimeExpired, setIsTimeExpired] = useState(remainingSeconds <= 0);

  // Submission state
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);

  // Codebase Explorer state
  const [repoFiles, setRepoFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [loadingFile, setLoadingFile] = useState(false);
  const [fileSearch, setFileSearch] = useState('');
  const [repoName, setRepoName] = useState(initialAttempt?.repository_name || 'Attached Codebase');

  // Debounce ref for autosave
  const autosaveTimerRef = useRef({});

  // Countdown timer effect
  useEffect(() => {
    if (remainingSeconds <= 0 || submitResult) {
      if (remainingSeconds <= 0 && !submitResult && !isTimeExpired) {
        setIsTimeExpired(true);
        handleAutoExpire();
      }
      return;
    }

    const interval = setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          setIsTimeExpired(true);
          handleAutoExpire();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [remainingSeconds, submitResult]);

  // Load codebase files on mount
  useEffect(() => {
    if (attempt?.id) {
      loadCodebaseFiles();
    }
  }, [attempt?.id]);

  const loadCodebaseFiles = async () => {
    try {
      const data = await assessmentApi.getAttemptCodebaseFiles(attempt.id);
      setRepoFiles(data?.files || []);
      if (data?.repo_name) {
        setRepoName(data.repo_name);
      }
      // Auto-open first file if available
      if (data?.files?.length > 0) {
        handleOpenFile(data.files[0]);
      }
    } catch (err) {
      console.warn('Could not load codebase files:', err);
    }
  };

  const handleOpenFile = async (filePath) => {
    setSelectedFile(filePath);
    setLoadingFile(true);
    try {
      const data = await assessmentApi.getAttemptCodebaseFileContent(attempt.id, filePath);
      setFileContent(data?.content || '');
    } catch (err) {
      setFileContent(`// Error loading file: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoadingFile(false);
    }
  };

  const handleAutoExpire = async () => {
    alert('⏱️ Assessment deadline has expired. Submitting your current answers.');
    await handleSubmitAttempt();
  };

  const triggerAutosave = (questionId, newResponse) => {
    setSaveStatus('saving');

    if (autosaveTimerRef.current[questionId]) {
      clearTimeout(autosaveTimerRef.current[questionId]);
    }

    autosaveTimerRef.current[questionId] = setTimeout(async () => {
      try {
        await assessmentApi.autosaveAnswer(attempt.id, questionId, newResponse);
        setSaveStatus('saved');
      } catch (err) {
        console.error('Autosave failed:', err);
        setSaveStatus('error');
      }
    }, 600);
  };

  const handleAnswerChange = (questionId, value, responseFormat) => {
    if (isTimeExpired || submitResult) return;

    let updated;
    if (responseFormat === 'MULTI_SELECT') {
      const current = Array.isArray(answers[questionId]) ? [...answers[questionId]] : [];
      if (current.includes(value)) {
        updated = current.filter((x) => x !== value);
      } else {
        updated = [...current, value];
      }
    } else {
      updated = value;
    }

    setAnswers((prev) => ({
      ...prev,
      [questionId]: updated,
    }));

    triggerAutosave(questionId, updated);
  };

  const handleSubmitAttempt = async () => {
    setSubmitting(true);
    try {
      const res = await assessmentApi.submitAttempt(attempt.id);
      setSubmitResult(res);
      setShowSubmitModal(false);
    } catch (err) {
      alert(`Submission failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const formatTimer = (sec) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const currentQ = questions[currentIndex] || null;
  const answeredCount = Object.keys(answers).filter(
    (k) => answers[k] !== undefined && answers[k] !== null && answers[k] !== '' && (!Array.isArray(answers[k]) || answers[k].length > 0)
  ).length;

  // Filtered files for explorer
  const filteredFiles = repoFiles.filter((f) =>
    f.toLowerCase().includes(fileSearch.toLowerCase())
  );

  // If already submitted, show completion scorecard
  if (submitResult) {
    const isReleased = submitResult.release_policy === 'IMMEDIATE' || submitResult.results_released;
    const scorePct = submitResult.percentage !== undefined ? submitResult.percentage : null;

    return (
      <div style={styles.completionContainer}>
        <div style={styles.completionCard}>
          <div style={styles.completionIcon}>
            {submitResult.is_passing ? '🎉' : '🏁'}
          </div>

          <h2 style={styles.completionTitle}>Assessment Successfully Submitted</h2>
          <p style={styles.completionSubtitle}>
            Your answers and timestamps have been durably stored in ARCHITECH's audit trail.
          </p>

          {isReleased && scorePct !== null ? (
            <div style={styles.resultsBreakdownBox}>
              <div style={styles.scoreRow}>
                <div>
                  <div style={styles.scoreBig}>
                    {scorePct.toFixed(1)}%
                  </div>
                  <div style={{ fontSize: '13px', color: '#94a3b8' }}>
                    Score: {submitResult.score} / {submitResult.max_score} Points
                  </div>
                </div>

                <div
                  style={{
                    ...styles.passBadge,
                    backgroundColor: submitResult.is_passing ? '#065f46' : '#7f1d1d',
                    color: submitResult.is_passing ? '#34d399' : '#fca5a5',
                  }}
                >
                  {submitResult.is_passing ? 'PASSED' : 'DID NOT PASS'}
                </div>
              </div>

              {submitResult.competency_scores && Object.keys(submitResult.competency_scores).length > 0 && (
                <div style={{ marginTop: '20px' }}>
                  <h4 style={{ color: '#f8fafc', fontSize: '13px', margin: '0 0 10px' }}>
                    COMPETENCY BREAKDOWN
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {Object.entries(submitResult.competency_scores).map(([comp, val]) => (
                      <div key={comp} style={styles.compRow}>
                        <span style={{ fontSize: '12px', color: '#cbd5e1' }}>
                          {comp.replace(/_/g, ' ')}
                        </span>
                        <span style={{ fontSize: '12px', fontWeight: '700', color: '#38bdf8' }}>
                          {val.percentage ? `${val.percentage.toFixed(0)}%` : `${val.earned}/${val.possible}`}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={styles.pendingReviewBox}>
              <div style={{ fontSize: '24px', marginBottom: '8px' }}>🔒</div>
              <h4 style={{ color: '#f8fafc', margin: '0 0 4px', fontSize: '15px' }}>
                Results Pending Recruiter Review
              </h4>
              <p style={{ color: '#94a3b8', fontSize: '13px', margin: 0, lineHeight: '1.4' }}>
                Per organization policy, assessment scores and feedback are withheld pending final review by the hiring team. You will be notified when your evaluation is released.
              </p>
            </div>
          )}

          <button onClick={onExit} style={styles.returnBtn}>
            ← Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.workspaceWrapper}>
      {/* Top Authoritative Header */}
      <header style={styles.topHeader}>
        <div style={styles.headerLeft}>
          <div style={styles.tagLive}>🔴 LIVE ATTEMPT</div>
          <h2 style={styles.headerTitle}>{attempt?.assessment_title || 'Assessment'}</h2>
        </div>

        <div style={styles.headerCenter}>
          {/* Server-authoritative timer */}
          <div
            style={{
              ...styles.timerBox,
              borderColor: remainingSeconds < 300 ? '#ef4444' : '#334155',
              backgroundColor: remainingSeconds < 300 ? '#451a1a' : '#0f172a',
            }}
          >
            <span style={{ fontSize: '16px' }}>⏱️</span>
            <span
              style={{
                ...styles.timerDigits,
                color: remainingSeconds < 300 ? '#fca5a5' : '#38bdf8',
              }}
            >
              {formatTimer(remainingSeconds)}
            </span>
          </div>

          {/* Autosave status indicator */}
          <div style={styles.saveStatusBadge}>
            {saveStatus === 'saving' && (
              <span style={{ color: '#f59e0b', fontSize: '12px' }}>🔄 Saving...</span>
            )}
            {saveStatus === 'saved' && (
              <span style={{ color: '#10b981', fontSize: '12px' }}>✓ Saved</span>
            )}
            {saveStatus === 'error' && (
              <span style={{ color: '#ef4444', fontSize: '12px' }}>✕ Save failed</span>
            )}
          </div>
        </div>

        <div style={styles.headerRight}>
          <button
            onClick={() => setShowSubmitModal(true)}
            disabled={submitting}
            style={styles.finishBtn}
          >
            Submit Assessment
          </button>
        </div>
      </header>

      {/* Main Split-Pane Layout */}
      <div style={styles.splitLayout}>
        {/* Left Pane: Question Runner */}
        <section style={styles.leftPane}>
          {/* Question Palette */}
          <div style={styles.paletteBar}>
            <div style={styles.paletteLabel}>
              Questions ({answeredCount}/{questions.length} answered):
            </div>
            <div style={styles.paletteList}>
              {questions.map((q, idx) => {
                const isCurrent = idx === currentIndex;
                const isAnswered =
                  answers[q.id] !== undefined &&
                  answers[q.id] !== null &&
                  answers[q.id] !== '' &&
                  (!Array.isArray(answers[q.id]) || answers[q.id].length > 0);

                return (
                  <button
                    key={q.id || idx}
                    onClick={() => setCurrentIndex(idx)}
                    style={{
                      ...styles.paletteBtn,
                      backgroundColor: isCurrent
                        ? '#2563eb'
                        : isAnswered
                        ? '#065f46'
                        : '#1e293b',
                      borderColor: isCurrent ? '#60a5fa' : '#334155',
                      color: isCurrent || isAnswered ? '#ffffff' : '#94a3b8',
                    }}
                  >
                    {idx + 1}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Current Question Body */}
          {currentQ ? (
            <div style={styles.questionCard}>
              <div style={styles.qMetaRow}>
                <span style={styles.qNumBadge}>Question {currentIndex + 1} of {questions.length}</span>
                {currentQ.competency && (
                  <span style={styles.compBadge}>{currentQ.competency.replace(/_/g, ' ')}</span>
                )}
                {currentQ.difficulty && (
                  <span style={styles.diffBadge}>{currentQ.difficulty}</span>
                )}
                <span style={styles.pointsBadge}>{currentQ.points || 1} pt{currentQ.points > 1 ? 's' : ''}</span>
              </div>

              <div style={styles.qPrompt}>
                {currentQ.question_text || currentQ.prompt}
              </div>

              {/* Code Snippet / Evidence Reference if attached */}
              {currentQ.evidence_references && (
                <div style={styles.evidenceRefBox}>
                  <div style={styles.evidenceRefTitle}>
                    <span>🔍 Grounded Code Evidence:</span>
                    {typeof currentQ.evidence_references === 'string' && repoFiles.length > 0 && (
                      <button
                        onClick={() => {
                          const fileRef = currentQ.evidence_references.split(':')[0];
                          if (fileRef) handleOpenFile(fileRef);
                        }}
                        style={styles.openEvidenceBtn}
                      >
                        Open in Workspace →
                      </button>
                    )}
                  </div>
                  <pre style={styles.evidenceCode}>
                    {typeof currentQ.evidence_references === 'object'
                      ? JSON.stringify(currentQ.evidence_references, null, 2)
                      : currentQ.evidence_references}
                  </pre>
                </div>
              )}

              {/* Answer Controls */}
              <div style={styles.answerSection}>
                <div style={styles.answerLabel}>
                  {currentQ.response_format === 'MULTI_SELECT'
                    ? 'Select all options that apply:'
                    : currentQ.response_format === 'TRUE_FALSE'
                    ? 'Choose True or False:'
                    : 'Select one option:'}
                </div>

                {/* Multiple Options (SINGLE_SELECT or MULTI_SELECT) */}
                {currentQ.options && Array.isArray(currentQ.options) && (
                  <div style={styles.optionsList}>
                    {currentQ.options.map((opt, oIdx) => {
                      const optId = opt.id || String.fromCharCode(65 + oIdx);
                      const optText = opt.text || opt;
                      const isMulti = currentQ.response_format === 'MULTI_SELECT';
                      const isSelected = isMulti
                        ? Array.isArray(answers[currentQ.id]) && answers[currentQ.id].includes(optId)
                        : answers[currentQ.id] === optId;

                      return (
                        <div
                          key={optId}
                          onClick={() => handleAnswerChange(currentQ.id, optId, currentQ.response_format)}
                          style={{
                            ...styles.optionCard,
                            borderColor: isSelected ? '#38bdf8' : '#334155',
                            backgroundColor: isSelected ? '#082f49' : '#0f172a',
                          }}
                        >
                          <div
                            style={{
                              ...styles.optLetter,
                              borderColor: isSelected ? '#38bdf8' : '#475569',
                              backgroundColor: isSelected ? '#38bdf8' : 'transparent',
                              color: isSelected ? '#0f172a' : '#cbd5e1',
                            }}
                          >
                            {optId}
                          </div>
                          <div style={styles.optText}>{optText}</div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* TRUE / FALSE Options */}
                {currentQ.response_format === 'TRUE_FALSE' && (
                  <div style={styles.tfRow}>
                    {['True', 'False'].map((val) => {
                      const isSelected = answers[currentQ.id] === val;
                      return (
                        <button
                          key={val}
                          onClick={() => handleAnswerChange(currentQ.id, val, 'TRUE_FALSE')}
                          style={{
                            ...styles.tfBtn,
                            borderColor: isSelected ? '#38bdf8' : '#334155',
                            backgroundColor: isSelected ? '#082f49' : '#0f172a',
                            color: isSelected ? '#38bdf8' : '#cbd5e1',
                          }}
                        >
                          {val}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Bottom Q Nav */}
              <div style={styles.qFooter}>
                <button
                  onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
                  disabled={currentIndex === 0}
                  style={styles.navBtn}
                >
                  ← Previous
                </button>

                <div style={{ fontSize: '12px', color: '#64748b' }}>
                  {currentIndex + 1} / {questions.length}
                </div>

                <button
                  onClick={() => setCurrentIndex((prev) => Math.min(questions.length - 1, prev + 1))}
                  disabled={currentIndex === questions.length - 1}
                  style={styles.navBtn}
                >
                  Next →
                </button>
              </div>
            </div>
          ) : (
            <div style={styles.noQuestionsBox}>No questions in this assessment snapshot.</div>
          )}
        </section>

        {/* Right Pane: Codebase Workspace */}
        <section style={styles.rightPane}>
          <div style={styles.codebaseHeader}>
            <div style={styles.codebaseTitle}>
              <span>📁</span>
              <span>{repoName}</span>
              <span style={styles.readOnlyPill}>READ ONLY</span>
            </div>

            {/* File search */}
            <input
              type="text"
              placeholder="Search files..."
              value={fileSearch}
              onChange={(e) => setFileSearch(e.target.value)}
              style={styles.fileSearchInput}
            />
          </div>

          <div style={styles.codebaseBody}>
            {/* Left mini file-tree */}
            <div style={styles.fileTreePanel}>
              <div style={styles.fileTreeHeader}>REPOSITORY FILES ({filteredFiles.length})</div>
              {filteredFiles.length === 0 ? (
                <div style={{ padding: '16px', color: '#64748b', fontSize: '12px' }}>
                  No repository files found or attached.
                </div>
              ) : (
                filteredFiles.map((fp) => {
                  const isSelected = selectedFile === fp;
                  return (
                    <div
                      key={fp}
                      onClick={() => handleOpenFile(fp)}
                      style={{
                        ...styles.fileTreeItem,
                        backgroundColor: isSelected ? '#334155' : 'transparent',
                        color: isSelected ? '#f8fafc' : '#94a3b8',
                      }}
                      title={fp}
                    >
                      <span style={{ marginRight: '6px' }}>📄</span>
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {fp}
                      </span>
                    </div>
                  );
                })
              )}
            </div>

            {/* Right Source Code Viewer */}
            <div style={styles.codeViewerPanel}>
              <div style={styles.codeViewerBreadcrumb}>
                {selectedFile ? (
                  <span>Viewing: <strong>{selectedFile}</strong></span>
                ) : (
                  <span>Select a file from the repository tree to inspect implementation</span>
                )}
              </div>

              {loadingFile ? (
                <div style={styles.loadingFileBox}>Loading file contents...</div>
              ) : selectedFile ? (
                <pre style={styles.codeViewerPre}>
                  <code>{fileContent}</code>
                </pre>
              ) : (
                <div style={styles.emptyCodeBox}>
                  <div style={{ fontSize: '32px', marginBottom: '8px' }}>🔍</div>
                  <p style={{ margin: 0, color: '#94a3b8', fontSize: '13px' }}>
                    Explore the repository files while deriving answers. All question evidence is drawn directly from this codebase.
                  </p>
                </div>
              )}
            </div>
          </div>
        </section>
      </div>

      {/* Submit Confirmation Modal */}
      {showSubmitModal && (
        <div style={styles.modalOverlay}>
          <div style={styles.confirmModal}>
            <h3 style={{ margin: '0 0 10px', color: '#f8fafc', fontSize: '18px' }}>
              Submit Assessment Attempt?
            </h3>
            <p style={{ margin: '0 0 16px', color: '#cbd5e1', fontSize: '13px', lineHeight: '1.5' }}>
              You have answered <strong>{answeredCount}</strong> of <strong>{questions.length}</strong> questions.
              {answeredCount < questions.length && (
                <span style={{ display: 'block', color: '#f59e0b', marginTop: '8px' }}>
                  ⚠️ Warning: {questions.length - answeredCount} question(s) remain unanswered and will be scored as 0.
                </span>
              )}
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                onClick={() => setShowSubmitModal(false)}
                disabled={submitting}
                style={styles.cancelModalBtn}
              >
                Continue Assessment
              </button>
              <button
                onClick={handleSubmitAttempt}
                disabled={submitting}
                style={styles.confirmSubmitBtn}
              >
                {submitting ? 'Submitting & Grading...' : 'Confirm Submission'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  workspaceWrapper: {
    display: 'flex',
    flexDirection: 'column',
    height: 'calc(100vh - 120px)',
    backgroundColor: '#090d16',
    color: '#f8fafc',
    borderRadius: '10px',
    overflow: 'hidden',
    border: '1px solid #334155',
  },
  topHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 20px',
    backgroundColor: '#0f172a',
    borderBottom: '1px solid #334155',
    flexShrink: 0,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  tagLive: {
    fontSize: '11px',
    fontWeight: '800',
    backgroundColor: '#7f1d1d',
    color: '#fca5a5',
    padding: '2px 8px',
    borderRadius: '4px',
    letterSpacing: '0.04em',
  },
  headerTitle: {
    fontSize: '16px',
    fontWeight: '700',
    margin: 0,
    color: '#f8fafc',
  },
  headerCenter: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  timerBox: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '6px 14px',
    borderRadius: '8px',
    border: '1px solid #334155',
  },
  timerDigits: {
    fontSize: '18px',
    fontWeight: '800',
    letterSpacing: '0.05em',
    fontFamily: 'monospace',
  },
  saveStatusBadge: {
    fontSize: '12px',
    minWidth: '80px',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  finishBtn: {
    backgroundColor: '#059669',
    color: '#ffffff',
    border: 'none',
    borderRadius: '6px',
    padding: '8px 16px',
    fontSize: '13px',
    fontWeight: '700',
    cursor: 'pointer',
    transition: 'background-color 0.15s ease',
  },
  splitLayout: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  },
  leftPane: {
    flex: '1 1 50%',
    display: 'flex',
    flexDirection: 'column',
    borderRight: '1px solid #334155',
    backgroundColor: '#0f172a',
    overflowY: 'auto',
  },
  paletteBar: {
    padding: '12px 16px',
    borderBottom: '1px solid #334155',
    backgroundColor: '#1e293b',
  },
  paletteLabel: {
    fontSize: '11px',
    color: '#94a3b8',
    fontWeight: '700',
    marginBottom: '8px',
  },
  paletteList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
  },
  paletteBtn: {
    width: '32px',
    height: '32px',
    borderRadius: '6px',
    border: '1px solid',
    fontSize: '12px',
    fontWeight: '700',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  questionCard: {
    padding: '24px',
    display: 'flex',
    flexDirection: 'column',
    gap: '18px',
    flex: 1,
  },
  qMetaRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
  },
  qNumBadge: {
    fontSize: '12px',
    fontWeight: '700',
    color: '#f8fafc',
  },
  compBadge: {
    fontSize: '10px',
    fontWeight: '700',
    backgroundColor: '#0284c7',
    color: '#ffffff',
    padding: '2px 8px',
    borderRadius: '10px',
  },
  diffBadge: {
    fontSize: '10px',
    fontWeight: '700',
    backgroundColor: '#334155',
    color: '#cbd5e1',
    padding: '2px 8px',
    borderRadius: '10px',
  },
  pointsBadge: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#38bdf8',
    marginLeft: 'auto',
  },
  qPrompt: {
    fontSize: '15px',
    fontWeight: '600',
    color: '#f1f5f9',
    lineHeight: '1.5',
  },
  evidenceRefBox: {
    backgroundColor: '#090d16',
    border: '1px solid #334155',
    borderRadius: '8px',
    padding: '12px',
  },
  evidenceRefTitle: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontSize: '12px',
    fontWeight: '700',
    color: '#94a3b8',
    marginBottom: '8px',
  },
  openEvidenceBtn: {
    backgroundColor: 'transparent',
    border: 'none',
    color: '#38bdf8',
    fontSize: '11px',
    cursor: 'pointer',
    fontWeight: '600',
  },
  evidenceCode: {
    margin: 0,
    fontSize: '12px',
    color: '#e2e8f0',
    fontFamily: 'monospace',
    whiteSpace: 'pre-wrap',
  },
  answerSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  answerLabel: {
    fontSize: '12px',
    fontWeight: '700',
    color: '#94a3b8',
    textTransform: 'uppercase',
  },
  optionsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  optionCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px 14px',
    borderRadius: '8px',
    border: '1px solid',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  optLetter: {
    width: '28px',
    height: '28px',
    borderRadius: '50%',
    border: '1px solid',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '12px',
    fontWeight: '700',
    flexShrink: 0,
  },
  optText: {
    fontSize: '14px',
    color: '#f8fafc',
    lineHeight: '1.4',
  },
  tfRow: {
    display: 'flex',
    gap: '14px',
  },
  tfBtn: {
    flex: 1,
    padding: '16px',
    borderRadius: '8px',
    border: '1px solid',
    fontSize: '16px',
    fontWeight: '700',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  qFooter: {
    marginTop: 'auto',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: '20px',
    borderTop: '1px solid #334155',
  },
  navBtn: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    color: '#f8fafc',
    borderRadius: '6px',
    padding: '8px 16px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  noQuestionsBox: {
    padding: '40px',
    textAlign: 'center',
    color: '#94a3b8',
  },
  rightPane: {
    flex: '1 1 50%',
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#090d16',
    overflow: 'hidden',
  },
  codebaseHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 16px',
    backgroundColor: '#0f172a',
    borderBottom: '1px solid #334155',
  },
  codebaseTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '13px',
    fontWeight: '700',
    color: '#f8fafc',
  },
  readOnlyPill: {
    fontSize: '10px',
    fontWeight: '700',
    backgroundColor: '#334155',
    color: '#94a3b8',
    padding: '2px 6px',
    borderRadius: '4px',
  },
  fileSearchInput: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '6px',
    padding: '6px 10px',
    color: '#f8fafc',
    fontSize: '12px',
    width: '180px',
    outline: 'none',
  },
  codebaseBody: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  },
  fileTreePanel: {
    width: '220px',
    borderRight: '1px solid #334155',
    backgroundColor: '#0b1120',
    overflowY: 'auto',
    flexShrink: 0,
  },
  fileTreeHeader: {
    fontSize: '10px',
    fontWeight: '700',
    color: '#94a3b8',
    padding: '8px 12px',
    borderBottom: '1px solid #1e293b',
    letterSpacing: '0.05em',
  },
  fileTreeItem: {
    padding: '8px 12px',
    fontSize: '12px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    transition: 'background-color 0.1s ease',
  },
  codeViewerPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    backgroundColor: '#090d16',
  },
  codeViewerBreadcrumb: {
    padding: '8px 16px',
    fontSize: '12px',
    color: '#94a3b8',
    backgroundColor: '#0f172a',
    borderBottom: '1px solid #334155',
  },
  codeViewerPre: {
    margin: 0,
    padding: '16px',
    flex: 1,
    overflow: 'auto',
    fontFamily: 'monospace',
    fontSize: '12px',
    color: '#e2e8f0',
    lineHeight: '1.5',
    backgroundColor: '#090d16',
  },
  loadingFileBox: {
    padding: '40px',
    textAlign: 'center',
    color: '#94a3b8',
  },
  emptyCodeBox: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
    padding: '40px',
    textAlign: 'center',
  },
  completionContainer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '40px 20px',
    minHeight: '70vh',
  },
  completionCard: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '16px',
    padding: '40px',
    maxWidth: '560px',
    width: '100%',
    textAlign: 'center',
  },
  completionIcon: {
    fontSize: '48px',
    marginBottom: '16px',
  },
  completionTitle: {
    fontSize: '24px',
    fontWeight: '800',
    color: '#f8fafc',
    margin: '0 0 8px',
  },
  completionSubtitle: {
    fontSize: '14px',
    color: '#94a3b8',
    margin: '0 0 24px',
  },
  resultsBreakdownBox: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '12px',
    padding: '20px',
    textAlign: 'left',
    marginBottom: '24px',
  },
  scoreRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingBottom: '16px',
    borderBottom: '1px solid #334155',
  },
  scoreBig: {
    fontSize: '32px',
    fontWeight: '800',
    color: '#38bdf8',
  },
  passBadge: {
    fontSize: '13px',
    fontWeight: '800',
    padding: '6px 14px',
    borderRadius: '20px',
    letterSpacing: '0.05em',
  },
  compRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '6px 0',
    borderBottom: '1px solid #1e293b',
  },
  pendingReviewBox: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '12px',
    padding: '24px',
    marginBottom: '24px',
  },
  returnBtn: {
    backgroundColor: '#2563eb',
    color: '#ffffff',
    border: 'none',
    borderRadius: '8px',
    padding: '12px 24px',
    fontSize: '14px',
    fontWeight: '700',
    cursor: 'pointer',
    width: '100%',
  },
  modalOverlay: {
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
  confirmModal: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '12px',
    padding: '24px',
    maxWidth: '480px',
    width: '100%',
  },
  cancelModalBtn: {
    backgroundColor: '#334155',
    border: 'none',
    borderRadius: '6px',
    padding: '10px 16px',
    color: '#f8fafc',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  confirmSubmitBtn: {
    backgroundColor: '#059669',
    border: 'none',
    borderRadius: '6px',
    padding: '10px 16px',
    color: '#ffffff',
    fontSize: '13px',
    fontWeight: '700',
    cursor: 'pointer',
  },
};
