import React, { useEffect, useRef } from 'react';

/**
 * ClipboardCopier
 *
 * A hidden component that copies a given text to the clipboard.
 * It first attempts to use the modern Clipboard API, and if not available,
 * falls back to using document.execCommand('copy').
 *
 * @param {Object} props - Component props.
 * @param {string} props.text - The text content to be copied to the clipboard.
 *
 */
const ClipboardCopier = ({ text }) => {
  const textRef = useRef(null);

  useEffect(() => {
    if (text) {
      // Note: disabled navigator API for copy
      // First try using the modern Clipboard API
      if (false && navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        navigator.clipboard
          .writeText(text)
          .catch((err) => console.error('Failed to copy text using Clipboard API:', err));
      } else {
        // Fallback for older browsers
        const textArea = textRef.current;
        if (!textArea) return;
        textArea.focus();
        textArea.select();
        try {
          if (document.queryCommandSupported && document.queryCommandSupported('copy')) {
            document.execCommand('copy');
          } else {
            console.error('Copy command is not supported');
          }
        } catch (err) {
          console.error('Failed to copy text using execCommand:', err);
        }
      }
    }
  }, [text]);

  return (
    <textarea
      ref={textRef}
      defaultValue={text}
      style={{
        position: 'fixed',
        left: '-9999px',
        top: '-9999px',
        opacity: 0,
      }}
      readOnly
      // aria-hidden='true'
    />
  );
};

export default ClipboardCopier;
