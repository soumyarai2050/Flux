
import React, { useState } from 'react';
import { IconButton } from '@mui/material';
import { ContentCopy, Check } from '@mui/icons-material';

const ContentCopier = ({ text }) => {
    const [copied, setCopied] = useState(false);

    const handleCopy = (e) => {
        e.stopPropagation();
        if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
            navigator.clipboard.writeText(text)
                .then(() => {
                    setCopied(true);
                    setTimeout(() => setCopied(false), 1000);
                })
                .catch((err) => console.error('Failed to copy text using Clipboard API:', err));
        } else {
            // Fallback for older browsers or insecure contexts
            try {
                const textArea = document.createElement('textarea');
                textArea.value = text;
                textArea.style.position = 'fixed';
                textArea.style.left = '-9999px';
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                setCopied(true);
                setTimeout(() => setCopied(false), 1000);
            } catch (err) {
                console.error('Failed to copy text using execCommand:', err);
            }
        }
    };

    return (
        <IconButton
            title="Copy"
            onClick={handleCopy}
            size="small"
        >
            {copied ? <Check sx={{ color: 'var(--blue-info)' }} fontSize="small" /> : <ContentCopy fontSize="small" />}
        </IconButton>
    );
};

export default ContentCopier;
