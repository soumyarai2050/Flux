/* ErrorBoundary.jsx
 * Enhanced Error Boundary to catch errors, display a user-friendly UI, and allow retries.
 */

import React from 'react';
import PropTypes from 'prop-types';
import Alert from '@mui/material/Alert';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import ErrorOutline from '@mui/icons-material/ErrorOutline';
import { ErrorBoundary as Boundary } from 'react-error-boundary';

/**
 * @function ErrorFallback
 * @description Fallback component to display when an error occurs within an ErrorBoundary.
 * It shows a user-friendly message, the error details, and a retry button.
 * @param {object} props - The properties for the component.
 * @param {Error} props.error - The error object caught by the ErrorBoundary.
 * @param {Function} props.onReset - Function provided by react-error-boundary to reset the error state.
 * @returns {React.ReactElement} The rendered error fallback UI.
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
    onReset: PropTypes.func.isRequired,
};

/**
 * @function ErrorBoundary
 * @description A higher-order component that catches JavaScript errors anywhere in its child component tree,
 * logs those errors, and displays a fallback UI instead of the crashed component tree.
 * It uses `react-error-boundary` internally.
 * @param {object} props - Component props.
 * @param {React.ReactNode} props.children - Child components to be wrapped by the error boundary.
 * @returns {React.ReactElement} The wrapped children or the error fallback UI.
 */
const ErrorBoundary = ({ children }) => {
    /**
     * Handles the reset of the error boundary by reloading the entire window.
     * This is a common strategy for top-level error boundaries to ensure a clean state.
     */
    const handleReset = () => {
        window.location.reload();
    };

    return (
        <Boundary
            FallbackComponent={ErrorFallback}
            onReset={handleReset}
        >
            {children}
        </Boundary>
    );
};

// Prop validation for ErrorBoundary
ErrorBoundary.propTypes = {
    children: PropTypes.node.isRequired,
};

export default React.memo(ErrorBoundary);
