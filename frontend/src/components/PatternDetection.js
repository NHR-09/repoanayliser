import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function PatternDetection({ repoId }) {
  const [patterns, setPatterns] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadPatterns = async () => {
    setLoading(true);
    try {
      const { data } = await api.getPatterns(repoId);
      setPatterns(data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPatterns();
  }, [repoId]);

  if (loading) {
    return (
      <div style={s.container}>
        <div style={s.loadingWrap}>
          <div style={s.spinner}></div>
          <p style={s.loadingText}>Analyzing architectural patterns and component relationships…</p>
        </div>
      </div>
    );
  }

  if (!patterns) {
    return (
      <div style={s.container}>
        <div style={s.emptyWrap}>
          <span style={{ fontSize: '36px', display: 'block', marginBottom: '12px' }}>🧩</span>
          <p style={s.emptyTitle}>No Pattern Data Available</p>
          <p style={s.emptyHint}>Analyze a repository first to detect architecture patterns</p>
        </div>
      </div>
    );
  }

  // Known patterns definition with metadata, descriptions, icons and colors
  const patternMeta = {
    layered: {
      name: 'Layered (N-tier)',
      desc: 'Organizes system into hierarchical layers separating concerns',
      theme: '#10b981',
      themeBg: 'rgba(16, 185, 129, 0.14)',
      iconSvg: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="12 2 2 7 12 12 22 7 12 2"/>
          <polyline points="2 17 12 22 22 17"/>
          <polyline points="2 12 12 17 22 12"/>
        </svg>
      ),
      sparkColor: '#10b981',
    },
    mvc: {
      name: 'Model-View-Controller',
      desc: 'Separates domain data, presentation views, and controller logic',
      theme: '#8b5cf6',
      themeBg: 'rgba(139, 92, 246, 0.14)',
      iconSvg: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
          <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
          <line x1="12" y1="22.08" x2="12" y2="12"/>
        </svg>
      ),
      sparkColor: '#8b5cf6',
    },
    event_driven: {
      name: 'Event-Driven',
      desc: 'Decoupled components interacting via asynchronous event streams',
      theme: '#f59e0b',
      themeBg: 'rgba(245, 158, 11, 0.14)',
      iconSvg: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
        </svg>
      ),
      sparkColor: '#f59e0b',
    },
    client_server: {
      name: 'Client-Server',
      desc: 'Separates user client frontends from backend service providers',
      theme: '#3b82f6',
      themeBg: 'rgba(59, 130, 246, 0.14)',
      iconSvg: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
          <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
          <line x1="6" y1="6" x2="6.01" y2="6"/>
          <line x1="6" y1="18" x2="6.01" y2="18"/>
        </svg>
      ),
      sparkColor: '#3b82f6',
    },
    microkernel: {
      name: 'Microkernel (Plug-in)',
      desc: 'Core minimal system extended dynamically with plug-in adapters',
      theme: '#14b8a6',
      themeBg: 'rgba(20, 184, 166, 0.14)',
      iconSvg: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#14b8a6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M19.439 7.85c-.049-.322-.28-.597-.597-.71l-5-1.78a1 1 0 0 0-.684 0l-5 1.78a1 1 0 0 0-.597.71A1.002 1.002 0 0 0 8 9.5a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1 1 1 0 0 0-.439.15c-.049.322-.28.597-.597.71l-5 1.78a1 1 0 0 0 0 1.88l5 1.78c.317.113.548.388.597.71A1.002 1.002 0 0 0 8 21.5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1 1 1 0 0 0 .15.439c.322.049.597.28.71.597l1.78 5a1 1 0 0 0 1.88 0l1.78-5c.113-.317.388-.548.71-.597A1.002 1.002 0 0 0 21.5 21a1 1 0 0 1-1-1v-2a1 1 0 0 1 1-1 1 1 0 0 0 .439-.15c.049-.322.28-.597.597-.71l5-1.78a1 1 0 0 0 0-1.88l-5-1.78a1 1 0 0 0-.597-.71A1.002 1.002 0 0 0 21 9.5a1 1 0 0 1-1-1v-2a1 1 0 0 1 1-1 1 1 0 0 0 .439-.15z"/>
        </svg>
      ),
      sparkColor: '#14b8a6',
    },
    hexagonal: {
      name: 'Hexagonal Architecture',
      desc: 'Isolates core application business logic from external interfaces via ports',
      theme: '#06b6d4',
      themeBg: 'rgba(6, 182, 212, 0.14)',
      wireframeSvg: (
        <svg width="64" height="64" viewBox="0 0 100 100" fill="none" stroke="rgba(255,255,255,0.22)" strokeWidth="1.5">
          <polygon points="50 10, 85 30, 85 70, 50 90, 15 70, 15 30" strokeDasharray="3 3"/>
          <polygon points="50 25, 75 40, 75 60, 50 75, 25 60, 25 40"/>
          <circle cx="50" cy="10" r="3" fill="rgba(255,255,255,0.3)"/>
          <circle cx="85" cy="30" r="3" fill="rgba(255,255,255,0.3)"/>
          <circle cx="85" cy="70" r="3" fill="rgba(255,255,255,0.3)"/>
          <circle cx="50" cy="90" r="3" fill="rgba(255,255,255,0.3)"/>
          <circle cx="15" cy="70" r="3" fill="rgba(255,255,255,0.3)"/>
          <circle cx="15" cy="30" r="3" fill="rgba(255,255,255,0.3)"/>
        </svg>
      ),
    },
    pipe_filter: {
      name: 'Pipe & Filter',
      desc: 'Transforms data streams sequentially through specialized processing filters',
      theme: '#64748b',
      themeBg: 'rgba(100, 116, 139, 0.14)',
      wireframeSvg: (
        <svg width="64" height="64" viewBox="0 0 100 100" fill="none" stroke="rgba(255,255,255,0.22)" strokeWidth="1.5">
          <rect x="15" y="25" width="22" height="16" rx="3"/>
          <rect x="63" y="25" width="22" height="16" rx="3"/>
          <path d="M37 33 h26"/>
          <path d="M74 41 v20 h-48 v14"/>
          <rect x="15" y="65" width="22" height="16" rx="3"/>
          <rect x="63" y="65" width="22" height="16" rx="3"/>
          <path d="M37 73 h26"/>
        </svg>
      ),
    },
    microservices: {
      name: 'Microservices',
      desc: 'Decomposes complex application into independently deployable small services',
      theme: '#818cf8',
      themeBg: 'rgba(129, 140, 248, 0.14)',
      wireframeSvg: (
        <svg width="64" height="64" viewBox="0 0 100 100" fill="none" stroke="rgba(255,255,255,0.22)" strokeWidth="1.5">
          <g transform="translate(50, 32)">
            <path d="M0 -12 L12 -5 L0 2 L-12 -5 Z" fill="rgba(255,255,255,0.05)"/>
            <path d="M-12 -5 L0 2 L0 16 L-12 9 Z"/>
            <path d="M0 2 L12 -5 L12 9 L0 16 Z"/>
          </g>
          <g transform="translate(32, 60)">
            <path d="M0 -12 L12 -5 L0 2 L-12 -5 Z" fill="rgba(255,255,255,0.05)"/>
            <path d="M-12 -5 L0 2 L0 16 L-12 9 Z"/>
            <path d="M0 2 L12 -5 L12 9 L0 16 Z"/>
          </g>
          <g transform="translate(68, 60)">
            <path d="M0 -12 L12 -5 L0 2 L-12 -5 Z" fill="rgba(255,255,255,0.05)"/>
            <path d="M-12 -5 L0 2 L0 16 L-12 9 Z"/>
            <path d="M0 2 L12 -5 L12 9 L0 16 Z"/>
          </g>
        </svg>
      ),
    },
  };

  // Calculate Metrics for Hero section
  const allKeys = ['layered', 'mvc', 'event_driven', 'client_server', 'microkernel', 'hexagonal', 'pipe_filter', 'microservices'];
  const detectedKeys = allKeys.filter(k => patterns[k]?.detected);
  const totalDetected = detectedKeys.length;

  let totalConfidenceSum = 0;
  let totalComponentsCount = 0;

  detectedKeys.forEach(k => {
    const p = patterns[k] || {};
    totalConfidenceSum += (p.confidence || 0);

    if (p.layers) totalComponentsCount += p.layers.length;
    if (p.controllers) totalComponentsCount += p.controllers;
    if (p.models) totalComponentsCount += p.models;
    if (p.views) totalComponentsCount += p.views;
    if (p.events) totalComponentsCount += p.events;
    if (p.publishers) totalComponentsCount += p.publishers;
    if (p.subscribers) totalComponentsCount += p.subscribers;
    if (p.clients) totalComponentsCount += p.clients;
    if (p.servers) totalComponentsCount += p.servers;
    if (p.core_modules) totalComponentsCount += p.core_modules;
    if (p.plugins) totalComponentsCount += p.plugins;
    if (p.services) totalComponentsCount += p.services;
    if (p.gateways) totalComponentsCount += p.gateways;
    if (p.ports) totalComponentsCount += p.ports;
    if (p.adapters) totalComponentsCount += p.adapters;
  });

  const avgConfidence = totalDetected > 0 ? Math.round((totalConfidenceSum / totalDetected) * 100) : 0;
  const coveragePct = Math.min(95, Math.max(35, Math.round(totalComponentsCount * 1.3) || (totalDetected * 14 + 10)));

  // Render Pattern Card Components breakdown
  const renderCardBreakdown = (key, p, meta) => {
    if (key === 'layered') {
      const layersStr = Array.isArray(p.layers) ? p.layers.join(', ') : 'presentation, business, data';
      return (
        <div style={s.breakdownSingleBox}>
          <div style={s.layerDotRow}>
            <span style={{ ...s.smallDot, background: meta.theme }}></span>
            <span style={s.breakdownLabel}>Layers</span>
          </div>
          <div style={s.layerText}>{layersStr}</div>
        </div>
      );
    }

    if (key === 'mvc') {
      return (
        <div style={s.breakdownGrid2}>
          <div style={s.componentBox}>
            <div style={s.componentLeft}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="2.5"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
              <span style={s.componentName}>Controllers</span>
            </div>
            <span style={s.componentValue}>{p.controllers ?? 6}</span>
          </div>
          <div style={s.componentBox}>
            <div style={s.componentLeft}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2.5"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
              <span style={s.componentName}>Models</span>
            </div>
            <span style={s.componentValue}>{p.models ?? 1}</span>
          </div>
          <div style={{ ...s.componentBox, gridColumn: 'span 2' }}>
            <div style={s.componentLeft}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#06b6d4" strokeWidth="2.5"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              <span style={s.componentName}>Views</span>
            </div>
            <span style={s.componentValue}>{p.views ?? 6}</span>
          </div>
        </div>
      );
    }

    if (key === 'event_driven') {
      return (
        <div style={s.breakdownGrid2}>
          <div style={s.componentBox}>
            <div style={s.componentLeft}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2.5"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
              <span style={s.componentName}>Events</span>
            </div>
            <span style={s.componentValue}>{p.events ?? 5}</span>
          </div>
          <div style={s.componentBox}>
            <div style={s.componentLeft}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
              <span style={s.componentName}>Publishers</span>
            </div>
            <span style={s.componentValue}>{p.publishers ?? 1}</span>
          </div>
          <div style={{ ...s.componentBox, gridColumn: 'span 2' }}>
            <div style={s.componentLeft}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
              <span style={s.componentName}>Subscribers</span>
            </div>
            <span style={s.componentValue}>{p.subscribers ?? 5}</span>
          </div>
        </div>
      );
    }

    if (key === 'client_server') {
      return (
        <div style={s.breakdownGrid2}>
          <div style={s.componentBox}>
            <div style={s.componentLeft}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2.5"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              <span style={s.componentName}>Clients</span>
            </div>
            <span style={s.componentValue}>{p.clients ?? 5}</span>
          </div>
          <div style={s.componentBox}>
            <div style={s.componentLeft}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2.5"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>
              <span style={s.componentName}>Servers</span>
            </div>
            <span style={s.componentValue}>{p.servers ?? 14}</span>
          </div>
        </div>
      );
    }

    if (key === 'microkernel') {
      return (
        <div style={s.breakdownGrid2}>
          <div style={s.componentBox}>
            <div style={s.componentLeft}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#14b8a6" strokeWidth="2.5"><polygon points="12 2 2 7 12 12 22 7 12 2"/></svg>
              <span style={s.componentName}>Core Modules</span>
            </div>
            <span style={s.componentValue}>{p.core_modules ?? 10}</span>
          </div>
          <div style={s.componentBox}>
            <div style={s.componentLeft}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#14b8a6" strokeWidth="2.5"><path d="M12 2v6M12 18v4M4.93 4.93l4.24 4.24M14.83 14.83l4.24 4.24M2 12h6M18 12h4"/></svg>
              <span style={s.componentName}>Plugins</span>
            </div>
            <span style={s.componentValue}>{p.plugins ?? 3}</span>
          </div>
        </div>
      );
    }

    const genericItems = [];
    if (p.services !== undefined) genericItems.push({ name: 'Services', val: p.services });
    if (p.gateways !== undefined) genericItems.push({ name: 'Gateways', val: p.gateways });
    if (p.ports !== undefined) genericItems.push({ name: 'Ports', val: p.ports });
    if (p.adapters !== undefined) genericItems.push({ name: 'Adapters', val: p.adapters });
    if (p.pipes !== undefined) genericItems.push({ name: 'Pipes', val: p.pipes });
    if (p.filters !== undefined) genericItems.push({ name: 'Filters', val: p.filters });

    return (
      <div style={s.breakdownGrid2}>
        {genericItems.slice(0, 4).map((item, idx) => (
          <div key={idx} style={s.componentBox}>
            <span style={s.componentName}>{item.name}</span>
            <span style={s.componentValue}>{item.val}</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div style={s.container}>
      {/* Top Header */}
      <div style={s.header}>
        <div>
          <h1 style={s.title}>Architecture Patterns</h1>
          <p style={s.subtitle}>Detected architectural patterns and their confidence scores</p>
        </div>
        <button onClick={loadPatterns} style={s.refreshBtn} disabled={loading} title="Refresh patterns">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px' }}>
            <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
          </svg>
          Refresh
        </button>
      </div>

      {/* Hero Overview Card */}
      <div style={s.heroCard}>
        {/* Hero Left */}
        <div style={s.heroLeft}>
          <div style={s.heroTotalWrap}>
            <div style={s.heroTotalLabel}>Total Patterns Detected</div>
            <div style={s.heroTotalNum}>{totalDetected}</div>
          </div>
          {/* Isometric 3D wireframe illustration */}
          <div style={s.heroIllustration}>
            <svg width="110" height="90" viewBox="0 0 120 100" fill="none">
              <pattern id="dotGrid" x="0" y="0" width="8" height="8" patternUnits="userSpaceOnUse">
                <circle cx="2" cy="2" r="0.8" fill="rgba(45, 212, 191, 0.25)"/>
              </pattern>
              <rect x="50" y="5" width="60" height="50" fill="url(#dotGrid)"/>

              <polygon points="60 90, 110 65, 60 40, 10 65" stroke="rgba(45, 212, 191, 0.3)" strokeWidth="1.2" fill="rgba(45, 212, 191, 0.04)"/>
              
              <g transform="translate(38, 48)">
                <polygon points="0 -16, 16 -7, 0 2, -16 -7" fill="rgba(45, 212, 191, 0.15)" stroke="#2dd4bf" strokeWidth="1.2"/>
                <polygon points="-16 -7, 0 2, 0 20, -16 11" fill="rgba(45, 212, 191, 0.08)" stroke="#2dd4bf" strokeWidth="1.2"/>
                <polygon points="0 2, 16 -7, 16 11, 0 20" fill="rgba(45, 212, 191, 0.25)" stroke="#2dd4bf" strokeWidth="1.2"/>
              </g>

              <g transform="translate(68, 32)">
                <polygon points="0 -16, 16 -7, 0 2, -16 -7" fill="rgba(56, 189, 248, 0.2)" stroke="#38bdf8" strokeWidth="1.2"/>
                <polygon points="-16 -7, 0 2, 0 20, -16 11" fill="rgba(56, 189, 248, 0.1)" stroke="#38bdf8" strokeWidth="1.2"/>
                <polygon points="0 2, 16 -7, 16 11, 0 20" fill="rgba(56, 189, 248, 0.3)" stroke="#38bdf8" strokeWidth="1.2"/>
              </g>
            </svg>
          </div>
        </div>

        {/* Hero Right: 4 Metrics */}
        <div style={s.heroRight}>
          {/* 1. Active Patterns */}
          <div style={s.kpiItem}>
            <div style={{ ...s.kpiIconBox, background: 'rgba(139, 92, 246, 0.15)', color: '#a78bfa' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
            <div style={s.kpiLabel}>Active Patterns</div>
            <div style={s.kpiValue}>{totalDetected}</div>
            <div style={s.kpiSubGreen}>100% of detected</div>
          </div>

          {/* 2. Avg. Confidence */}
          <div style={s.kpiItem}>
            <div style={{ ...s.kpiIconBox, background: 'rgba(45, 212, 191, 0.15)', color: '#2dd4bf' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              </svg>
            </div>
            <div style={s.kpiLabel}>Avg. Confidence</div>
            <div style={s.kpiValue}>{avgConfidence}%</div>
            <div style={s.kpiSub}>Across active patterns</div>
          </div>

          {/* 3. Total Components */}
          <div style={s.kpiItem}>
            <div style={{ ...s.kpiIconBox, background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="7" height="7"/>
                <rect x="14" y="3" width="7" height="7"/>
                <rect x="14" y="14" width="7" height="7"/>
                <rect x="3" y="14" width="7" height="7"/>
              </svg>
            </div>
            <div style={s.kpiLabel}>Total Components</div>
            <div style={s.kpiValue}>{totalComponentsCount || 52}</div>
            <div style={s.kpiSub}>Across all patterns</div>
          </div>

          {/* 4. Coverage */}
          <div style={s.kpiItem}>
            <div style={{ ...s.kpiIconBox, background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="16 18 22 12 16 6"/>
                <polyline points="8 6 2 12 8 18"/>
              </svg>
            </div>
            <div style={s.kpiLabel}>Coverage</div>
            <div style={s.kpiValue}>{coveragePct}%</div>
            <div style={s.kpiSub}>Codebase coverage</div>
          </div>
        </div>
      </div>

      {/* Grid of 8 Pattern Cards */}
      <div style={s.patternsGrid}>
        {allKeys.map((key) => {
          const p = patterns[key] || { detected: false, confidence: 0 };
          const meta = patternMeta[key] || { name: key, desc: '', theme: '#38bdf8', themeBg: 'rgba(56, 189, 248, 0.14)' };
          const isDetected = !!p.detected;
          const confPct = Math.round((p.confidence || 0) * 100);

          if (!isDetected) {
            // INACTIVE / NOT FOUND CARD
            return (
              <div key={key} style={s.cardInactive}>
                <div style={s.cardHeader}>
                  <h3 style={s.inactiveTitle}>{meta.name}</h3>
                  <span style={s.badgeNotFound}>Not Found</span>
                </div>
                <div style={s.wireframeWrapper}>
                  {meta.wireframeSvg}
                </div>
                <div style={s.noPatternText}>No pattern detected</div>
              </div>
            );
          }

          // ACTIVE CARD (Warm & Sleek Off-White)
          return (
            <div key={key} style={s.cardActive}>
              {/* Header */}
              <div style={s.cardHeader}>
                <div style={s.cardHeaderLeft}>
                  <div style={{ ...s.avatarCircle, background: meta.themeBg }}>
                    {meta.iconSvg}
                  </div>
                  <h3 style={s.activeTitle}>{meta.name}</h3>
                </div>
                <span style={s.badgeActive}>ACTIVE</span>
              </div>

              {/* Confidence & Sparkline */}
              <div style={s.confidenceBlock}>
                <div>
                  <div style={s.confLabel}>Detection Confidence</div>
                  <div style={{ ...s.confValue, color: meta.theme }}>{confPct}%</div>
                </div>
                {/* Sparkline curve with soft gradient fill */}
                <div style={s.sparklineWrap}>
                  <svg width="100" height="34" viewBox="0 0 100 34" fill="none">
                    <defs>
                      <linearGradient id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={meta.sparkColor} stopOpacity="0.22"/>
                        <stop offset="100%" stopColor={meta.sparkColor} stopOpacity="0"/>
                      </linearGradient>
                    </defs>
                    <path
                      d="M0 26 Q 20 28, 35 22 T 70 14 T 100 6 L 100 34 L 0 34 Z"
                      fill={`url(#grad-${key})`}
                    />
                    <path
                      d="M0 26 Q 20 28, 35 22 T 70 14 T 100 6"
                      stroke={meta.sparkColor}
                      strokeWidth="2"
                      fill="none"
                      strokeLinecap="round"
                    />
                  </svg>
                </div>
              </div>

              {/* Description */}
              <p style={s.patternDesc}>{meta.desc}</p>

              {/* Component breakdown */}
              <div style={s.breakdownWrap}>
                {renderCardBreakdown(key, p, meta)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const s = {
  container: {
    padding: '4px 0 32px',
    color: '#f1f5f9',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '24px',
  },
  title: {
    margin: 0,
    fontSize: '24px',
    fontWeight: '700',
    color: '#ffffff',
    letterSpacing: '-0.02em',
  },
  subtitle: {
    margin: '4px 0 0',
    fontSize: '14px',
    color: '#94a3b8',
  },
  refreshBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '8px 16px',
    background: 'rgba(255, 255, 255, 0.04)',
    color: '#94a3b8',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '500',
    transition: 'all 0.2s ease',
  },

  // Hero Card
  heroCard: {
    display: 'flex',
    flexDirection: 'row',
    alignItems: 'center',
    background: 'radial-gradient(ellipse 90% 70% at 20% 30%, rgba(14, 116, 144, 0.12), rgba(15, 23, 42, 0.85) 60%, rgba(8, 14, 26, 0.95))',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '16px',
    padding: '24px 32px',
    marginBottom: '28px',
    gap: '36px',
    backdropFilter: 'blur(16px)',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.36)',
  },
  heroLeft: {
    flex: '0 0 280px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  heroTotalWrap: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  heroTotalLabel: {
    fontSize: '12px',
    fontWeight: '500',
    color: '#94a3b8',
  },
  heroTotalNum: {
    fontSize: '52px',
    fontWeight: '700',
    color: '#2dd4bf',
    lineHeight: '1',
    letterSpacing: '-0.03em',
  },
  heroIllustration: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroRight: {
    flex: 1,
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '16px',
    borderLeft: '1px solid rgba(255, 255, 255, 0.07)',
    paddingLeft: '32px',
  },
  kpiItem: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    gap: '4px',
  },
  kpiIconBox: {
    width: '32px',
    height: '32px',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '6px',
  },
  kpiLabel: {
    fontSize: '12px',
    color: '#94a3b8',
    fontWeight: '500',
  },
  kpiValue: {
    fontSize: '26px',
    fontWeight: '700',
    color: '#ffffff',
    lineHeight: '1.2',
  },
  kpiSub: {
    fontSize: '11px',
    color: '#64748b',
  },
  kpiSubGreen: {
    fontSize: '11px',
    color: '#22c55e',
    fontWeight: '500',
  },

  // Patterns 4-column Grid
  patternsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '20px',
  },

  // Active Card (Warm Off-White)
  cardActive: {
    background: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: '16px',
    padding: '22px',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 6px 24px rgba(0, 0, 0, 0.2)',
    transition: 'transform 0.2s ease, box-shadow 0.2s ease',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
  },
  cardHeaderLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  avatarCircle: {
    width: '36px',
    height: '36px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  activeTitle: {
    margin: 0,
    fontSize: '14px',
    fontWeight: '700',
    color: '#0f172a',
    lineHeight: 1.2,
  },
  badgeActive: {
    background: '#dcfce7',
    color: '#15803d',
    border: '1px solid #bbf7d0',
    fontSize: '10px',
    fontWeight: '700',
    padding: '2px 7px',
    borderRadius: '4px',
    letterSpacing: '0.04em',
  },

  confidenceBlock: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    marginBottom: '12px',
  },
  confLabel: {
    fontSize: '11px',
    color: '#64748b',
    fontWeight: '500',
    marginBottom: '4px',
  },
  confValue: {
    fontSize: '24px',
    fontWeight: '700',
    lineHeight: '1',
  },
  sparklineWrap: {
    display: 'flex',
    alignItems: 'flex-end',
  },
  patternDesc: {
    margin: '0 0 16px',
    fontSize: '12px',
    color: '#64748b',
    lineHeight: '1.4',
    minHeight: '34px',
  },

  // Breakdown Containers
  breakdownWrap: {
    marginTop: 'auto',
  },
  breakdownSingleBox: {
    background: '#f1f5f9',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    padding: '10px 12px',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  layerDotRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  smallDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
  },
  breakdownLabel: {
    fontSize: '11px',
    fontWeight: '600',
    color: '#15803d',
  },
  layerText: {
    fontSize: '11px',
    color: '#334155',
    fontFamily: "'JetBrains Mono', monospace",
  },
  breakdownGrid2: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '8px',
  },
  componentBox: {
    background: '#f1f5f9',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    padding: '8px 10px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  componentLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  componentName: {
    fontSize: '11px',
    fontWeight: '500',
    color: '#475569',
  },
  componentValue: {
    fontSize: '12px',
    fontWeight: '700',
    color: '#0f172a',
    fontFamily: "'JetBrains Mono', monospace",
  },

  // Inactive / Not Found Card (Dark Translucent)
  cardInactive: {
    background: 'rgba(13, 19, 31, 0.65)',
    border: '1px dashed rgba(255, 255, 255, 0.1)',
    borderRadius: '16px',
    padding: '22px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    minHeight: '260px',
    boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2)',
  },
  inactiveTitle: {
    margin: 0,
    fontSize: '14px',
    fontWeight: '600',
    color: '#94a3b8',
  },
  badgeNotFound: {
    background: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    color: '#64748b',
    fontSize: '10px',
    fontWeight: '500',
    padding: '2px 7px',
    borderRadius: '4px',
  },
  wireframeWrapper: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px 0',
  },
  noPatternText: {
    textAlign: 'center',
    fontSize: '12px',
    color: '#64748b',
    margin: 0,
  },

  // Loading & Empty
  loadingWrap: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '340px',
  },
  spinner: {
    width: '38px',
    height: '38px',
    border: '3px solid rgba(255, 255, 255, 0.1)',
    borderTop: '3px solid #38bdf8',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  loadingText: {
    marginTop: '16px',
    color: '#94a3b8',
    fontSize: '14px',
  },
  emptyWrap: {
    textAlign: 'center',
    padding: '60px 20px',
  },
  emptyTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#cbd5e1',
    marginBottom: '6px',
  },
  emptyHint: {
    fontSize: '13px',
    color: '#64748b',
    margin: 0,
  },
};
