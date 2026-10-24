import React, { useState } from 'react';

export default function QuizResults({ results, onPracticeAgain, onBackToDashboard }) {
  const [expandedQId, setExpandedQId] = useState(null);

  if (!results) return null;

  const {
    total_score = 0,
    max_score = 0,
    percentage_score = 0,
    competency_breakdown = {},
    questions = [],
    recommendations = [],
    mode,
    skill_name
  } = results;

  const toggleExpand = (id) => {
    setExpandedQId(expandedQId === id ? null : id);
  };

  const getScoreColor = (pct) => {
    if (pct >= 80) return 'var(--green)';
    if (pct >= 50) return 'var(--amber)';
    return 'var(--red)';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Score Banner */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '28px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '20px'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Practice Session Completed • {mode === 'REPOSITORY_BASED' ? 'Repository Grounded' : `Skill: ${skill_name || 'General'}`}
          </span>
          <h2 style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-primary)' }}>
            Practice Score: <span style={{ color: getScoreColor(percentage_score) }}>{total_score} / {max_score}</span> ({percentage_score}%)
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Objective scoring applied. Precision-sensitive partial credit computed for multiple-select questions.
          </p>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontStyle: 'italic', marginTop: '4px' }}>
            * Practice feedback is an internal educational metric and does not constitute a formal hiring qualification.
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          {onPracticeAgain && (
            <button
              onClick={onPracticeAgain}
              style={{
                padding: '9px 18px',
                background: 'var(--accent)',
                color: '#09090b',
                fontWeight: 600,
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                fontSize: '13px'
              }}
            >
              Practice Again ↻
            </button>
          )}
          {onBackToDashboard && (
            <button
              onClick={onBackToDashboard}
              style={{
                padding: '9px 18px',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                color: 'var(--text-primary)',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                fontSize: '13px'
              }}
            >
              Dashboard
            </button>
          )}
        </div>
      </div>

      {/* Competency Breakdown & Recommendations */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
        {/* Competency Mastery */}
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px'
        }}>
          <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Competency Breakdown
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {Object.keys(competency_breakdown).length === 0 ? (
              <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>No competency breakdown available.</div>
            ) : (
              Object.entries(competency_breakdown).map(([comp, stats]) => (
                <div key={comp} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                    <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>
                      {comp.replace('_', ' ')} ({stats.question_count} {stats.question_count === 1 ? 'q' : 'qs'})
                    </span>
                    <span style={{ color: getScoreColor(stats.percentage), fontWeight: 600 }}>
                      {stats.awarded}/{stats.max} ({stats.percentage}%)
                    </span>
                  </div>
                  <div style={{ height: '6px', background: 'var(--bg-elevated)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${stats.percentage}%`,
                      background: getScoreColor(stats.percentage),
                      transition: 'width 0.3s ease'
                    }} />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Suggested Next Practice Recommendations */}
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}>
          <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Targeted Learning Insights
          </h3>
          {recommendations.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {recommendations.map((rec, i) => (
                <div key={i} style={{
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  fontSize: '13px',
                  color: 'var(--text-secondary)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '8px'
                }}>
                  <span style={{ color: 'var(--blue)' }}>💡</span>
                  <span>{rec}</span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: '13px', color: 'var(--green)', padding: '12px', background: 'var(--green-dim)', borderRadius: 'var(--radius-md)' }}>
              Outstanding execution! All questions answered with full precision.
            </div>
          )}
        </div>
      </div>

      {/* Detailed Question Review */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px'
      }}>
        <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' }}>
          Detailed Question Explanations & Evidence ({questions.length})
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {questions.map((q, idx) => {
            const awarded = q.awarded_points || 0;
            const isFullCredit = awarded >= 0.99;
            const isExpanded = expandedQId === q.id || idx === 0;

            const selectedAnswers = q.selected_options || [];
            const correctAnswers = q.answer_key || [];

            return (
              <div
                key={q.id || idx}
                style={{
                  background: 'var(--bg-elevated)',
                  border: `1px solid ${isFullCredit ? 'rgba(74, 222, 128, 0.25)' : 'rgba(248, 113, 113, 0.25)'}`,
                  borderRadius: 'var(--radius-md)',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px'
                }}
              >
                <div
                  onClick={() => toggleExpand(q.id)}
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: '50%',
                      background: isFullCredit ? 'var(--green-dim)' : 'var(--red-dim)',
                      color: isFullCredit ? 'var(--green)' : 'var(--red)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '12px',
                      fontWeight: 700
                    }}>
                      {isFullCredit ? '✓' : '✕'}
                    </span>
                    <span style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)' }}>
                      Q{idx + 1}: {q.question_text?.slice(0, 90)}{q.question_text?.length > 90 ? '...' : ''}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '12px', fontWeight: 600, color: isFullCredit ? 'var(--green)' : 'var(--red)' }}>
                      Score: {awarded} / 1.0
                    </span>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      {isExpanded ? '▲' : '▼'}
                    </span>
                  </div>
                </div>

                {isExpanded && (
                  <div style={{
                    marginTop: '8px',
                    borderTop: '1px solid var(--border)',
                    paddingTop: '12px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px'
                  }}>
                    <div style={{ fontSize: '14px', color: 'var(--text-primary)', lineHeight: 1.5 }}>
                      {q.question_text}
                    </div>

                    {/* Options list showing candidate selection and answer key */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {q.options?.map(opt => {
                        const isSelected = selectedAnswers.includes(opt.id);
                        const isCorrectKey = correctAnswers.includes(opt.id);

                        let borderCol = 'var(--border)';
                        let bgCol = 'transparent';
                        if (isCorrectKey) {
                          borderCol = 'var(--green)';
                          bgCol = 'var(--green-dim)';
                        } else if (isSelected && !isCorrectKey) {
                          borderCol = 'var(--red)';
                          bgCol = 'var(--red-dim)';
                        }

                        return (
                          <div
                            key={opt.id}
                            style={{
                              padding: '10px 14px',
                              borderRadius: 'var(--radius-sm)',
                              border: `1px solid ${borderCol}`,
                              background: bgCol,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              fontSize: '13px'
                            }}
                          >
                            <span style={{ color: 'var(--text-primary)' }}>
                              <strong>{opt.id}.</strong> {opt.text}
                            </span>
                            <div style={{ display: 'flex', gap: '6px' }}>
                              {isCorrectKey && (
                                <span style={{ fontSize: '11px', color: 'var(--green)', fontWeight: 600 }}>
                                  [Correct Answer]
                                </span>
                              )}
                              {isSelected && (
                                <span style={{ fontSize: '11px', color: isCorrectKey ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>
                                  [Your Answer]
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Comprehensive Explanation */}
                    {q.explanation && (
                      <div style={{
                        padding: '12px 14px',
                        background: 'rgba(0,0,0,0.3)',
                        borderLeft: '3px solid var(--blue)',
                        borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
                        fontSize: '13px',
                        color: 'var(--text-secondary)',
                        lineHeight: 1.5
                      }}>
                        <strong style={{ color: 'var(--blue)', display: 'block', marginBottom: '4px' }}>Explanation:</strong>
                        {q.explanation}
                      </div>
                    )}

                    {/* Repository Evidence */}
                    {q.evidence_references?.length > 0 && (
                      <div style={{
                        fontSize: '12px',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--blue)',
                        background: 'rgba(0,0,0,0.2)',
                        padding: '8px 12px',
                        borderRadius: 'var(--radius-sm)'
                      }}>
                        <span style={{ fontWeight: 600, display: 'block', marginBottom: '2px' }}>Grounded Code Reference:</span>
                        {q.evidence_references.map((ref, rIdx) => (
                          <div key={rIdx}>
                            📄 {ref.file_path} {ref.entity_name && `• Symbol: ${ref.entity_name}`} {ref.line && `(line ${ref.line})`}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
