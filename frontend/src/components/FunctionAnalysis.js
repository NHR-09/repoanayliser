import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function FunctionAnalysis() {
  const [functions, setFunctions] = useState([]);
  const [selectedFunction, setSelectedFunction] = useState('');
  const [functionInfo, setFunctionInfo] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadFunctions();
  }, []);

  const loadFunctions = async () => {
    try {
      const { data } = await api.getFunctions();
      setFunctions(data.functions || []);
    } catch (error) {
      console.error(error);
    }
  };

  const analyzeFunction = async () => {
    if (!selectedFunction) return;
    setLoading(true);
    try {
      const { data } = await api.getFunctionInfo(selectedFunction);
      setFunctionInfo(data);
    } catch (error) {
      console.error(error);
      setFunctionInfo({ error: error.message });
    }
    setLoading(false);
  };

  const formatExplanation = (text) => {
    if (!text) return null;
    
    // Convert markdown-style formatting to HTML
    return text
      .split('\n')
      .map((line, idx) => {
        // Bold text: **text** or __text__
        line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        line = line.replace(/__(.+?)__/g, '<strong>$1</strong>');
        
        // Code: `code`
        line = line.replace(/`(.+?)`/g, '<code>$1</code>');
        
        // Headers: ## Header
        if (line.startsWith('####')) {
          return <h4 key={idx} style={styles.h4}>{line.replace(/####\s*/, '')}</h4>;
        } else if (line.startsWith('###')) {
          return <h4 key={idx} style={styles.h4}>{line.replace(/###\s*/, '')}</h4>;
        } else if (line.startsWith('##')) {
          return <h3 key={idx} style={styles.h3}>{line.replace(/##\s*/, '')}</h3>;
        } else if (line.startsWith('#')) {
          return <h2 key={idx} style={styles.h2}>{line.replace(/#\s*/, '')}</h2>;
        }
        
        // Numbered lists: 1. Item
        if (/^\d+\.\s/.test(line)) {
          return <div key={idx} style={styles.listItem} dangerouslySetInnerHTML={{ __html: line }} />;
        }
        
        // Bullet points: - Item or * Item
        if (/^[-*]\s/.test(line)) {
          return <div key={idx} style={styles.bulletItem} dangerouslySetInnerHTML={{ __html: line.replace(/^[-*]\s/, '• ') }} />;
        }
        
        // Regular paragraph
        if (line.trim()) {
          return <p key={idx} style={styles.paragraph} dangerouslySetInnerHTML={{ __html: line }} />;
        }
        
        return <br key={idx} />;
      });
  };

  return (
    <div style={styles.container}>
      <h2>Function Analysis</h2>
      
      <div style={styles.inputSection}>
        <select 
          value={selectedFunction} 
          onChange={(e) => setSelectedFunction(e.target.value)}
          style={styles.select}
        >
          <option value="">Select a function...</option>
          {functions.map((fn, idx) => (
            <option key={idx} value={fn.name}>
              {fn.name} ({fn.file})
            </option>
          ))}
        </select>
        <button onClick={analyzeFunction} disabled={loading || !selectedFunction} style={styles.button}>
          {loading ? 'Analyzing...' : 'Analyze Function'}
        </button>
      </div>

      {functionInfo && !functionInfo.error && (
        <div style={styles.result}>
          <h3>Function: {functionInfo.function_name}</h3>
          
          <div style={styles.section}>
            <strong>Location:</strong> {functionInfo.file} (line {functionInfo.line})
          </div>

          <div style={styles.section}>
            <h4>Called By ({functionInfo.usage_count} locations)</h4>
            {functionInfo.callers && functionInfo.callers.length > 0 ? (
              functionInfo.callers.map((caller, idx) => (
                <div key={idx} style={styles.caller}>
                  <strong>{caller.caller_name}</strong> in {caller.caller_file}
                  {caller.line > 0 && ` (line ${caller.line})`}
                </div>
              ))
            ) : (
              <p style={styles.noData}>No callers found (function may be unused or calls not tracked)</p>
            )}
          </div>

          <div style={styles.section}>
            <h4>AI Explanation</h4>
            <div style={styles.explanation}>
              {formatExplanation(functionInfo.explanation)}
            </div>
          </div>

          {functionInfo.related_code && functionInfo.related_code.length > 0 && (
            <div style={styles.section}>
              <h4>Related Code Context</h4>
              {functionInfo.related_code.map((code, idx) => (
                <div key={idx} style={styles.relatedCode}>
                  <strong>{code.metadata.file_path}</strong>
                  <pre style={styles.code}>{code.code}</pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {functionInfo && functionInfo.error && (
        <div style={styles.error}>
          Error: {functionInfo.error}
        </div>
      )}
    </div>
  );
}

const styles = {
  container: { padding: '20px', background: '#fff', borderRadius: '8px', marginBottom: '20px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' },
  inputSection: { display: 'flex', gap: '10px', marginBottom: '20px' },
  select: { flex: 1, padding: '10px', fontSize: '14px', borderRadius: '4px', border: '1px solid #ddd' },
  button: { padding: '10px 20px', background: '#667eea', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' },
  result: { marginTop: '20px' },
  section: { marginBottom: '20px', padding: '15px', background: '#f9f9f9', borderRadius: '6px' },
  caller: { padding: '8px', background: '#fff', borderRadius: '4px', marginBottom: '5px', border: '1px solid #e0e0e0' },
  noData: { color: '#666', fontStyle: 'italic' },
  explanation: { padding: '15px', background: '#e7f3ff', borderRadius: '4px', lineHeight: '1.8' },
  h2: { fontSize: '20px', fontWeight: 'bold', marginTop: '15px', marginBottom: '10px', color: '#333' },
  h3: { fontSize: '18px', fontWeight: 'bold', marginTop: '12px', marginBottom: '8px', color: '#444' },
  h4: { fontSize: '16px', fontWeight: 'bold', marginTop: '10px', marginBottom: '6px', color: '#555' },
  paragraph: { marginBottom: '10px', lineHeight: '1.6' },
  listItem: { marginLeft: '20px', marginBottom: '8px', lineHeight: '1.6' },
  bulletItem: { marginLeft: '20px', marginBottom: '6px', lineHeight: '1.6' },
  relatedCode: { marginBottom: '15px', padding: '10px', background: '#fff', borderRadius: '4px', border: '1px solid #e0e0e0' },
  code: { background: '#f5f5f5', padding: '10px', borderRadius: '4px', overflow: 'auto', fontSize: '12px' },
  error: { padding: '15px', background: '#f8d7da', color: '#721c24', borderRadius: '4px', marginTop: '20px' }
};
