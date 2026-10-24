import React, { useState, useEffect } from 'react';
import './App.css';
import AnalyzeRepo from './components/AnalyzeRepo';
import PatternDetection from './components/PatternDetection';
import CouplingAnalysis from './components/CouplingAnalysis';
import ArchitectureView from './components/ArchitectureView';
import DependencyGraph from './components/DependencyGraph';
import FunctionGraph from './components/FunctionGraph';
import FunctionAnalysis from './components/FunctionAnalysis';
import RepositoryManager from './components/RepositoryManager';
import SnapshotComparison from './components/SnapshotComparison';
import BlastRadius from './components/BlastRadius';
import CodeHealth from './components/CodeHealth';
import CinematicStory from './components/cinematic/CinematicStory';
import AuthModal from './components/auth/AuthModal';
import UserMenu from './components/auth/UserMenu';
import CandidateDashboard from './components/practice/CandidateDashboard';
import HrStudio from './components/hr/HrStudio';
import CandidateAssignedAssessments from './components/assessment/CandidateAssignedAssessments';
import AssessmentWorkspace from './components/assessment/AssessmentWorkspace';
import { authService } from './services/auth';

const repositoryLabel = (result, source) => {
  const explicit = result?.repo_name || result?.repository_name || result?.name;
  if (explicit) return explicit;

  const raw = source || result?.repo_url || result?.repo_path || '';
  const normalized = String(raw).replace(/\\/g, '/').replace(/\/$/, '');
  return normalized.split('/').filter(Boolean).pop()?.replace(/\.git$/i, '') || 'Current repository';
};

