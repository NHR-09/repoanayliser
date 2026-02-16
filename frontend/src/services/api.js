import axios from 'axios';

const API_BASE = 'http://localhost:8000';

export const api = {
  analyzeRepo: (repoUrl) => 
    axios.post(`${API_BASE}/analyze`, { repo_url: repoUrl }),
  
  getStatus: (jobId) => 
    axios.get(`${API_BASE}/status/${jobId}`),
  
  getArchitecture: (repoId) => 
    axios.get(`${API_BASE}/architecture`, { params: repoId ? { repo_id: repoId } : {} }),
  
  getPatterns: (repoId) => 
    axios.get(`${API_BASE}/patterns`, { params: repoId ? { repo_id: repoId } : {} }),
  
  getCoupling: (repoId) => 
    axios.get(`${API_BASE}/coupling`, { params: repoId ? { repo_id: repoId } : {} }),
  
  analyzeImpact: (filePath, changeType = 'modify') => 
    axios.post(`${API_BASE}/impact`, { file_path: filePath, change_type: changeType }),
  
  getDependencies: (filePath) => 
    axios.get(`${API_BASE}/dependencies/${filePath}`),
  
  getBlastRadius: (filePath, changeType = 'modify') => 
    axios.get(`${API_BASE}/blast-radius/${filePath}`, { params: { change_type: changeType } }),
  
  debugFiles: () => 
    axios.get(`${API_BASE}/debug/files`),
  
  getGraphData: () => 
    axios.get(`${API_BASE}/graph/data`),
  
  getFunctions: () => 
    axios.get(`${API_BASE}/functions`),
  
  getFiles: (repoId) => 
    axios.get(`${API_BASE}/files`, { params: repoId ? { repo_id: repoId } : {} }),
  
  getFunctionInfo: (functionName) => 
    axios.get(`${API_BASE}/function/${functionName}`),
  
  getFunctionGraph: () => 
    axios.get(`${API_BASE}/graph/functions`),
  
  getFunctionCallChain: (functionName) => 
    axios.get(`${API_BASE}/graph/function/${functionName}`),
  
  // Version Tracking APIs
  getRepositories: () => 
    axios.get(`${API_BASE}/repositories`),
  
  loadRepository: (repoId) =>
    axios.post(`${API_BASE}/repository/${repoId}/load`),
  
  getRepositoryVersions: (repoId) => 
    axios.get(`${API_BASE}/repository/${repoId}/versions`),
  
  getFileHistory: (repoId, filePath) => 
    axios.get(`${API_BASE}/repository/${repoId}/file-history`, { params: { file_path: filePath } }),
  
  checkFileIntegrity: (repoId, filePath) => 
    axios.post(`${API_BASE}/repository/${repoId}/check-integrity`, null, { params: { file_path: filePath } }),
  
  getContributors: (repoId) => 
    axios.get(`${API_BASE}/repository/${repoId}/contributors`),
  
  importGitHistory: (repoId, maxCommits = 100) => 
    axios.post(`${API_BASE}/repository/${repoId}/import-git-history`, null, { params: { max_commits: maxCommits } }),
  
  deleteRepository: (repoId) => 
    axios.delete(`${API_BASE}/repository/${repoId}`),
  
  getCommits: (repoId) => 
    axios.get(`${API_BASE}/repository/${repoId}/commits`),
  
  compareArchitecture: (repoId, commit1, commit2) => 
    axios.get(`${API_BASE}/repository/${repoId}/compare-architecture/${commit1}/${commit2}`),
  
  // Snapshot APIs
  getSnapshots: (repoId) => 
    axios.get(`${API_BASE}/repository/${repoId}/snapshots`),
  
  deleteSnapshot: (repoId, snapshotId) =>
    axios.delete(`${API_BASE}/repository/${repoId}/snapshot/${snapshotId}`),
  
  compareSnapshots: (repoId, snapshot1, snapshot2) => 
    axios.get(`${API_BASE}/repository/${repoId}/compare-snapshots/${snapshot1}/${snapshot2}`),
  
  getConfidenceReport: (repoId) => 
    axios.get(`${API_BASE}/confidence-report`, { params: repoId ? { repo_id: repoId } : {} })
};

export const getConfidenceReport = async (repoId) => {
  const response = await api.getConfidenceReport(repoId);
  return response.data;
};
