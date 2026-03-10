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
      const { data } = await api.getBlastRadius(filePath, changeType, repoId);
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
    const width = 800, height = 400;
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

    svg.append('g').selectAll('line').data(links).enter().append('line')
      .attr('stroke', '#3f3f46').attr('stroke-width', 1.5);

    const node = svg.append('g').selectAll('circle').data(nodes).enter().append('circle')
      .attr('r', d => d.type === 'target' ? 11 : 7)
      .attr('fill', d => d.type === 'target' ? '#f87171' : d.type === 'direct' ? '#fbbf24' : '#71717a')
      .attr('stroke', '#27272a').attr('stroke-width', 1);

    const label = svg.append('g').selectAll('text').data(nodes).enter().append('text')
      .text(d => d.label).attr('font-size', 10).attr('fill', '#a1a1aa')
      .attr('font-family', 'Inter, sans-serif').attr('dx', 12).attr('dy', 4);

    simulation.on('tick', () => {
      svg.selectAll('line').attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
      node.attr('cx', d => d.x).attr('cy', d => d.y);
      label.attr('x', d => d.x).attr('y', d => d.y);
    });
  };

  const getRiskColor = (level) => {
    const colors = { critical: '#f87171', high: '#fb923c', medium: '#fbbf24', low: '#4ade80' };
    return colors[level] || 'var(--text-muted)';
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.heading}>Blast Radius Analyzer</h2>

      <div style={styles.controls}>
        <select value={filePath} onChange={(e) => setFilePath(e.target.value)} style={styles.select}>
          <option value="">Select file…</option>
          {files.filter(f => f).map(f => (
            <option key={f} value={f}>{f.split(/[/\\]/).pop()}</option>
          ))}
        </select>
        <select value={changeType} onChange={(e) => setChangeType(e.target.value)} style={{ ...styles.select, flex: 'none', width: '120px' }}>
          <option value="modify">MODIFY</option>
          <option value="delete">DELETE</option>
          <option value="move">MOVE</option>
        </select>
        <button onClick={analyze} disabled={loading || !filePath} style={styles.btn}>
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>

      {result && !result.error && (
        <>
          <div style={styles.graphContainer}>
            <h3 style={styles.sectionHeading}>Dependency Graph</h3>
            <svg ref={svgRef} style={styles.svg}></svg>
            <div style={styles.legend}>
              <span style={styles.legendItem}><span style={{ ...styles.legendDot, background: '#f87171' }}></span> Target</span>
              <span style={styles.legendItem}><span style={{ ...styles.legendDot, background: '#fbbf24' }}></span> Direct</span>
              <span style={styles.legendItem}><span style={{ ...styles.legendDot, background: '#71717a' }}></span> Indirect</span>
            </div>
          </div>

          <div style={styles.terminal}>
            <div style={styles.terminalHeader}>
              <div style={styles.terminalButtons}>
                <span style={{ ...styles.terminalButton, background: '#ff5f56' }}></span>
                <span style={{ ...styles.terminalButton, background: '#ffbd2e' }}></span>
                <span style={{ ...styles.terminalButton, background: '#27c93f' }}></span>
              </div>
              <div style={styles.terminalTitle}>blast-radius — {result.change_type}</div>
            </div>
            <div style={styles.terminalBody}>
              <div style={styles.line}><Highlighter color="#fbbf24">CHANGE TYPE:</Highlighter> {result.change_type?.toUpperCase()}</div>
              <div style={styles.line}>
                <Highlighter color="#fbbf24">RISK LEVEL:</Highlighter>{' '}
                <span style={{ color: getRiskColor(result.risk_level), fontWeight: 'bold' }}>
                  {result.risk_level?.toUpperCase()}
                </span>
                {result.risk_score && ` (${result.risk_score}/100)`}
              </div>
              <div style={styles.line}></div>
              <div style={styles.line}><Highlighter color="#4ade80">DIRECT DEPENDENTS:</Highlighter> {result.impact_breakdown?.direct_count || 0}</div>
              {result.direct_dependents?.slice(0, 5).map((f, i) => (
                <div key={i} style={styles.line}>  • {f ? f.split(/[/\\]/).slice(-2).join('/') : 'N/A'}</div>
              ))}
              {result.direct_dependents?.length > 5 && <div style={styles.line}>  … and {result.direct_dependents.length - 5} more</div>}
              <div style={styles.line}></div>
              <div style={styles.line}><Highlighter color="#f87171">INDIRECT DEPENDENTS:</Highlighter> {result.impact_breakdown?.indirect_count || 0}</div>
              {result.indirect_dependents?.slice(0, 5).map((f, i) => (
                <div key={i} style={styles.line}>  • {f ? f.split(/[/\\]/).slice(-2).join('/') : 'N/A'}</div>
              ))}
              {result.indirect_dependents?.length > 5 && <div style={styles.line}>  … and {result.indirect_dependents.length - 5} more</div>}
              <div style={styles.line}></div>
              {result.functions_affected?.total_functions > 0 && (
                <>
                  <div style={styles.line}><Highlighter color="#a78bfa">FUNCTIONS AFFECTED:</Highlighter> {result.functions_affected.total_functions}</div>
                  {result.functions_affected.functions?.slice(0, 3).map((fn, i) => (
                    <div key={i} style={styles.line}>  • {fn.name} ({fn.caller_count} callers)</div>
                  ))}
                  <div style={styles.line}></div>
                </>
              )}
              <div style={styles.line}><Highlighter color="#fbbf24">TOTAL AFFECTED:</Highlighter> {result.total_affected || 0} files</div>
              {result.structural_risk && result.structural_risk.score > 0 && (
                <>
                  <div style={styles.line}></div>
                  <div style={styles.line}>
                    <Highlighter color="#c084fc">STRUCTURAL RISK:</Highlighter>{' '}
                    <span style={{ color: getRiskColor(result.structural_risk.level), fontWeight: 'bold' }}>
                      {result.structural_risk.level?.toUpperCase()}
                    </span>{` (${result.structural_risk.score}/100)`}
                  </div>
                  <div style={styles.line}>  ↓ Fan-in: {result.structural_risk.fan_in} <span style={{ color: result.structural_risk.fan_in > 5 ? '#fb923c' : '#4ade80' }}>{result.structural_risk.fan_in > 5 ? '⚠ HIGH' : '✓'}</span></div>
                  <div style={styles.line}>  ↑ Fan-out: {result.structural_risk.fan_out} <span style={{ color: result.structural_risk.fan_out > 5 ? '#fb923c' : '#4ade80' }}>{result.structural_risk.fan_out > 5 ? '⚠ HIGH' : '✓'}</span></div>
                  {result.structural_risk.in_cycle && <div style={styles.line}>  <span style={{ color: '#f87171' }}>CIRCULAR DEPENDENCY DETECTED (+30 risk)</span></div>}
                </>
              )}
              {result.explanation && (
                <>
                  <div style={styles.line}></div>
                  <div style={styles.line}><Highlighter color="#a78bfa">EXPLANATION:</Highlighter></div>
                  <div style={styles.line}>{result.explanation}</div>
                </>
              )}
            </div>
          </div>
        </>
      )}

      {result?.error && (
        <div style={{ ...styles.terminal, borderColor: 'var(--red)' }}>
          <div style={styles.terminalBody}>
            <Highlighter color="#f87171">Error: {result.error}</Highlighter>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  container: { padding: '28px', background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', marginBottom: '20px' },
  heading: { margin: '0 0 20px', fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)' },
  controls: { display: 'flex', gap: '10px', marginBottom: '20px' },
  select: { flex: 1, padding: '10px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', background: 'var(--bg-input)', color: 'var(--text-primary)', fontSize: '13px' },
  btn: { padding: '10px 22px', background: 'var(--text-primary)', color: 'var(--bg-primary)', border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontWeight: 600, fontSize: '13px', whiteSpace: 'nowrap' },
  graphContainer: { marginBottom: '20px', padding: '20px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' },
  sectionHeading: { margin: '0 0 12px', fontSize: '14px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' },
  svg: { width: '100%', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', background: 'var(--bg-primary)' },
  legend: { display: 'flex', gap: '16px', marginTop: '10px', fontSize: '12px', color: 'var(--text-muted)' },
  legendItem: { display: 'flex', alignItems: 'center', gap: '6px' },
  legendDot: { display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%' },
  terminal: { borderRadius: 'var(--radius-md)', overflow: 'hidden', border: '1px solid var(--border)' },
  terminalHeader: { background: 'var(--bg-elevated)', padding: '10px 15px', display: 'flex', alignItems: 'center', gap: '10px', borderBottom: '1px solid var(--border)' },
  terminalButtons: { display: 'flex', gap: '7px' },
  terminalButton: { width: '11px', height: '11px', borderRadius: '50%' },
  terminalTitle: { color: 'var(--text-muted)', fontSize: '12px', fontFamily: 'var(--font-mono)', fontWeight: 500 },
  terminalBody: { background: 'var(--bg-primary)', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: '13px', padding: '20px', minHeight: '200px', lineHeight: '1.9' },
  line: { marginBottom: '1px' },
};
