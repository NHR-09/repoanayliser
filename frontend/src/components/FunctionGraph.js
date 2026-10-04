import React, { useEffect, useMemo, useRef, useState } from 'react';
import * as d3 from 'd3';
import { api } from '../services/api';
import SearchableTreeSelect from './SearchableTreeSelect';

const functionValue = (fn) => `${fn.file || ''}::${fn.name}::${fn.line || 0}`;

export default function FunctionGraph({ repoId }) {
  const svgRef = useRef();
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(false);
  const [selectedFunction, setSelectedFunction] = useState('');
  const [functions, setFunctions] = useState([]);

  useEffect(() => {
    loadFunctions();
    loadFunctionGraph();
  }, [repoId]);

  useEffect(() => {
    if (!loading && svgRef.current) return renderGraph(graphData);
    return undefined;
  }, [graphData, loading]);

  const loadFunctions = async () => {
    try {
      const { data } = await api.getFunctions(repoId);
      setFunctions(data.functions || []);
    } catch (error) {
      console.error('Failed to load functions:', error);
    }
  };

  const loadFunctionGraph = async () => {
    setLoading(true);
    try {
      const { data } = await api.getFunctionGraph(repoId);
      setGraphData(data);
    } catch (error) {
      console.error(error);
    }
    setLoading(false);
  };

  const loadFunctionCallChain = async (fn) => {
    setLoading(true);
    try {
      const { data } = await api.getFunctionCallChain(fn.name, repoId, fn.file);
      setGraphData(data);
    } catch (error) {
      console.error(error);
    }
    setLoading(false);
  };

  const handleFunctionSelect = (nextValue) => {
    setSelectedFunction(nextValue);
    const selected = functions.find(fn => functionValue(fn) === nextValue);
    if (selected) {
      loadFunctionCallChain(selected);
    } else {
      loadFunctionGraph();
    }
  };

  const renderGraph = (data) => {
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    if (!data.nodes || data.nodes.length === 0) return undefined;

    const width = 900;
    const height = 600;

    const graphNodes = data.nodes.map(node => ({ ...node }));
    const graphEdges = data.edges.map(edge => ({
      ...edge,
      source: typeof edge.source === 'object' ? edge.source.id : edge.source,
      target: typeof edge.target === 'object' ? edge.target.id : edge.target
    }));

    svg.attr('viewBox', `0 0 ${width} ${height}`).attr('height', height);
    const g = svg.append('g');

    const degree = new Map(graphNodes.map(node => [node.id, 0]));
    graphEdges.forEach(edge => {
      degree.set(edge.source, (degree.get(edge.source) || 0) + 1);
      degree.set(edge.target, (degree.get(edge.target) || 0) + 1);
    });
    const isTinyGraph = graphNodes.length <= 4;
    const linkDistance = isTinyGraph ? 82 : Math.min(125, 76 + Math.sqrt(graphNodes.length) * 4);
    const baseCharge = isTinyGraph ? -85 : Math.max(-260, -105 - graphNodes.length * 2.5);

    const simulation = d3.forceSimulation(graphNodes)
      .force('link', d3.forceLink(graphEdges).id(d => d.id).distance(linkDistance).strength(0.75))
      .force('charge', d3.forceManyBody().strength(d => (degree.get(d.id) || 0) === 0 ? -25 : baseCharge))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('x', d3.forceX(width / 2).strength(isTinyGraph ? 0.16 : 0.045))
      .force('y', d3.forceY(height / 2).strength(isTinyGraph ? 0.16 : 0.045))
      .force('collision', d3.forceCollide().radius(isTinyGraph ? 28 : 36));

    const defs = svg.append('defs');
    defs.append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '-0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('orient', 'auto')
      .attr('markerWidth', 8)
      .attr('markerHeight', 8)
      .append('svg:path')
      .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
      .attr('fill', '#52525b');

    const link = g.append('g')
      .selectAll('line')
      .data(graphEdges)
      .enter()
      .append('line')
      .attr('stroke', '#3f3f46')
      .attr('stroke-width', 1.5)
      .attr('stroke-opacity', 0.5)
      .attr('marker-end', 'url(#arrowhead)');

    const node = g.append('g')
      .selectAll('circle')
      .data(graphNodes)
      .enter()
      .append('circle')
      .attr('r', d => d.focus ? 13 : d.type === 'function' ? 9 : 7)
      .attr('fill', d => d.focus ? '#60a5fa' : d.type === 'function' ? '#fbbf24' : '#a1a1aa')
      .attr('stroke', d => d.type === 'function' ? '#92400e' : '#52525b')
      .attr('stroke-width', 1.5)
      .call(d3.drag()
        .on('start', dragStarted)
        .on('drag', dragged)
        .on('end', dragEnded));

    node.append('title')
      .text(d => `${d.label}\n${d.file || ''}\n${d.line ? 'Line: ' + d.line : ''}`);

    const labels = g.append('g')
      .selectAll('text')
      .data(graphNodes)
      .enter()
      .append('text')
      .text(d => d.label)
      .attr('font-size', 10)
      .attr('font-family', 'Inter, sans-serif')
      .attr('font-weight', d => d.type === 'function' ? '600' : '400')
      .attr('fill', d => d.type === 'function' ? '#e4e4e7' : '#71717a')
      .attr('dx', 12)
      .attr('dy', 4);

    // Build adjacency map for quick neighbor lookup
    const neighbors = new Map();
    graphEdges.forEach(e => {
      const sId = typeof e.source === 'object' ? e.source.id : e.source;
      const tId = typeof e.target === 'object' ? e.target.id : e.target;
      if (!neighbors.has(sId)) neighbors.set(sId, new Set());
      if (!neighbors.has(tId)) neighbors.set(tId, new Set());
      neighbors.get(sId).add(tId);
      neighbors.get(tId).add(sId);
    });

    let selectedNode = null;

    const resetHighlight = () => {
      selectedNode = null;
      node.transition().duration(300)
        .attr('fill', d => d.type === 'function' ? '#fbbf24' : '#a1a1aa')
        .attr('stroke', d => d.type === 'function' ? '#92400e' : '#52525b')
        .attr('stroke-width', 1.5)
        .attr('r', d => d.type === 'function' ? 9 : 7)
        .attr('opacity', 1);
      link.transition().duration(300)
        .attr('stroke', '#3f3f46')
        .attr('stroke-width', 1.5)
        .attr('stroke-opacity', 0.5);
      labels.transition().duration(300)
        .attr('fill', d => d.type === 'function' ? '#e4e4e7' : '#71717a')
        .attr('opacity', 1)
        .attr('font-weight', d => d.type === 'function' ? '600' : '400');
    };

    const highlightNode = (event, d) => {
      event.stopPropagation();
      if (selectedNode === d.id) { resetHighlight(); return; }
      selectedNode = d.id;
      const connectedIds = neighbors.get(d.id) || new Set();

      node.transition().duration(300)
        .attr('opacity', n => n.id === d.id || connectedIds.has(n.id) ? 1 : 0.08)
        .attr('fill', n => {
          if (n.id === d.id) return '#60a5fa';
          return n.type === 'function' ? '#fbbf24' : '#a1a1aa';
        })
        .attr('stroke', n => n.id === d.id ? '#3b82f6' : n.type === 'function' ? '#92400e' : '#52525b')
        .attr('stroke-width', n => n.id === d.id ? 3 : 1.5)
        .attr('r', n => n.id === d.id ? 12 : n.type === 'function' ? 9 : 7);

      link.transition().duration(300)
        .attr('stroke', l => {
          const sId = typeof l.source === 'object' ? l.source.id : l.source;
          const tId = typeof l.target === 'object' ? l.target.id : l.target;
          return (sId === d.id || tId === d.id) ? '#60a5fa' : '#3f3f46';
        })
        .attr('stroke-width', l => {
          const sId = typeof l.source === 'object' ? l.source.id : l.source;
          const tId = typeof l.target === 'object' ? l.target.id : l.target;
          return (sId === d.id || tId === d.id) ? 2.5 : 1;
        })
        .attr('stroke-opacity', l => {
          const sId = typeof l.source === 'object' ? l.source.id : l.source;
          const tId = typeof l.target === 'object' ? l.target.id : l.target;
          return (sId === d.id || tId === d.id) ? 1 : 0.05;
        });

      labels.transition().duration(300)
        .attr('opacity', n => n.id === d.id || connectedIds.has(n.id) ? 1 : 0.08)
        .attr('fill', n => n.id === d.id ? '#fafafa' : connectedIds.has(n.id) ? (n.type === 'function' ? '#e4e4e7' : '#a1a1aa') : '#71717a')
        .attr('font-weight', n => n.id === d.id ? '700' : n.type === 'function' ? '600' : '400');
    };

    node.on('click', highlightNode);
    svg.on('click', () => { if (selectedNode) resetHighlight(); });

    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => { g.attr('transform', event.transform); });
    svg.call(zoom);

    const fitTimer = setTimeout(() => {
      try {
        const bounds = g.node().getBBox();
        const fullWidth = bounds.width;
        const fullHeight = bounds.height;
        const midX = bounds.x + fullWidth / 2;
        const midY = bounds.y + fullHeight / 2;
        if (fullWidth > 0 && fullHeight > 0) {
          const scale = Math.min(isTinyGraph ? 1.35 : 1.8, 0.78 / Math.max(fullWidth / width, fullHeight / height));
          const translate = [width / 2 - scale * midX, height / 2 - scale * midY];
          svg.transition().duration(750).call(
            zoom.transform,
            d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
          );
        }
      } catch (e) {
        console.log('Auto-fit skipped:', e.message);
      }
    }, 500);

    simulation.on('tick', () => {
      link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
      node.attr('cx', d => d.x).attr('cy', d => d.y);
      labels.attr('x', d => d.x).attr('y', d => d.y);
    });

    function dragStarted(event, d) { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }
    function dragged(event, d) { d.fx = event.x; d.fy = event.y; }
    function dragEnded(event, d) { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }

    return () => {
      clearTimeout(fitTimer);
      simulation.stop();
    };
  };

  const functionItems = useMemo(() => functions.map(fn => ({
    value: functionValue(fn),
    label: fn.name,
    path: fn.file || 'unknown',
    secondary: fn.line ? `L${fn.line}` : ''
  })), [functions]);

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loaderWrapper}>
          <div style={styles.spinner}></div>
          <p style={styles.loadingText}>Loading function graph…</p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.heading}>Function Call Graph</h2>
        <div style={styles.selectorWrap}>
          <SearchableTreeSelect
            items={functionItems}
            value={selectedFunction}
            onChange={handleFunctionSelect}
            placeholder="All Functions"
            searchPlaceholder="Search functions or file paths…"
            groupByFile
            emptyOption="All Functions"
          />
        </div>
      </div>
      <div style={styles.legend}>
        <span style={styles.legendItem}>
          <span style={{ ...styles.legendDot, background: '#fbbf24' }}></span> Functions
        </span>
        <span style={styles.legendItem}>
          <span style={{ ...styles.legendDot, background: '#a1a1aa' }}></span> Files
        </span>
      </div>
      {graphData.nodes.length === 0 ? (
        <div style={styles.emptyState}>
          <span style={{ fontSize: '32px', display: 'block', marginBottom: '12px' }}>⬣</span>
          <p style={styles.emptyText}>No function call data available</p>
          <p style={styles.emptyHint}>Analyze a repository first to see function relationships</p>
        </div>
      ) : (
        <>
          <div style={styles.stats}>
            <span style={styles.statBadge}>{graphData.nodes.length} nodes</span>
            <span style={styles.statBadge}>{graphData.edges.length} edges</span>
          </div>
          <svg ref={svgRef} style={styles.svg}></svg>
        </>
      )}
    </div>
  );
}

const styles = {
  container: { padding: '28px', background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', marginBottom: '20px' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' },
  heading: { margin: 0, fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)' },
  selectorWrap: { width: '420px', maxWidth: '60%' },
  legend: { display: 'flex', gap: '16px', marginBottom: '12px', fontSize: '12px', color: 'var(--text-muted)' },
  legendItem: { display: 'flex', alignItems: 'center', gap: '6px' },
  legendDot: { width: '10px', height: '10px', borderRadius: '50%', display: 'inline-block' },
  stats: { display: 'flex', gap: '8px', marginBottom: '12px' },
  statBadge: { padding: '4px 10px', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: '10px', fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' },
  svg: { width: '100%', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', background: 'var(--bg-primary)' },
  loaderWrapper: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '400px' },
  spinner: { width: '40px', height: '40px', border: '3px solid var(--border)', borderTop: '3px solid var(--text-secondary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' },
  loadingText: { marginTop: '16px', color: 'var(--text-muted)', fontSize: '14px' },
  emptyState: { textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' },
  emptyText: { fontSize: '16px', fontWeight: 600, marginBottom: '6px', color: 'var(--text-secondary)' },
  emptyHint: { fontSize: '13px', color: 'var(--text-muted)' },
};
