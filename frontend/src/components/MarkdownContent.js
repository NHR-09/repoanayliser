import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const normalizeMarkdown = (value = '') => value
  .replace(/&#x20;/gi, ' ')
  .replace(/\\([|`*_#~-])/g, '$1')
  .replace(/^\s*•\s+/gm, '- ');

export default function MarkdownContent({ children }) {
  if (!children) return null;
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children: heading, ...props }) => <h2 style={styles.h2} {...props}>{heading}</h2>,
        h2: ({ children: heading, ...props }) => <h3 style={styles.h3} {...props}>{heading}</h3>,
        h3: ({ children: heading, ...props }) => <h4 style={styles.h4} {...props}>{heading}</h4>,
        p: props => <p style={styles.paragraph} {...props} />,
        ul: props => <ul style={styles.list} {...props} />,
        ol: props => <ol style={styles.list} {...props} />,
        li: props => <li style={styles.listItem} {...props} />,
        table: props => <div style={styles.tableWrap}><table style={styles.table} {...props} /></div>,
        th: props => <th style={styles.th} {...props} />,
        td: props => <td style={styles.td} {...props} />,
        blockquote: props => <blockquote style={styles.blockquote} {...props} />,
        hr: props => <hr style={styles.hr} {...props} />,
        pre: props => <pre style={styles.pre} {...props} />,
        code: ({ className, children: codeText, ...props }) => {
          const isBlock = Boolean(className) || String(codeText).includes('\n');
          return (
            <code
              className={className}
              style={isBlock ? styles.code : styles.inlineCode}
              {...props}
            >
              {codeText}
            </code>
          );
        }
      }}
    >
      {normalizeMarkdown(children)}
    </ReactMarkdown>
  );
}

const styles = {
  h2: { margin: '20px 0 8px', fontSize: '18px', color: 'var(--text-primary)' },
  h3: { margin: '18px 0 8px', fontSize: '16px', color: 'var(--text-primary)' },
  h4: { margin: '14px 0 6px', fontSize: '14px', color: 'var(--text-secondary)' },
  paragraph: { margin: '0 0 10px', lineHeight: 1.75 },
  list: { margin: '0 0 12px', paddingLeft: '24px' },
  listItem: { marginBottom: '5px', lineHeight: 1.65 },
  tableWrap: { overflowX: 'auto', margin: '12px 0 18px', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: '12px' },
  th: { padding: '9px 11px', textAlign: 'left', background: 'var(--bg-elevated)', color: 'var(--text-primary)', borderBottom: '1px solid var(--border)' },
  td: { padding: '9px 11px', verticalAlign: 'top', borderBottom: '1px solid var(--border)', color: 'var(--text-secondary)' },
  blockquote: { margin: '12px 0', padding: '4px 14px', borderLeft: '3px solid var(--text-muted)', color: 'var(--text-muted)' },
  hr: { border: 0, borderTop: '1px solid var(--border)', margin: '18px 0' },
  pre: { margin: '12px 0', padding: '14px', overflowX: 'auto', background: 'var(--bg-primary)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)' },
  code: { fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-secondary)' },
  inlineCode: { padding: '2px 5px', background: 'var(--bg-elevated)', borderRadius: '4px', fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-primary)' }
};
