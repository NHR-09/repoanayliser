import React, { useState } from 'react';
import { hrApi } from '../../services/hrApi';

const COMPETENCIES = [
  { id: 'CODE_COMPREHENSION', label: 'Code Comprehension' },
  { id: 'DEPENDENCY_TRACING', label: 'Dependency Tracing' },
  { id: 'ARCHITECTURE_REASONING', label: 'Architecture Reasoning' },
  { id: 'DEBUGGING', label: 'Debugging & Diagnostics' },
  { id: 'CHANGE_IMPACT', label: 'Change Impact' },
];

const DIFFICULTIES = ['BEGINNER', 'INTERMEDIATE', 'ADVANCED'];
const FORMATS = ['SINGLE_SELECT', 'MULTI_SELECT', 'TRUE_FALSE'];

export default function QuestionEditorModal({
  orgId,
  existingQuestion = null,
  onClose,
  onSaved,
}) {
  const isEditing = Boolean(existingQuestion);

  const [questionText, setQuestionText] = useState(existingQuestion?.question_text || '');
  const [competency, setCompetency] = useState(existingQuestion?.competency || 'CODE_COMPREHENSION');
  const [difficulty, setDifficulty] = useState(existingQuestion?.difficulty || 'INTERMEDIATE');
  const [responseFormat, setResponseFormat] = useState(existingQuestion?.response_format || 'SINGLE_SELECT');
  const [skillTagsInput, setSkillTagsInput] = useState((existingQuestion?.skill_tags || ['React', 'Architecture']).join(', '));
  const [explanation, setExplanation] = useState(existingQuestion?.explanation || '');

  // Options state
  const [options, setOptions] = useState(
    existingQuestion?.options?.map((o) => ({
      key: o.id || o.key,
      text: o.text || '',
    })) || [
      { key: 'A', text: '' },
      { key: 'B', text: '' },
      { key: 'C', text: '' },
      { key: 'D', text: '' },
    ]
  );

  const [answerKey, setAnswerKey] = useState(existingQuestion?.answer_key || ['A']);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  // Handle format change to auto-adjust options
  const handleFormatChange = (newFormat) => {
    setResponseFormat(newFormat);
    if (newFormat === 'TRUE_FALSE') {
      setOptions([
        { key: 'true', text: 'True' },
        { key: 'false', text: 'False' },
      ]);
      setAnswerKey(['true']);
    } else if (options.length < 3) {
      setOptions([
        { key: 'A', text: '' },
        { key: 'B', text: '' },
        { key: 'C', text: '' },
        { key: 'D', text: '' },
      ]);
      setAnswerKey(['A']);
    }
  };

  const handleOptionTextChange = (idx, text) => {
    const updated = [...options];
    updated[idx].text = text;
    setOptions(updated);
  };

  const handleToggleAnswer = (key) => {
    if (responseFormat === 'MULTI_SELECT') {
      if (answerKey.includes(key)) {
        if (answerKey.length > 1) {
          setAnswerKey(answerKey.filter((k) => k !== key));
        }
      } else {
        setAnswerKey([...answerKey, key]);
      }
    } else {
      // SINGLE_SELECT or TRUE_FALSE
      setAnswerKey([key]);
    }
  };

  const handleAddOption = () => {
    if (options.length >= 6) return;
    const nextKey = String.fromCharCode(65 + options.length);
    setOptions([...options, { key: nextKey, text: '' }]);
  };

  const handleRemoveOption = (idx) => {
    if (options.length <= 2) return;
    const removedKey = options[idx].key;
    const updated = options.filter((_, i) => i !== idx);
    setOptions(updated);
    if (answerKey.includes(removedKey)) {
      setAnswerKey(answerKey.filter((k) => k !== removedKey));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Pre-flight client validations
    if (questionText.trim().length < 15) {
      setError('Question text must be at least 15 characters long.');
      return;
    }
    if (explanation.trim().length < 10) {
      setError('Explanation must be at least 10 characters long.');
      return;
    }

    for (const opt of options) {
      if (!opt.text.trim()) {
        setError(`Option '${opt.key}' text cannot be blank.`);
        return;
      }
    }

    if (responseFormat === 'SINGLE_SELECT' && answerKey.length !== 1) {
      setError('SINGLE_SELECT questions must have exactly one correct answer selected.');
      return;
    }
    if (responseFormat === 'MULTI_SELECT' && answerKey.length < 2) {
      setError('MULTI_SELECT questions must have at least two correct answers selected.');
      return;
    }

    const tags = skillTagsInput
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    const payload = {
      question_text: questionText.trim(),
      competency,
      difficulty,
      response_format: responseFormat,
      skill_tags: tags.length > 0 ? tags : ['General'],
      options: options.map((o) => ({ id: o.key, key: o.key, text: o.text.trim() })),
      answer_key: answerKey,
      explanation: explanation.trim(),
    };

    setSaving(true);
    try {
      if (isEditing) {
        await hrApi.updateQuestion(orgId, existingQuestion.id, payload);
      } else {
        await hrApi.createQuestion(orgId, payload);
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to save question.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        {/* Header */}
        <div style={styles.header}>
          <div>
            <div style={styles.badge}>{isEditing ? 'EDIT QUESTION' : 'AUTHOR TECHNICAL QUESTION'}</div>
            <h3 style={styles.title}>
              {isEditing ? `Editing Question v${existingQuestion.version}` : 'Create Question Bank Entry'}
            </h3>
            {isEditing && (existingQuestion.review_status === 'PUBLISHED' || existingQuestion.review_status === 'APPROVED') && (
              <p style={{ margin: '4px 0 0', color: '#f59e0b', fontSize: '12px' }}>
                ⚠️ Notice: Modifying an approved/published question will bump its version to v{existingQuestion.version + 1} and return it to NEEDS_REVIEW status.
              </p>
            )}
          </div>
          <button style={styles.closeBtn} onClick={onClose}>&times;</button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={styles.body}>
          {error && <div style={styles.errorBox}>{error}</div>}

          {/* Configuration Grid */}
          <div style={styles.gridRow}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Competency</label>
              <select
                value={competency}
                onChange={(e) => setCompetency(e.target.value)}
                style={styles.select}
              >
                {COMPETENCIES.map((c) => (
                  <option key={c.id} value={c.id}>{c.label}</option>
                ))}
              </select>
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>Difficulty</label>
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
              <label style={styles.label}>Response Format</label>
              <select
                value={responseFormat}
                onChange={(e) => handleFormatChange(e.target.value)}
                style={styles.select}
              >
                {FORMATS.map((f) => (
                  <option key={f} value={f}>{f.replace('_', ' ')}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Question Text */}
          <div style={styles.formGroup}>
            <label style={styles.label}>Question Text *</label>
            <textarea
              rows={4}
              value={questionText}
              onChange={(e) => setQuestionText(e.target.value)}
              placeholder="e.g. In a microservices architecture, what is the primary structural benefit of an event-driven pub/sub bus compared to direct REST point-to-point calls?"
              style={styles.textarea}
              required
            />
          </div>

          {/* Skill Tags */}
          <div style={styles.formGroup}>
            <label style={styles.label}>Skill Tags (comma separated)</label>
            <input
              type="text"
              value={skillTagsInput}
              onChange={(e) => setSkillTagsInput(e.target.value)}
              placeholder="e.g. Microservices, PubSub, Architecture, Scalability"
              style={styles.input}
            />
          </div>

          {/* Options & Correct Answer Selector */}
          <div style={styles.formGroup}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <label style={styles.label}>
                Response Options & Answer Key *
                <span style={{ fontWeight: 'normal', color: '#94a3b8', marginLeft: '6px' }}>
                  (Check the radio/checkbox to mark correct answer)
                </span>
              </label>
              {responseFormat !== 'TRUE_FALSE' && options.length < 6 && (
                <button
                  type="button"
                  onClick={handleAddOption}
                  style={styles.addOptionBtn}
                >
                  + Add Option
                </button>
              )}
            </div>

            <div style={styles.optionsList}>
              {options.map((opt, idx) => {
                const isSelected = answerKey.includes(opt.key);
                return (
                  <div
                    key={opt.key}
                    style={{
                      ...styles.optionRow,
                      borderColor: isSelected ? '#10b981' : '#334155',
                      backgroundColor: isSelected ? 'rgba(16, 185, 129, 0.05)' : '#0f172a',
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => handleToggleAnswer(opt.key)}
                      style={{
                        ...styles.answerCheckbox,
                        backgroundColor: isSelected ? '#10b981' : 'transparent',
                        borderColor: isSelected ? '#10b981' : '#64748b',
                        color: isSelected ? '#0f172a' : '#94a3b8',
                      }}
                      title="Toggle correct answer"
                    >
                      {isSelected ? '✓ ' + opt.key : opt.key}
                    </button>
                    <input
                      type="text"
                      value={opt.text}
                      onChange={(e) => handleOptionTextChange(idx, e.target.value)}
                      placeholder={`Enter text for option ${opt.key}...`}
                      style={styles.optionInput}
                      required
                    />
                    {responseFormat !== 'TRUE_FALSE' && options.length > 2 && (
                      <button
                        type="button"
                        onClick={() => handleRemoveOption(idx)}
                        style={styles.removeOptionBtn}
                        title="Remove option"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Explanation */}
          <div style={styles.formGroup}>
            <label style={styles.label}>Explanation & Pedagogical Rationale *</label>
            <textarea
              rows={3}
              value={explanation}
              onChange={(e) => setExplanation(e.target.value)}
              placeholder="Explain why the keyed answer is technically correct and why the distractors are incorrect..."
              style={styles.textarea}
              required
            />
          </div>

          {/* Footer Actions */}
          <div style={styles.footer}>
            <button type="button" onClick={onClose} style={styles.cancelBtn}>
              Cancel
            </button>
            <button type="submit" disabled={saving} style={styles.submitBtn}>
              {saving ? 'Saving...' : isEditing ? 'Save & Submit Changes' : 'Create Question'}
            </button>
          </div>
        </form>
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
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  gridRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: '16px',
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
  input: {
    padding: '10px 14px',
    borderRadius: '6px',
    border: '1px solid #334155',
    backgroundColor: '#1e293b',
    color: '#f8fafc',
    fontSize: '14px',
    outline: 'none',
  },
  textarea: {
    padding: '10px 14px',
    borderRadius: '6px',
    border: '1px solid #334155',
    backgroundColor: '#1e293b',
    color: '#f8fafc',
    fontSize: '14px',
    outline: 'none',
    resize: 'vertical',
    fontFamily: 'inherit',
    lineHeight: '1.5',
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
  optionsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  optionRow: {
    display: 'flex',
    alignItems: 'center',
    padding: '8px 12px',
    borderRadius: '6px',
    border: '1px solid #334155',
    gap: '12px',
  },
  answerCheckbox: {
    padding: '6px 12px',
    borderRadius: '6px',
    border: '1px solid #64748b',
    fontSize: '12px',
    fontWeight: '700',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    flexShrink: 0,
  },
  optionInput: {
    flex: 1,
    background: 'none',
    border: 'none',
    color: '#f8fafc',
    fontSize: '14px',
    outline: 'none',
  },
  addOptionBtn: {
    background: 'none',
    border: '1px solid #38bdf8',
    color: '#38bdf8',
    padding: '3px 10px',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  removeOptionBtn: {
    background: 'none',
    border: 'none',
    color: '#ef4444',
    fontSize: '14px',
    cursor: 'pointer',
    padding: '4px 8px',
  },
  errorBox: {
    padding: '12px 16px',
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid #ef4444',
    color: '#fca5a5',
    borderRadius: '6px',
    fontSize: '13px',
  },
  footer: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    marginTop: '12px',
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
