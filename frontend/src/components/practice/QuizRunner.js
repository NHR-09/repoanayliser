import React, { useState } from 'react';
import { practiceApi } from '../../services/practiceApi';

export default function QuizRunner({ quiz, onQuizCompleted, onCancel }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({}); // { [qId]: ["A", "C"] }
  const [showEvidence, setShowEvidence] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const questions = quiz.questions || [];
  const currentQ = questions[currentIndex] || {};
  const totalCount = questions.length;

  const currentSelected = answers[currentQ.id] || [];

  const handleSelectOption = (optId) => {
    const fmt = currentQ.response_format;
    if (fmt === 'SINGLE_SELECT' || fmt === 'TRUE_FALSE') {
      setAnswers({
        ...answers,
        [currentQ.id]: [optId],
      });
    } else if (fmt === 'MULTI_SELECT') {
      const exists = currentSelected.includes(optId);
      const next = exists
        ? currentSelected.filter(id => id !== optId)
        : [...currentSelected, optId];
      setAnswers({
        ...answers,
        [currentQ.id]: next,
      });
    }
  };

  const handleNext = () => {
    if (currentIndex < totalCount - 1) {
      setCurrentIndex(currentIndex + 1);
      setShowEvidence(false);
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setShowEvidence(false);
    }
  };

  const handleSubmit = async () => {
    const answeredCount = Object.keys(answers).filter(k => answers[k]?.length > 0).length;
    if (answeredCount < totalCount) {
      const confirmSubmit = window.confirm(
        `You have answered ${answeredCount} of ${totalCount} questions. Submit anyway?`
      );
      if (!confirmSubmit) return;
    }

    setSubmitting(true);
    setError('');

    try {
      const results = await practiceApi.submitQuiz(quiz.quiz_id, answers);
      if (onQuizCompleted) {
        onQuizCompleted(results);
      }
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || 'Submission failed.';
      setError(`Error submitting answers: ${detail}`);
    } finally {
      setSubmitting(false);
    }
  };

  const progressPct = totalCount > 0 ? ((currentIndex + 1) / totalCount) * 100 : 0;
  const answeredTotal = Object.keys(answers).filter(k => answers[k]?.length > 0).length;

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      padding: '28px',
      display: 'flex',
      flexDirection: 'column',
      gap: '24px'
    }}>
      {/* Top Header & Progress */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>
              QUESTION {currentIndex + 1} OF {totalCount}
            </span>
            <span style={{
              fontSize: '11px',
              padding: '2px 8px',
              borderRadius: '4px',
              background: 'var(--bg-elevated)',
              color: 'var(--text-muted)'
            }}>
              {currentQ.competency?.replace('_', ' ')}
            </span>
            <span style={{
              fontSize: '11px',
              padding: '2px 8px',
              borderRadius: '4px',
              background: 'var(--bg-elevated)',
              color: 'var(--text-muted)'
            }}>
              {currentQ.difficulty}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Answered: {answeredTotal}/{totalCount}
            </span>
            {onCancel && (
              <button
                onClick={onCancel}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-dim)',
                  cursor: 'pointer',
                  fontSize: '12px'
                }}
              >
                Exit Practice
              </button>
            )}
          </div>
        </div>

        {/* Progress Bar */}
        <div style={{
          height: '4px',
          background: 'var(--bg-elevated)',
          borderRadius: '2px',
          overflow: 'hidden'
        }}>
          <div style={{
            height: '100%',
            width: `${progressPct}%`,
            background: 'var(--accent)',
            transition: 'width 0.2s ease'
          }} />
        </div>
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

      {/* Question Content */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <h2 style={{
          fontSize: '16px',
          fontWeight: 600,
          color: 'var(--text-primary)',
          lineHeight: 1.5,
          whiteSpace: 'pre-line'
        }}>
          {currentQ.question_text}
        </h2>

        {/* Format hint */}
        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          {currentQ.response_format === 'MULTI_SELECT'
            ? '☑ Multiple Choice: Select all options that apply.'
            : currentQ.response_format === 'TRUE_FALSE'
            ? '◉ True / False'
            : '◉ Single Choice: Select one answer.'}
        </div>

        {/* Repository Evidence Link / Preview (Does NOT reveal answer) */}
        {currentQ.evidence_references?.length > 0 && (
          <div style={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            padding: '10px 14px'
          }}>
            <button
              onClick={() => setShowEvidence(!showEvidence)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--blue)',
                fontSize: '12px',
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: 0
              }}
            >
              <span>{showEvidence ? '▼' : '▶'}</span>
              <span>Inspect Repository Code Provenance ({currentQ.evidence_references.length} reference)</span>
            </button>

            {showEvidence && (
              <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {currentQ.evidence_references.map((ref, i) => (
                  <div key={i} style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                    📄 {ref.file_path} {ref.entity_name && `• Symbol: ${ref.entity_name}`} {ref.line && `(line ${ref.line})`}
                  </div>
                ))}
                <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontStyle: 'italic', marginTop: '4px' }}>
                  This question is strictly grounded in the analyzed symbols from your repository.
                </div>
              </div>
            )}
          </div>
        )}

        {/* Options List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '8px' }}>
          {currentQ.options?.map(opt => {
            const isSelected = currentSelected.includes(opt.id);
            const isMulti = currentQ.response_format === 'MULTI_SELECT';

            return (
              <div
                key={opt.id}
                onClick={() => handleSelectOption(opt.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '14px 16px',
                  borderRadius: 'var(--radius-md)',
                  border: `1px solid ${isSelected ? 'var(--blue)' : 'var(--border)'}`,
                  background: isSelected ? 'rgba(96, 165, 250, 0.08)' : 'var(--bg-elevated)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: isMulti ? '4px' : '50%',
                  border: `2px solid ${isSelected ? 'var(--blue)' : 'var(--border-hover)'}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: isSelected ? 'var(--blue)' : 'transparent',
                  color: isSelected ? '#fff' : 'var(--text-muted)',
                  fontSize: '11px',
                  fontWeight: 600,
                  flexShrink: 0
                }}>
                  {isSelected ? (isMulti ? '✓' : opt.id) : opt.id}
                </div>

                <div style={{ fontSize: '14px', color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)', lineHeight: 1.4 }}>
                  {opt.text}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Navigation & Submission Controls */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderTop: '1px solid var(--border)',
        paddingTop: '20px',
        marginTop: '8px'
      }}>
        <button
          onClick={handlePrev}
          disabled={currentIndex === 0}
          style={{
            padding: '8px 16px',
            background: 'transparent',
            border: '1px solid var(--border)',
            color: currentIndex === 0 ? 'var(--text-dim)' : 'var(--text-secondary)',
            borderRadius: 'var(--radius-sm)',
            cursor: currentIndex === 0 ? 'not-allowed' : 'pointer',
            fontSize: '13px'
          }}
        >
          ← Previous
        </button>

        <div style={{ display: 'flex', gap: '10px' }}>
          {currentIndex < totalCount - 1 ? (
            <button
              onClick={handleNext}
              style={{
                padding: '8px 20px',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-hover)',
                color: 'var(--text-primary)',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: 500
              }}
            >
              Next →
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={submitting}
              style={{
                padding: '8px 24px',
                background: submitting ? 'var(--border)' : 'var(--green)',
                color: '#09090b',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                cursor: submitting ? 'not-allowed' : 'pointer',
                fontSize: '13px',
                fontWeight: 600
              }}
            >
              {submitting ? 'Submitting Answers...' : 'Submit Quiz & View Results'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
