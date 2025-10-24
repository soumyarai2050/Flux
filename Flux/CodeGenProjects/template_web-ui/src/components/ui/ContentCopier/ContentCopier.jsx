
import React, { useState } from 'react';
import IconButton from '@mui/material/IconButton';
import ContentCopy from '@mui/icons-material/ContentCopy';
import Check from '@mui/icons-material/Check';
import { copyToClipboard } from '../../../utils/core/stringUtils';

const ContentCopier = ({ text }) => {
    const [copied, setCopied] = useState(false);

    const handleCopy = (e) => {
        e.stopPropagation();
        copyToClipboard(text)
            .then(() => {
                setCopied(true);
                setTimeout(() => setCopied(false), 1000);
            })
            .catch((err) => {
                console.error('Failed to copy text to clipboard:', err);
            });
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
