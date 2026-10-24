import React, { useState, useEffect } from 'react';
import { practiceApi } from '../../services/practiceApi';

export default function SkillEvidenceViewer({ repoId, repoName }) {
  const [evidenceList, setEvidenceList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);

  useEffect(() => {
    if (repoId) {
      loadEvidence();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repoId]);

  const loadEvidence = async () => {
    setLoading(true);
    try {
      const data = await practiceApi.getSkillEvidence(repoId);
      setEvidenceList(data || []);
    } catch (err) {
      console.error('Failed to load skill evidence:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleReevaluate = async () => {
    setEvaluating(true);
    try {
      const data = await practiceApi.getSkillEvidence(repoId);
      setEvidenceList(data || []);
    } catch (err) {
      console.error('Failed to re-evaluate evidence:', err);
    } finally {
      setEvaluating(false);
    }
  };

  if (!repoId) {
    return (
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '32px',
        textAlign: 'center',
        color: 'var(--text-muted)'
      }}>
        Connect and select an analyzed repository above to map skill claims to actual code AST evidence.
      </div>
    );
  }

  const verifiedCount = evidenceList.filter(e => e.evidence_status === 'CODE_EVIDENCE_FOUND').length;
  const claimedCount = evidenceList.length;

  const getStatusBadge = (status) => {
    if (status === 'CODE_EVIDENCE_FOUND') {
      return (
        <span style={{
          background: 'var(--green-dim)',
          color: 'var(--green)',
          padding: '2px 8px',
          borderRadius: '4px',
          fontSize: '11px',
          fontWeight: 600
        }}>
          ✓ CODE VERIFIED
        </span>
      );
    } else if (status === 'ASSESSMENT_EVIDENCE_FOUND') {
      return (
        <span style={{
          background: 'var(--blue-dim)',
          color: 'var(--blue)',
          padding: '2px 8px',
          borderRadius: '4px',
          fontSize: '11px',
          fontWeight: 600
        }}>
          ★ ASSESSMENT VERIFIED
        </span>
      );
    } else {
      return (
        <span style={{
          background: 'var(--amber-dim)',
          color: 'var(--amber)',
          padding: '2px 8px',
          borderRadius: '4px',
          fontSize: '11px',
          fontWeight: 600
        }}>
          CLAIMED ONLY
        </span>
      );
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
      gap: '16px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Skill-to-Code Evidence Mapping
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Active Repository: <strong style={{ color: 'var(--text-primary)' }}>{repoName || 'Connected Repository'}</strong> • Grounded in AST symbols, imports, and architectural patterns.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <div style={{
            padding: '6px 12px',
            background: 'var(--bg-elevated)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '12px',
            color: 'var(--text-secondary)'
          }}>
            Code Grounding: <strong style={{ color: 'var(--green)' }}>{verifiedCount}</strong> / {claimedCount} skills
          </div>
          <button
            onClick={handleReevaluate}
            disabled={evaluating}
            style={{
              padding: '6px 12px',
              background: 'transparent',
              border: '1px solid var(--border-hover)',
              color: 'var(--text-secondary)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '12px',
              cursor: evaluating ? 'not-allowed' : 'pointer'
            }}
          >
            {evaluating ? 'Analyzing AST...' : '↻ Re-evaluate'}
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
          Evaluating repository code graph for claimed skills...
        </div>
      ) : evidenceList.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
          No skills found to evaluate. Add skills in the Resume & Skills tab first.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {evidenceList.map((item, idx) => (
            <div
              key={idx}
              style={{
                background: 'var(--bg-elevated)',
                border: `1px solid ${item.evidence_status === 'CODE_EVIDENCE_FOUND' ? 'rgba(74, 222, 128, 0.2)' : 'var(--border)'}`,
                borderRadius: 'var(--radius-md)',
                padding: '14px 16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)' }}>
                  {item.skill_name}
                </span>
                {getStatusBadge(item.evidence_status)}
              </div>

              <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                {item.evidence_description}
              </div>

              {item.file_path && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--blue)',
                  background: 'rgba(0,0,0,0.2)',
                  padding: '4px 8px',
                  borderRadius: 'var(--radius-sm)',
                  marginTop: '4px'
                }}>
                  <span>📄 {item.file_path}</span>
                  {item.entity_name && <span>• Symbol: {item.entity_name}</span>}
                  {item.line_number && <span>• Line: {item.line_number}</span>}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
