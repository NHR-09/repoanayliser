import React, { useState, useEffect, useCallback } from 'react';
import { hrApi } from '../../services/hrApi';
import QuestionBankTable from './QuestionBankTable';
import RepositoryLibrary from './RepositoryLibrary';
import AssessmentList from '../assessment/AssessmentList';

export default function HrStudio({ currentUser }) {
  const [organizations, setOrganizations] = useState([]);
  const [selectedOrgId, setSelectedOrgId] = useState('');
  const [activeTab, setActiveTab] = useState('assessments'); // 'assessments' | 'questions' | 'repositories'
  const [loadingOrgs, setLoadingOrgs] = useState(true);
  const [orgError, setOrgError] = useState('');

  // Cross-component generation trigger
  const [genTrigger, setGenTrigger] = useState({ open: false, repoId: '' });

  const loadOrganizations = useCallback(async () => {
    setLoadingOrgs(true);
    setOrgError('');
    try {
      const data = await hrApi.getOrganizations();
      const orgs = data?.organizations || [];
      setOrganizations(orgs);
      if (orgs.length > 0) {
        setSelectedOrgId(orgs[0].id);
      } else if (currentUser?.organizations?.length > 0) {
        setOrganizations(currentUser.organizations);
        setSelectedOrgId(currentUser.organizations[0].org_id || currentUser.organizations[0].id);
      }
    } catch (err) {
      console.error('Failed to load HR organizations:', err);
      if (currentUser?.organizations?.length > 0) {
        setOrganizations(currentUser.organizations);
        setSelectedOrgId(currentUser.organizations[0].org_id || currentUser.organizations[0].id);
      } else {
        setOrgError(err.response?.data?.detail || err.message || 'Failed to resolve organization memberships.');
      }
    } finally {
      setLoadingOrgs(false);
    }
  }, [currentUser]);

  useEffect(() => {
    loadOrganizations();
  }, [loadOrganizations]);

  const handleOpenGenerateForRepo = (repo) => {
    setGenTrigger({
      open: true,
      repoId: repo.id || repo.repo_id,
    });
    setActiveTab('questions');
  };

  const currentOrg = organizations.find((o) => (o.id || o.org_id) === selectedOrgId);

  return (
    <div style={styles.container}>
      {/* Top Studio Header & Org Context Switcher */}
      <div style={styles.headerCard}>
        <div style={styles.headerLeft}>
          <div style={styles.iconCircle}>🏢</div>
          <div>
            <div style={styles.badgeRow}>
              <span style={styles.tagBlue}>HR ASSESSMENT STUDIO</span>
              <span style={styles.tagZinc}>PHASE 4 ACTIVE</span>
              {currentOrg && (
                <span style={styles.tagGreen}>
                  {currentOrg.user_role || currentOrg.org_role || 'RECRUITER'}
                </span>
              )}
            </div>
            <h1 style={styles.studioTitle}>Enterprise Assessment Studio & Repository Intelligence</h1>
            <p style={styles.studioSubtitle}>
              Create immutable assessments, evaluate candidate reasoning on real codebases, and review objective scorecards.
            </p>
          </div>
        </div>

        {/* Organization Switcher */}
        <div style={styles.headerRight}>
          <div style={styles.orgSelectorBox}>
            <label style={styles.orgLabel}>Active Organization</label>
            {loadingOrgs ? (
              <span style={{ fontSize: '13px', color: '#94a3b8' }}>Resolving memberships...</span>
            ) : organizations.length > 0 ? (
              <select
                value={selectedOrgId}
                onChange={(e) => setSelectedOrgId(e.target.value)}
                style={styles.orgSelect}
              >
                {organizations.map((org) => {
                  const orgId = org.id || org.org_id;
                  const orgName = org.name || org.org_name || orgId;
                  const role = org.user_role || org.org_role || 'MEMBER';
                  return (
                    <option key={orgId} value={orgId}>
                      {orgName} ({role})
                    </option>
                  );
                })}
              </select>
            ) : (
              <span style={{ fontSize: '13px', color: '#ef4444' }}>No organization memberships found</span>
            )}
          </div>
        </div>
      </div>

      {orgError && (
        <div style={styles.errorBox}>
          <strong>Organization Resolution Error:</strong> {orgError}
        </div>
      )}

      {/* Sub-Navigation Tabs */}
      <div style={styles.navTabs}>
        <button
          onClick={() => setActiveTab('assessments')}
          style={{
            ...styles.navTabBtn,
            ...(activeTab === 'assessments' ? styles.navTabBtnActive : {}),
          }}
        >
          <span style={{ marginRight: '8px', fontSize: '15px' }}>🎯</span>
          Enterprise Assessments
          <span style={styles.tabBadge}>Studio & Scoring</span>
        </button>

        <button
          onClick={() => setActiveTab('questions')}
          style={{
            ...styles.navTabBtn,
            ...(activeTab === 'questions' ? styles.navTabBtnActive : {}),
          }}
        >
          <span style={{ marginRight: '8px', fontSize: '15px' }}>📋</span>
          HR Question Bank
          <span style={styles.tabBadge}>Curated & Grounded</span>
        </button>

        <button
          onClick={() => setActiveTab('repositories')}
          style={{
            ...styles.navTabBtn,
            ...(activeTab === 'repositories' ? styles.navTabBtnActive : {}),
          }}
        >
          <span style={{ marginRight: '8px', fontSize: '15px' }}>🏛️</span>
          Approved Repository Library
          <span style={styles.tabBadge}>AST & Evidence</span>
        </button>
      </div>

      {/* Tab Panels */}
      <div style={styles.contentArea}>
        {!selectedOrgId ? (
          <div style={styles.emptyOrgState}>
            <span style={{ fontSize: '32px' }}>🔒</span>
            <h3 style={{ margin: '12px 0 6px', color: '#f8fafc' }}>Select an Authorized Organization</h3>
            <p style={{ margin: 0, color: '#94a3b8', fontSize: '14px', maxWidth: '480px' }}>
              Your account must be provisioned with active HR or Owner permissions inside an organization to manage assessments, questions, and approved repositories.
            </p>
          </div>
        ) : activeTab === 'assessments' ? (
          <AssessmentList orgId={selectedOrgId} />
        ) : activeTab === 'questions' ? (
          <QuestionBankTable
            orgId={selectedOrgId}
            initialOpenGen={genTrigger.open}
            initialGenRepoId={genTrigger.repoId}
            onClearGenTrigger={() => setGenTrigger({ open: false, repoId: '' })}
          />
        ) : (
          <RepositoryLibrary
            orgId={selectedOrgId}
            onOpenGenerateForRepo={handleOpenGenerateForRepo}
          />
        )}
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
    maxWidth: '1400px',
    margin: '0 auto',
    width: '100%',
  },
  headerCard: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '12px',
    padding: '24px',
    boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2)',
    flexWrap: 'wrap',
    gap: '20px',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '18px',
  },
  iconCircle: {
    width: '56px',
    height: '56px',
    borderRadius: '12px',
    backgroundColor: 'rgba(56, 189, 248, 0.1)',
    border: '1px solid rgba(56, 189, 248, 0.3)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '28px',
  },
  badgeRow: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
    marginBottom: '6px',
  },
  tagBlue: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#38bdf8',
    backgroundColor: 'rgba(56, 189, 248, 0.12)',
    padding: '2px 8px',
    borderRadius: '4px',
    letterSpacing: '0.05em',
  },
  tagZinc: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#94a3b8',
    backgroundColor: '#334155',
    padding: '2px 8px',
    borderRadius: '4px',
    letterSpacing: '0.05em',
  },
  tagGreen: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#10b981',
    backgroundColor: 'rgba(16, 185, 129, 0.12)',
    padding: '2px 8px',
    borderRadius: '4px',
    letterSpacing: '0.05em',
  },
  studioTitle: {
    margin: 0,
    fontSize: '22px',
    fontWeight: '700',
    color: '#f8fafc',
    letterSpacing: '-0.02em',
  },
  studioSubtitle: {
    margin: '4px 0 0',
    fontSize: '13px',
    color: '#94a3b8',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
  },
  orgSelectorBox: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    minWidth: '260px',
  },
  orgLabel: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  orgSelect: {
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '8px',
    color: '#f8fafc',
    padding: '9px 12px',
    fontSize: '13px',
    fontWeight: '500',
    outline: 'none',
    cursor: 'pointer',
  },
  errorBox: {
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    color: '#fca5a5',
    padding: '12px 16px',
    borderRadius: '8px',
    fontSize: '13px',
  },
  navTabs: {
    display: 'flex',
    gap: '12px',
    borderBottom: '1px solid #334155',
    paddingBottom: '12px',
  },
  navTabBtn: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: 'transparent',
    border: '1px solid transparent',
    color: '#94a3b8',
    padding: '10px 18px',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.15s ease-in-out',
  },
  navTabBtnActive: {
    backgroundColor: '#1e293b',
    borderColor: '#38bdf8',
    color: '#f8fafc',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
  },
  tabBadge: {
    marginLeft: '10px',
    fontSize: '11px',
    fontWeight: '500',
    color: '#64748b',
    backgroundColor: '#0f172a',
    padding: '2px 8px',
    borderRadius: '12px',
    border: '1px solid #334155',
  },
  contentArea: {
    minHeight: '500px',
  },
  emptyOrgState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 20px',
    backgroundColor: '#1e293b',
    border: '1px dashed #334155',
    borderRadius: '12px',
    textAlign: 'center',
  },
};
