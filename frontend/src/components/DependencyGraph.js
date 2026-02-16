import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { api } from '../services/api';

export default function DependencyGraph() {
  const svgRef = useRef();
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadGraphData();
  }, []);

  const loadGraphData = async () => {
    setLoading(true);
    try {
      const { data } = await api.getGraphData();
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

    const width = 800;
    const height = 600;

    svg.attr('width', width).attr('height', height);
    
    const g = svg.append('g');

    const simulation = d3.forceSimulation(data.nodes)
      .force('link', d3.forceLink(data.edges).id(d => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(40));

    // Draw edges
    const link = g.append('g')
      .selectAll('line')
      .data(data.edges)
      .enter()
      .append('line')
      .attr('stroke', '#999')
      .attr('stroke-width', 2)
      .attr('stroke-opacity', 0.6);

    // Draw nodes
    const node = g.append('g')
      .selectAll('circle')
      .data(data.nodes)
      .enter()
      .append('circle')
      .attr('r', 8)
      .attr('fill', '#667eea')
      .call(d3.drag()
        .on('start', dragStarted)
        .on('drag', dragged)
        .on('end', dragEnded));

    // Draw labels
    const labels = g.append('g')
      .selectAll('text')
      .data(data.nodes)
      .enter()
      .append('text')
      .text(d => d.label)
      .attr('font-size', 10)
      .attr('dx', 12)
      .attr('dy', 4);
    
    // Add zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });
    
    svg.call(zoom);
    
    // Fit to view on load
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
          <p style={styles.loadingText}>Loading dependency graph...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <h2>Dependency Graph</h2>
      <p>Nodes: {graphData.nodes.length} | Edges: {graphData.edges.length}</p>
      <svg ref={svgRef} style={styles.svg}></svg>
    </div>
  );
}

const styles = {
  container: { padding: '20px', background: '#fff', borderRadius: '8px', marginBottom: '20px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' },
  svg: { border: '1px solid #ddd', borderRadius: '4px', background: '#fafafa' },
  loaderWrapper: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '400px' },
  spinner: {
    width: '50px',
    height: '50px',
    border: '5px solid #f3f3f3',
    borderTop: '5px solid #667eea',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite'
  },
  loadingText: { marginTop: '20px', color: '#666', fontSize: '16px' }
};
