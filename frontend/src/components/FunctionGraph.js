import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { api } from '../services/api';

export default function FunctionGraph() {
  const svgRef = useRef();
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(false);
  const [selectedFunction, setSelectedFunction] = useState('');
  const [functions, setFunctions] = useState([]);

  useEffect(() => {
    loadFunctions();
    loadFunctionGraph();
  }, []);

  const loadFunctions = async () => {
    try {
      const { data } = await api.getFunctions();
      setFunctions(data.functions || []);
    } catch (error) {
      console.error('Failed to load functions:', error);
    }
  };

  const loadFunctionGraph = async () => {
    setLoading(true);
    try {
      const { data } = await api.getFunctionGraph();
      setGraphData(data);
      renderGraph(data);
    } catch (error) {
      console.error(error);
    }
    setLoading(false);
  };

  const loadFunctionCallChain = async (funcName) => {
    setLoading(true);
    try {
      const { data } = await api.getFunctionCallChain(funcName);
      setGraphData(data);
      renderGraph(data);
    } catch (error) {
      console.error(error);
    }
    setLoading(false);
  };

  const handleFunctionSelect = (e) => {
    const funcName = e.target.value;
    setSelectedFunction(funcName);
    if (funcName) {
      loadFunctionCallChain(funcName);
    } else {
      loadFunctionGraph();
    }
  };

  const renderGraph = (data) => {
    if (!data.nodes || data.nodes.length === 0) {
      return;
    }

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = 800;
    const height = 600;

    svg.attr('width', width).attr('height', height);
    
    const g = svg.append('g');

    const simulation = d3.forceSimulation(data.nodes)
      .force('link', d3.forceLink(data.edges).id(d => d.id).distance(150))
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(50));

    // Draw edges with arrows
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
      .attr('fill', '#999');

    const link = g.append('g')
      .selectAll('line')
      .data(data.edges)
      .enter()
      .append('line')
      .attr('stroke', '#999')
      .attr('stroke-width', 2)
      .attr('stroke-opacity', 0.6)
      .attr('marker-end', 'url(#arrowhead)');

    // Draw nodes with different colors for functions vs files
    const node = g.append('g')
      .selectAll('circle')
      .data(data.nodes)
      .enter()
      .append('circle')
      .attr('r', d => d.type === 'function' ? 10 : 8)
      .attr('fill', d => d.type === 'function' ? '#f59e0b' : '#667eea')
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .call(d3.drag()
        .on('start', dragStarted)
        .on('drag', dragged)
        .on('end', dragEnded));

    // Add tooltips
    node.append('title')
      .text(d => `${d.label}\n${d.file || ''}\n${d.line ? 'Line: ' + d.line : ''}`);

    // Draw labels
    const labels = g.append('g')
      .selectAll('text')
      .data(data.nodes)
      .enter()
      .append('text')
      .text(d => d.label)
      .attr('font-size', 11)
      .attr('font-weight', d => d.type === 'function' ? 'bold' : 'normal')
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
          <p style={styles.loadingText}>Loading function graph...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2>Function Call Graph</h2>
        <div style={styles.controls}>
          <select 
            value={selectedFunction} 
            onChange={handleFunctionSelect}
            style={styles.select}
          >
            <option value="">All Functions</option>
            {functions.map(fn => (
              <option key={fn.name} value={fn.name}>
                {fn.name} ({fn.file?.split(/[\\\/]/).pop()})
              </option>
            ))}
          </select>
        </div>
      </div>
      <div style={styles.legend}>
        <span style={styles.legendItem}>
          <span style={{...styles.legendDot, background: '#f59e0b'}}></span>
          Functions
        </span>
        <span style={styles.legendItem}>
          <span style={{...styles.legendDot, background: '#667eea'}}></span>
          Files
        </span>
      </div>
      {graphData.nodes.length === 0 ? (
        <div style={styles.emptyState}>
          <p style={styles.emptyText}>No function call data available</p>
          <p style={styles.emptyHint}>Analyze a repository first to see function relationships</p>
        </div>
      ) : (
        <>
          <p>Nodes: {graphData.nodes.length} | Edges: {graphData.edges.length}</p>
          <svg ref={svgRef} style={styles.svg}></svg>
        </>
      )}
    </div>
  );
}

const styles = {
  container: { 
    padding: '20px', 
    background: '#fff', 
    borderRadius: '8px', 
    marginBottom: '20px', 
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)' 
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '15px'
  },
  controls: {
    display: 'flex',
    gap: '10px'
  },
  select: {
    padding: '8px 12px',
    borderRadius: '4px',
    border: '1px solid #ddd',
    fontSize: '14px',
    minWidth: '250px'
  },
  legend: {
    display: 'flex',
    gap: '20px',
    marginBottom: '10px',
    fontSize: '14px'
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  },
  legendDot: {
    width: '12px',
    height: '12px',
    borderRadius: '50%',
    display: 'inline-block'
  },
  svg: { 
    border: '1px solid #ddd', 
    borderRadius: '4px', 
    background: '#fafafa' 
  },
  loaderWrapper: { 
    display: 'flex', 
    flexDirection: 'column', 
    alignItems: 'center', 
    justifyContent: 'center', 
    minHeight: '400px' 
  },
  spinner: {
    width: '50px',
    height: '50px',
    border: '5px solid #f3f3f3',
    borderTop: '5px solid #667eea',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite'
  },
  loadingText: { 
    marginTop: '20px', 
    color: '#666', 
    fontSize: '16px' 
  },
  emptyState: {
    textAlign: 'center',
    padding: '60px 20px',
    color: '#999'
  },
  emptyText: {
    fontSize: '18px',
    fontWeight: 'bold',
    marginBottom: '10px'
  },
  emptyHint: {
    fontSize: '14px'
  }
};
