import React, { useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';

const compactPath = value => {
  const parts = String(value || '').replace(/\\/g, '/').split('/').filter(Boolean);
  return parts.slice(-4).join('/');
};

const matches = (value, query) => JSON.stringify(value).toLowerCase().includes(query.toLowerCase());

function CandidateRow({ title, path, line, reason, confidence }) {
  return (
    <div style={styles.row}>
      <div style={styles.rowMain}>
        <strong style={styles.rowTitle}>{title}</strong>
        <code title={path} style={styles.path}>{compactPath(path)}{line ? `:${line}` : ''}</code>
        <span style={styles.reason}>{reason}</span>
      </div>
      <span style={styles.confidence}>{Math.round((confidence || 0) * 100)}% signal</span>
    </div>
  );
}

function Section({ title, hint, count, children, empty }) {
  return (
    <section style={styles.section}>
      <div style={styles.sectionHeader}>
        <div>
          <h3 style={styles.sectionTitle}>{title}</h3>
          <p style={styles.sectionHint}>{hint}</p>
        </div>
        <span style={styles.count}>{count}</span>
      </div>
      <div style={styles.rows}>{count ? children : <div style={styles.empty}>{empty}</div>}</div>
    </section>
  );
}

export default function CodeHealth({ repoId }) {
  const [report, setReport] = useState(null);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    api.getCodeHealth(repoId)
      .then(({ data }) => {
        if (cancelled) return;
        if (data?.error) throw new Error(data.error);
        setReport(data);
      })
      .catch(err => !cancelled && setError(err.message || 'Failed to load code-health candidates'))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [repoId]);

  const filtered = useMemo(() => {
    const source = report || {};
    if (!query.trim()) return source;
    return {
      ...source,
      file_candidates: (source.file_candidates || []).filter(item => matches(item, query)),
      function_candidates: (source.function_candidates || []).filter(item => matches(item, query)),
      duplicate_file_groups: (source.duplicate_file_groups || []).filter(item => matches(item, query)),
      duplicate_function_groups: (source.duplicate_function_groups || []).filter(item => matches(item, query))
    };
  }, [report, query]);

  if (loading) return <div style={styles.state}>Building the static code-health report…</div>;
  if (error) return <div style={{ ...styles.state, color: '#f87171' }}>{error}</div>;
  if (!report) return <div style={styles.state}>Select a repository to inspect unused and redundant code candidates.</div>;

  const files = filtered.file_candidates || [];
  const functions = filtered.function_candidates || [];
  const duplicateFiles = filtered.duplicate_file_groups || [];
  const duplicates = filtered.duplicate_function_groups || [];

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>Unused & Redundant Candidates</h2>
          <p style={styles.subtitle}>A list-based companion to the graphs, based on missing inbound references and repeated function names.</p>
        </div>
        <input
          value={query}
          onChange={event => setQuery(event.target.value)}
          placeholder="Search function or file…"
          style={styles.search}
        />
      </div>

      <div style={styles.notice}>
        <strong>Review before deleting.</strong> {report.caveat}
      </div>

      <div style={styles.summaryGrid}>
        <div style={styles.summaryCard}><strong>{report.summary?.files || 0}</strong><span>file candidates</span></div>
        <div style={styles.summaryCard}><strong>{report.summary?.functions || 0}</strong><span>function candidates</span></div>
        <div style={styles.summaryCard}><strong>{report.summary?.duplicate_files || 0}</strong><span>exact duplicate groups</span></div>
        <div style={styles.summaryCard}><strong>{report.summary?.duplicate_groups || 0}</strong><span>duplicate-name groups</span></div>
      </div>

      <Section
        title="Files with no inbound dependencies"
        hint="Isolated files have neither inbound nor outbound internal edges; unreferenced files may still be app entry points."
        count={files.length}
        empty="No matching file candidates."
      >
        {files.map(item => (
          <CandidateRow
            key={item.file}
            title={item.kind === 'isolated' ? 'Isolated file' : 'No inbound references'}
            path={item.file}
            reason={item.reason}
            confidence={item.confidence}
          />
        ))}
      </Section>

      <Section
        title="Exact duplicate files"
        hint="Files in each group have the same stored content hash, which is a strong redundancy signal."
        count={duplicateFiles.length}
        empty="No matching exact duplicate files."
      >
        {duplicateFiles.map(group => (
          <details key={group.content_hash} style={styles.duplicate}>
            <summary style={styles.duplicateSummary}>
              <strong>Identical content</strong>
              <span>{group.files?.length || 0} files</span>
            </summary>
            <div style={styles.occurrences}>
              {(group.files || []).map(file => (
                <code key={file} title={file} style={styles.path}>{compactPath(file)}</code>
              ))}
            </div>
          </details>
        ))}
      </Section>

      <Section
        title="Functions with no resolved callers"
        hint="Functions invoked by decorators, routes, reflection, or framework lifecycle hooks can appear here."
        count={functions.length}
        empty="No matching function candidates."
      >
        {functions.map((item, index) => (
          <CandidateRow
            key={`${item.file}:${item.line}:${item.name}:${index}`}
            title={item.name}
            path={item.file}
            line={item.line}
            reason={item.reason}
            confidence={item.confidence}
          />
        ))}
      </Section>

      <Section
        title="Repeated function names"
        hint="These are possible consolidation opportunities, not proof that implementations are duplicates."
        count={duplicates.length}
        empty="No matching duplicate-name groups."
      >
        {duplicates.map(group => (
          <details key={group.name} style={styles.duplicate}>
            <summary style={styles.duplicateSummary}>
              <strong>{group.name}</strong>
              <span>{group.occurrences?.length || 0} occurrences</span>
            </summary>
            <div style={styles.occurrences}>
              {(group.occurrences || []).map((item, index) => (
                <code key={`${item.file}:${item.line}:${index}`} title={item.file} style={styles.path}>
                  {compactPath(item.file)}{item.line ? `:${item.line}` : ''}
                </code>
              ))}
            </div>
          </details>
        ))}
      </Section>
    </div>
  );
}

