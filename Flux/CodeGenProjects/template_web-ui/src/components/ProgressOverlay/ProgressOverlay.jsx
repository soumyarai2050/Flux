import React from 'react';
import { Box, LinearProgress, Typography, Button } from '@mui/material';
import { Close } from '@mui/icons-material';
import PropTypes from 'prop-types';

const ProgressOverlay = ({
    isVisible = false,
    current = 0,
    total = 0,
    onCancel,
    title = "Loading"
}) => {
    if (!isVisible) {
        return null;
    }

    const progressPercentage = total > 0 ? Math.round((current / total) * 100) : 0;

    return (
        <Box
            sx={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(0, 0, 0, 0.1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 9999,
                backdropFilter: 'blur(0.5px)'
            }}
            onClick={(e) => e.stopPropagation()}
        >
            <Box
                sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '12px',
                    minWidth: '300px'
                }}
            >
                <LinearProgress
                    variant="determinate"
                    value={progressPercentage}
                    sx={{
                        width: '50%',
                        height: '8px',
                        borderRadius: '4px',
                        backgroundColor: 'rgba(210, 130, 73, 0.2)',
                        '& .MuiLinearProgress-bar': {
                            borderRadius: '4px',
                            backgroundColor: '#5d4037'
                        }
                    }}
                />

                <Typography
                    variant="h6"
                    sx={{
                        fontWeight: 600,
                        fontSize: '1.2rem',
                        color: 'white',
                        textShadow: '0 1px 2px rgba(0,0,0,0.5)'
                    }}
                >
                    {progressPercentage}%
                </Typography>

                <Button
                    variant="contained"
                    startIcon={<Close />}
                    onClick={onCancel}
                    sx={{
                        backgroundColor: 'rgba(244, 67, 54, 0.9)',
                        color: 'white',
                        fontWeight: 500,
                        padding: '8px 16px',
                        borderRadius: '20px',
                        textTransform: 'none',
                        fontSize: '0.9rem',
                        boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                        '&:hover': {
                            backgroundColor: 'rgba(211, 47, 47, 0.95)',
                        },
                        transition: 'all 0.2s ease'
                    }}
                >
                    Cancel
                </Button>
            </Box>
        </Box>
    );
};

ProgressOverlay.propTypes = {
    isVisible: PropTypes.bool,
    current: PropTypes.number,
    total: PropTypes.number,
    onCancel: PropTypes.func.isRequired,
    title: PropTypes.string
};

export default ProgressOverlay;