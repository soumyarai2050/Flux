/* ErrorBoundary.jsx
 * Enhanced Error Boundary to catch errors, display a user-friendly UI, and allow retries.
 */

import React from 'react';
import PropTypes from 'prop-types';
import { Alert, Typography, Box, Button, Stack } from '@mui/material';
import { ErrorBoundary as Boundary } from 'react-error-boundary';
import { ErrorOutline } from '@mui/icons-material';

/**
 * Fallback component to display when an error occurs.
 * @param {Object} error - The error object.
 * @param {Function} onReset - Function to reset the error boundary.
 */
function ErrorFallback({ error, onReset }) {
    // Log the error for debugging or external monitoring
    console.error('ErrorBoundary caught an error:', error);

    return (
        <Box sx={{ padding: 4, textAlign: 'center' }}>
            <Stack spacing={3} alignItems="center">
                <Typography variant="h4" color="error" gutterBottom>
                    <ErrorOutline sx={{ verticalAlign: 'middle', mr: 1 }} />
                    Oops! Something went wrong.
                </Typography>

                <Alert severity="error" sx={{ width: '100%', textAlign: 'left' }}>
                    <Typography variant="subtitle1" gutterBottom>
                        {error?.message || 'An unexpected error occurred.'}
                    </Typography>
                    {error?.stack && (
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                            {error.stack}
                        </Typography>
                    )}
                </Alert>

                <Button variant="contained" color="primary" onClick={onReset}>
                    Retry
                </Button>
            </Stack>
        </Box>
    );
}

// Prop validation for ErrorFallback
ErrorFallback.propTypes = {
    error: PropTypes.object.isRequired,
    resetErrorBoundary: PropTypes.func.isRequired,
};

/**
 * ErrorBoundary component to wrap around application parts prone to errors.
 * @param {Object} props - Component props.
 * @param {React.ReactNode} props.children - Child components to be wrapped.
 */
const ErrorBoundary = ({ children }) => (
    <Boundary
        FallbackComponent={ErrorFallback}
        onReset={() => {
            console.warn('Error boundary reset triggered.');
        }}
    >
        {children}
    </Boundary>
);

// Prop validation for ErrorBoundary
ErrorBoundary.propTypes = {
    children: PropTypes.node.isRequired,
};

export default React.memo(ErrorBoundary);