function App() {
  const [activeTab, setActiveTab] = useState('story');
  const [refreshKey, setRefreshKey] = useState(0);
  const [displayText, setDisplayText] = useState('');
  const [currentRepoId, setCurrentRepoId] = useState('eac55829cf3ea1d6');
  const [currentRepoName, setCurrentRepoName] = useState('repoanayliser');

  // Authentication & RBAC state
  const [currentUser, setCurrentUser] = useState(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authTestResult, setAuthTestResult] = useState(null);
  const [authTestLoading, setAuthTestLoading] = useState(false);
  const [activeAssessmentAttempt, setActiveAssessmentAttempt] = useState(null);

  const handleAnalysisComplete = (result, source) => {
    setRefreshKey(prev => prev + 1);
    if (result?.repo_id) {
      setCurrentRepoId(result.repo_id);
      setCurrentRepoName(repositoryLabel(result, source));
    }
    setActiveTab('patterns');
  };

  const handleRepoSelect = (repo) => {
    setCurrentRepoId(repo.repo_id);
    setCurrentRepoName(repo.name);
    setRefreshKey(prev => prev + 1);
  };

  const handleRepoDelete = (deletedRepoId) => {
    if (currentRepoId === deletedRepoId) {
      setCurrentRepoId(null);
      setCurrentRepoName(null);
      setRefreshKey(prev => prev + 1);
    }
  };

  // Check authentication on initial load
  useEffect(() => {
    authService.getMe()
      .then(user => setCurrentUser(user))
      .catch(() => setCurrentUser(null));

    // Auto-navigate to assessments if invite token is in URL
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('invite')) {
      setActiveTab('candidate-assessments');
    }
  }, []);

  const handleAuthSuccess = (user) => {
    setCurrentUser(user);
    setAuthTestResult(null);
  };

  const handleLogout = async () => {
    await authService.logout();
    setCurrentUser(null);
    setAuthTestResult(null);
    setActiveAssessmentAttempt(null);
  };

  const testEndpoint = async (type) => {
    setAuthTestLoading(true);
    setAuthTestResult(null);
    try {
      if (type === 'user') {
        const res = await authService.testUserEndpoint();
        setAuthTestResult({ success: true, data: res });
      } else {
        const res = await authService.testHrEndpoint();
        setAuthTestResult({ success: true, data: res });
      }
    } catch (err) {
      setAuthTestResult({
        success: false,
        status: err.response?.status,
        error: err.response?.data?.detail || err.message
      });
    } finally {
      setAuthTestLoading(false);
    }
  };

  useEffect(() => {
    const finalText = 'ARCHITECH';
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&*';
    let iteration = 0;

    const interval = setInterval(() => {
      setDisplayText(
        finalText
          .split('')
          .map((letter, index) => {
            if (index < iteration) {
              return finalText[index];
            }
            return chars[Math.floor(Math.random() * chars.length)];
          })
          .join('')
      );

      if (iteration >= finalText.length) {
        clearInterval(interval);
      }

      iteration += 1 / 3;
    }, 30);

    return () => clearInterval(interval);
  }, []);

  const isHr = currentUser?.role === 'HR' || currentUser?.role === 'ADMIN';

  const tabs = [
    { id: 'story', label: 'Story Experience', icon: '▶' },
    { id: 'candidate-assessments', label: 'My Assessments', icon: '📝' },
    { id: 'practice', label: 'Candidate Practice', icon: '🎯' },
    { id: 'hr-studio', label: 'HR Studio', icon: '🏢' },
    { id: 'architecture', label: 'Architecture', icon: '△' },
    { id: 'graph', label: 'File Graph', icon: '⬢' },
    { id: 'blast-radius', label: 'Blast Radius', icon: '◎' },
    { id: 'patterns', label: 'Patterns', icon: '◬' },
    { id: 'coupling', label: 'Coupling', icon: '⬡' },
    { id: 'functions', label: 'Functions', icon: 'ƒ' },
    { id: 'health', label: 'Unused', icon: '○' },
    { id: 'function-graph', label: 'Fn Graph', icon: '⬣' },
    { id: 'repositories', label: 'Repos', icon: '▦' },
    { id: 'analyze', label: 'Analyze', icon: '◈' },
    { id: 'snapshots', label: 'Snapshots', icon: '❐' }
  ];

  return (
    <div style={styles.app}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerInner}>
          <div style={styles.headerLeft}>
            <h1 style={styles.title}>{displayText}</h1>
            <p style={styles.subtitle}>Repository-Aware Assessment & Architectural Intelligence</p>
          </div>

          <div style={styles.headerRight}>
            {currentRepoName && (
              <div style={styles.repoIndicator}>
                <span style={styles.repoDot}></span>
                {currentRepoName}
              </div>
            )}
            <UserMenu
              user={currentUser}
              onOpenAuth={() => setIsAuthModalOpen(true)}
              onLogout={handleLogout}
            />
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav style={styles.nav}>
        <div style={styles.navInner}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                ...styles.tab,
                ...(activeTab === tab.id ? styles.activeTab : {}),
                ...(tab.id === 'hr-studio' && isHr ? styles.hrTabActive : {})
              }}
            >
              <span style={styles.tabIcon}>{tab.icon}</span>
              {tab.label}
              {tab.id === 'hr-studio' && isHr && (
                <span style={styles.badgePill}>HR</span>
              )}
            </button>
          ))}
        </div>
      </nav>

      {/* Main Content */}
      <main style={styles.main}>
        <div className="fade-in" key={activeTab + refreshKey}>
          {/* Phase 4 Candidate Assigned Assessments & Workspace */}
          {activeTab === 'candidate-assessments' && (
            activeAssessmentAttempt ? (
              <AssessmentWorkspace
                initialAttempt={activeAssessmentAttempt}
                onExit={() => setActiveAssessmentAttempt(null)}
              />
            ) : currentUser ? (
              <CandidateAssignedAssessments
                onStartAttempt={(attempt) => setActiveAssessmentAttempt(attempt)}
                onViewResult={() => {
                  setActiveAssessmentAttempt(null);
                }}
              />
            ) : (
              <div style={styles.sectionCard}>
                <div style={styles.cardHeader}>
                  <span style={{ fontSize: '24px' }}>📝</span>
                  <div>
                    <h2 style={styles.cardTitle}>Enterprise Technical Assessments</h2>
                    <p style={styles.cardSubtitle}>
                      Repository-aware timed assessments assigned by hiring organizations with automated objective evaluation.
                    </p>
                  </div>
                </div>

                <div style={styles.infoBox}>
                  <h3 style={styles.boxTitle}>Candidate Authentication Required</h3>
                  <p style={styles.boxText}>
                    Please sign in or register with the email address your invitation was sent to in order to claim and complete your technical assessment.
                  </p>
                  <button
                    onClick={() => setIsAuthModalOpen(true)}
                    style={styles.primaryBtn}
                  >
                    Sign In / Register as Candidate
                  </button>
                </div>
              </div>
            )
          )}

          {/* Phase 2 Candidate Practice View */}
          {activeTab === 'practice' && (
            currentUser ? (
              <CandidateDashboard />
            ) : (
              <div style={styles.sectionCard}>
                <div style={styles.cardHeader}>
                  <span style={{ fontSize: '24px' }}>🎯</span>
                  <div>
                    <h2 style={styles.cardTitle}>Candidate Practice & Skill Intelligence</h2>
                    <p style={styles.cardSubtitle}>
                      Personal technical practice grounded in real codebases, resume parsing, and verified code evidence.
                    </p>
                  </div>
                </div>

                <div style={styles.gridTwo}>
                  <div style={styles.infoBox}>
                    <h3 style={styles.boxTitle}>Authentication Required</h3>
                    <p style={styles.boxText}>
                      Sign in or create a candidate account to upload your resume, connect repositories, generate personalized quizzes, and track your practice history.
                    </p>
                    <button
                      onClick={() => setIsAuthModalOpen(true)}
                      style={styles.primaryBtn}
                    >
                      Sign In / Register as Candidate
                    </button>
                  </div>

                  <div style={styles.infoBox}>
                    <h3 style={styles.boxTitle}>Server-Side Endpoint Authorization Test</h3>
                    <p style={styles.boxText}>
                      Verify candidate endpoint protection (<code>GET /api/auth/test/user-only</code>):
                    </p>
                    <button
                      onClick={() => testEndpoint('user')}
                      disabled={authTestLoading}
                      style={styles.testBtn}
                    >
                      {authTestLoading ? 'Verifying with backend...' : 'Execute Candidate Endpoint Test'}
                    </button>

                    {authTestResult && (
                      <div style={{
                        ...styles.resultBox,
                        borderColor: authTestResult.success ? 'var(--green)' : 'var(--red)'
                      }}>
                        {authTestResult.success ? (
                          <div style={{ color: 'var(--green)' }}>
                            <strong>✓ 200 OK — Authorized:</strong>
                            <pre style={styles.codeBlock}>{JSON.stringify(authTestResult.data, null, 2)}</pre>
                          </div>
                        ) : (
                          <div style={{ color: 'var(--red)' }}>
                            <strong>✕ {authTestResult.status} — Rejected:</strong>
                            <pre style={styles.codeBlock}>{authTestResult.error}</pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                <div style={styles.workflowRoadmap}>
                  <h4 style={styles.roadmapTitle}>Phase 2 Practice Capabilities Live:</h4>
                  <ul style={styles.roadmapList}>
                    <li>✓ Resume upload & AI skill extraction (PDF, DOCX, TXT) with editable review</li>
                    <li>✓ Secure GitHub repository connection & AST analysis status tracking</li>
                    <li>✓ Grounded skill-to-code evidence mapping across AST symbols and architecture patterns</li>
                    <li>✓ Interactive practice quizzes (Skill-based Mode A & Repository Mode B)</li>
                    <li>✓ Objective scoring with multi-select partial credit & candidate question redaction</li>
                    <li>✓ Persisted practice history and competency progress tracking</li>
                  </ul>
                </div>
              </div>
            )
          )}

          {/* Phase 3 HR Studio View */}
          {activeTab === 'hr-studio' && (
            isHr ? (
              <HrStudio currentUser={currentUser} />
            ) : (
              <div style={styles.sectionCard}>
                <div style={styles.cardHeader}>
                  <span style={{ fontSize: '24px' }}>🏢</span>
                  <div>
                    <h2 style={styles.cardTitle}>HR Recruiter & Assessment Studio</h2>
                    <p style={styles.cardSubtitle}>
                      Organization assessment repository management, question curation, and candidate evaluations.
                    </p>
                  </div>
                </div>

                <div style={styles.restrictedNotice}>
                  <span style={{ fontSize: '28px', color: 'var(--amber)' }}>🔒</span>
                  <div style={{ flex: 1 }}>
                    <h3 style={{ margin: '0 0 6px 0', fontSize: '15px', color: 'var(--amber)' }}>
                      HR Recruiter Access Required
                    </h3>
                    <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-secondary)' }}>
                      This administrative module is strictly restricted to verified corporate recruiters and organization owners.
                      Candidate accounts cannot switch to the HR role without an authorized single-use invitation.
                    </p>
                  </div>
                  <button
                    onClick={() => testEndpoint('hr')}
                    disabled={authTestLoading}
                    style={styles.testBtn}
                  >
                    Test Server HR Guard (Expect 403)
                  </button>
                </div>

                {authTestResult && (
                  <div style={{
                    ...styles.resultBox,
                    marginTop: '16px',
                    borderColor: authTestResult.success ? 'var(--green)' : 'var(--red)'
                  }}>
                    {authTestResult.success ? (
                      <div style={{ color: 'var(--green)' }}>
                        <strong>✓ 200 OK — HR Access Verified:</strong>
                        <pre style={styles.codeBlock}>{JSON.stringify(authTestResult.data, null, 2)}</pre>
                      </div>
                    ) : (
                      <div style={{ color: 'var(--red)' }}>
                        <strong>✕ {authTestResult.status} Forbidden — Access Correctly Blocked:</strong>
                        <pre style={styles.codeBlock}>{authTestResult.error}</pre>
                      </div>
                    )}
                  </div>
                )}

                <div style={styles.workflowRoadmap}>
                  <h4 style={styles.roadmapTitle}>Phase 3 & Phase 4 Enterprise Assessment Capabilities Live:</h4>
                  <ul style={styles.roadmapList}>
                    <li>✓ Organization-scoped HR Question Bank with multi-criteria search & filters</li>
                    <li>✓ Manual question authoring & editing with automated option/answer validation</li>
                    <li>✓ AI-assisted question generation (Skill-based Mode A & Repository Mode B)</li>
                    <li>✓ Formal question lifecycle (Needs Review → Approved → Published → Archived)</li>
                    <li>✓ Approved Repository Library with SSRF-protected registration & code coverage analytics</li>
                    <li>✓ Enterprise Assessment Studio with Curated & Randomized Blueprint modes</li>
                    <li>✓ Cryptographically hashed candidate invitation tokens with email-bound claims</li>
                    <li>✓ Server-authoritative timed attempts with split-pane codebase explorer</li>
                    <li>✓ Durably persisted autosave & recovery with client-redacted answer keys</li>
                    <li>✓ Objective multi-format scoring with formula-injection-sanitized CSV exports</li>
                  </ul>
                </div>
              </div>
            )
          )}

          {/* Existing ARCHITECH Code Intelligence Features */}
          {activeTab === 'story' && (
            <CinematicStory
              repoId={currentRepoId || 'eac55829cf3ea1d6'}
              onSelectTab={(tabId) => setActiveTab(tabId)}
              onExitToApp={() => setActiveTab('graph')}
            />
          )}
          {activeTab === 'analyze' && <AnalyzeRepo onAnalysisComplete={handleAnalysisComplete} />}
          {activeTab === 'repositories' && (
            <RepositoryManager
              key={refreshKey}
              onRepoSelect={handleRepoSelect}
              onRepoDelete={handleRepoDelete}
            />
          )}
          {activeTab === 'patterns' && <PatternDetection key={refreshKey} repoId={currentRepoId} />}
          {activeTab === 'coupling' && <CouplingAnalysis key={refreshKey} repoId={currentRepoId} />}
          {activeTab === 'blast-radius' && <BlastRadius key={refreshKey} repoId={currentRepoId} />}
          {activeTab === 'functions' && <FunctionAnalysis key={refreshKey} repoId={currentRepoId} />}
          {activeTab === 'health' && <CodeHealth key={refreshKey} repoId={currentRepoId} />}
          {activeTab === 'architecture' && <ArchitectureView key={refreshKey} repoId={currentRepoId} />}
          {activeTab === 'graph' && <DependencyGraph key={refreshKey} repoId={currentRepoId} />}
          {activeTab === 'function-graph' && <FunctionGraph key={refreshKey} repoId={currentRepoId} />}
          {activeTab === 'snapshots' && currentRepoId && <SnapshotComparison key={refreshKey} repoId={currentRepoId} />}
          {activeTab === 'snapshots' && !currentRepoId && (
            <div style={styles.emptyState}>
              <span style={{ fontSize: '32px', marginBottom: '12px', display: 'block' }}>▦</span>
              Select a repository first from the Repos tab
            </div>
          )}
        </div>
      </main>

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onAuthSuccess={handleAuthSuccess}
      />
    </div>
  );
}

const styles = {
  app: {
    minHeight: '100vh',
    background: 'var(--bg-primary)',
    fontFamily: 'var(--font-sans)',
    color: 'var(--text-primary)',
  },
  header: {
    borderBottom: '1px solid var(--border)',
    backdropFilter: 'blur(12px)',
    background: 'rgba(9, 9, 11, 0.85)',
    position: 'sticky',
    top: 0,
    zIndex: 50,
  },
  headerInner: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: '16px 32px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerLeft: {},
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  title: {
    margin: 0,
    fontSize: '26px',
    fontFamily: 'var(--font-mono)',
    fontWeight: 600,
    letterSpacing: '3px',
    color: 'var(--text-primary)',
  },
  subtitle: {
    margin: '3px 0 0',
    fontSize: '12px',
    color: 'var(--text-muted)',
    fontWeight: 400,
    letterSpacing: '0.5px',
  },
  repoIndicator: {
    padding: '6px 12px',
    background: 'var(--accent-glow)',
    border: '1px solid var(--border)',
    borderRadius: '20px',
    fontSize: '12px',
    color: 'var(--text-secondary)',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  repoDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: 'var(--green)',
    display: 'inline-block',
    boxShadow: '0 0 6px var(--green)',
  },
  nav: {
    borderBottom: '1px solid var(--border)',
    background: 'rgba(9, 9, 11, 0.6)',
    backdropFilter: 'blur(8px)',
    position: 'sticky',
    top: '68px',
    zIndex: 40,
  },
  navInner: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: '8px 24px',
    display: 'flex',
    gap: '3px',
    overflowX: 'auto',
  },
  tab: {
    padding: '8px 12px',
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: 500,
    color: 'var(--text-muted)',
    borderRadius: 'var(--radius-sm)',
    transition: 'all 0.2s',
    whiteSpace: 'nowrap',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  activeTab: {
    background: 'var(--bg-elevated)',
    color: 'var(--text-primary)',
    boxShadow: '0 0 0 1px var(--border)',
  },
  hrTabActive: {
    borderLeft: '2px solid var(--blue)',
  },
  badgePill: {
    fontSize: '9px',
    background: 'var(--blue-dim)',
    color: 'var(--blue)',
    padding: '1px 5px',
    borderRadius: '6px',
    fontWeight: 600,
  },
  tabIcon: {
    fontSize: '11px',
    opacity: 0.7,
  },
  main: {
    maxWidth: '1400px',
    margin: '24px auto',
    padding: '0 32px',
  },
  sectionCard: {
    background: 'var(--bg-card)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: '28px',
    boxShadow: 'var(--shadow-card)',
  },
  cardHeader: {
    display: 'flex',
    gap: '16px',
    alignItems: 'center',
    marginBottom: '24px',
    paddingBottom: '16px',
    borderBottom: '1px solid var(--border)',
  },
  cardTitle: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  cardSubtitle: {
    margin: '4px 0 0',
    fontSize: '13px',
    color: 'var(--text-muted)',
  },
  gridTwo: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
    gap: '20px',
  },
  infoBox: {
    background: 'var(--bg-elevated)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    padding: '20px',
  },
  boxTitle: {
    margin: '0 0 10px 0',
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  boxText: {
    margin: 0,
    fontSize: '13px',
    color: 'var(--text-secondary)',
    lineHeight: '1.5',
  },
  tagGreen: {
    background: 'var(--green-dim)',
    color: 'var(--green)',
    padding: '2px 8px',
    borderRadius: '12px',
    fontSize: '11px',
    fontWeight: 600,
  },
  tagBlue: {
    background: 'var(--blue-dim)',
    color: 'var(--blue)',
    padding: '2px 8px',
    borderRadius: '12px',
    fontSize: '11px',
    fontWeight: 600,
  },
  primaryBtn: {
    marginTop: '14px',
    padding: '8px 16px',
    background: 'var(--text-primary)',
    color: 'var(--bg-primary)',
    fontWeight: 600,
    fontSize: '12px',
    borderRadius: 'var(--radius-sm)',
    border: 'none',
    cursor: 'pointer',
  },
  testBtn: {
    marginTop: '12px',
    padding: '8px 16px',
    background: 'var(--bg-card)',
    color: 'var(--text-primary)',
    fontWeight: 500,
    fontSize: '12px',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--border)',
    cursor: 'pointer',
  },
  resultBox: {
    marginTop: '12px',
    padding: '12px',
    background: 'var(--bg-input)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-sm)',
    fontSize: '12px',
  },
  codeBlock: {
    margin: '6px 0 0',
    padding: '8px',
    background: 'rgba(0,0,0,0.4)',
    borderRadius: '4px',
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    overflowX: 'auto',
  },
  restrictedNotice: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '20px',
    background: 'var(--amber-dim)',
    border: '1px solid rgba(251, 191, 36, 0.3)',
    borderRadius: 'var(--radius-md)',
  },
  workflowRoadmap: {
    marginTop: '24px',
    paddingTop: '16px',
    borderTop: '1px solid var(--border)',
  },
  roadmapTitle: {
    margin: '0 0 8px 0',
    fontSize: '12px',
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  roadmapList: {
    margin: 0,
    paddingLeft: '16px',
    fontSize: '12px',
    color: 'var(--text-dim)',
    lineHeight: '1.6',
  },
  emptyState: {
    textAlign: 'center',
    padding: '60px 20px',
    color: 'var(--text-muted)',
    fontSize: '14px',
  },
};

export default App;
