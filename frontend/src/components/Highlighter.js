import React from 'react';

export default function Highlighter({ children, action = 'highlight', color = '#fbbf24' }) {
  const styles = {
    highlight: {
      background: `linear-gradient(104deg, ${color}00 0.9%, ${color}33 2.4%, ${color}22 5.8%, ${color}08 93%, ${color}1A 96%, ${color}00 98%)`,
      padding: '2px 6px',
      fontWeight: 600,
      display: 'inline',
      color: color,
      borderRadius: '3px',
    },
    underline: {
      borderBottom: `2px solid ${color}`,
      paddingBottom: '2px',
      fontWeight: 600,
      display: 'inline',
      color: color,
    }
  };

  return <span style={styles[action]}>{children}</span>;
}
