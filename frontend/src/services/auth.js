import axios from 'axios';

const API_BASE = 'http://localhost:8000';

// Configure Axios client with credentials for HttpOnly cookie sessions
export const authClient = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
});

// Helper to extract cookie by name
export function getCookie(name) {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(new RegExp('(^|;\\s*)' + name + '=([^;]*)'));
  return match ? decodeURIComponent(match[2]) : null;
}

// Request interceptor to attach CSRF token and Bearer token fallback
authClient.interceptors.request.use((config) => {
  // Attach CSRF token on state-mutating requests
  const method = (config.method || '').toUpperCase();
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
    const csrfToken = getCookie('architech_csrf');
    if (csrfToken) {
      config.headers['X-CSRF-Token'] = csrfToken;
    }
  }

  // Attach token from localStorage if available (fallback for cross-origin setups)
  const token = localStorage.getItem('architech_token');
  if (token && !config.headers['Authorization']) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }

  return config;
});

export const authService = {
  // Public candidate registration (strictly assigns USER role)
  registerUser: async ({ email, password, fullName }) => {
    const res = await authClient.post('/api/auth/register', {
      email,
      password,
      full_name: fullName,
    });
    if (res.data?.token) {
      localStorage.setItem('architech_token', res.data.token);
    }
    if (res.data?.user) {
      localStorage.setItem('architech_user', JSON.stringify(res.data.user));
    }
    return res.data;
  },

  // HR registration (requires valid invitation code)
  registerHr: async ({ email, password, fullName, invitationCode }) => {
    const res = await authClient.post('/api/auth/register-hr', {
      email,
      password,
      full_name: fullName,
      invitation_code: invitationCode,
    });
    if (res.data?.token) {
      localStorage.setItem('architech_token', res.data.token);
    }
    if (res.data?.user) {
      localStorage.setItem('architech_user', JSON.stringify(res.data.user));
    }
    return res.data;
  },

  // One-time administrative provisioning
  provisionInitialAdmin: async ({ email, password, fullName, organizationName }) => {
    const res = await authClient.post('/api/auth/provision-initial-admin', {
      email,
      password,
      full_name: fullName,
      organization_name: organizationName,
    });
    if (res.data?.token) {
      localStorage.setItem('architech_token', res.data.token);
    }
    if (res.data?.user) {
      localStorage.setItem('architech_user', JSON.stringify(res.data.user));
    }
    return res.data;
  },

  // User login
  login: async ({ email, password }) => {
    const res = await authClient.post('/api/auth/login', {
      email,
      password,
    });
    if (res.data?.token) {
      localStorage.setItem('architech_token', res.data.token);
    }
    if (res.data?.user) {
      localStorage.setItem('architech_user', JSON.stringify(res.data.user));
    }
    return res.data;
  },

  // User logout
  logout: async () => {
    try {
      await authClient.post('/api/auth/logout');
    } catch (e) {
      // Ignore network errors during logout
    }
    localStorage.removeItem('architech_token');
    localStorage.removeItem('architech_user');
  },

  // Retrieve current authenticated user profile
  getMe: async () => {
    const res = await authClient.get('/api/auth/me');
    if (res.data?.user) {
      localStorage.setItem('architech_user', JSON.stringify(res.data.user));
    }
    return res.data?.user;
  },

  // Test candidate access
  testUserEndpoint: async () => {
    const res = await authClient.get('/api/auth/test/user-only');
    return res.data;
  },

  // Test HR access
  testHrEndpoint: async () => {
    const res = await authClient.get('/api/auth/test/hr-only');
    return res.data;
  },

  // Local storage helpers
  getCachedUser: () => {
    try {
      const stored = localStorage.getItem('architech_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  },
};
