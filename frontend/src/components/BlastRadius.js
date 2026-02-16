import React, { useState, useRef } from 'react';
import { api } from '../services/api';
import Highlighter from './Highlighter';
import * as d3 from 'd3';

export default function BlastRadius({ repoId }) {
  const [filePath, setFilePath] = useState('');
  const [changeType, setChangeType] = useState('modify');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [files, setFiles] = useState([]);
  const svgRef = useRef();

  const loadFiles = async () => {
    try {
      const { data } = await api.getFiles(repoId);
      setFiles(data.files || []);
    } catch (error) {
      console.error(error);
    }
  };

  React.useEffect(() => {
    loadFiles();
  }, [repoId]);

  const analyze = async () => {
    if (!filePath) return;
    setLoading(true);
    try {
      const { data } = await api.getBlastRadius(filePath, changeType);
      setResult(data);
      if (data && !data.error) {
        setTimeout(() => renderGraph(data), 100);
      }
    } catch (error) {
      console.error(error);
      setResult({ error: 'Analysis failed' });
    }
    setLoading(false);
  };

  const renderGraph = (data) => {
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = 800;
    const height = 400;
    svg.attr('width', width).attr('height', height);

    const getFileName = (path) => {
      const parts = path.split(/[/\\]/);
      return parts.length >= 2 ? `${parts[parts.length - 2]}/${parts[parts.length - 1]}` : parts[parts.length - 1];
    };

    const nodes = [
      { id: 'target', label: getFileName(data.file), type: 'target' },
      ...data.direct_dependents.map(f => ({ id: f, label: getFileName(f), type: 'direct' })),
      ...data.indirect_dependents.slice(0, 10).map(f => ({ id: f, label: getFileName(f), type: 'indirect' }))
    ];

    const links = [
      ...data.direct_dependents.map(f => ({ source: f, target: 'target' })),
      ...data.indirect_dependents.slice(0, 10).map(f => ({ source: f, target: data.direct_dependents[0] || 'target' }))
    ];

    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2));

    const link = svg.append('g')
      .selectAll('line')
      .data(links)
      .enter().append('line')
      .attr('stroke', '#999')
      .attr('stroke-width', 2);

    const node = svg.append('g')
      .selectAll('circle')
      .data(nodes)
      .enter().append('circle')
      .attr('r', d => d.type === 'target' ? 12 : 8)
      .attr('fill', d => {
        if (d.type === 'target') return '#FF4444';
        if (d.type === 'direct') return '#FF8844';
        return '#FFBB44';
      });

    const label = svg.append('g')
      .selectAll('text')
      .data(nodes)
      .enter().append('text')
      .text(d => d.label)
      .attr('font-size', 10)
      .attr('dx', 12)
      .attr('dy', 4);

    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      node
        .attr('cx', d => d.x)
        .attr('cy', d => d.y);

      label
        .attr('x', d => d.x)
        .attr('y', d => d.y);
    });
  };

  const getRiskColor = (level) => {
    const colors = {
      critical: '#FF4444',
      high: '#FF8844',
      medium: '#FFBB44',
      low: '#44FF88'
    };
    return colors[level] || '#888';
  };

  return (
    <div style={styles.container}>
      <h2>Blast Radius Analyzer</h2>
      
      <div style={styles.controls}>
        <select 
          value={filePath} 
          onChange={(e) => setFilePath(e.target.value)}
          style={styles.select}
        >
          <option value="">Select file...</option>
          {files.filter(f => f).map(f => (
            <option key={f} value={f}>{f.split(/[/\\]/).pop()}</option>
          ))}
        </select>

        <select 
          value={changeType} 
          onChange={(e) => setChangeType(e.target.value)}
          style={styles.select}
        >
          <option value="modify">MODIFY</option>
          <option value="delete">DELETE</option>
          <option value="move">MOVE</option>
        </select>

        <button onClick={analyze} disabled={loading || !filePath} style={styles.btn}>
          {loading ? 'Analyzing...' : 'Analyze Impact'}
        </button>
      </div>

      {result && !result.error && (
        <>
          <div style={styles.graphContainer}>
            <h3>Dependency Graph</h3>
            <svg ref={svgRef} style={styles.svg}></svg>
            <div style={styles.legend}>
              <span><span style={{...styles.legendDot, background: '#FF4444'}}></span> Target File</span>
              <span><span style={{...styles.legendDot, background: '#FF8844'}}></span> Direct Dependents</span>
              <span><span style={{...styles.legendDot, background: '#FFBB44'}}></span> Indirect Dependents</span>
            </div>
          </div>

          <div style={styles.terminal}>
            <div style={styles.terminalHeader}>
              <div style={styles.terminalButtons}>
                <span style={{...styles.terminalButton, background: '#ff5f56'}}></span>
                <span style={{...styles.terminalButton, background: '#ffbd2e'}}></span>
                <span style={{...styles.terminalButton, background: '#27c93f'}}></span>
              </div>
              <div style={styles.terminalTitle}>blast-radius — {result.change_type}</div>
            </div>
            <div style={styles.terminalBody}>
              <div style={styles.line}>
                <Highlighter color="#FFED4A">CHANGE TYPE:</Highlighter> {result.change_type?.toUpperCase()}
              </div>
              <div style={styles.line}>
                <Highlighter color="#FFED4A">RISK LEVEL:</Highlighter>{' '}
                <span style={{color: getRiskColor(result.risk_level), fontWeight: 'bold'}}>
                  {result.risk_level?.toUpperCase()}
                </span>
                {result.risk_score && ` (${result.risk_score}/100)`}
              </div>
              <div style={styles.line}></div>

              <div style={styles.line}>
                <Highlighter color="#82FFAD">DIRECT DEPENDENTS:</Highlighter> {result.impact_breakdown?.direct_count || 0}
              </div>
              {result.direct_dependents?.slice(0, 5).map((f, i) => (
                <div key={i} style={styles.line}>  • {f ? f.split(/[/\\]/).slice(-2).join('/') : 'N/A'}</div>
              ))}
              {result.direct_dependents?.length > 5 && (
                <div style={styles.line}>  ... and {result.direct_dependents.length - 5} more</div>
              )}
              <div style={styles.line}></div>

              <div style={styles.line}>
                <Highlighter color="#FF8282">INDIRECT DEPENDENTS:</Highlighter> {result.impact_breakdown?.indirect_count || 0}
              </div>
              {result.indirect_dependents?.slice(0, 5).map((f, i) => (
                <div key={i} style={styles.line}>  • {f ? f.split(/[/\\]/).slice(-2).join('/') : 'N/A'}</div>
              ))}
              {result.indirect_dependents?.length > 5 && (
                <div style={styles.line}>  ... and {result.indirect_dependents.length - 5} more</div>
              )}
              <div style={styles.line}></div>

              {result.functions_affected?.total_functions > 0 && (
                <>
                  <div style={styles.line}>
                    <Highlighter color="#A78BFA">FUNCTIONS AFFECTED:</Highlighter> {result.functions_affected.total_functions}
                  </div>
                  {result.functions_affected.functions?.slice(0, 3).map((fn, i) => (
                    <div key={i} style={styles.line}>
                      • {fn.name} ({fn.caller_count} callers)
                    </div>
                  ))}
                  <div style={styles.line}></div>
                </>
              )}

              <div style={styles.line}>
                <Highlighter color="#FFED4A">TOTAL AFFECTED:</Highlighter> {result.total_affected || 0} files
              </div>
              
              {result.explanation && (
                <>
                  <div style={styles.line}></div>
                  <div style={styles.line}>
                    <Highlighter color="#A78BFA">EXPLANATION:</Highlighter>
                  </div>
                  <div style={styles.line}>{result.explanation}</div>
                </>
              )}
            </div>
          </div>
        </>
      )}

      {result?.error && (
        <div style={{...styles.terminal, borderColor: '#ff5f56'}}>
          <div style={styles.terminalBody}>
            <Highlighter color="#FF8282">Error: {result.error}</Highlighter>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  container: { padding: '20px', background: '#fff', borderRadius: '8px', marginBottom: '20px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' },
  controls: { display: 'flex', gap: '10px', marginBottom: '20px' },
  select: { flex: 1, padding: '8px', borderRadius: '4px', border: '1px solid #ddd', fontSize: '14px' },
  btn: { padding: '8px 16px', background: '#667eea', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '14px' },
  graphContainer: { marginBottom: '20px', padding: '20px', background: '#f9f9f9', borderRadius: '8px' },
  svg: { border: '1px solid #ddd', borderRadius: '4px', background: 'white' },
  legend: { display: 'flex', gap: '20px', marginTop: '10px', fontSize: '14px' },
  legendDot: { display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%', marginRight: '5px' },
  terminal: { borderRadius: '8px', overflow: 'hidden', boxShadow: '0 4px 12px rgba(0,0,0,0.15)' },
  terminalHeader: { background: '#e8e8e8', padding: '10px 15px', display: 'flex', alignItems: 'center', gap: '10px' },
  terminalButtons: { display: 'flex', gap: '8px' },
  terminalButton: { width: '12px', height: '12px', borderRadius: '50%' },
  terminalTitle: { color: '#666', fontSize: '13px', fontWeight: '500' },
  terminalBody: { background: '#f5f5f5', color: '#333', fontFamily: 'Monaco, Menlo, monospace', fontSize: '14px', padding: '20px', minHeight: '200px', lineHeight: '1.8' },
  line: { marginBottom: '2px' }
};
