import React, { useState } from 'react';
import { authService } from '../../services/auth';

function AuthModal({ isOpen, onClose, onAuthSuccess }) {
  const [mode, setMode] = useState('login'); // 'login' | 'register_user' | 'register_hr' | 'initial_admin'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [invitationCode, setInvitationCode] = useState('');
  const [orgName, setOrgName] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState(null);

  if (!isOpen) return null;

  const resetForm = () => {
    setEmail('');
    setPassword('');
    setFullName('');
    setInvitationCode('');
    setOrgName('');
    setError(null);
    setSuccessMsg(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleModeChange = (newMode) => {
    setMode(newMode);
    setError(null);
    setSuccessMsg(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      if (mode === 'login') {
        const data = await authService.login({ email, password });
        onAuthSuccess(data.user);
        onClose();
      } else if (mode === 'register_user') {
        const data = await authService.registerUser({
          email,
          password,
          fullName,
        });
        onAuthSuccess(data.user);
        onClose();
      } else if (mode === 'register_hr') {
        const data = await authService.registerHr({
          email,
          password,
          fullName,
          invitationCode,
        });
        onAuthSuccess(data.user);
        onClose();
      } else if (mode === 'initial_admin') {
        const data = await authService.provisionInitialAdmin({
          email,
          password,
          fullName,
          organizationName: orgName,
        });
        setSuccessMsg('Initial Admin provisioned successfully! Logging in...');
        setTimeout(() => {
          onAuthSuccess(data.user);
          onClose();
        }, 1200);
      }
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        'Authentication failed. Please check your credentials.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        {/* Header */}
        <div style={styles.header}>
          <div>
            <h2 style={styles.title}>
              {mode === 'login' && 'Sign In to ARCHITECH'}
              {mode === 'register_user' && 'Create Candidate Account'}
              {mode === 'register_hr' && 'HR Recruiter Sign Up'}
              {mode === 'initial_admin' && 'Initial Admin Provisioning'}
            </h2>
            <p style={styles.subtitle}>
              {mode === 'login' && 'Access code intelligence, practice, and skill assessment.'}
              {mode === 'register_user' && 'Developer / Candidate profile (assigned strictly by server).'}
              {mode === 'register_hr' && 'Requires a single-use invitation code from an organization admin.'}
              {mode === 'initial_admin' && 'One-time initial administrative setup for primary organization.'}
            </p>
          </div>
          <button onClick={handleClose} style={styles.closeBtn}>✕</button>
        </div>

        {/* Tab Switcher */}
        <div style={styles.tabBar}>
          <button
            type="button"
            style={{ ...styles.tab, ...(mode === 'login' ? styles.activeTab : {}) }}
            onClick={() => handleModeChange('login')}
          >
            Sign In
          </button>
          <button
            type="button"
            style={{ ...styles.tab, ...(mode === 'register_user' ? styles.activeTab : {}) }}
            onClick={() => handleModeChange('register_user')}
          >
            Candidate Sign Up
          </button>
          <button
            type="button"
            style={{ ...styles.tab, ...(mode === 'register_hr' ? styles.activeTab : {}) }}
            onClick={() => handleModeChange('register_hr')}
          >
            HR with Invite
          </button>
          <button
            type="button"
            style={{ ...styles.tab, ...(mode === 'initial_admin' ? styles.activeTab : {}) }}
            onClick={() => handleModeChange('initial_admin')}
          >
            Initial Admin
          </button>
        </div>

        {/* Error / Success messages */}
        {error && (
          <div style={styles.errorAlert}>
            <span style={{ marginRight: '6px' }}>⚠</span>
            {error}
          </div>
        )}
        {successMsg && (
          <div style={styles.successAlert}>
            <span style={{ marginRight: '6px' }}>✓</span>
            {successMsg}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} style={styles.form}>
          {(mode === 'register_user' || mode === 'register_hr' || mode === 'initial_admin') && (
            <div style={styles.inputGroup}>
              <label style={styles.label}>Full Name</label>
              <input
                type="text"
                required
                placeholder="Jane Doe"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                style={styles.input}
              />
            </div>
          )}

          <div style={styles.inputGroup}>
            <label style={styles.label}>Email Address</label>
            <input
              type="email"
              required
              placeholder="developer@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={styles.input}
            />
          </div>

          <div style={styles.inputGroup}>
            <label style={styles.label}>Password</label>
            <input
              type="password"
              required
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={styles.input}
            />
            {mode !== 'login' && (
              <span style={styles.helpText}>
                Must be at least 8 characters with uppercase, lowercase, number, and special character.
              </span>
            )}
          </div>

          {mode === 'register_hr' && (
            <div style={styles.inputGroup}>
              <label style={styles.label}>HR Invitation Code</label>
              <input
                type="text"
                required
                placeholder="Paste your single-use invitation code"
                value={invitationCode}
                onChange={(e) => setInvitationCode(e.target.value)}
                style={styles.input}
              />
              <span style={styles.helpText}>
                HR accounts require an authorization token generated by your organization administrator.
              </span>
            </div>
          )}

          {mode === 'initial_admin' && (
            <div style={styles.inputGroup}>
              <label style={styles.label}>Organization Name</label>
              <input
                type="text"
                required
                placeholder="e.g. Acme Software Corp"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                style={styles.input}
              />
              <span style={styles.helpText}>
                Creates the root Organization and grants initial Owner / Admin rights.
              </span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{ ...styles.submitBtn, ...(loading ? { opacity: 0.7 } : {}) }}
          >
            {loading ? 'Processing...' : (
              mode === 'login' ? 'Sign In' :
              mode === 'register_user' ? 'Register as Candidate' :
              mode === 'register_hr' ? 'Activate HR Account' : 'Provision Administrator'
            )}
          </button>
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
    backdropFilter: 'blur(8px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 999,
  },
  modal: {
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    width: '100%',
    maxWidth: '520px',
    padding: '32px',
    boxShadow: 'var(--shadow-elevated)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '20px',
  },
  title: {
    margin: 0,
    fontSize: '20px',
    fontWeight: 600,
    letterSpacing: '0.5px',
    color: 'var(--text-primary)',
  },
  subtitle: {
    margin: '6px 0 0',
    fontSize: '12px',
    color: 'var(--text-muted)',
    lineHeight: '1.4',
  },
  closeBtn: {
    background: 'transparent',
    border: 'none',
    color: 'var(--text-muted)',
    fontSize: '18px',
    cursor: 'pointer',
    padding: '4px 8px',
    borderRadius: 'var(--radius-sm)',
  },
  tabBar: {
    display: 'flex',
    gap: '4px',
    padding: '4px',
    background: 'var(--bg-elevated)',
    borderRadius: 'var(--radius-md)',
    marginBottom: '20px',
  },
  tab: {
    flex: 1,
    padding: '8px 10px',
    fontSize: '11px',
    fontWeight: 500,
    border: 'none',
    background: 'transparent',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    borderRadius: 'var(--radius-sm)',
    transition: 'all 0.15s ease',
  },
  activeTab: {
    background: 'var(--bg-card)',
    color: 'var(--text-primary)',
    boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
  },
  errorAlert: {
    padding: '10px 14px',
    background: 'var(--red-dim)',
    border: '1px solid var(--red)',
    color: 'var(--red)',
    borderRadius: 'var(--radius-sm)',
    fontSize: '12px',
    marginBottom: '16px',
    lineHeight: '1.4',
  },
  successAlert: {
    padding: '10px 14px',
    background: 'var(--green-dim)',
    border: '1px solid var(--green)',
    color: 'var(--green)',
    borderRadius: 'var(--radius-sm)',
    fontSize: '12px',
    marginBottom: '16px',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  inputGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  label: {
    fontSize: '12px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
  },
  input: {
    padding: '10px 14px',
    background: 'var(--bg-input)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-sm)',
    color: 'var(--text-primary)',
    fontSize: '13px',
    outline: 'none',
    fontFamily: 'inherit',
    transition: 'border-color 0.2s',
  },
  helpText: {
    fontSize: '11px',
    color: 'var(--text-dim)',
    marginTop: '2px',
  },
  submitBtn: {
    marginTop: '8px',
    padding: '12px 20px',
    background: 'var(--text-primary)',
    color: 'var(--bg-primary)',
    fontWeight: 600,
    fontSize: '13px',
    border: 'none',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
    letterSpacing: '0.5px',
  },
};

export default AuthModal;