const styles = {
  page: { padding: '4px 0 32px' },
  header: { display: 'flex', justifyContent: 'space-between', gap: '20px', alignItems: 'flex-end', marginBottom: '18px' },
  title: { margin: 0, color: 'var(--text-primary)', fontSize: '22px' },
  subtitle: { margin: '6px 0 0', color: 'var(--text-muted)', fontSize: '13px' },
  search: { width: '290px', maxWidth: '40%', padding: '10px 12px', color: 'var(--text-primary)', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: '9px', outline: 'none' },
  notice: { marginBottom: '14px', padding: '12px 14px', color: '#cbd5e1', background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.24)', borderRadius: '10px', fontSize: '12px', lineHeight: 1.55 },
  summaryGrid: { display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: '12px', marginBottom: '18px' },
  summaryCard: { display: 'flex', flexDirection: 'column', gap: '4px', padding: '15px', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '11px', color: 'var(--text-muted)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.06em' },
  section: { marginBottom: '16px', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '13px', overflow: 'hidden' },
  sectionHeader: { display: 'flex', justifyContent: 'space-between', gap: '16px', padding: '16px 18px', borderBottom: '1px solid var(--border)' },
  sectionTitle: { margin: 0, color: 'var(--text-primary)', fontSize: '15px' },
  sectionHint: { margin: '5px 0 0', color: 'var(--text-muted)', fontSize: '11px' },
  count: { alignSelf: 'center', padding: '4px 9px', background: 'var(--bg-elevated)', borderRadius: '10px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: '11px' },
  rows: { maxHeight: '430px', overflowY: 'auto' },
  row: { display: 'flex', justifyContent: 'space-between', gap: '18px', padding: '12px 18px', borderBottom: '1px solid var(--border)' },
  rowMain: { minWidth: 0, display: 'grid', gridTemplateColumns: 'minmax(110px, .55fr) minmax(180px, 1fr) minmax(240px, 1.6fr)', alignItems: 'center', gap: '12px' },
  rowTitle: { color: 'var(--text-primary)', fontSize: '12px', overflow: 'hidden', textOverflow: 'ellipsis' },
  path: { color: '#a5b4fc', fontFamily: 'var(--font-mono)', fontSize: '11px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  reason: { color: 'var(--text-muted)', fontSize: '11px', lineHeight: 1.45 },
  confidence: { alignSelf: 'center', flexShrink: 0, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: '10px' },
  duplicate: { padding: '12px 18px', borderBottom: '1px solid var(--border)' },
  duplicateSummary: { display: 'flex', justifyContent: 'space-between', cursor: 'pointer', color: 'var(--text-secondary)', fontSize: '12px' },
  occurrences: { display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px', padding: '10px 14px', background: 'var(--bg-primary)', borderRadius: '8px' },
  empty: { padding: '24px 18px', textAlign: 'center', color: 'var(--text-dim)', fontSize: '12px' },
  state: { minHeight: '360px', display: 'grid', placeItems: 'center', color: 'var(--text-muted)', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '14px' }
};
