import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { api } from '../services/api';

export default function DependencyGraph({ repoId }) {
  const svgRef = useRef();
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadGraphData();
  }, [repoId]);

  const loadGraphData = async () => {
    setLoading(true);
    try {
      const { data } = await api.getGraphData(repoId);
      setGraphData(data);
      renderGraph(data);
    } catch (error) {
      console.error(error);
    }
    setLoading(false);
  };

  const renderGraph = (data) => {
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = 900;
    const height = 600;

    svg.attr('width', width).attr('height', height);

    const g = svg.append('g');

    const simulation = d3.forceSimulation(data.nodes)
      .force('link', d3.forceLink(data.edges).id(d => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(40));

    const link = g.append('g')
      .selectAll('line')
      .data(data.edges)
      .enter()
      .append('line')
      .attr('stroke', '#3f3f46')
      .attr('stroke-width', 1.5)
      .attr('stroke-opacity', 0.5);

    const node = g.append('g')
      .selectAll('circle')
      .data(data.nodes)
      .enter()
      .append('circle')
      .attr('r', 7)
      .attr('fill', '#a1a1aa')
      .attr('stroke', '#52525b')
      .attr('stroke-width', 1)
      .call(d3.drag()
        .on('start', dragStarted)
        .on('drag', dragged)
        .on('end', dragEnded));

    const labels = g.append('g')
      .selectAll('text')
      .data(data.nodes)
      .enter()
      .append('text')
      .text(d => d.label)
      .attr('font-size', 10)
      .attr('font-family', 'Inter, sans-serif')
      .attr('fill', '#71717a')
      .attr('dx', 12)
      .attr('dy', 4);

    // Build adjacency map for quick neighbor lookup
    const neighbors = new Map();
    data.edges.forEach(e => {
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
        .attr('fill', '#a1a1aa')
        .attr('stroke', '#52525b')
        .attr('stroke-width', 1)
        .attr('r', 7)
        .attr('opacity', 1);
      link.transition().duration(300)
        .attr('stroke', '#3f3f46')
        .attr('stroke-width', 1.5)
        .attr('stroke-opacity', 0.5);
      labels.transition().duration(300)
        .attr('fill', '#71717a')
        .attr('opacity', 1)
        .attr('font-weight', '400');
    };

    const highlightNode = (event, d) => {
      event.stopPropagation();
      if (selectedNode === d.id) { resetHighlight(); return; }
      selectedNode = d.id;
      const connectedIds = neighbors.get(d.id) || new Set();

      node.transition().duration(300)
        .attr('opacity', n => n.id === d.id || connectedIds.has(n.id) ? 1 : 0.08)
        .attr('fill', n => n.id === d.id ? '#60a5fa' : connectedIds.has(n.id) ? '#a1a1aa' : '#a1a1aa')
        .attr('stroke', n => n.id === d.id ? '#3b82f6' : '#52525b')
        .attr('stroke-width', n => n.id === d.id ? 2.5 : 1)
        .attr('r', n => n.id === d.id ? 10 : 7);

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
        .attr('fill', n => n.id === d.id ? '#fafafa' : connectedIds.has(n.id) ? '#a1a1aa' : '#71717a')
        .attr('font-weight', n => n.id === d.id ? '700' : '400');
    };

    node.on('click', highlightNode);
    svg.on('click', () => { if (selectedNode) resetHighlight(); });

    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);

    setTimeout(() => {
      try {
        const bounds = g.node().getBBox();
        const fullWidth = bounds.width;
        const fullHeight = bounds.height;
        const midX = bounds.x + fullWidth / 2;
        const midY = bounds.y + fullHeight / 2;

        if (fullWidth > 0 && fullHeight > 0) {
          const scale = 0.8 / Math.max(fullWidth / width, fullHeight / height);
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
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      node
        .attr('cx', d => d.x)
        .attr('cy', d => d.y);

      labels
        .attr('x', d => d.x)
        .attr('y', d => d.y);
    });

    function dragStarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragEnded(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loaderWrapper}>
          <div style={styles.spinner}></div>
          <p style={styles.loadingText}>Loading dependency graph…</p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.headerBar}>
        <h2 style={styles.heading}>Dependency Graph</h2>
        <div style={styles.stats}>
          <span style={styles.statBadge}>{graphData.nodes.length} nodes</span>
          <span style={styles.statBadge}>{graphData.edges.length} edges</span>
        </div>
      </div>
      <svg ref={svgRef} style={styles.svg}></svg>
    </div>
  );
}

const styles = {
  container: { padding: '28px', background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', marginBottom: '20px' },
  headerBar: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' },
  heading: { margin: 0, fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)' },
  stats: { display: 'flex', gap: '8px' },
  statBadge: { padding: '4px 10px', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: '10px', fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' },
  svg: { width: '100%', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', background: 'var(--bg-primary)' },
  loaderWrapper: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '400px' },
  spinner: { width: '40px', height: '40px', border: '3px solid var(--border)', borderTop: '3px solid var(--text-secondary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' },
  loadingText: { marginTop: '16px', color: 'var(--text-muted)', fontSize: '14px' },
};
