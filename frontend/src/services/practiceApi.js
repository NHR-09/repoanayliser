import { authClient } from './auth';

export const practiceApi = {
  // 1. Resume & Skill Extraction
  uploadResume: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await authClient.post('/api/candidate/resume/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  getResume: async () => {
    const res = await authClient.get('/api/candidate/resume');
    return res.data?.resume;
  },

  deleteResume: async () => {
    const res = await authClient.delete('/api/candidate/resume');
    return res.data;
  },

  // 2. Candidate Skills CRUD
  getSkills: async () => {
    const res = await authClient.get('/api/candidate/skills');
    return res.data?.skills || [];
  },

  addSkill: async (skillName, category = 'OTHER', evidenceText = '') => {
    const res = await authClient.post('/api/candidate/skills', {
      skill_name: skillName,
      category,
      evidence_text: evidenceText,
    });
    return res.data?.skill;
  },

  updateSkill: async (skillId, skillName, category, evidenceText) => {
    const res = await authClient.put(`/api/candidate/skills/${skillId}`, {
      skill_name: skillName,
      category,
      evidence_text: evidenceText,
    });
    return res.data?.skill;
  },

  deleteSkill: async (skillId) => {
    const res = await authClient.delete(`/api/candidate/skills/${skillId}`);
    return res.data;
  },

  // 3. GitHub Repositories
  registerRepository: async (repoUrl, displayName = '') => {
    const res = await authClient.post('/api/candidate/repositories', {
      repo_url: repoUrl,
      display_name: displayName,
    });
    return res.data?.repository;
  },

  getRepositories: async () => {
    const res = await authClient.get('/api/candidate/repositories');
    return res.data?.repositories || [];
  },

  getRepositoryStatus: async (repoId) => {
    const res = await authClient.get(`/api/candidate/repositories/${repoId}/status`);
    return res.data;
  },

  triggerReanalysis: async (repoId) => {
    const res = await authClient.post(`/api/candidate/repositories/${repoId}/analyze`);
    return res.data;
  },

  // 4. Skill-to-Code Evidence
  getSkillEvidence: async (repoId = null) => {
    const url = repoId ? `/api/candidate/skills/evidence?repo_id=${repoId}` : '/api/candidate/skills/evidence';
    const res = await authClient.get(url);
    return res.data?.evidence || [];
  },

  // 5. Practice Quizzes & History
  generateQuiz: async ({ mode, skillName, repoId, difficulty, competencies, questionCount }) => {
    const res = await authClient.post('/api/candidate/practice/generate', {
      mode,
      skill_name: skillName,
      repo_id: repoId,
      difficulty,
      competencies,
      question_count: questionCount,
    });
    return res.data;
  },

  getQuiz: async (quizId) => {
    const res = await authClient.get(`/api/candidate/practice/quiz/${quizId}`);
    return res.data?.quiz;
  },

  submitQuiz: async (quizId, answers) => {
    const res = await authClient.post(`/api/candidate/practice/quiz/${quizId}/submit`, {
      answers,
    });
    return res.data?.results;
  },

  getQuizResults: async (quizId) => {
    const res = await authClient.get(`/api/candidate/practice/quiz/${quizId}/results`);
    return res.data?.results;
  },

  getPracticeHistory: async () => {
    const res = await authClient.get('/api/candidate/practice/history');
    return res.data;
  },
};
