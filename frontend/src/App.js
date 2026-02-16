import React, { useState, useEffect } from 'react';
import './App.css';
import AnalyzeRepo from './components/AnalyzeRepo';
import PatternDetection from './components/PatternDetection';
import CouplingAnalysis from './components/CouplingAnalysis';
import ImpactAnalysis from './components/ImpactAnalysis';
import ArchitectureView from './components/ArchitectureView';
import DependencyGraph from './components/DependencyGraph';
import FunctionAnalysis from './components/FunctionAnalysis';

function App() {
  const [activeTab, setActiveTab] = useState('analyze');
  const [refreshKey, setRefreshKey] = useState(0);
  const [displayText, setDisplayText] = useState('');

  const handleAnalysisComplete = () => {
    setRefreshKey(prev => prev + 1);
    setActiveTab('patterns');
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
    { id: 'patterns', label: 'Patterns' },
    { id: 'coupling', label: 'Coupling' },
    { id: 'impact', label: 'Impact' },
    { id: 'functions', label: 'Functions' },
    { id: 'architecture', label: 'Architecture' },
    { id: 'graph', label: 'Graph' }
  ];

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <h1 style={styles.title}>🏗️ {displayText}</h1>
        <p style={styles.subtitle}>Architectural Recovery & Semantic Synthesis Platform</p>
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
        {activeTab === 'patterns' && <PatternDetection key={refreshKey} />}
        {activeTab === 'coupling' && <CouplingAnalysis key={refreshKey} />}
        {activeTab === 'impact' && <ImpactAnalysis />}
        {activeTab === 'functions' && <FunctionAnalysis key={refreshKey} />}
        {activeTab === 'architecture' && <ArchitectureView key={refreshKey} />}
        {activeTab === 'graph' && <DependencyGraph key={refreshKey} />}
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
  nav: { display: 'flex', justifyContent: 'center', background: 'white', padding: '10px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' },
  tab: { padding: '10px 20px', margin: '0 5px', border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '14px', borderRadius: '4px', transition: 'all 0.3s' },
  activeTab: { background: '#667eea', color: 'white' },
  main: { maxWidth: '1200px', margin: '20px auto', padding: '0 20px' },
  footer: { textAlign: 'center', padding: '20px', color: '#666', fontSize: '12px' }
};

export default App;
