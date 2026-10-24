import React, { useState, useEffect, useRef } from 'react';
import { practiceApi } from '../../services/practiceApi';

export default function ResumeUploader({ onSkillsUpdated }) {
  const [resume, setResume] = useState(null);
  const [skills, setSkills] = useState([]);
  const [githubUrls, setGithubUrls] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });

  // Add skill form state
  const [newSkillName, setNewSkillName] = useState('');
  const [newSkillCategory, setNewSkillCategory] = useState('FRAMEWORK');
  const [newSkillEvidence, setNewSkillEvidence] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);

  // Edit skill state
  const [editingSkillId, setEditingSkillId] = useState(null);
  const [editName, setEditName] = useState('');
  const [editCategory, setEditCategory] = useState('OTHER');
  const [editEvidence, setEditEvidence] = useState('');

  const fileInputRef = useRef(null);

  const CATEGORIES = ['LANGUAGE', 'FRAMEWORK', 'DATABASE', 'TOOL', 'ARCHITECTURE', 'AI_ML', 'OTHER'];

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [resData, skillsData] = await Promise.all([
        practiceApi.getResume(),
        practiceApi.getSkills()
      ]);
      setResume(resData);
      setSkills(skillsData || []);
      if (onSkillsUpdated) onSkillsUpdated(skillsData || []);
    } catch (err) {
      console.error('Failed to load resume or skills:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (file) => {
    if (!file) return;

    const validExtensions = ['.pdf', '.docx', '.txt'];
    const fileName = file.name.toLowerCase();
    const hasValidExt = validExtensions.some(ext => fileName.endsWith(ext));
    if (!hasValidExt) {
      setMessage({ text: 'Unsupported file format. Please upload PDF, DOCX, or TXT.', type: 'error' });
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setMessage({ text: 'File exceeds 10 MB size limit.', type: 'error' });
      return;
    }

    setUploading(true);
    setMessage({ text: 'Uploading document and extracting technical skills via AI...', type: 'info' });

    try {
      const res = await practiceApi.uploadResume(file);
      setResume(res.resume);
      setSkills(res.extracted_skills || []);
      setGithubUrls(res.github_urls || []);
      setProjects(res.projects || []);
      setMessage({ text: `Successfully parsed resume! Extracted ${res.extracted_skills?.length || 0} technical skills.`, type: 'success' });
      if (onSkillsUpdated) onSkillsUpdated(res.extracted_skills || []);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || 'Upload failed.';
      setMessage({ text: `Upload Error: ${detail}`, type: 'error' });
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteResume = async () => {
    if (!window.confirm('Are you sure you want to remove your uploaded resume? Your reviewed skills will remain.')) return;
    try {
      await practiceApi.deleteResume();
      setResume(null);
      setMessage({ text: 'Resume document removed successfully.', type: 'success' });
    } catch (err) {
      setMessage({ text: 'Failed to delete resume.', type: 'error' });
    }
  };

  const handleAddManualSkill = async (e) => {
    e.preventDefault();
    if (!newSkillName.trim()) return;

    try {
      const added = await practiceApi.addSkill(newSkillName.trim(), newSkillCategory, newSkillEvidence.trim());
      const updated = [...skills, added];
      setSkills(updated);
      setNewSkillName('');
      setNewSkillEvidence('');
      setShowAddForm(false);
      setMessage({ text: `Added skill "${added.skill_name}".`, type: 'success' });
      if (onSkillsUpdated) onSkillsUpdated(updated);
    } catch (err) {
      setMessage({ text: err.response?.data?.detail || 'Failed to add skill.', type: 'error' });
    }
  };

  const handleStartEdit = (skill) => {
    setEditingSkillId(skill.id);
    setEditName(skill.skill_name);
    setEditCategory(skill.category);
    setEditEvidence(skill.evidence_text || '');
  };

  const handleSaveEdit = async (skillId) => {
    try {
      const updated = await practiceApi.updateSkill(skillId, editName, editCategory, editEvidence);
      const nextSkills = skills.map(s => s.id === skillId ? updated : s);
      setSkills(nextSkills);
      setEditingSkillId(null);
      setMessage({ text: `Updated skill "${updated.skill_name}".`, type: 'success' });
      if (onSkillsUpdated) onSkillsUpdated(nextSkills);
    } catch (err) {
      setMessage({ text: 'Failed to update skill.', type: 'error' });
    }
  };

  const handleDeleteSkill = async (skillId, skillName) => {
    if (!window.confirm(`Remove skill "${skillName}" from your profile?`)) return;
    try {
      await practiceApi.deleteSkill(skillId);
      const nextSkills = skills.filter(s => s.id !== skillId);
      setSkills(nextSkills);
      setMessage({ text: `Removed "${skillName}".`, type: 'success' });
      if (onSkillsUpdated) onSkillsUpdated(nextSkills);
    } catch (err) {
      setMessage({ text: 'Failed to delete skill.', type: 'error' });
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Alert Messages */}
      {message.text && (
        <div style={{
          padding: '12px 16px',
          borderRadius: 'var(--radius-md)',
          background: message.type === 'error' ? 'var(--red-dim)' : message.type === 'success' ? 'var(--green-dim)' : 'var(--blue-dim)',
          color: message.type === 'error' ? 'var(--red)' : message.type === 'success' ? 'var(--green)' : 'var(--blue)',
          border: `1px solid ${message.type === 'error' ? 'var(--red)' : message.type === 'success' ? 'var(--green)' : 'var(--blue)'}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>{message.text}</span>
          <button
            onClick={() => setMessage({ text: '', type: '' })}
            style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '14px' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Upload Zone */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '24px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' }}>Resume & Document Ingestion</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Upload your resume in PDF, DOCX, or TXT format (max 10 MB). Our AI extracts your verified skill claims.
            </p>
          </div>
          {resume && (
            <button
              onClick={handleDeleteResume}
              style={{
                padding: '6px 12px',
                background: 'transparent',
                border: '1px solid var(--border)',
                color: 'var(--red)',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                fontSize: '12px'
              }}
            >
              Remove Document
            </button>
          )}
        </div>

        {/* Drag & Drop Area */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            if (e.dataTransfer.files?.[0]) handleFileUpload(e.dataTransfer.files[0]);
          }}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${dragOver ? 'var(--blue)' : 'var(--border)'}`,
            borderRadius: 'var(--radius-md)',
            padding: '32px 20px',
            textAlign: 'center',
            cursor: uploading ? 'not-allowed' : 'pointer',
            background: dragOver ? 'var(--blue-dim)' : 'var(--bg-elevated)',
            transition: 'all 0.2s ease'
          }}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => {
              if (e.target.files?.[0]) handleFileUpload(e.target.files[0]);
            }}
            accept=".pdf,.docx,.txt"
            style={{ display: 'none' }}
          />

          <div style={{ fontSize: '28px', marginBottom: '8px' }}>📄</div>
          <div style={{ fontWeight: 500, fontSize: '14px', color: 'var(--text-primary)' }}>
            {uploading ? 'Processing & Extracting Skills...' : resume ? 'Click or drag a file to replace current resume' : 'Click or drag your resume here to begin'}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Supported: PDF (text-based), DOCX, TXT • Secure storage outside static root
          </div>
        </div>

        {/* Existing Resume Metadata */}
        {resume && (
          <div style={{
            marginTop: '16px',
            padding: '12px 16px',
            background: 'var(--bg-elevated)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '13px' }}>
                📁 {resume.filename} ({formatFileSize(resume.file_size)})
              </span>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Uploaded: {new Date(resume.created_at).toLocaleDateString()}
              </span>
            </div>
            {resume.text_preview && (
              <div style={{
                fontSize: '12px',
                color: 'var(--text-secondary)',
                fontStyle: 'italic',
                background: 'rgba(0,0,0,0.2)',
                padding: '8px 12px',
                borderRadius: 'var(--radius-sm)'
              }}>
                "{resume.text_preview}"
              </div>
            )}
          </div>
        )}

        {/* Extracted GitHub Links & Projects */}
        {(githubUrls.length > 0 || projects.length > 0) && (
          <div style={{ marginTop: '16px', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
            {githubUrls.length > 0 && (
              <div style={{ flex: 1, minWidth: '240px', background: 'var(--bg-elevated)', padding: '12px', borderRadius: 'var(--radius-md)' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>Detected GitHub Profiles:</span>
                <ul style={{ listStyle: 'none', padding: 0, marginTop: '6px' }}>
                  {githubUrls.map((u, i) => (
                    <li key={i} style={{ fontSize: '12px', color: 'var(--blue)' }}>🔗 {u}</li>
                  ))}
                </ul>
              </div>
            )}
            {projects.length > 0 && (
              <div style={{ flex: 1, minWidth: '240px', background: 'var(--bg-elevated)', padding: '12px', borderRadius: 'var(--radius-md)' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>Detected Projects:</span>
                <ul style={{ listStyle: 'none', padding: 0, marginTop: '6px' }}>
                  {projects.map((p, i) => (
                    <li key={i} style={{ fontSize: '12px', color: 'var(--text-primary)' }}>
                      <strong>{p.name}</strong>: {p.technologies?.join(', ')}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Editable Reviewed Skills Section */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '24px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' }}>
              Reviewed Skills ({skills.length})
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Confirm, edit, or augment your technical skills. Provenance is preserved (<span style={{ color: 'var(--blue)' }}>RESUME</span> vs <span style={{ color: 'var(--amber)' }}>MANUAL</span>).
            </p>
          </div>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            style={{
              padding: '6px 14px',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-hover)',
              color: 'var(--text-primary)',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 500
            }}
          >
            {showAddForm ? '✕ Cancel' : '+ Add Skill'}
          </button>
        </div>

        {/* Add Skill Form */}
        {showAddForm && (
          <form onSubmit={handleAddManualSkill} style={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-hover)',
            borderRadius: 'var(--radius-md)',
            padding: '16px',
            marginBottom: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
          }}>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <div style={{ flex: 2, minWidth: '180px' }}>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Skill Name</label>
                <input
                  type="text"
                  placeholder="e.g. Docker, TypeScript, Microservices"
                  value={newSkillName}
                  onChange={(e) => setNewSkillName(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border)',
                    background: 'var(--bg-input)',
                    color: 'var(--text-primary)',
                    fontSize: '13px'
                  }}
                />
              </div>
              <div style={{ flex: 1, minWidth: '140px' }}>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Category</label>
                <select
                  value={newSkillCategory}
                  onChange={(e) => setNewSkillCategory(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border)',
                    background: 'var(--bg-input)',
                    color: 'var(--text-primary)',
                    fontSize: '13px'
                  }}
                >
                  {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Supporting Evidence / Notes</label>
              <input
                type="text"
                placeholder="Optional description of usage or project context"
                value={newSkillEvidence}
                onChange={(e) => setNewSkillEvidence(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border)',
                  background: 'var(--bg-input)',
                  color: 'var(--text-primary)',
                  fontSize: '13px'
                }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                style={{
                  padding: '6px 14px',
                  background: 'transparent',
                  border: '1px solid var(--border)',
                  color: 'var(--text-muted)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12px',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                style={{
                  padding: '6px 16px',
                  background: 'var(--green)',
                  border: 'none',
                  color: '#000',
                  fontWeight: 600,
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12px',
                  cursor: 'pointer'
                }}
              >
                Save Skill
              </button>
            </div>
          </form>
        )}

        {/* Skills Grid */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>Loading skills...</div>
        ) : skills.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
            No skills recorded yet. Upload a resume above or add your skills manually.
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '12px'
          }}>
            {skills.map(s => {
              const isEditing = editingSkillId === s.id;
              return (
                <div key={s.id} style={{
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)',
                  padding: '12px 14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                  position: 'relative'
                }}>
                  {isEditing ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        style={{ padding: '6px', background: 'var(--bg-input)', border: '1px solid var(--border)', color: '#fff', fontSize: '13px' }}
                      />
                      <select
                        value={editCategory}
                        onChange={(e) => setEditCategory(e.target.value)}
                        style={{ padding: '6px', background: 'var(--bg-input)', border: '1px solid var(--border)', color: '#fff', fontSize: '12px' }}
                      >
                        {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                      </select>
                      <input
                        type="text"
                        value={editEvidence}
                        placeholder="Evidence text"
                        onChange={(e) => setEditEvidence(e.target.value)}
                        style={{ padding: '6px', background: 'var(--bg-input)', border: '1px solid var(--border)', color: '#fff', fontSize: '12px' }}
                      />
                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                        <button
                          onClick={() => setEditingSkillId(null)}
                          style={{ padding: '4px 8px', background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-muted)', fontSize: '11px', cursor: 'pointer' }}
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => handleSaveEdit(s.id)}
                          style={{ padding: '4px 10px', background: 'var(--blue)', border: 'none', color: '#fff', fontSize: '11px', cursor: 'pointer', borderRadius: 'var(--radius-sm)' }}
                        >
                          Save
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '14px' }}>
                          {s.skill_name}
                        </span>
                        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                          <span style={{
                            fontSize: '10px',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            background: s.source === 'RESUME' ? 'var(--blue-dim)' : 'var(--amber-dim)',
                            color: s.source === 'RESUME' ? 'var(--blue)' : 'var(--amber)',
                            fontWeight: 600
                          }}>
                            {s.source}
                          </span>
                          <span style={{
                            fontSize: '10px',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            background: 'rgba(255,255,255,0.06)',
                            color: 'var(--text-muted)'
                          }}>
                            {s.category}
                          </span>
                        </div>
                      </div>

                      {s.evidence_text && (
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                          {s.evidence_text}
                        </div>
                      )}

                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: 'auto', paddingTop: '6px' }}>
                        <button
                          onClick={() => handleStartEdit(s)}
                          style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '11px' }}
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteSkill(s.id, s.skill_name)}
                          style={{ background: 'none', border: 'none', color: 'var(--red)', cursor: 'pointer', fontSize: '11px' }}
                        >
                          Delete
                        </button>
                      </div>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
