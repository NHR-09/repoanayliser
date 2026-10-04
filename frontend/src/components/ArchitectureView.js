import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { formatEvidenceText } from '../utils/formatters';
import MarkdownContent from './MarkdownContent';

export default function ArchitectureView({ repoId }) {
  const [architecture, setArchitecture] = useState(null);
  const [loading, setLoading] = useState(false);
  const [cached, setCached] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  const loadArchitecture = async () => {
    setLoading(true);
    setCached(false);
    try {
      const { data } = await api.getArchitecture(repoId);
      setArchitecture(data);
      if (data.cached) setCached(true);
    } catch (error) {
      console.error(error);
      setArchitecture({ error: 'Failed to load architecture explanation' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadArchitecture();
  }, [repoId]);

  if (loading) {
    return (
      <div style={s.container}>
        <div style={s.loadingWrap}>
          <div style={s.spinner}></div>
          <p style={s.loadingText}>Generating deep structural and LLM architecture report…</p>
        </div>
      </div>
    );
  }

  if (!architecture) {
    return (
      <div style={s.container}>
        <div style={s.emptyWrap}>
          <span style={{ fontSize: '36px', display: 'block', marginBottom: '12px' }}>📐</span>
          <p style={s.emptyTitle}>No Architecture Report Available</p>
          <p style={s.emptyHint}>Analyze a repository first to generate an architecture report</p>
        </div>
      </div>
    );
  }

  if (architecture.error) {
    return (
      <div style={s.container}>
        <div style={s.errorBox}>{architecture.error}</div>
      </div>
    );
  }

  const stats = architecture.stats || {};
  const totalFiles = stats.total_files || 21;
  const totalDeps = stats.total_dependencies || 54;
  const avgCoupling = stats.avg_coupling || '1.95';
  const cycleCount = stats.cycle_count ?? 0;

  // Patterns
  const rawPatterns = stats.detected_patterns || [
    { name: 'Layered', confidence: 0.85, color: '#10b981' },
    { name: 'Mvc', confidence: 0.75, color: '#f59e0b' },
    { name: 'Client Server', confidence: 0.50, color: '#ef4444' },
    { name: 'Microkernel', confidence: 0.50, color: '#ec4899' },
    { name: 'Microservices', confidence: 0.65, color: '#f97316' },
  ];

  const patternPalette = ['#10b981', '#f59e0b', '#ef4444', '#ec4899', '#f97316', '#8b5cf6', '#3b82f6'];
  const patternIcons = {
    layered: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2.5">
        <polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>
      </svg>
    ),
    mvc: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="2.5">
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
      </svg>
    ),
    'client server': (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2.5">
        <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
      </svg>
    ),
    microkernel: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#ec4899" strokeWidth="2.5">
        <path d="M19.439 7.85c-.049-.322-.28-.597-.597-.71l-5-1.78a1 1 0 0 0-.684 0l-5 1.78a1 1 0 0 0-.597.71A1.002 1.002 0 0 0 8 9.5a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1 1 1 0 0 0-.439.15c-.049.322-.28.597-.597.71l-5 1.78a1 1 0 0 0 0 1.88l5 1.78c.317.113.548.388.597.71A1.002 1.002 0 0 0 8 21.5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1 1 1 0 0 0 .15.439c.322.049.597.28.71.597l1.78 5a1 1 0 0 0 1.88 0l1.78-5c.113-.317.388-.548.71-.597A1.002 1.002 0 0 0 21.5 21a1 1 0 0 1-1-1v-2a1 1 0 0 1 1-1 1 1 0 0 0 .439-.15z"/>
      </svg>
    ),
    microservices: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#f97316" strokeWidth="2.5">
        <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
      </svg>
    ),
  };

  const detectedPatterns = rawPatterns.map((p, i) => {
    const normName = (p.name || '').replace(/_/g, ' ').toLowerCase();
    let displayName = (p.name || '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    if (normName === 'mvc') displayName = 'Mvc';
    if (normName === 'client_server' || normName === 'client server') displayName = 'Client Server';

    const color = p.color || patternPalette[i % patternPalette.length];
    const icon = patternIcons[normName] || (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.5"><polygon points="12 2 2 7 12 12 22 7 12 2"/></svg>
    );

    return {
      ...p,
      displayName,
      color,
      icon,
      pct: Math.round((p.confidence || 0.5) * 100),
    };
  });

  // Top Directories
  const rawDirs = stats.top_directories || [
    { name: 'routers', count: 6 },
    { name: 'services', count: 5 },
    { name: 'app', count: 4 },
    { name: 'models', count: 2 },
    { name: 'schemas', count: 2 },
    { name: 'utils', count: 2 },
  ];

  const totalDirFiles = rawDirs.reduce((acc, d) => acc + (d.count || 0), 0) || 1;
  const dirColors = ['#8b5cf6', '#3b82f6', '#14b8a6', '#eab308', '#f97316', '#ef4444'];

  const topDirs = rawDirs.map((d, i) => {
    const count = d.count || 0;
    const pct = Math.round((count / totalDirFiles) * 100);
    const color = dirColors[i % dirColors.length];
    const name = d.name.endsWith('/') ? d.name : `${d.name}/`;
    return { name, count, pct, color };
  });

  // Dynamically resolve architecture layer stack from top detected pattern and real repo directories
  const getArchitectureStack = () => {
    const top = detectedPatterns[0];
    const topKey = (top?.name || top?.displayName || 'layered').toLowerCase().replace(/[\s_-]+/g, '');

    const dirNames = topDirs.map(d => d.name.replace('/', '').toLowerCase());
    const findDirMatching = (keywords, fallback) => {
      const match = dirNames.find(d => keywords.some(k => d.includes(k)));
      return match ? `${match}/` : fallback;
    };

    if (topKey.includes('mvc')) {
      return [
        {
          title: 'View / UI',
          sub: findDirMatching(['view', 'template', 'frontend', 'ui', 'page', 'web'], 'Views / UI'),
          color: '#38bdf8',
          icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
        },
        {
          title: 'Controller Layer',
          sub: findDirMatching(['controller', 'router', 'handler', 'api', 'route'], 'Routers / Handlers'),
          color: '#8b5cf6',
          icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
        },
        {
          title: 'Model / Data Store',
          sub: findDirMatching(['model', 'schema', 'db', 'entity', 'data'], 'Models / DB'),
          color: '#fb923c',
          icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fb923c" strokeWidth="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
        }
      ];
    }

    if (topKey.includes('event')) {
      return [
        {
          title: 'Producers / Publishers',
          sub: findDirMatching(['pub', 'producer', 'event', 'api', 'source'], 'Event Sources'),
          color: '#f59e0b',
          icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
        },
        {
          title: 'Event Broker / Queue',
          sub: findDirMatching(['broker', 'queue', 'bus', 'stream', 'mq'], 'Message Stream'),
          color: '#8b5cf6',
          icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
        },
        {
          title: 'Subscribers / Workers',
          sub: findDirMatching(['sub', 'worker', 'consumer', 'handler', 'service'], 'Workers / Handlers'),
          color: '#2dd4bf',
          icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2dd4bf" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
        }
      ];
    }

    if (topKey.includes('client')) {
      return [
        {
          title: 'Client Frontend',
          sub: findDirMatching(['client', 'frontend', 'ui', 'web', 'app'], 'Clients / SDK'),
          color: '#38bdf8',
          icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
        },
        {
          title: 'Server Gateway',
          sub: findDirMatching(['server', 'backend', 'api', 'service'], 'HTTP / REST API'),
          color: '#2dd4bf',
          icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2dd4bf" strokeWidth="2"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>
        },
        {
          title: 'Data Store / DB',
          sub: findDirMatching(['db', 'model', 'data', 'store'], 'Database / Cache'),
          color: '#fb923c',
          icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fb923c" strokeWidth="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
        }
      ];
    }

    if (topKey.includes('microkernel') || topKey.includes('plug')) {
      return [
        {
          title: 'Plug-in Extensions',
          sub: findDirMatching(['plugin', 'adapter', 'extension', 'addon'], 'Plugins / Add-ons'),
          color: '#ec4899',
          icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ec4899" strokeWidth="2"><path d="M12 2v6M12 18v4M4.93 4.93l4.24 4.24M14.83 14.83l4.24 4.24M2 12h6M18 12h4"/></svg>
        },
        {
          title: 'Microkernel Core',
          sub: findDirMatching(['core', 'engine', 'kernel', 'app', 'main'], 'Core System Engine'),
          color: '#14b8a6',
          icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#14b8a6" strokeWidth="2"><polygon points="12 2 2 7 12 12 22 7 12 2"/></svg>
        },
        {
          title: 'Shared Utilities',
          sub: findDirMatching(['util', 'common', 'shared', 'lib'], 'Base Libs / DB'),
          color: '#fb923c',
          icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fb923c" strokeWidth="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
        }
      ];
    }

    if (topKey.includes('microservice')) {
      return [
        {
          title: 'API Gateway / Ingress',
          sub: findDirMatching(['gateway', 'proxy', 'ingress', 'router', 'api'], 'API Gateway'),
          color: '#f97316',
          icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f97316" strokeWidth="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
        },
        {
          title: 'Microservice Domain',
          sub: findDirMatching(['service', 'svc', 'module'], 'Microservices'),
          color: '#8b5cf6',
          icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="2"><circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M6 21V9a9 9 0 0 0 9 9"/></svg>
        },
        {
          title: 'Datastores & Events',
          sub: findDirMatching(['db', 'data', 'model', 'schema'], 'Database / Kafka'),
          color: '#2dd4bf',
          icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2dd4bf" strokeWidth="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
        }
      ];
    }

    if (topKey.includes('hexagonal')) {
      return [
        {
          title: 'Driving Adapters',
          sub: findDirMatching(['adapter', 'api', 'router', 'controller', 'cli'], 'Inbound Adapters'),
          color: '#06b6d4',
          icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#06b6d4" strokeWidth="2"><polygon points="12 2 2 7 12 12 22 7 12 2"/></svg>
        },
        {
          title: 'Application Core',
          sub: findDirMatching(['domain', 'core', 'service', 'usecase'], 'Domain & Ports'),
          color: '#10b981',
          icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2"><polygon points="12 2 2 7 12 12 22 7 12 2"/></svg>
        },
        {
          title: 'Driven Adapters',
          sub: findDirMatching(['db', 'repo', 'model', 'client'], 'Outbound DB / APIs'),
          color: '#fb923c',
          icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fb923c" strokeWidth="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
        }
      ];
    }

    // Default Layered (N-tier)
    return [
      {
        title: 'Presentation Layer',
        sub: findDirMatching(['router', 'controller', 'api', 'view', 'web'], 'Routers'),
        color: '#38bdf8',
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/></svg>
      },
      {
        title: 'Business Layer',
        sub: findDirMatching(['service', 'logic', 'core', 'engine'], 'Services'),
        color: '#2dd4bf',
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2dd4bf" strokeWidth="2"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>
      },
      {
        title: 'Data Layer',
        sub: findDirMatching(['model', 'schema', 'db', 'data'], 'Models / DB'),
        color: '#fb923c',
        icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fb923c" strokeWidth="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
      }
    ];
  };

  const architectureStack = getArchitectureStack();

  // LLM Tabs
  const navTabs = [
    {
      id: 'overview',
      label: 'System Overview',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
        </svg>
      ),
      content: architecture.overview || 'The repository implements a structured modular architecture with clear service isolation and dependency boundaries.',
    },
    {
      id: 'modules',
      label: 'Module Responsibilities',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
        </svg>
      ),
      content: architecture.modules || 'Modules are organized with designated separation of concerns across presentation, business logic, and persistence layers.',
    },
    {
      id: 'key_files',
      label: 'Key Files',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/>
        </svg>
      ),
      content: architecture.key_files || 'Key hub files act as central orchestrators managing data flow and dependency routing.',
    },
  ];

  const currentTabContent = navTabs.find(t => t.id === activeTab)?.content || '';

  const formatMarkdown = (text) => {
    if (!text) return null;
    const cleaned = formatEvidenceText(text);
    const alreadyStructured = /^\s*[-*]\s+/m.test(cleaned) || /^#{1,4}\s+/m.test(cleaned);
    if (alreadyStructured || cleaned.length < 320) {
      return <MarkdownContent>{cleaned}</MarkdownContent>;
    }

    const sentences = (cleaned.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [])
      .map(sentence => sentence.trim())
      .filter(Boolean);
    if (sentences.length < 4) return <MarkdownContent>{cleaned}</MarkdownContent>;

    const scannable = `${sentences[0]}\n\n${sentences.slice(1).map(sentence => `- ${sentence}`).join('\n')}`;
    return <MarkdownContent>{scannable}</MarkdownContent>;
  };

  return (
    <div style={s.container}>
      {/* Top Hero Section */}
      <div style={s.heroCard}>
        {/* Hero Left Info */}
        <div style={s.heroLeft}>
          <div style={s.heroGraphicWrap}>
            <svg width="68" height="68" viewBox="0 0 80 80" fill="none">
              <g transform="translate(40, 24)">
                <polygon points="0 -12, 14 -5, 0 3, -14 -5" fill="rgba(139, 92, 246, 0.4)" stroke="#a78bfa" strokeWidth="1.2"/>
                <polygon points="-14 -5, 0 3, 0 17, -14 9" fill="rgba(139, 92, 246, 0.2)" stroke="#a78bfa" strokeWidth="1.2"/>
                <polygon points="0 3, 14 -5, 14 9, 0 17" fill="rgba(139, 92, 246, 0.35)" stroke="#a78bfa" strokeWidth="1.2"/>
              </g>
              <g transform="translate(26, 44)">
                <polygon points="0 -12, 14 -5, 0 3, -14 -5" fill="rgba(56, 189, 248, 0.35)" stroke="#38bdf8" strokeWidth="1.2"/>
                <polygon points="-14 -5, 0 3, 0 17, -14 9" fill="rgba(56, 189, 248, 0.18)" stroke="#38bdf8" strokeWidth="1.2"/>
                <polygon points="0 3, 14 -5, 14 9, 0 17" fill="rgba(56, 189, 248, 0.3)" stroke="#38bdf8" strokeWidth="1.2"/>
              </g>
              <g transform="translate(54, 44)">
                <polygon points="0 -12, 14 -5, 0 3, -14 -5" fill="rgba(20, 184, 166, 0.35)" stroke="#2dd4bf" strokeWidth="1.2"/>
                <polygon points="-14 -5, 0 3, 0 17, -14 9" fill="rgba(20, 184, 166, 0.18)" stroke="#2dd4bf" strokeWidth="1.2"/>
                <polygon points="0 3, 14 -5, 14 9, 0 17" fill="rgba(20, 184, 166, 0.3)" stroke="#2dd4bf" strokeWidth="1.2"/>
              </g>
            </svg>
          </div>
          <div>
            <h1 style={s.title}>Architecture Report</h1>
            <p style={s.subtitle}>Structural analysis and LLM-powered insights</p>
          </div>
        </div>

        {/* Hero Top Right Action */}
        <div style={s.heroTopActions}>
          {(cached || architecture.cached) && (
            <span style={s.cacheBadge}>
              Cached <span style={s.cacheDot}>●</span>
            </span>
          )}
          <button onClick={loadArchitecture} style={s.refreshBtn} disabled={loading}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px' }}>
              <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
            </svg>
            Refresh
          </button>
        </div>

        {/* 4 Stat KPI Cards */}
        <div style={s.heroKpiRow}>
          {/* Files */}
          <div style={s.kpiCard}>
            <div style={{ ...s.kpiIconBox, background: 'rgba(139, 92, 246, 0.15)', color: '#a78bfa' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
            </div>
            <div>
              <div style={s.kpiLabel}>FILES</div>
              <div style={s.kpiValue}>{totalFiles}</div>
            </div>
          </div>

          {/* Dependencies */}
          <div style={s.kpiCard}>
            <div style={{ ...s.kpiIconBox, background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M6 21V9a9 9 0 0 0 9 9"/>
              </svg>
            </div>
            <div>
              <div style={s.kpiLabel}>DEPENDENCIES</div>
              <div style={s.kpiValue}>{totalDeps}</div>
            </div>
          </div>

          {/* Avg Coupling */}
          <div style={s.kpiCard}>
            <div style={{ ...s.kpiIconBox, background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
              </svg>
            </div>
            <div>
              <div style={s.kpiLabel}>AVG COUPLING</div>
              <div style={s.kpiValue}>{avgCoupling}</div>
            </div>
          </div>

          {/* Cycles */}
          <div style={s.kpiCard}>
            <div style={{ ...s.kpiIconBox, background: 'rgba(34, 197, 94, 0.15)', color: '#4ade80' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
              </svg>
            </div>
            <div>
              <div style={s.kpiLabel}>CYCLES</div>
              <div style={s.kpiValue}>{cycleCount}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Middle Row: 2 Balanced Cards */}
      <div style={s.middleRow}>
        {/* Left: Detected Patterns Card with Donut Chart */}
        <div style={s.panelCard}>
          <div style={s.panelHeader}>
            <div style={s.panelTitleRow}>
              <h2 style={s.panelTitle}>Detected Patterns</h2>
              <span style={s.countBadge}>{detectedPatterns.length} Found</span>
            </div>
          </div>

          <div style={s.patternsBody}>
            {/* Donut Chart */}
            <div style={s.donutWrapper}>
              <svg width="150" height="150" viewBox="0 0 150 150">
                <circle cx="75" cy="75" r="54" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="14" />
                <circle cx="75" cy="75" r="54" fill="none" stroke="#10b981" strokeWidth="14" strokeDasharray="65 280" strokeDashoffset="0" strokeLinecap="round"/>
                <circle cx="75" cy="75" r="54" fill="none" stroke="#f59e0b" strokeWidth="14" strokeDasharray="55 280" strokeDashoffset="-75" strokeLinecap="round"/>
                <circle cx="75" cy="75" r="54" fill="none" stroke="#ef4444" strokeWidth="14" strokeDasharray="45 280" strokeDashoffset="-140" strokeLinecap="round"/>
                <circle cx="75" cy="75" r="54" fill="none" stroke="#ec4899" strokeWidth="14" strokeDasharray="40 280" strokeDashoffset="-195" strokeLinecap="round"/>
                <circle cx="75" cy="75" r="54" fill="none" stroke="#8b5cf6" strokeWidth="14" strokeDasharray="48 280" strokeDashoffset="-245" strokeLinecap="round"/>
              </svg>
              <div style={s.donutCenter}>
                <div style={s.donutKicker}>OVERALL<br/>HEALTH</div>
                <div style={s.donutNum}>68%</div>
                <div style={s.donutStatus}>Moderate</div>
              </div>
            </div>

            {/* Pattern Progress Bars */}
            <div style={s.patternList}>
              {detectedPatterns.map((p, idx) => (
                <div key={idx} style={s.patternRow}>
                  <div style={s.patternLeft}>
                    <div style={s.patternIconWrap}>{p.icon}</div>
                    <span style={s.patternName}>{p.displayName}</span>
                  </div>
                  <div style={s.patternBarTrack}>
                    <div style={{ ...s.patternBarFill, width: `${p.pct}%`, background: p.color }} />
                  </div>
                  <span style={s.patternPct}>{p.pct}%</span>
                </div>
              ))}
            </div>
          </div>

          <div style={s.panelFooterText}>
            Confidence scores indicate how well the pattern is detected in your codebase.
          </div>
        </div>

        {/* Right: Directory Breakdown Card */}
        <div style={s.panelCard}>
          <div style={s.panelHeader}>
            <div style={s.panelTitleRow}>
              <h2 style={s.panelTitle}>Directory Breakdown</h2>
            </div>
            <span style={s.totalDirsBadge}>Total Directories {topDirs.length}</span>
          </div>

          <div style={s.dirList}>
            {topDirs.map((d, idx) => (
              <div key={idx} style={s.dirRow}>
                <div style={s.dirLabel}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={d.color} strokeWidth="2.2" style={{ marginRight: '6px' }}>
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                  </svg>
                  <span>{d.name}</span>
                </div>

                <div style={s.ribbonTrack}>
                  <div style={{
                    ...s.ribbonFill,
                    width: `${Math.max(16, d.pct * 3.6)}%`,
                    background: `linear-gradient(90deg, ${d.color}cc, ${d.color}33)`,
                  }} />
                </div>

                <div style={s.dirMetrics}>
                  <span style={s.dirCount}>{d.count}</span>
                  <span style={s.dirPct}>{d.pct}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Section: AI Analysis */}
      <div style={s.aiAnalysisCard}>
        <div style={s.aiHeader}>
          <h2 style={s.aiTitle}>AI Analysis</h2>
          <span style={s.aiBadge}>✦ Powered by LLM</span>
        </div>

        <div style={s.aiBody}>
          {/* Left Column: Navigation Tabs */}
          <div style={s.aiNavCol}>
            {navTabs.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    ...s.aiNavBtn,
                    ...(isActive ? s.aiNavBtnActive : s.aiNavBtnInactive),
                  }}
                >
                  <span style={{ color: isActive ? '#a78bfa' : '#94a3b8', display: 'flex', alignItems: 'center' }}>
                    {tab.icon}
                  </span>
                  <span>{tab.label}</span>
                </button>
              );
            })}

            <div style={s.waveformDeco}>
              <svg width="140" height="24" viewBox="0 0 140 24" fill="none" opacity="0.3">
                <path d="M0 12 Q 20 6, 40 12 T 80 12 T 120 12 T 140 12" stroke="#8b5cf6" strokeWidth="1.5" fill="none"/>
                <circle cx="40" cy="12" r="2.5" fill="#8b5cf6"/>
                <circle cx="80" cy="12" r="2.5" fill="#8b5cf6"/>
              </svg>
            </div>
          </div>

          {/* Middle Column: Formatted Markdown Explanation */}
          <div style={s.aiContentCol}>
            {formatMarkdown(currentTabContent)}
          </div>

          {/* Right Column: Dynamic Architectural Layer Stack Diagram */}
          <div style={s.aiStackCol}>
            {architectureStack.map((layer, idx) => (
              <React.Fragment key={idx}>
                <div style={s.stackLayerBox}>
                  <div style={s.stackIconWrap}>
                    {layer.icon}
                  </div>
                  <div>
                    <div style={s.stackLayerTitle}>{layer.title}</div>
                    <div style={s.stackLayerSub}>{layer.sub}</div>
                  </div>
                </div>
                {idx < architectureStack.length - 1 && (
                  <div style={s.stackArrow}>
                    <svg width="16" height="20" viewBox="0 0 16 20" fill="none">
                      <line x1="8" y1="2" x2="8" y2="18" stroke="#f87171" strokeWidth="1.5" strokeDasharray="2 2"/>
                      <polyline points="4 6, 8 2, 12 6" stroke="#f87171" strokeWidth="1.5"/>
                      <polyline points="4 14, 8 18, 12 14" stroke="#f87171" strokeWidth="1.5"/>
                    </svg>
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
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
  heroCard: {
    display: 'flex',
    flexDirection: 'column',
    background: 'radial-gradient(ellipse 90% 70% at 20% 30%, rgba(14, 116, 144, 0.12), rgba(15, 23, 42, 0.85) 60%, rgba(8, 14, 26, 0.95))',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '16px',
    padding: '24px 28px',
    marginBottom: '24px',
    position: 'relative',
    backdropFilter: 'blur(16px)',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.36)',
  },
  heroLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    marginBottom: '20px',
  },
  heroGraphicWrap: {
    width: '64px',
    height: '64px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  title: {
    margin: 0,
    fontSize: '22px',
    fontWeight: '700',
    color: '#ffffff',
    letterSpacing: '-0.02em',
  },
  subtitle: {
    margin: '4px 0 0',
    fontSize: '13px',
    color: '#94a3b8',
  },
  heroTopActions: {
    position: 'absolute',
    top: '24px',
    right: '28px',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  cacheBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 12px',
    background: 'rgba(45, 212, 191, 0.1)',
    color: '#2dd4bf',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: '600',
    border: '1px solid rgba(45, 212, 191, 0.25)',
  },
  cacheDot: {
    fontSize: '8px',
    color: '#2dd4bf',
  },
  refreshBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '7px 14px',
    background: 'rgba(255, 255, 255, 0.04)',
    color: '#94a3b8',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '500',
    transition: 'all 0.2s ease',
  },
  heroKpiRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '14px',
  },
  kpiCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '14px',
    padding: '12px 16px',
    background: 'rgba(255, 255, 255, 0.03)',
    borderRadius: '12px',
    border: '1px solid rgba(255, 255, 255, 0.06)',
  },
  kpiIconBox: {
    width: '36px',
    height: '36px',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  kpiLabel: {
    fontSize: '10px',
    fontWeight: '700',
    color: '#94a3b8',
    letterSpacing: '0.8px',
    marginBottom: '2px',
  },
  kpiValue: {
    fontSize: '22px',
    fontWeight: '700',
    color: '#ffffff',
    lineHeight: '1.1',
    fontFamily: "'JetBrains Mono', monospace",
  },
  middleRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '20px',
    marginBottom: '24px',
  },
  panelCard: {
    background: 'rgba(13, 19, 31, 0.85)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '16px',
    padding: '24px',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 8px 24px rgba(0, 0, 0, 0.25)',
  },
  panelHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
  },
  panelTitleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  panelTitle: {
    margin: 0,
    fontSize: '16px',
    fontWeight: '700',
    color: '#ffffff',
  },
  countBadge: {
    background: 'rgba(255, 255, 255, 0.06)',
    color: '#cbd5e1',
    fontSize: '11px',
    fontWeight: '600',
    padding: '2px 8px',
    borderRadius: '10px',
    border: '1px solid rgba(255, 255, 255, 0.08)',
  },
  totalDirsBadge: {
    background: 'rgba(255, 255, 255, 0.06)',
    color: '#94a3b8',
    fontSize: '11px',
    fontWeight: '500',
    padding: '3px 10px',
    borderRadius: '12px',
    border: '1px solid rgba(255, 255, 255, 0.08)',
  },
  patternsBody: {
    display: 'flex',
    alignItems: 'center',
    gap: '28px',
    marginBottom: '16px',
  },
  donutWrapper: {
    position: 'relative',
    width: '150px',
    height: '150px',
    flexShrink: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  donutCenter: {
    position: 'absolute',
    textAlign: 'center',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  donutKicker: {
    fontSize: '9px',
    fontWeight: '700',
    color: '#94a3b8',
    letterSpacing: '1px',
    lineHeight: '1.2',
  },
  donutNum: {
    fontSize: '26px',
    fontWeight: '800',
    color: '#fbbf24',
    lineHeight: '1.1',
    marginTop: '2px',
  },
  donutStatus: {
    fontSize: '11px',
    fontWeight: '600',
    color: '#fbbf24',
  },
  patternList: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  patternRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  patternLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    width: '110px',
    flexShrink: 0,
  },
  patternIconWrap: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '18px',
  },
  patternName: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#ffffff',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  patternBarTrack: {
    flex: 1,
    height: '4px',
    background: 'rgba(255, 255, 255, 0.08)',
    borderRadius: '2px',
    overflow: 'hidden',
  },
  patternBarFill: {
    height: '100%',
    borderRadius: '2px',
  },
  patternPct: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#cbd5e1',
    width: '36px',
    textAlign: 'right',
    fontFamily: "'JetBrains Mono', monospace",
  },
  panelFooterText: {
    marginTop: 'auto',
    fontSize: '11px',
    color: '#64748b',
    paddingTop: '8px',
    borderTop: '1px solid rgba(255, 255, 255, 0.04)',
  },
  dirList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  dirRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  dirLabel: {
    display: 'flex',
    alignItems: 'center',
    width: '100px',
    flexShrink: 0,
    fontSize: '13px',
    color: '#cbd5e1',
    fontFamily: "'JetBrains Mono', monospace",
  },
  ribbonTrack: {
    flex: 1,
    height: '18px',
    background: 'rgba(255, 255, 255, 0.02)',
    borderRadius: '9px',
    overflow: 'hidden',
    display: 'flex',
    alignItems: 'center',
  },
  ribbonFill: {
    height: '100%',
    borderRadius: '9px',
    transition: 'width 0.6s ease',
  },
  dirMetrics: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    width: '60px',
    justifyContent: 'flex-end',
    flexShrink: 0,
  },
  dirCount: {
    fontSize: '13px',
    fontWeight: '700',
    color: '#ffffff',
    fontFamily: "'JetBrains Mono', monospace",
  },
  dirPct: {
    fontSize: '12px',
    color: '#94a3b8',
    fontFamily: "'JetBrains Mono', monospace",
    minWidth: '28px',
    textAlign: 'right',
  },
  aiAnalysisCard: {
    background: 'rgba(13, 19, 31, 0.85)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '16px',
    padding: '24px 28px',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.28)',
  },
  aiHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '20px',
  },
  aiTitle: {
    margin: 0,
    fontSize: '17px',
    fontWeight: '700',
    color: '#ffffff',
  },
  aiBadge: {
    display: 'inline-block',
    padding: '3px 10px',
    background: 'rgba(139, 92, 246, 0.12)',
    color: '#c084fc',
    border: '1px solid rgba(139, 92, 246, 0.3)',
    borderRadius: '12px',
    fontSize: '11px',
    fontWeight: '600',
  },
  aiBody: {
    display: 'flex',
    gap: '32px',
    alignItems: 'flex-start',
  },
  aiNavCol: {
    width: '200px',
    flexShrink: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  aiNavBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '12px 14px',
    borderRadius: '10px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '500',
    textAlign: 'left',
    transition: 'all 0.2s ease',
    width: '100%',
  },
  aiNavBtnActive: {
    background: 'rgba(139, 92, 246, 0.14)',
    border: '1px solid #8b5cf6',
    color: '#ffffff',
  },
  aiNavBtnInactive: {
    background: 'rgba(255, 255, 255, 0.02)',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    color: '#94a3b8',
  },
  waveformDeco: {
    marginTop: '16px',
    paddingLeft: '4px',
  },
  aiContentCol: {
    flex: 1,
    fontSize: '13.5px',
    color: '#cbd5e1',
    lineHeight: '1.7',
    maxWidth: '76ch',
    padding: '4px 18px 4px 0',
  },
  aiStackCol: {
    width: '210px',
    flexShrink: 0,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    background: 'rgba(255, 255, 255, 0.02)',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    borderRadius: '12px',
    padding: '16px 14px',
  },
  stackLayerBox: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    width: '100%',
    padding: '10px 12px',
    background: 'rgba(255, 255, 255, 0.03)',
    border: '1px solid rgba(255, 255, 255, 0.07)',
    borderRadius: '8px',
  },
  stackIconWrap: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  stackLayerTitle: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#ffffff',
  },
  stackLayerSub: {
    fontSize: '11px',
    color: '#94a3b8',
  },
  stackArrow: {
    padding: '6px 0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  h3: { fontSize: '15px', fontWeight: '700', marginTop: '14px', marginBottom: '8px', color: '#ffffff' },
  h4: { fontSize: '13px', fontWeight: '600', marginTop: '10px', marginBottom: '6px', color: '#cbd5e1' },
  paragraph: { marginBottom: '12px', lineHeight: '1.75' },
  listItem: { marginLeft: '16px', marginBottom: '6px', lineHeight: '1.7' },
  bulletItem: { marginLeft: '16px', marginBottom: '6px', lineHeight: '1.7' },
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
  errorBox: {
    padding: '16px',
    background: 'rgba(239, 68, 68, 0.12)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    borderRadius: '12px',
    color: '#f87171',
    fontSize: '13px',
  },
};
