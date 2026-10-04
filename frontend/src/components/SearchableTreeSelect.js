import React, { useEffect, useMemo, useRef, useState } from 'react';

const normalizePath = (path = '') => path.replace(/\\/g, '/').replace(/\/+$/, '');

const relativePaths = (items) => {
  const paths = items.map(item => normalizePath(item.path)).filter(Boolean);
  if (!paths.length) return new Map();

  const splitPaths = paths.map(path => path.split('/'));
  let commonLength = Math.min(...splitPaths.map(parts => parts.length)) - 1;
  for (let index = 0; index < commonLength; index += 1) {
    const segment = splitPaths[0][index].toLowerCase();
    if (!splitPaths.every(parts => parts[index]?.toLowerCase() === segment)) {
      commonLength = index;
      break;
    }
  }

  return new Map(paths.map((path, index) => [
    path,
    splitPaths[index].slice(commonLength).join('/') || splitPaths[index].slice(-1)[0]
  ]));
};

const buildTree = (items, pathMap, groupByFile) => {
  const root = { children: new Map(), items: [] };
  items.forEach(item => {
    const normalized = normalizePath(item.path);
    const relative = pathMap.get(normalized) || normalized;
    const parts = relative.split('/').filter(Boolean);
    const branches = groupByFile ? parts : parts.slice(0, -1);
    const leafLabel = groupByFile ? item.label : (parts.at(-1) || item.label);
    let node = root;
    branches.forEach(part => {
      if (!node.children.has(part)) {
        node.children.set(part, { children: new Map(), items: [] });
      }
      node = node.children.get(part);
    });
    node.items.push({ ...item, leafLabel, relativePath: relative });
  });
  return root;
};

export default function SearchableTreeSelect({
  items = [],
  value = '',
  onChange,
  placeholder = 'Select an item',
  searchPlaceholder = 'Search by name or path…',
  disabled = false,
  groupByFile = false,
  emptyOption = null
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const rootRef = useRef(null);

  useEffect(() => {
    const closeOnOutsideClick = (event) => {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener('mousedown', closeOnOutsideClick);
    return () => document.removeEventListener('mousedown', closeOnOutsideClick);
  }, []);

  const pathMap = useMemo(() => relativePaths(items), [items]);
  const filteredItems = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return items;
    return items.filter(item => {
      const relative = pathMap.get(normalizePath(item.path)) || item.path || '';
      return `${item.label} ${relative} ${item.secondary || ''}`.toLowerCase().includes(needle);
    });
  }, [items, pathMap, query]);
  const tree = useMemo(
    () => buildTree(filteredItems, pathMap, groupByFile),
    [filteredItems, pathMap, groupByFile]
  );
  const selected = items.find(item => item.value === value);

  const choose = (nextValue) => {
    onChange(nextValue);
    setOpen(false);
    setQuery('');
  };

  const renderNode = (node, depth = 0, keyPrefix = 'root') => {
    const folders = [...node.children.entries()].sort(([a], [b]) => a.localeCompare(b));
    const leaves = [...node.items].sort((a, b) => a.leafLabel.localeCompare(b.leafLabel));
    return (
      <>
        {folders.map(([name, child]) => (
          <div key={`${keyPrefix}/${name}`}>
            <div style={{ ...styles.folder, paddingLeft: 10 + depth * 16 }}>
              <span style={styles.folderIcon}>▾</span>
              <span>{name}</span>
            </div>
            {renderNode(child, depth + 1, `${keyPrefix}/${name}`)}
          </div>
        ))}
        {leaves.map(item => (
          <button
            type="button"
            key={item.value}
            onClick={() => choose(item.value)}
            title={item.path}
            style={{
              ...styles.item,
              paddingLeft: 22 + depth * 16,
              ...(item.value === value ? styles.itemSelected : {})
            }}
          >
            <span style={styles.itemIcon}>{groupByFile ? 'ƒ' : '•'}</span>
            <span style={styles.itemText}>{item.leafLabel}</span>
            {item.secondary && <span style={styles.secondary}>{item.secondary}</span>}
          </button>
        ))}
      </>
    );
  };

  return (
    <div ref={rootRef} style={styles.root}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen(current => !current)}
        style={{ ...styles.trigger, ...(disabled ? styles.disabled : {}) }}
      >
        <span style={selected ? styles.selectedText : styles.placeholder}>
          {selected ? `${selected.label} — ${pathMap.get(normalizePath(selected.path)) || selected.path}` : placeholder}
        </span>
        <span style={styles.chevron}>{open ? '▴' : '▾'}</span>
      </button>

      {open && !disabled && (
        <div style={styles.popover}>
          <input
            autoFocus
            value={query}
            onChange={event => setQuery(event.target.value)}
            placeholder={searchPlaceholder}
            style={styles.search}
          />
          <div style={styles.tree}>
            {emptyOption && !query && (
              <button type="button" onClick={() => choose('')} style={styles.item}>
                <span style={styles.itemText}>{emptyOption}</span>
              </button>
            )}
            {filteredItems.length ? renderNode(tree) : (
              <div style={styles.empty}>No matching items</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  root: { position: 'relative', flex: 1, minWidth: 0 },
  trigger: { width: '100%', minHeight: '40px', padding: '9px 12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', background: 'var(--bg-input)', color: 'var(--text-primary)', cursor: 'pointer', textAlign: 'left', fontSize: '13px' },
  disabled: { opacity: 0.55, cursor: 'not-allowed' },
  selectedText: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'var(--font-mono)', fontSize: '12px' },
  placeholder: { color: 'var(--text-muted)' },
  chevron: { color: 'var(--text-muted)', flexShrink: 0 },
  popover: { position: 'absolute', zIndex: 100, left: 0, right: 0, top: 'calc(100% + 6px)', padding: '8px', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', boxShadow: '0 16px 40px rgba(0,0,0,0.4)' },
  search: { width: '100%', boxSizing: 'border-box', padding: '9px 11px', marginBottom: '7px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', outline: 'none', background: 'var(--bg-input)', color: 'var(--text-primary)', fontSize: '13px' },
  tree: { maxHeight: '360px', overflowY: 'auto', padding: '2px 0' },
  folder: { height: '27px', display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600 },
  folderIcon: { color: 'var(--text-dim)', width: '10px' },
  item: { width: '100%', minHeight: '30px', padding: '6px 10px', display: 'flex', alignItems: 'center', gap: '7px', border: 0, borderRadius: 'var(--radius-sm)', background: 'transparent', color: 'var(--text-secondary)', cursor: 'pointer', textAlign: 'left', fontSize: '12px' },
  itemSelected: { background: 'var(--accent-glow)', color: 'var(--text-primary)' },
  itemIcon: { width: '12px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' },
  itemText: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'var(--font-mono)' },
  secondary: { marginLeft: 'auto', color: 'var(--text-dim)', fontSize: '10px', flexShrink: 0 },
  empty: { padding: '20px 12px', color: 'var(--text-muted)', textAlign: 'center', fontSize: '12px' }
};
