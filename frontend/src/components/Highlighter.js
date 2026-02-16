import React from 'react';

export default function Highlighter({ children, action = 'highlight', color = '#FFED4A' }) {
  const styles = {
    highlight: {
      background: `linear-gradient(104deg, ${color}00 0.9%, ${color}FF 2.4%, ${color}80 5.8%, ${color}1A 93%, ${color}B3 96%, ${color}00 98%), linear-gradient(183deg, ${color}00 0%, ${color}4D 7.9%, ${color}00 15%)`,
      padding: '2px 4px',
      fontWeight: 'bold',
      display: 'inline'
    },
    underline: {
      borderBottom: `3px solid ${color}`,
      paddingBottom: '2px',
      fontWeight: 'bold',
      display: 'inline'
    }
  };

  return <span style={styles[action]}>{children}</span>;
}
