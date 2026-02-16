import axios from 'axios';

const API_BASE = 'http://localhost:8000';

export const api = {
  analyzeRepo: (repoUrl) => 
    axios.post(`${API_BASE}/analyze`, { repo_url: repoUrl }),
  
  getStatus: (jobId) => 
    axios.get(`${API_BASE}/status/${jobId}`),
  
  getArchitecture: () => 
    axios.get(`${API_BASE}/architecture`),
  
  getPatterns: () => 
    axios.get(`${API_BASE}/patterns`),
  
  getCoupling: () => 
    axios.get(`${API_BASE}/coupling`),
  
  analyzeImpact: (filePath) => 
    axios.post(`${API_BASE}/impact`, { file_path: filePath }),
  
  getDependencies: (filePath) => 
    axios.get(`${API_BASE}/dependencies/${filePath}`),
  
  getBlastRadius: (filePath) => 
    axios.get(`${API_BASE}/blast-radius/${filePath}`),
  
  debugFiles: () => 
    axios.get(`${API_BASE}/debug/files`),
  
  getGraphData: () => 
    axios.get(`${API_BASE}/graph/data`),
  
  getFunctions: () => 
    axios.get(`${API_BASE}/functions`),
  
  getFunctionInfo: (functionName) => 
    axios.get(`${API_BASE}/function/${functionName}`)
};
