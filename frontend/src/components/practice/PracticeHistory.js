import React, { useState, useEffect } from 'react';
import { practiceApi } from '../../services/practiceApi';

export default function PracticeHistory({ onReviewQuiz }) {
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const data = await practiceApi.getPracticeHistory();
      setHistory(data);
    } catch (err) {
      console.error('Failed to load practice history:', err);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (pct) => {
    if (pct >= 80) return 'var(--green)';
    if (pct >= 50) return 'var(--amber)';
    return 'var(--red)';
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
        Loading practice history...
      </div>
    );
  }

  const {
    completed_quizzes_count = 0,
    total_questions_answered = 0,
    average_score_pct = 0,
    competency_progress = {},
    recent_quizzes = []
  } = history || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Metric Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Completed Quizzes
          </span>
          <span style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-primary)' }}>
            {completed_quizzes_count}
          </span>
          <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
            Personal practice sessions
          </span>
        </div>

        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Questions Solved
          </span>
          <span style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-primary)' }}>
            {total_questions_answered}
          </span>
          <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
            Verified technical problems
          </span>
        </div>

        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Average Accuracy
          </span>
          <span style={{ fontSize: '28px', fontWeight: 700, color: getScoreColor(average_score_pct) }}>
            {average_score_pct}%
          </span>
          <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
            Across all practice attempts
          </span>
        </div>
      </div>

      {/* Competency Mastery Overview */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px'
      }}>
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Cumulative Competency Progress
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Track your performance breakdown across core technical domains. Each percentage displays the supporting question count.
          </p>
        </div>

        {Object.keys(competency_progress).length === 0 ? (
          <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)', fontSize: '13px' }}>
            No questions solved yet. Start a practice quiz to build your competency profile.
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
            {Object.entries(competency_progress).map(([comp, stats]) => (
              <div key={comp} style={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)' }}>
                    {comp.replace('_', ' ')}
                  </span>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: getScoreColor(stats.accuracy_pct) }}>
                    {stats.accuracy_pct}%
                  </span>
                </div>

                <div style={{ height: '6px', background: 'var(--bg-input)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{
                    height: '100%',
                    width: `${stats.accuracy_pct}%`,
                    background: getScoreColor(stats.accuracy_pct),
                    transition: 'width 0.3s ease'
                  }} />
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-dim)' }}>
                  <span>Points: {stats.awarded_points}/{stats.max_points}</span>
                  <span>Sample size: {stats.question_count} questions</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Historical Quizzes Table */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' }}>
              Recent Practice Quizzes
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Review past quizzes, score breakdowns, and detailed explanations.
            </p>
          </div>
          <button
            onClick={loadHistory}
            style={{
              padding: '4px 10px',
              background: 'transparent',
              border: '1px solid var(--border)',
              color: 'var(--text-muted)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '12px',
              cursor: 'pointer'
            }}
          >
            ↻ Refresh
          </button>
        </div>

        {recent_quizzes.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
            No practice sessions recorded yet. Configure and generate your first quiz above!
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {recent_quizzes.map((q) => {
              const isCompleted = q.status === 'COMPLETED';
              return (
                <div
                  key={q.id}
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-md)',
                    padding: '14px 16px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '12px'
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '14px' }}>
                        {q.mode === 'REPOSITORY_BASED' ? `Repo: ${q.repo_name || 'Codebase'}` : `Skill: ${q.skill_name || 'General'}`}
                      </span>
                      <span style={{
                        fontSize: '10px',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: 'rgba(255,255,255,0.06)',
                        color: 'var(--text-muted)'
                      }}>
                        {q.difficulty}
                      </span>
                      <span style={{
                        fontSize: '10px',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: isCompleted ? 'var(--green-dim)' : 'var(--amber-dim)',
                        color: isCompleted ? 'var(--green)' : 'var(--amber)'
                      }}>
                        {q.status}
                      </span>
                    </div>

                    <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
                      Date: {new Date(q.created_at).toLocaleString()} • {q.question_count} Questions
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    {isCompleted && (
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '15px', fontWeight: 700, color: getScoreColor(q.percentage_score) }}>
                          {q.total_score} / {q.max_score} ({q.percentage_score}%)
                        </div>
                      </div>
                    )}

                    {onReviewQuiz && isCompleted && (
                      <button
                        onClick={() => onReviewQuiz(q.id)}
                        style={{
                          padding: '6px 12px',
                          background: 'var(--bg-card)',
                          border: '1px solid var(--border-hover)',
                          color: 'var(--text-primary)',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '12px',
                          cursor: 'pointer'
                        }}
                      >
                        Review Explanations →
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
