import { authClient } from './auth';

export const hrApi = {
  // 1. Organization Context
  getOrganizations: async () => {
    const res = await authClient.get('/api/hr/organizations');
    return res.data?.organizations || [];
  },

  // 2. Question Bank Listing & Filtering
  getQuestions: async (orgId, params = {}) => {
    const {
      page = 1,
      pageSize = 10,
      search = '',
      competency = '',
      difficulty = '',
      responseFormat = '',
      sourceType = '',
      repositoryId = '',
      validationStatus = '',
      reviewStatus = '',
      sortBy = 'created_at',
      sortDir = 'desc',
    } = params;

    const query = new URLSearchParams();
    if (orgId) query.append('organization_id', orgId);
    if (page) query.append('page', page);
    if (pageSize) query.append('page_size', pageSize);
    if (search) query.append('search', search);
    if (competency) query.append('competency', competency);
    if (difficulty) query.append('difficulty', difficulty);
    if (responseFormat) query.append('response_format', responseFormat);
    if (sourceType) query.append('source_type', sourceType);
    if (repositoryId) query.append('repository_id', repositoryId);
    if (validationStatus) query.append('validation_status', validationStatus);
    if (reviewStatus) query.append('review_status', reviewStatus);
    if (sortBy) query.append('sort_by', sortBy);
    if (sortDir) query.append('sort_dir', sortDir);

    const res = await authClient.get(`/api/hr/questions?${query.toString()}`);
    return res.data;
  },

  // 3. Question Retrieval
  getQuestion: async (orgId, questionId) => {
    const res = await authClient.get(`/api/hr/questions/${questionId}`, {
      params: { organization_id: orgId },
    });
    return res.data?.question;
  },

  // 4. Manual Question Creation
  createQuestion: async (orgId, data) => {
    const res = await authClient.post('/api/hr/questions', data, {
      params: { organization_id: orgId },
    });
    return res.data?.question;
  },

  // 5. Question Updating
  updateQuestion: async (orgId, questionId, data) => {
    const res = await authClient.put(`/api/hr/questions/${questionId}`, data, {
      params: { organization_id: orgId },
    });
    return res.data?.question;
  },

  // 6. Question Lifecycle Transition (APPROVE, REJECT, PUBLISH, ARCHIVE, RESTORE)
  transitionQuestion: async (orgId, questionId, action, reviewerNotes = '') => {
    const res = await authClient.post(
      `/api/hr/questions/${questionId}/transition`,
      {
        action,
        reviewer_notes: reviewerNotes,
      },
      {
        params: { organization_id: orgId },
      }
    );
    return res.data?.question;
  },

  // 7. Question Versions History
  getQuestionVersions: async (orgId, questionId) => {
    const res = await authClient.get(`/api/hr/questions/${questionId}/versions`, {
      params: { organization_id: orgId },
    });
    return res.data?.versions || [];
  },

  // 8. Candidate Mode Preview
  previewQuestion: async (orgId, questionId) => {
    const res = await authClient.get(`/api/hr/questions/${questionId}/preview`, {
      params: { organization_id: orgId },
    });
    return res.data?.preview;
  },

  // 9. AI Question Generation (Mode A: Skill-based, Mode B: Repo-grounded)
  generateQuestions: async (orgId, params) => {
    const res = await authClient.post('/api/hr/questions/generate', params, {
      params: { organization_id: orgId },
    });
    return res.data;
  },

  // 10. Repository Library
  getRepositories: async (orgId, params = {}) => {
    const { page = 1, pageSize = 20, status = '', approvalStatus = '' } = params;
    const query = new URLSearchParams();
    if (orgId) query.append('organization_id', orgId);
    if (page) query.append('page', page);
    if (pageSize) query.append('page_size', pageSize);
    if (status) query.append('status', status);
    if (approvalStatus) query.append('approval_status', approvalStatus);

    const res = await authClient.get(`/api/hr/repositories?${query.toString()}`);
    return res.data;
  },

  // 11. Repository Details
  getRepository: async (orgId, repoId) => {
    const res = await authClient.get(`/api/hr/repositories/${repoId}`, {
      params: { organization_id: orgId },
    });
    return res.data?.repository;
  },

  // 12. Register Repository
  registerRepository: async (orgId, data) => {
    const res = await authClient.post('/api/hr/repositories', data, {
      params: { organization_id: orgId },
    });
    return res.data?.repository;
  },

  // 13. Repository Approval Lifecycle (APPROVE, ARCHIVE, RESTORE)
  transitionRepository: async (orgId, repoId, action) => {
    const res = await authClient.post(
      `/api/hr/repositories/${repoId}/transition`,
      { action },
      { params: { organization_id: orgId } }
    );
    return res.data?.repository;
  },

  // 14. Repository Re-analysis
  reanalyzeRepository: async (orgId, repoId) => {
    const res = await authClient.post(
      `/api/hr/repositories/${repoId}/reanalyze`,
      {},
      { params: { organization_id: orgId } }
    );
    return res.data;
  },

  // 15. Repository Question Coverage
  getRepositoryCoverage: async (orgId, repoId) => {
    const res = await authClient.get(`/api/hr/repositories/${repoId}/coverage`, {
      params: { organization_id: orgId },
    });
    return res.data?.coverage;
  },
};
