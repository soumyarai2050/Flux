import React, { useState } from 'react';
import PropTypes from 'prop-types';
import Tooltip from '@mui/material/Tooltip';
import IconButton from '@mui/material/IconButton';
import ContentCopy from '@mui/icons-material/ContentCopy';
import Box from '@mui/material/Box';
import { copyToClipboard } from '../../../utils/core/stringUtils';

/**
 * CustomToolTip component that displays a tooltip with a copy icon
 * Clicking the copy icon copies the tooltip text to clipboard
 *
 * @param {string} title - The tooltip text content
 * @param {string} placement - Tooltip placement position
 * @param {ReactNode} children - Child element to wrap with tooltip (optional)
 * @param {boolean} showCopyIcon - Show copy icon in tooltip
 * @param {string} copySuccessMessage - Message shown when copy succeeds
 * @param {number} copySuccessDuration - Duration to show success state in ms
 */
const CustomToolTip = ({
  title,
  placement = 'top',
  children = null,
  showCopyIcon = true,
  copySuccessMessage = 'Copied!',
  copySuccessDuration = 2000
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopyClick = (e) => {
    e.stopPropagation();
    if (title) {
      copyToClipboard(title)
        .then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), copySuccessDuration);
        })
        .catch((err) => {
          console.error('Failed to copy text:', err);
        });
    }
  };

  return (
    <Tooltip
      title={
        <Box sx={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>{title}</span>
          {showCopyIcon && (
            <IconButton
              size="small"
              onClick={handleCopyClick}
              sx={{
                padding: '2px',
                color: 'inherit',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                }
              }}
              title={copied ? copySuccessMessage : 'Copy to clipboard'}
            >
              {copied ? (
                <span style={{ fontSize: '16px' }}>✓</span>
              ) : (
                <ContentCopy sx={{ fontSize: '16px' }} />
              )}
            </IconButton>
          )}
        </Box>
      }
      placement={placement}
    >
      {children}
    </Tooltip>
  );
};

CustomToolTip.propTypes = {
  title: PropTypes.string.isRequired,
  placement: PropTypes.oneOf([
    'top',
    'bottom',
    'left',
    'right',
    'top-start',
    'top-end',
    'bottom-start',
    'bottom-end',
    'left-start',
    'left-end',
    'right-start',
    'right-end'
  ]),
  children: PropTypes.node,
  showCopyIcon: PropTypes.bool,
  copySuccessMessage: PropTypes.string,
  copySuccessDuration: PropTypes.number
};

CustomToolTip.defaultProps = {
  placement: 'top',
  showCopyIcon: true,
  copySuccessMessage: 'Copied!',
  copySuccessDuration: 2000
};

export default CustomToolTip;
