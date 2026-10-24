import React, { useState, useEffect, useCallback } from 'react';
import { hrApi } from '../../services/hrApi';

const COMPETENCIES = [
  { id: 'CODE_COMPREHENSION', label: 'Code Comprehension', desc: 'Syntax, control flows, logic understanding' },
  { id: 'DEPENDENCY_TRACING', label: 'Dependency Tracing', desc: 'Imports, call chains, module coupling' },
  { id: 'ARCHITECTURE_REASONING', label: 'Architecture Reasoning', desc: 'Layering, patterns, design principles' },
  { id: 'DEBUGGING', label: 'Debugging & Diagnostics', desc: 'Edge cases, error handling, failure modes' },
  { id: 'CHANGE_IMPACT', label: 'Change Impact', desc: 'Blast radius, breaking changes, regression risks' },
];

const DIFFICULTIES = ['BEGINNER', 'INTERMEDIATE', 'ADVANCED'];

export default function QuestionGenerationModal({
  orgId,
  onClose,
  onGenerated,
  initialMode = 'SKILL_BASED',
  initialRepoId = '',
}) {
  const [mode, setMode] = useState(initialMode);
  const [skillName, setSkillName] = useState('Python');
  const [selectedRepoId, setSelectedRepoId] = useState(initialRepoId);
  const [repositories, setRepositories] = useState([]);
  const [difficulty, setDifficulty] = useState('INTERMEDIATE');
  const [selectedCompetencies, setSelectedCompetencies] = useState([
    'CODE_COMPREHENSION',
    'DEPENDENCY_TRACING',
  ]);
  const [requestedCount, setRequestedCount] = useState(3);
  const [generationNotes, setGenerationNotes] = useState('');

  const [loadingRepos, setLoadingRepos] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [resultSummary, setResultSummary] = useState(null);

  const loadApprovedRepositories = useCallback(async () => {
    setLoadingRepos(true);
    try {
      const data = await hrApi.getRepositories(orgId, { pageSize: 50 });
      const repos = data?.items || [];
      setRepositories(repos);
      if (initialRepoId) {
        setSelectedRepoId(initialRepoId);
      } else if (repos.length > 0) {
        setSelectedRepoId((prev) => prev || repos[0].id);
      }
    } catch (err) {
      console.error('Failed to load repositories:', err);
    } finally {
      setLoadingRepos(false);
    }
  }, [orgId, initialRepoId]);

  useEffect(() => {
    loadApprovedRepositories();
  }, [loadApprovedRepositories]);

  const handleToggleCompetency = (id) => {
    if (selectedCompetencies.includes(id)) {
      if (selectedCompetencies.length > 1) {
        setSelectedCompetencies(selectedCompetencies.filter((c) => c !== id));
      }
    } else {
      setSelectedCompetencies([...selectedCompetencies, id]);
    }
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    setError('');
    setResultSummary(null);

    if (mode === 'REPOSITORY_BASED' && !selectedRepoId) {
      setError('Please select an authorized repository for repository-grounded question generation.');
      return;
    }

    if (mode === 'SKILL_BASED' && !skillName.trim()) {
      setError('Please enter a target technical skill or language.');
      return;
    }

    setGenerating(true);
    try {
      const payload = {
        mode,
        skill_name: mode === 'SKILL_BASED' ? skillName.trim() : null,
        repo_id: mode === 'REPOSITORY_BASED' ? selectedRepoId : null,
        difficulty,
        competencies: selectedCompetencies,
        requested_count: Number(requestedCount),
        notes: generationNotes.trim() || undefined,
      };

      const res = await hrApi.generateQuestions(orgId, payload);
      setResultSummary(res);
      onGenerated();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Generation failed. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  const selectedRepo = repositories.find((r) => r.id === selectedRepoId);

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        {/* Header */}
        <div style={styles.header}>
          <div>
            <div style={styles.badge}>AI-ASSISTED QUESTION GENERATION</div>
            <h3 style={styles.title}>Generate Questions for HR Question Bank</h3>
            <p style={styles.subtext}>
              All generated questions default to NEEDS_REVIEW status and require human HR verification before publication.
            </p>
          </div>
          <button style={styles.closeBtn} onClick={onClose}>&times;</button>
        </div>

        {/* Content Body */}
        <div style={styles.body}>
          {error && <div style={styles.errorBox}>{error}</div>}

          {/* Mode Switcher */}
          <div style={styles.modeContainer}>
            <button
              type="button"
              onClick={() => setMode('SKILL_BASED')}
              style={{
                ...styles.modeBtn,
                backgroundColor: mode === 'SKILL_BASED' ? '#38bdf8' : '#1e293b',
                color: mode === 'SKILL_BASED' ? '#0f172a' : '#cbd5e1',
                borderColor: mode === 'SKILL_BASED' ? '#38bdf8' : '#334155',
              }}
            >
              <span style={{ fontSize: '16px', marginRight: '6px' }}>⚡</span>
              Mode A: Skill-Based Generation
            </button>
            <button
              type="button"
              onClick={() => setMode('REPOSITORY_BASED')}
              style={{
                ...styles.modeBtn,
                backgroundColor: mode === 'REPOSITORY_BASED' ? '#38bdf8' : '#1e293b',
                color: mode === 'REPOSITORY_BASED' ? '#0f172a' : '#cbd5e1',
                borderColor: mode === 'REPOSITORY_BASED' ? '#38bdf8' : '#334155',
              }}
            >
              <span style={{ fontSize: '16px', marginRight: '6px' }}>📦</span>
              Mode B: Repository-Grounded Generation
            </button>
          </div>

          <form onSubmit={handleGenerate} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Mode Specific Inputs */}
            {mode === 'SKILL_BASED' ? (
              <div style={styles.formGroup}>
                <label style={styles.label}>Target Skill or Technology</label>
                <input
                  type="text"
                  value={skillName}
                  onChange={(e) => setSkillName(e.target.value)}
                  placeholder="e.g. TypeScript, React Hooks, PostgreSQL, Kubernetes"
                  style={styles.input}
                  required
                />
                <span style={styles.helpText}>Generates scenario-based technical questions for this technology.</span>
              </div>
            ) : (
              <div style={styles.formGroup}>
                <label style={styles.label}>Select Approved Repository</label>
                {loadingRepos ? (
                  <div style={{ color: '#94a3b8', fontSize: '13px' }}>Loading repositories...</div>
                ) : repositories.length === 0 ? (
                  <div style={styles.warningBox}>
                    No registered repositories found for this organization. Please register and analyze a repository in the Repository Library first.
                  </div>
                ) : (
                  <select
                    value={selectedRepoId}
                    onChange={(e) => setSelectedRepoId(e.target.value)}
                    style={styles.select}
                  >
                    {repositories.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.display_name} ({r.approval_status} — {r.analysis_status})
                      </option>
                    ))}
                  </select>
                )}
                {selectedRepo && (
                  <div style={styles.repoDetailsBox}>
                    <div><strong>Revision:</strong> {selectedRepo.last_analyzed_commit || 'HEAD'}</div>
                    <div><strong>Status:</strong> {selectedRepo.analysis_status}</div>
                    {selectedRepo.analysis_status !== 'COMPLETED' && (
                      <div style={{ color: '#f59e0b', marginTop: '4px' }}>
                        ⚠️ Static code analysis is {selectedRepo.analysis_status.toLowerCase()}. Analysis must complete before generating grounded questions.
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Difficulty & Count */}
            <div style={styles.gridRow}>
              <div style={styles.formGroup}>
                <label style={styles.label}>Difficulty Level</label>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                  style={styles.select}
                >
                  {DIFFICULTIES.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Question Count (1 - 10)</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={requestedCount}
                  onChange={(e) => setRequestedCount(e.target.value)}
                  style={styles.input}
                  required
                />
              </div>
            </div>

            {/* Competencies */}
            <div style={styles.formGroup}>
              <label style={styles.label}>Competencies to Cover</label>
              <div style={styles.competencyGrid}>
                {COMPETENCIES.map((c) => {
                  const isChecked = selectedCompetencies.includes(c.id);
                  return (
                    <div
                      key={c.id}
                      onClick={() => handleToggleCompetency(c.id)}
                      style={{
                        ...styles.competencyCard,
                        borderColor: isChecked ? '#38bdf8' : '#334155',
                        backgroundColor: isChecked ? 'rgba(56, 189, 248, 0.08)' : '#1e293b',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {}}
                          style={{ cursor: 'pointer' }}
                        />
                        <span style={{ fontSize: '13px', fontWeight: '600', color: '#f8fafc' }}>
                          {c.label}
                        </span>
                      </div>
                      <span style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
                        {c.desc}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Optional Evaluation Notes */}
            <div style={styles.formGroup}>
              <label style={styles.label}>Instructions or Focus Notes (Optional)</label>
              <input
                type="text"
                value={generationNotes}
                onChange={(e) => setGenerationNotes(e.target.value)}
                placeholder="e.g. Focus on asynchronous concurrency patterns and error handling"
                style={styles.input}
              />
            </div>

            {/* Results Callout */}
            {resultSummary && (
              <div style={styles.successBox}>
                <div style={{ fontWeight: '700', fontSize: '14px', marginBottom: '4px' }}>
                  ✓ Generated {resultSummary.generated_count} Validated Questions!
                </div>
                <div style={{ fontSize: '13px', color: '#e2e8f0' }}>{resultSummary.note}</div>
                <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '6px' }}>
                  The newly generated drafts have been added to your Question Bank in <strong>NEEDS_REVIEW</strong> status.
                </div>
              </div>
            )}

            {/* Submit Button */}
            <div style={styles.footer}>
              <button type="button" onClick={onClose} style={styles.cancelBtn}>
                {resultSummary ? 'Done' : 'Cancel'}
              </button>
              <button
                type="submit"
                disabled={generating || (mode === 'REPOSITORY_BASED' && selectedRepo?.analysis_status !== 'COMPLETED')}
                style={{
                  ...styles.submitBtn,
                  opacity: generating ? 0.6 : 1,
                }}
              >
                {generating ? 'Generating & Validating Questions...' : 'Start Question Generation'}
              </button>
            </div>
          </form>
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
    maxWidth: '820px',
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
  modeContainer: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
    marginBottom: '20px',
  },
  modeBtn: {
    padding: '12px 16px',
    borderRadius: '8px',
    border: '1px solid',
    fontSize: '13px',
    fontWeight: '700',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.15s ease',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  label: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#cbd5e1',
  },
  helpText: {
    fontSize: '12px',
    color: '#94a3b8',
  },
  input: {
    padding: '10px 14px',
    borderRadius: '6px',
    border: '1px solid #334155',
    backgroundColor: '#1e293b',
    color: '#f8fafc',
    fontSize: '14px',
    outline: 'none',
  },
  select: {
    padding: '10px 14px',
    borderRadius: '6px',
    border: '1px solid #334155',
    backgroundColor: '#1e293b',
    color: '#f8fafc',
    fontSize: '14px',
    outline: 'none',
    cursor: 'pointer',
  },
  gridRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '16px',
  },
  competencyGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '10px',
  },
  competencyCard: {
    padding: '10px 12px',
    borderRadius: '6px',
    border: '1px solid #334155',
    cursor: 'pointer',
    display: 'flex',
    flexDirection: 'column',
    transition: 'all 0.15s ease',
  },
  repoDetailsBox: {
    fontSize: '12px',
    color: '#cbd5e1',
    backgroundColor: '#1e293b',
    padding: '8px 12px',
    borderRadius: '6px',
    border: '1px solid #334155',
    marginTop: '6px',
  },
  warningBox: {
    padding: '10px 14px',
    backgroundColor: 'rgba(245, 158, 11, 0.1)',
    border: '1px solid #f59e0b',
    color: '#fbbf24',
    borderRadius: '6px',
    fontSize: '13px',
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
  successBox: {
    padding: '14px 18px',
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    border: '1px solid #10b981',
    color: '#10b981',
    borderRadius: '8px',
  },
  footer: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    marginTop: '16px',
    paddingTop: '16px',
    borderTop: '1px solid #1e293b',
  },
  cancelBtn: {
    backgroundColor: 'transparent',
    border: '1px solid #334155',
    color: '#cbd5e1',
    padding: '10px 20px',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  submitBtn: {
    backgroundColor: '#38bdf8',
    border: 'none',
    color: '#0f172a',
    padding: '10px 24px',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: '700',
    cursor: 'pointer',
  },
};
