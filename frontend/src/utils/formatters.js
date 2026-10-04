export const formatFilePath = (path, depth = 2) => {
  if (!path) return '';
  const normalized = path.replace(/\\/g, '/');
  const parts = normalized.split('/').filter(Boolean);
  if (parts.length === 0) return normalized;
  return parts.slice(-depth).join('/');
};

export const getFileName = (path) => {
  if (!path) return '';
  const normalized = path.replace(/\\/g, '/');
  const parts = normalized.split('/');
  return parts[parts.length - 1];
};

export const formatEvidenceText = (text) => {
  if (!text) return '';
  return text.replace(/File:\s*([^\s,\]]+)/g, (match, path) => {
    return `File: ${formatFilePath(path, 3)}`;
  });
};
