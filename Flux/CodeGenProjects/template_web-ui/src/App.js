/* App.js
 * Main application component for initializing theme, loading schema, and rendering layout.
 */
import './colors.css';
import './App.css';
import React, { useEffect, useState, useMemo } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Box, ThemeProvider, CssBaseline, useMediaQuery } from '@mui/material';
import { HashLoader } from 'react-spinners';
import { getSchema } from './features/schemaSlice';
import { getTheme } from './theme';
import { PROJECT_NAME } from './constants';
import ErrorBoundary from './components/ErrorBoundary';
import Layout from './components/Layout';


function App() {
    // Redux state
    const { loading } = useSelector((state) => state.schema);

    // Detect system theme preference
    const prefersDarkMode = useMediaQuery('(prefers-color-scheme: dark)');
    const [theme, setTheme] = useState(prefersDarkMode ? 'dark' : 'light');

    // Redux dispatch
    const dispatch = useDispatch();

    // Memoized theme object for performance
    const muiTheme = useMemo(() => getTheme(theme), [theme]);

    // Fetch schema on initial load
    useEffect(() => {
        dispatch(getSchema());
    }, [dispatch]);

    // Sync mode with system preference
    useEffect(() => {
        setTheme(prefersDarkMode ? 'dark' : 'light');
    }, [prefersDarkMode]);

    // Toggle theme mode
    const handleThemeToggle = () => setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));

    // Render loader while schema is loading
    if (loading) {
        return (
            <Box className="app" sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
                <HashLoader size={50} color={muiTheme.palette.primary.main} />
            </Box>
        );
    }

    return (
        <ThemeProvider theme={muiTheme}>
            <CssBaseline /> {/* Ensures consistent baseline styling */}
            <ErrorBoundary>
                <Layout theme={theme} onThemeToggle={handleThemeToggle} projectName={PROJECT_NAME} />
            </ErrorBoundary>
        </ThemeProvider>
    );
}

export default React.memo(App);
