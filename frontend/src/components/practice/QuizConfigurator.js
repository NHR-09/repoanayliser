import React, { useState } from 'react';
import { practiceApi } from '../../services/practiceApi';

export default function QuizConfigurator({ skills = [], repos = [], onQuizStarted }) {
  const [mode, setMode] = useState('SKILL_BASED');
  const [selectedSkill, setSelectedSkill] = useState(skills[0]?.skill_name || 'Python');
  const [selectedRepoId, setSelectedRepoId] = useState(repos[0]?.id || '');
  const [difficulty, setDifficulty] = useState('INTERMEDIATE');
  const [questionCount, setQuestionCount] = useState(5);
  const [selectedCompetencies, setSelectedCompetencies] = useState([
    'CODE_COMPREHENSION',
    'DEPENDENCY_TRACING',
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const COMPETENCIES = [
    { id: 'CODE_COMPREHENSION', label: 'Code Comprehension', desc: 'Understanding syntax, logic, and control flows' },
    { id: 'DEPENDENCY_TRACING', label: 'Dependency Tracing', desc: 'Call graphs, callers, and module boundaries' },
    { id: 'ARCHITECTURE_REASONING', label: 'Architecture Reasoning', desc: 'Patterns, layering, decoupling, and design decisions' },
    { id: 'DEBUGGING', label: 'Debugging & Diagnostics', desc: 'Error handling, race conditions, and edge cases' },
    { id: 'CHANGE_IMPACT', label: 'Change Impact', desc: 'Blast radius and cascading modification effects' },
  ];

  const handleToggleCompetency = (id) => {
    if (selectedCompetencies.includes(id)) {
      if (selectedCompetencies.length > 1) {
        setSelectedCompetencies(selectedCompetencies.filter(c => c !== id));
      }
    } else {
      setSelectedCompetencies([...selectedCompetencies, id]);
    }
  };

  const handleStartQuiz = async (e) => {
    e.preventDefault();
    setError('');

    if (mode === 'REPOSITORY_BASED' && !selectedRepoId) {
      setError('Please select a connected repository for repository-grounded practice.');
      return;
    }

    setLoading(true);
    try {
      const quiz = await practiceApi.generateQuiz({
        mode,
        skillName: mode === 'SKILL_BASED' ? selectedSkill : null,
        repoId: mode === 'REPOSITORY_BASED' ? selectedRepoId : null,
        difficulty,
        competencies: selectedCompetencies,
        questionCount,
      });

      if (onQuizStarted) {
        onQuizStarted(quiz);
      }
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || 'Quiz generation failed.';
      setError(`Generation Error: ${detail}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      padding: '24px',
      display: 'flex',
      flexDirection: 'column',
      gap: '20px'
    }}>
      <div>
        <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' }}>
          Configure Technical Practice Quiz
        </h3>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          Choose your practice mode and target competencies. Every question is validated for objective precision.
        </p>
      </div>

      {error && (
        <div style={{
          padding: '10px 14px',
          borderRadius: 'var(--radius-md)',
          background: 'var(--red-dim)',
          color: 'var(--red)',
          border: '1px solid var(--red)',
          fontSize: '13px'
        }}>
          {error}
        </div>
      )}

      <form onSubmit={handleStartQuiz} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Mode Selector */}
        <div>
          <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '8px' }}>
            PRACTICE MODE
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div
              onClick={() => setMode('SKILL_BASED')}
              style={{
                padding: '14px',
                borderRadius: 'var(--radius-md)',
                border: `1px solid ${mode === 'SKILL_BASED' ? 'var(--blue)' : 'var(--border)'}`,
                background: mode === 'SKILL_BASED' ? 'var(--blue-dim)' : 'var(--bg-elevated)',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              <div style={{ fontWeight: 600, color: mode === 'SKILL_BASED' ? 'var(--blue)' : 'var(--text-primary)', fontSize: '14px' }}>
                Mode A: Skill-Based Practice
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Practice questions tailored to your claimed languages, frameworks, or databases without repository dependencies.
              </div>
            </div>

            <div
              onClick={() => setMode('REPOSITORY_BASED')}
              style={{
                padding: '14px',
                borderRadius: 'var(--radius-md)',
                border: `1px solid ${mode === 'REPOSITORY_BASED' ? 'var(--green)' : 'var(--border)'}`,
                background: mode === 'REPOSITORY_BASED' ? 'var(--green-dim)' : 'var(--bg-elevated)',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              <div style={{ fontWeight: 600, color: mode === 'REPOSITORY_BASED' ? 'var(--green)' : 'var(--text-primary)', fontSize: '14px' }}>
                Mode B: Repository-Grounded Practice
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Generate questions strictly grounded in actual AST symbols, file snippets, and caller-callee graphs of your connected repository.
              </div>
            </div>
          </div>
        </div>

        {/* Dynamic target based on Mode */}
        {mode === 'SKILL_BASED' ? (
          <div>
            <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
              TARGET TECHNOLOGY / SKILL
            </label>
            {skills.length > 0 ? (
              <select
                value={selectedSkill}
                onChange={(e) => setSelectedSkill(e.target.value)}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border)',
                  background: 'var(--bg-input)',
                  color: 'var(--text-primary)',
                  fontSize: '13px'
                }}
              >
                {skills.map(s => (
                  <option key={s.id} value={s.skill_name}>{s.skill_name} ({s.category})</option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={selectedSkill}
                onChange={(e) => setSelectedSkill(e.target.value)}
                placeholder="Enter technology (e.g. Python, React, PostgreSQL)"
                required
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border)',
                  background: 'var(--bg-input)',
                  color: 'var(--text-primary)',
                  fontSize: '13px'
                }}
              />
            )}
          </div>
        ) : (
          <div>
            <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
              TARGET REPOSITORY
            </label>
            {repos.length > 0 ? (
              <select
                value={selectedRepoId}
                onChange={(e) => setSelectedRepoId(e.target.value)}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border)',
                  background: 'var(--bg-input)',
                  color: 'var(--text-primary)',
                  fontSize: '13px'
                }}
              >
                {repos.map(r => (
                  <option key={r.id} value={r.id}>
                    {r.display_name} ({r.analysis_status})
                  </option>
                ))}
              </select>
            ) : (
              <div style={{ fontSize: '13px', color: 'var(--amber)' }}>
                No repositories connected yet. Please connect a repository in the Repositories tab first.
              </div>
            )}
          </div>
        )}

        {/* Difficulty & Count */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
              DIFFICULTY LEVEL
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              {['BEGINNER', 'INTERMEDIATE', 'ADVANCED'].map(d => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDifficulty(d)}
                  style={{
                    flex: 1,
                    padding: '8px 0',
                    borderRadius: 'var(--radius-sm)',
                    border: `1px solid ${difficulty === d ? 'var(--accent)' : 'var(--border)'}`,
                    background: difficulty === d ? 'var(--bg-elevated)' : 'transparent',
                    color: difficulty === d ? 'var(--text-primary)' : 'var(--text-muted)',
                    fontSize: '12px',
                    fontWeight: difficulty === d ? 600 : 400,
                    cursor: 'pointer'
                  }}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
              QUESTION COUNT
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              {[5, 10, 15].map(cnt => (
                <button
                  key={cnt}
                  type="button"
                  onClick={() => setQuestionCount(cnt)}
                  style={{
                    flex: 1,
                    padding: '8px 0',
                    borderRadius: 'var(--radius-sm)',
                    border: `1px solid ${questionCount === cnt ? 'var(--accent)' : 'var(--border)'}`,
                    background: questionCount === cnt ? 'var(--bg-elevated)' : 'transparent',
                    color: questionCount === cnt ? 'var(--text-primary)' : 'var(--text-muted)',
                    fontSize: '12px',
                    fontWeight: questionCount === cnt ? 600 : 400,
                    cursor: 'pointer'
                  }}
                >
                  {cnt} Questions
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Competencies */}
        <div>
          <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '8px' }}>
            TARGET COMPETENCIES (Select at least 1)
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '8px' }}>
            {COMPETENCIES.map(comp => {
              const isChecked = selectedCompetencies.includes(comp.id);
              return (
                <div
                  key={comp.id}
                  onClick={() => handleToggleCompetency(comp.id)}
                  style={{
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: `1px solid ${isChecked ? 'var(--accent)' : 'var(--border)'}`,
                    background: isChecked ? 'rgba(255,255,255,0.04)' : 'var(--bg-elevated)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px'
                  }}
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    readOnly
                    style={{ marginTop: '3px' }}
                  />
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 500, color: isChecked ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                      {comp.label}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', lineHeight: 1.3 }}>
                      {comp.desc}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Action Button */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '12px' }}>
          <button
            type="submit"
            disabled={loading}
            style={{
              padding: '10px 24px',
              background: loading ? 'var(--border)' : 'var(--accent)',
              color: '#09090b',
              fontWeight: 600,
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: '13px',
              transition: 'all 0.2s'
            }}
          >
            {loading ? 'Validating & Generating Quiz...' : '⚡ Generate & Start Practice Quiz'}
          </button>
        </div>
      </form>
    </div>
  );
}
