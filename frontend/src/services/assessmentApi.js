import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

// Create axios instance with credentials support
const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const assessmentApi = {
  // -------------------------------------------------------------
  // HR Assessment Endpoints
  // -------------------------------------------------------------
  getAssessments: async (orgId, params = {}) => {
    const res = await api.get('/hr/assessments', {
      params: { organization_id: orgId, ...params },
    });
    return res.data;
  },

  getAssessment: async (orgId, assessmentId) => {
    const res = await api.get(`/hr/assessments/${assessmentId}`, {
      params: { organization_id: orgId },
    });
    return res.data.assessment;
  },

  createAssessment: async (orgId, data) => {
    const res = await api.post('/hr/assessments', data, {
      params: { organization_id: orgId },
    });
    return res.data.assessment;
  },

  updateAssessment: async (orgId, assessmentId, data) => {
    const res = await api.put(`/hr/assessments/${assessmentId}`, data, {
      params: { organization_id: orgId },
    });
    return res.data.assessment;
  },

  publishAssessment: async (orgId, assessmentId) => {
    const res = await api.post(`/hr/assessments/${assessmentId}/publish`, {}, {
      params: { organization_id: orgId },
    });
    return res.data;
  },

  archiveAssessment: async (orgId, assessmentId) => {
    const res = await api.post(`/hr/assessments/${assessmentId}/archive`, {}, {
      params: { organization_id: orgId },
    });
    return res.data;
  },

  getAssignments: async (orgId, assessmentId) => {
    const res = await api.get(`/hr/assessments/${assessmentId}/assignments`, {
      params: { organization_id: orgId },
    });
    return res.data.assignments;
  },

  assignAssessment: async (orgId, assessmentId, data) => {
    const res = await api.post(`/hr/assessments/${assessmentId}/assign`, data, {
      params: { organization_id: orgId },
    });
    return res.data;
  },

  revokeAssignment: async (orgId, assignmentId, reason = 'Revoked by recruiter') => {
    const res = await api.post(
      `/hr/assessments/assignments/${assignmentId}/revoke`,
      { reason },
      { params: { organization_id: orgId } }
    );
    return res.data;
  },

  getAttempts: async (orgId, assessmentId) => {
    const res = await api.get(`/hr/assessments/${assessmentId}/attempts`, {
      params: { organization_id: orgId },
    });
    return res.data.attempts;
  },

  getScorecard: async (orgId, attemptId) => {
    const res = await api.get(`/hr/assessments/attempts/${attemptId}/scorecard`, {
      params: { organization_id: orgId },
    });
    return res.data.scorecard;
  },

  manualScoreOverride: async (orgId, attemptId, newScore, reason) => {
    const res = await api.post(
      `/hr/assessments/attempts/${attemptId}/override`,
      { new_score: newScore, reason },
      { params: { organization_id: orgId } }
    );
    return res.data.scorecard;
  },

  releaseResult: async (orgId, attemptId) => {
    const res = await api.post(`/hr/assessments/attempts/${attemptId}/release`, {}, {
      params: { organization_id: orgId },
    });
    return res.data;
  },

  exportResultsCsvUrl: (orgId, assessmentId) => {
    return `${API_BASE}/hr/assessments/${assessmentId}/export?organization_id=${orgId}`;
  },

  // -------------------------------------------------------------
  // Candidate Assessment Endpoints
  // -------------------------------------------------------------
  getCandidateAssigned: async () => {
    const res = await api.get('/candidate/assessments/assigned');
    return res.data.assigned;
  },

  claimInvitation: async (token) => {
    const res = await api.post('/candidate/assessments/claim', { token });
    return res.data;
  },

  startAttempt: async (assignmentId) => {
    const res = await api.post('/candidate/assessments/start', { assignment_id: assignmentId });
    return res.data.attempt;
  },

  getActiveAttempt: async (attemptId) => {
    const res = await api.get(`/candidate/assessments/attempts/${attemptId}`);
    return res.data.attempt;
  },

  autosaveAnswer: async (attemptId, questionId, candidateResponse) => {
    const res = await api.post(`/candidate/assessments/attempts/${attemptId}/answers`, {
      question_id: questionId,
      candidate_response: candidateResponse,
    });
    return res.data;
  },

  submitAttempt: async (attemptId) => {
    const res = await api.post(`/candidate/assessments/attempts/${attemptId}/submit`);
    return res.data.result;
  },

  getAttemptResult: async (attemptId) => {
    const res = await api.get(`/candidate/assessments/attempts/${attemptId}/result`);
    return res.data.result;
  },

  getAttemptCodebaseFiles: async (attemptId) => {
    const res = await api.get(`/candidate/assessments/attempts/${attemptId}/codebase/files`);
    return res.data;
  },

  getAttemptCodebaseFileContent: async (attemptId, path) => {
    const res = await api.get(`/candidate/assessments/attempts/${attemptId}/codebase/file-content`, {
      params: { path },
    });
    return res.data;
  },
};
