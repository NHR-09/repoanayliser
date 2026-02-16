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
    { id: 'analyze', label: 'Analyze' },
    { id: 'repositories', label: 'Repositories' },
    { id: 'patterns', label: 'Patterns' },
    { id: 'coupling', label: 'Coupling' },
    { id: 'blast-radius', label: 'Blast Radius' },
    { id: 'impact', label: 'Impact' },
    { id: 'confidence', label: 'Confidence' },
    { id: 'functions', label: 'Functions' },
    { id: 'architecture', label: 'Architecture' },
    { id: 'graph', label: 'File Graph' },
    { id: 'function-graph', label: 'Function Graph' },
    { id: 'snapshots', label: 'Snapshots' }
  ];

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <h1 style={styles.title}>🏗️ {displayText}</h1>
        <p style={styles.subtitle}>Architectural Recovery & Semantic Synthesis Platform</p>
        {currentRepoName && (
          <div style={styles.repoIndicator}>
            📦 Active: {currentRepoName}
          </div>
        )}
      </header>

      <nav style={styles.nav}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              ...styles.tab,
              ...(activeTab === tab.id ? styles.activeTab : {})
            }}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main style={styles.main}>
        {activeTab === 'analyze' && <AnalyzeRepo onAnalysisComplete={handleAnalysisComplete} />}
        {activeTab === 'repositories' && <RepositoryManager key={refreshKey} onRepoSelect={handleRepoSelect} />}
        {activeTab === 'patterns' && <PatternDetection key={refreshKey} repoId={currentRepoId} />}
        {activeTab === 'coupling' && <CouplingAnalysis key={refreshKey} repoId={currentRepoId} />}
        {activeTab === 'blast-radius' && <BlastRadius key={refreshKey} repoId={currentRepoId} />}
        {activeTab === 'impact' && <ImpactAnalysis />}
        {activeTab === 'confidence' && <ConfidenceReport key={refreshKey} repoId={currentRepoId} />}
        {activeTab === 'functions' && <FunctionAnalysis key={refreshKey} />}
        {activeTab === 'architecture' && <ArchitectureView key={refreshKey} repoId={currentRepoId} />}
        {activeTab === 'graph' && <DependencyGraph key={refreshKey} />}
        {activeTab === 'function-graph' && <FunctionGraph key={refreshKey} />}
        {activeTab === 'snapshots' && currentRepoId && <SnapshotComparison key={refreshKey} repoId={currentRepoId} />}
        {activeTab === 'snapshots' && !currentRepoId && (
          <div style={{textAlign: 'center', padding: '40px', color: '#666'}}>
            Please select a repository first from the Repositories tab
          </div>
        )}
      </main>

      <footer style={styles.footer}>
        <p>Backend API: http://localhost:8000 | Neo4j: http://localhost:7474</p>
      </footer>
    </div>
  );
}

const styles = {
  app: { minHeight: '100vh', background: '#f0f2f5', fontFamily: 'Arial, sans-serif' },
  header: { background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white', padding: '30px 20px', textAlign: 'center' },
  title: { margin: 0, fontSize: '36px', fontFamily: 'monospace', letterSpacing: '2px' },
  subtitle: { margin: '10px 0 0 0', fontSize: '16px', opacity: 0.9 },
  repoIndicator: { marginTop: '10px', padding: '8px 16px', background: 'rgba(255,255,255,0.2)', borderRadius: '20px', fontSize: '14px', display: 'inline-block' },
  nav: { display: 'flex', justifyContent: 'center', background: 'white', padding: '10px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' },
  tab: { padding: '10px 20px', margin: '0 5px', border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '14px', borderRadius: '4px', transition: 'all 0.3s' },
  activeTab: { background: '#667eea', color: 'white' },
  main: { maxWidth: '1200px', margin: '20px auto', padding: '0 20px' },
  footer: { textAlign: 'center', padding: '20px', color: '#666', fontSize: '12px' }
};

export default App;
