import React from 'react';

function UserMenu({ user, onOpenAuth, onLogout }) {
  if (!user) {
    return (
      <button onClick={onOpenAuth} style={styles.signInBtn}>
        <span style={{ fontSize: '13px', opacity: 0.8 }}>⚡</span>
        Sign In / Register
      </button>
    );
  }

  const primaryOrg = user.organizations && user.organizations[0];
  const isHr = user.role === 'HR' || user.role === 'ADMIN';

  return (
    <div style={styles.container}>
      <div style={styles.userInfo}>
        <div style={styles.avatar}>
          {(user.full_name || user.email || 'U').charAt(0).toUpperCase()}
        </div>
        <div style={styles.details}>
          <div style={styles.nameRow}>
            <span style={styles.userName}>{user.full_name || user.email}</span>
            <span
              style={{
                ...styles.roleBadge,
                ...(isHr ? styles.hrBadge : styles.userBadge),
              }}
            >
              {isHr ? 'HR Recruiter' : 'Candidate'}
            </span>
          </div>
          {isHr && primaryOrg && (
            <span style={styles.orgLabel}>
              🏢 {primaryOrg.org_name}
            </span>
          )}
          {!isHr && (
            <span style={styles.emailLabel}>
              {user.email}
            </span>
          )}
        </div>
      </div>

      <button onClick={onLogout} style={styles.signOutBtn} title="Sign Out">
        Sign Out
      </button>
    </div>
  );
}

const styles = {
  signInBtn: {
    padding: '7px 16px',
    background: 'var(--bg-elevated)',
    border: '1px solid var(--border)',
    borderRadius: '20px',
    color: 'var(--text-primary)',
    fontSize: '12px',
    fontWeight: 500,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    transition: 'all 0.2s ease',
  },
  container: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '4px 10px',
    background: 'var(--bg-elevated)',
    border: '1px solid var(--border)',
    borderRadius: '24px',
  },
  userInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  avatar: {
    width: '26px',
    height: '26px',
    borderRadius: '50%',
    background: 'var(--border)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  details: {
    display: 'flex',
    flexDirection: 'column',
    lineHeight: '1.2',
  },
  nameRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  userName: {
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    maxWidth: '120px',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  roleBadge: {
    fontSize: '9px',
    padding: '1px 6px',
    borderRadius: '10px',
    fontWeight: 600,
    letterSpacing: '0.5px',
    textTransform: 'uppercase',
  },
  userBadge: {
    background: 'var(--green-dim)',
    color: 'var(--green)',
    border: '1px solid rgba(74, 222, 128, 0.3)',
  },
  hrBadge: {
    background: 'var(--blue-dim)',
    color: 'var(--blue)',
    border: '1px solid rgba(96, 165, 250, 0.3)',
  },
  orgLabel: {
    fontSize: '10px',
    color: 'var(--text-muted)',
    marginTop: '1px',
    maxWidth: '140px',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  emailLabel: {
    fontSize: '10px',
    color: 'var(--text-dim)',
    marginTop: '1px',
    maxWidth: '140px',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  signOutBtn: {
    padding: '4px 10px',
    background: 'transparent',
    border: 'none',
    color: 'var(--text-muted)',
    fontSize: '11px',
    cursor: 'pointer',
    borderRadius: 'var(--radius-sm)',
    transition: 'color 0.2s ease',
  },
};

export default UserMenu;
