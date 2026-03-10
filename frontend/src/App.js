import React, { useState, useEffect } from 'react';
import './App.css';
import AnalyzeRepo from './components/AnalyzeRepo';
import PatternDetection from './components/PatternDetection';
import CouplingAnalysis from './components/CouplingAnalysis';
import ImpactAnalysis from './components/ImpactAnalysis';
import ArchitectureView from './components/ArchitectureView';
import DependencyGraph from './components/DependencyGraph';
import FunctionGraph from './components/FunctionGraph';
import FunctionAnalysis from './components/FunctionAnalysis';
import RepositoryManager from './components/RepositoryManager';
import SnapshotComparison from './components/SnapshotComparison';
import BlastRadius from './components/BlastRadius';
import ConfidenceReport from './components/ConfidenceReport';

function App() {
  const [activeTab, setActiveTab] = useState('analyze');
  const [refreshKey, setRefreshKey] = useState(0);
  const [displayText, setDisplayText] = useState('');
  const [currentRepoId, setCurrentRepoId] = useState(null);
  const [currentRepoName, setCurrentRepoName] = useState(null);

  const handleAnalysisComplete = (result) => {
    setRefreshKey(prev => prev + 1);
    if (result?.repo_id) {
      setCurrentRepoId(result.repo_id);
    }
    setActiveTab('patterns');
  };

  const handleRepoSelect = (repo) => {
    setCurrentRepoId(repo.repo_id);
    setCurrentRepoName(repo.name);
    setRefreshKey(prev => prev + 1);
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

  const tabs = [
    { id: 'analyze', label: 'Analyze', icon: '◈' },
    { id: 'repositories', label: 'Repos', icon: '▦' },
    { id: 'patterns', label: 'Patterns', icon: '◬' },
    { id: 'coupling', label: 'Coupling', icon: '⬡' },
    { id: 'blast-radius', label: 'Blast', icon: '◎' },
    { id: 'impact', label: 'Impact', icon: '⚡' },
    { id: 'confidence', label: 'Confidence', icon: '◉' },
    { id: 'functions', label: 'Functions', icon: 'ƒ' },
    { id: 'architecture', label: 'Architecture', icon: '△' },
    { id: 'graph', label: 'File Graph', icon: '⬢' },
    { id: 'function-graph', label: 'Fn Graph', icon: '⬣' },
    { id: 'snapshots', label: 'Snapshots', icon: '❐' }
  ];

  return (
    <div style={styles.app}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerInner}>
          <div style={styles.headerLeft}>
            <h1 style={styles.title}>{displayText}</h1>
            <p style={styles.subtitle}>Architectural Recovery & Semantic Synthesis</p>
          </div>
          {currentRepoName && (
            <div style={styles.repoIndicator}>
              <span style={styles.repoDot}></span>
              {currentRepoName}
            </div>
          )}
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
                ...(activeTab === tab.id ? styles.activeTab : {})
              }}
            >
              <span style={styles.tabIcon}>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Main Content */}
      <main style={styles.main}>
        <div className="fade-in" key={activeTab + refreshKey}>
          {activeTab === 'analyze' && <AnalyzeRepo onAnalysisComplete={handleAnalysisComplete} />}
          {activeTab === 'repositories' && <RepositoryManager key={refreshKey} onRepoSelect={handleRepoSelect} />}
          {activeTab === 'patterns' && <PatternDetection key={refreshKey} repoId={currentRepoId} />}
          {activeTab === 'coupling' && <CouplingAnalysis key={refreshKey} repoId={currentRepoId} />}
          {activeTab === 'blast-radius' && <BlastRadius key={refreshKey} repoId={currentRepoId} />}
          {activeTab === 'impact' && <ImpactAnalysis repoId={currentRepoId} />}
          {activeTab === 'confidence' && <ConfidenceReport key={refreshKey} repoId={currentRepoId} />}
          {activeTab === 'functions' && <FunctionAnalysis key={refreshKey} repoId={currentRepoId} />}
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

      {/* Footer */}
      <footer style={styles.footer}>
        <span style={styles.footerDot}></span>
        API: localhost:8000
        <span style={{ margin: '0 12px', color: 'var(--border)' }}>|</span>
        Neo4j: localhost:7474
      </footer>
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
    padding: '20px 32px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerLeft: {},
  title: {
    margin: 0,
    fontSize: '28px',
    fontFamily: 'var(--font-mono)',
    fontWeight: 600,
    letterSpacing: '4px',
    color: 'var(--text-primary)',
  },
  subtitle: {
    margin: '4px 0 0',
    fontSize: '13px',
    color: 'var(--text-muted)',
    fontWeight: 400,
    letterSpacing: '0.5px',
  },
  repoIndicator: {
    padding: '6px 14px',
    background: 'var(--accent-glow)',
    border: '1px solid var(--border)',
    borderRadius: '20px',
    fontSize: '13px',
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
    top: '72px',
    zIndex: 40,
  },
  navInner: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: '8px 24px',
    display: 'flex',
    gap: '2px',
    overflowX: 'auto',
  },
  tab: {
    padding: '8px 14px',
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    fontSize: '13px',
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
  tabIcon: {
    fontSize: '11px',
    opacity: 0.7,
  },
  main: {
    maxWidth: '1400px',
    margin: '24px auto',
    padding: '0 32px',
  },
  emptyState: {
    textAlign: 'center',
    padding: '60px 20px',
    color: 'var(--text-muted)',
    fontSize: '14px',
  },
  footer: {
    textAlign: 'center',
    padding: '20px',
    color: 'var(--text-dim)',
    fontSize: '12px',
    borderTop: '1px solid var(--border)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
  },
  footerDot: {
    width: '5px',
    height: '5px',
    borderRadius: '50%',
    background: 'var(--green)',
    display: 'inline-block',
  },
};

export default App;
