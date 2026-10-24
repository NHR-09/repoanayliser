import React, { useState, useEffect } from 'react';
import { assessmentApi } from '../../services/assessmentApi';
import { hrApi } from '../../services/hrApi';

const COMPETENCIES = [
  'CODE_COMPREHENSION',
  'DEPENDENCY_TRACING',
  'ARCHITECTURE_REASONING',
  'DEBUGGING',
  'CHANGE_IMPACT',
];

const DIFFICULTIES = ['BEGINNER', 'INTERMEDIATE', 'ADVANCED'];

export default function AssessmentWizardModal({ orgId, initialAssessment, onClose, onSaved }) {
  const isEditing = Boolean(initialAssessment?.id);
  const [step, setStep] = useState(1);

  // Step 1: Details
  const [title, setTitle] = useState(initialAssessment?.title || '');
  const [description, setDescription] = useState(initialAssessment?.description || '');
  const [instructions, setInstructions] = useState(
    initialAssessment?.instructions ||
      'Please read each question carefully and explore the connected codebase workspace. All answers are autosaved.'
  );
  const [jobRole, setJobRole] = useState(initialAssessment?.job_role || 'Senior Full Stack Engineer');
  const [durationMinutes, setDurationMinutes] = useState(initialAssessment?.duration_minutes || 60);
  const [passingScorePct, setPassingScorePct] = useState(initialAssessment?.passing_score_pct || 70.0);
  const [resultReleasePolicy, setResultReleasePolicy] = useState(
    initialAssessment?.result_release_policy || 'WITHHOLD_PENDING_REVIEW'
  );
  const [maxAttempts, setMaxAttempts] = useState(initialAssessment?.max_attempts_per_candidate || 1);

  // Step 2: Composition Mode
  const [mode, setMode] = useState(initialAssessment?.mode || 'CURATED'); // 'CURATED' | 'RANDOMIZED'
  // Curated questions selection
  const [availableQuestions, setAvailableQuestions] = useState([]);
  const [loadingQuestions, setLoadingQuestions] = useState(false);
  const [selectedQuestionIds, setSelectedQuestionIds] = useState(
    initialAssessment?.curated_questions?.map((q) => q.question_id) || []
  );

  // Randomized blueprint configuration
  const [blueprintCount, setBlueprintCount] = useState(
    initialAssessment?.blueprint_config?.question_count || 5
  );
  const [selectedCompetencies, setSelectedCompetencies] = useState(
    initialAssessment?.blueprint_config?.required_competencies || ['CODE_COMPREHENSION', 'DEPENDENCY_TRACING']
  );
  const [blueprintDifficulty, setBlueprintDifficulty] = useState(
    initialAssessment?.blueprint_config?.difficulty || 'INTERMEDIATE'
  );

  // Step 3: Repository
  const [repositories, setRepositories] = useState([]);
  const [selectedRepoId, setSelectedRepoId] = useState(initialAssessment?.repository_id || '');
  const [loadingRepos, setLoadingRepos] = useState(false);

  // General State
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadRepositories();
    if (mode === 'CURATED') {
      loadPublishedQuestions();
    }
  }, [orgId, mode]);

  const loadRepositories = async () => {
    setLoadingRepos(true);
    try {
      const data = await hrApi.getRepositories(orgId, { pageSize: 50 });
      setRepositories(data?.items || []);
    } catch (err) {
      console.error('Failed to load repositories:', err);
    } finally {
      setLoadingRepos(false);
    }
  };

  const loadPublishedQuestions = async () => {
    setLoadingQuestions(true);
    try {
      const data = await hrApi.getQuestions(orgId, { reviewStatus: 'PUBLISHED', pageSize: 100 });
      setAvailableQuestions(data?.items || []);
    } catch (err) {
      console.error('Failed to load published questions:', err);
    } finally {
      setLoadingQuestions(false);
    }
  };

  const handleToggleQuestion = (qid) => {
    if (selectedQuestionIds.includes(qid)) {
      setSelectedQuestionIds(selectedQuestionIds.filter((id) => id !== qid));
    } else {
      setSelectedQuestionIds([...selectedQuestionIds, qid]);
    }
  };

  const handleToggleCompetency = (comp) => {
    if (selectedCompetencies.includes(comp)) {
      if (selectedCompetencies.length > 1) {
        setSelectedCompetencies(selectedCompetencies.filter((c) => c !== comp));
      }
    } else {
      setSelectedCompetencies([...selectedCompetencies, comp]);
    }
  };

  const validateStep1 = () => {
    if (!title.trim()) {
      setError('Assessment title is required.');
      return false;
    }
    if (durationMinutes < 5 || durationMinutes > 360) {
      setError('Duration must be between 5 and 360 minutes.');
      return false;
    }
    setError('');
    return true;
  };

  const validateStep2 = () => {
    if (mode === 'CURATED' && selectedQuestionIds.length === 0) {
      setError('Please select at least one published question for curated mode.');
      return false;
    }
    setError('');
    return true;
  };

  const handleNext = () => {
    if (step === 1 && !validateStep1()) return;
    if (step === 2 && !validateStep2()) return;
    setError('');
    setStep(step + 1);
  };

  const handleSaveDraft = async () => {
    setError('');
    setSaving(true);
    try {
      const payload = {
        title: title.trim(),
        description: description.trim(),
        instructions: instructions.trim(),
        job_role: jobRole.trim(),
        mode,
        duration_minutes: Number(durationMinutes),
        passing_score_pct: Number(passingScorePct),
        result_release_policy: resultReleasePolicy,
        max_attempts_per_candidate: Number(maxAttempts),
        repository_id: selectedRepoId || null,
        question_ids: mode === 'CURATED' ? selectedQuestionIds : [],
        blueprint_config:
          mode === 'RANDOMIZED'
            ? {
                question_count: Number(blueprintCount),
                required_competencies: selectedCompetencies,
                difficulty: blueprintDifficulty,
              }
            : null,
      };

      if (isEditing) {
        await assessmentApi.updateAssessment(orgId, initialAssessment.id, payload);
      } else {
        await assessmentApi.createAssessment(orgId, payload);
      }

      onSaved();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to save assessment draft.');
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    setError('');
    setPublishing(true);
    try {
      let currentId = initialAssessment?.id;
      // If new, save first
      if (!currentId) {
        const payload = {
          title: title.trim(),
          description: description.trim(),
          instructions: instructions.trim(),
          job_role: jobRole.trim(),
          mode,
          duration_minutes: Number(durationMinutes),
          passing_score_pct: Number(passingScorePct),
          result_release_policy: resultReleasePolicy,
          max_attempts_per_candidate: Number(maxAttempts),
          repository_id: selectedRepoId || null,
          question_ids: mode === 'CURATED' ? selectedQuestionIds : [],
          blueprint_config:
            mode === 'RANDOMIZED'
              ? {
                  question_count: Number(blueprintCount),
                  required_competencies: selectedCompetencies,
                  difficulty: blueprintDifficulty,
                }
              : null,
        };
        const created = await assessmentApi.createAssessment(orgId, payload);
        currentId = created.id;
      }

      await assessmentApi.publishAssessment(orgId, currentId);
      onSaved();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to publish assessment.');
    } finally {
      setPublishing(false);
    }
  };

  const selectedRepo = repositories.find((r) => r.id === selectedRepoId);

  return (
    <div style={styles.backdrop}>
      <div style={styles.modal}>
        {/* Header */}
        <div style={styles.header}>
          <div>
            <div style={styles.badgeRow}>
              <span style={styles.tagBlue}>ASSESSMENT STUDIO</span>
              <span style={styles.tagZinc}>STEP {step} OF 4</span>
            </div>
            <h2 style={styles.title}>
              {isEditing ? `Edit Assessment: ${title || 'Draft'}` : 'Create Formal Technical Assessment'}
            </h2>
            <p style={styles.subtitle}>
              Configure assessment blueprints, curated question sets, duration, and repository environments.
            </p>
          </div>
          <button onClick={onClose} style={styles.closeBtn}>✕</button>
        </div>

        {/* Wizard Stepper Tabs */}
        <div style={styles.stepperBar}>
          <div style={{ ...styles.stepItem, ...(step >= 1 ? styles.stepItemActive : {}) }}>
            1. Details & Policies
          </div>
          <div style={{ ...styles.stepItem, ...(step >= 2 ? styles.stepItemActive : {}) }}>
            2. Question Composition
          </div>
          <div style={{ ...styles.stepItem, ...(step >= 3 ? styles.stepItemActive : {}) }}>
            3. Codebase Workspace
          </div>
          <div style={{ ...styles.stepItem, ...(step >= 4 ? styles.stepItemActive : {}) }}>
            4. Review & Publish
          </div>
        </div>

        {error && <div style={styles.errorBox}>{error}</div>}

        <div style={styles.body}>
          {/* STEP 1: Details */}
          {step === 1 && (
            <div style={styles.stepContent}>
              <div style={styles.formGroup}>
                <label style={styles.label}>
                  Assessment Title <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Senior Backend Engineer - Codebase Evaluation"
                  style={styles.input}
                  required
                />
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Description & Objective</label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Evaluate candidate comprehension of architecture and design patterns"
                  style={styles.input}
                />
              </div>

              <div style={styles.rowTwo}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>Target Job Role</label>
                  <input
                    type="text"
                    value={jobRole}
                    onChange={(e) => setJobRole(e.target.value)}
                    placeholder="e.g. Backend Lead"
                    style={styles.input}
                  />
                </div>
                <div style={styles.formGroup}>
                  <label style={styles.label}>Duration (Minutes)</label>
                  <input
                    type="number"
                    min="5"
                    max="360"
                    value={durationMinutes}
                    onChange={(e) => setDurationMinutes(e.target.value)}
                    style={styles.input}
                  />
                </div>
              </div>

              <div style={styles.rowTwo}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>Passing Score Percentage (%)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="5"
                    value={passingScorePct}
                    onChange={(e) => setPassingScorePct(e.target.value)}
                    style={styles.input}
                  />
                </div>
                <div style={styles.formGroup}>
                  <label style={styles.label}>Max Attempts Per Candidate</label>
                  <input
                    type="number"
                    min="1"
                    max="5"
                    value={maxAttempts}
                    onChange={(e) => setMaxAttempts(parseInt(e.target.value) || 1)}
                    style={styles.input}
                  />
                </div>
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Result Release Policy</label>
                <select
                  value={resultReleasePolicy}
                  onChange={(e) => setResultReleasePolicy(e.target.value)}
                  style={styles.select}
                >
                  <option value="WITHHOLD_PENDING_REVIEW">Withhold Pending Recruiter Review (Default)</option>
                  <option value="IMMEDIATE">Immediate Candidate Feedback & Score</option>
                  <option value="RELEASE_SCORE_ONLY">Release Score Only (Questions Withheld)</option>
                </select>
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Candidate Instructions</label>
                <textarea
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  rows={3}
                  style={styles.textarea}
                />
              </div>
            </div>
          )}

          {/* STEP 2: Composition Mode */}
          {step === 2 && (
            <div style={styles.stepContent}>
              <div style={styles.modeSwitcher}>
                <button
                  type="button"
                  onClick={() => setMode('CURATED')}
                  style={{
                    ...styles.modeCard,
                    ...(mode === 'CURATED' ? styles.modeCardActive : {}),
                  }}
                >
                  <div style={styles.modeIcon}>🎯</div>
                  <div>
                    <h4 style={styles.modeTitle}>Curated Selection Mode</h4>
                    <p style={styles.modeDesc}>
                      Hand-pick specific verified questions from your organization's Question Bank.
                    </p>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setMode('RANDOMIZED')}
                  style={{
                    ...styles.modeCard,
                    ...(mode === 'RANDOMIZED' ? styles.modeCardActive : {}),
                  }}
                >
                  <div style={styles.modeIcon}>🎲</div>
                  <div>
                    <h4 style={styles.modeTitle}>Randomized Blueprint Mode</h4>
                    <p style={styles.modeDesc}>
                      Define competency distributions and difficulty constraints for automated selection.
                    </p>
                  </div>
                </button>
              </div>

              {/* Curated Mode Question Selector */}
              {mode === 'CURATED' && (
                <div style={styles.curatedListCard}>
                  <div style={styles.curatedHeader}>
                    <h4 style={{ margin: 0, fontSize: '14px', color: '#f8fafc' }}>
                      Select Questions ({selectedQuestionIds.length} chosen)
                    </h4>
                    <span style={{ fontSize: '12px', color: '#94a3b8' }}>
                      Only APPROVED & PUBLISHED questions are eligible.
                    </span>
                  </div>

                  {loadingQuestions ? (
                    <div style={styles.loadingBox}>Loading approved questions...</div>
                  ) : availableQuestions.length === 0 ? (
                    <div style={styles.emptyBox}>
                      No published questions found in Question Bank. Please publish questions before creating a curated assessment.
                    </div>
                  ) : (
                    <div style={styles.qSelectionList}>
                      {availableQuestions.map((q) => {
                        const isSelected = selectedQuestionIds.includes(q.id);
                        return (
                          <div
                            key={q.id}
                            onClick={() => handleToggleQuestion(q.id)}
                            style={{
                              ...styles.qSelectionItem,
                              borderColor: isSelected ? '#38bdf8' : '#334155',
                              backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.08)' : '#0f172a',
                            }}
                          >
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => {}} // handled by row click
                              style={{ marginRight: '12px' }}
                            />
                            <div style={{ flex: 1 }}>
                              <div style={styles.qSelectionTags}>
                                <span style={styles.tagZinc}>{q.competency}</span>
                                <span style={styles.tagBlue}>{q.difficulty}</span>
                                <span style={styles.tagZinc}>{q.response_format}</span>
                              </div>
                              <div style={styles.qSelectionText}>{q.question_text}</div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Randomized Blueprint Editor */}
              {mode === 'RANDOMIZED' && (
                <div style={styles.blueprintCard}>
                  <div style={styles.rowTwo}>
                    <div style={styles.formGroup}>
                      <label style={styles.label}>Number of Questions</label>
                      <input
                        type="number"
                        min="1"
                        max="50"
                        value={blueprintCount}
                        onChange={(e) => setBlueprintCount(e.target.value)}
                        style={styles.input}
                      />
                    </div>
                    <div style={styles.formGroup}>
                      <label style={styles.label}>Difficulty Constraint</label>
                      <select
                        value={blueprintDifficulty}
                        onChange={(e) => setBlueprintDifficulty(e.target.value)}
                        style={styles.select}
                      >
                        {DIFFICULTIES.map((d) => (
                          <option key={d} value={d}>{d}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div style={styles.formGroup}>
                    <label style={styles.label}>Required Competencies (Select at least one)</label>
                    <div style={styles.chipsRow}>
                      {COMPETENCIES.map((c) => {
                        const isSelected = selectedCompetencies.includes(c);
                        return (
                          <button
                            key={c}
                            type="button"
                            onClick={() => handleToggleCompetency(c)}
                            style={{
                              ...styles.chipBtn,
                              backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.2)' : '#0f172a',
                              borderColor: isSelected ? '#38bdf8' : '#334155',
                              color: isSelected ? '#38bdf8' : '#94a3b8',
                            }}
                          >
                            {isSelected ? '✓ ' : '+ '}
                            {c.replace(/_/g, ' ')}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* STEP 3: Repository Workspace */}
          {step === 3 && (
            <div style={styles.stepContent}>
              <div style={styles.formGroup}>
                <label style={styles.label}>Attach Approved Codebase Repository (Optional)</label>
                <p style={styles.hint}>
                  Enables the candidate split-pane workspace with live Codebase Explorer and AST symbol exploration.
                </p>
                {loadingRepos ? (
                  <div style={styles.loadingBox}>Loading approved repositories...</div>
                ) : (
                  <select
                    value={selectedRepoId}
                    onChange={(e) => setSelectedRepoId(e.target.value)}
                    style={styles.select}
                  >
                    <option value="">No repository attached (General assessment)</option>
                    {repositories.map((repo) => (
                      <option key={repo.id} value={repo.id}>
                        {repo.display_name} ({repo.approval_status} • {repo.last_analyzed_commit ? repo.last_analyzed_commit.slice(0, 7) : 'no commit'})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {selectedRepo && (
                <div style={styles.repoDetailsCard}>
                  <div style={styles.repoCardHeader}>
                    <span style={{ fontSize: '20px' }}>🏛️</span>
                    <div>
                      <h4 style={{ margin: 0, fontSize: '15px', color: '#f8fafc' }}>
                        {selectedRepo.display_name}
                      </h4>
                      <code style={{ fontSize: '11px', color: '#94a3b8' }}>{selectedRepo.repo_url}</code>
                    </div>
                  </div>
                  <div style={styles.repoMetaGrid}>
                    <div>
                      <span style={styles.metaLabel}>Approval Status:</span>
                      <span style={{ color: '#10b981', fontWeight: '600' }}> {selectedRepo.approval_status}</span>
                    </div>
                    <div>
                      <span style={styles.metaLabel}>Analyzed Commit:</span>
                      <code> {selectedRepo.last_analyzed_commit ? selectedRepo.last_analyzed_commit.slice(0, 8) : 'HEAD'}</code>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* STEP 4: Review & Publish */}
          {step === 4 && (
            <div style={styles.stepContent}>
              <div style={styles.reviewCard}>
                <h4 style={{ margin: '0 0 16px', fontSize: '16px', color: '#f8fafc' }}>
                  Assessment Verification Summary
                </h4>
                <div style={styles.reviewGrid}>
                  <div style={styles.reviewItem}>
                    <span style={styles.reviewLabel}>Title:</span>
                    <strong style={styles.reviewVal}>{title}</strong>
                  </div>
                  <div style={styles.reviewItem}>
                    <span style={styles.reviewLabel}>Mode:</span>
                    <span style={styles.tagBlue}>{mode}</span>
                  </div>
                  <div style={styles.reviewItem}>
                    <span style={styles.reviewLabel}>Duration:</span>
                    <strong style={styles.reviewVal}>{durationMinutes} minutes</strong>
                  </div>
                  <div style={styles.reviewItem}>
                    <span style={styles.reviewLabel}>Passing Threshold:</span>
                    <strong style={styles.reviewVal}>{passingScorePct}%</strong>
                  </div>
                  <div style={styles.reviewItem}>
                    <span style={styles.reviewLabel}>Total Questions:</span>
                    <strong style={styles.reviewVal}>
                      {mode === 'CURATED' ? selectedQuestionIds.length : `${blueprintCount} (randomized)`}
                    </strong>
                  </div>
                  <div style={styles.reviewItem}>
                    <span style={styles.reviewLabel}>Release Policy:</span>
                    <span style={styles.tagZinc}>{resultReleasePolicy}</span>
                  </div>
                  <div style={styles.reviewItem}>
                    <span style={styles.reviewLabel}>Attached Codebase:</span>
                    <strong style={styles.reviewVal}>{selectedRepo?.display_name || 'None'}</strong>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer Navigation */}
        <div style={styles.footer}>
          {step > 1 && (
            <button onClick={() => setStep(step - 1)} style={styles.cancelBtn}>
              ← Previous
            </button>
          )}
          <div style={{ flex: 1 }} />
          {step < 4 ? (
            <button onClick={handleNext} style={styles.primaryBtn}>
              Continue →
            </button>
          ) : (
            <div style={{ display: 'flex', gap: '10px' }}>
              <button onClick={handleSaveDraft} disabled={saving} style={styles.cancelBtn}>
                {saving ? 'Saving Draft...' : 'Save Draft'}
              </button>
              <button onClick={handlePublish} disabled={publishing} style={styles.publishBtn}>
                {publishing ? 'Publishing Version...' : '🚀 Publish Assessment'}
              </button>
            </div>
          )}
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
    maxWidth: '860px',
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
  stepperBar: {
    display: 'flex',
    borderBottom: '1px solid #334155',
    backgroundColor: '#0f172a',
  },
  stepItem: {
    flex: 1,
    padding: '10px 14px',
    fontSize: '12px',
    fontWeight: '600',
    color: '#64748b',
    textAlign: 'center',
    borderBottom: '2px solid transparent',
  },
  stepItemActive: {
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
  stepContent: {
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
    fontSize: '13px',
    outline: 'none',
  },
  select: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '8px',
    color: '#f8fafc',
    padding: '10px 14px',
    fontSize: '13px',
    outline: 'none',
    cursor: 'pointer',
  },
  textarea: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '8px',
    color: '#f8fafc',
    padding: '10px 14px',
    fontSize: '13px',
    outline: 'none',
    fontFamily: 'inherit',
    resize: 'vertical',
  },
  hint: {
    margin: 0,
    fontSize: '12px',
    color: '#64748b',
  },
  modeSwitcher: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '14px',
  },
  modeCard: {
    backgroundColor: '#0f172a',
    border: '2px solid #334155',
    borderRadius: '10px',
    padding: '16px',
    display: 'flex',
    alignItems: 'center',
    gap: '14px',
    cursor: 'pointer',
    textAlign: 'left',
    transition: 'all 0.15s ease',
  },
  modeCardActive: {
    borderColor: '#38bdf8',
    backgroundColor: 'rgba(56, 189, 248, 0.08)',
  },
  modeIcon: {
    fontSize: '28px',
  },
  modeTitle: {
    margin: '0 0 4px',
    fontSize: '14px',
    fontWeight: '700',
    color: '#f8fafc',
  },
  modeDesc: {
    margin: 0,
    fontSize: '12px',
    color: '#94a3b8',
    lineHeight: '1.4',
  },
  curatedListCard: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '10px',
    padding: '16px',
  },
  curatedHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '14px',
  },
  qSelectionList: {
    maxHeight: '300px',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  qSelectionItem: {
    border: '1px solid',
    borderRadius: '8px',
    padding: '10px 14px',
    display: 'flex',
    alignItems: 'center',
    cursor: 'pointer',
  },
  qSelectionTags: {
    display: 'flex',
    gap: '6px',
    marginBottom: '4px',
  },
  qSelectionText: {
    fontSize: '13px',
    color: '#f8fafc',
  },
  blueprintCard: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '10px',
    padding: '18px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  chipsRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
  },
  chipBtn: {
    border: '1px solid',
    borderRadius: '20px',
    padding: '6px 14px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  repoDetailsCard: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '10px',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  repoCardHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  repoMetaGrid: {
    display: 'flex',
    gap: '24px',
    fontSize: '12px',
  },
  metaLabel: {
    color: '#94a3b8',
  },
  reviewCard: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '10px',
    padding: '18px',
  },
  reviewGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '14px',
  },
  reviewItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  reviewLabel: {
    fontSize: '11px',
    fontWeight: '600',
    color: '#94a3b8',
    textTransform: 'uppercase',
  },
  reviewVal: {
    fontSize: '14px',
    color: '#f8fafc',
  },
  footer: {
    display: 'flex',
    alignItems: 'center',
    padding: '16px 24px',
    borderTop: '1px solid #334155',
    backgroundColor: '#0f172a',
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
  publishBtn: {
    backgroundColor: '#10b981',
    color: '#0f172a',
    border: 'none',
    padding: '9px 20px',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '700',
    cursor: 'pointer',
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
    padding: '30px',
    textAlign: 'center',
    color: '#94a3b8',
  },
  emptyBox: {
    padding: '30px',
    textAlign: 'center',
    color: '#64748b',
    border: '1px dashed #334155',
    borderRadius: '8px',
  },
};
