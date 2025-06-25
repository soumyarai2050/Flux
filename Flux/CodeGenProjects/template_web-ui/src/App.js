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
import { getTheme, BaseColor, Theme as ThemeModes, DEFAULT_BASE_COLOR } from './theme';
import { PROJECT_NAME } from './constants';
import ErrorBoundary from './components/ErrorBoundary';
import Layout from './components/Layout';
import { DraggableProvider } from './contexts/DraggableContext';
// import { ScrollableProvider } from './contexts/ScrollableContext';

const THEME_MODE_STORAGE_KEY = 'appThemeMode';
const BASE_COLOR_STORAGE_KEY = 'appBaseColor';

function App() {
    // Redux state
    const { loading } = useSelector((state) => state.schema);
    const dispatch = useDispatch();

    // Detect system theme preference
    const prefersDarkMode = useMediaQuery('(prefers-color-scheme: dark)');

    // State for theme mode (light/dark)
    const [themeMode, setThemeMode] = useState(() => {
        const storedMode = localStorage.getItem(THEME_MODE_STORAGE_KEY);
        return storedMode ? storedMode : (prefersDarkMode ? ThemeModes.DARK : ThemeModes.LIGHT);
    });

    // State for base color
    const [currentBaseColor, setCurrentBaseColor] = useState(() => {
        // Start with default color, layout loading will override if needed
        return DEFAULT_BASE_COLOR;
    });

    // Memoized theme object for performance, depends on themeMode and currentBaseColor
    const muiTheme = useMemo(() => getTheme(themeMode, currentBaseColor), [themeMode, currentBaseColor]);

    // Fetch schema on initial load
    useEffect(() => {
        dispatch(getSchema());
    }, [dispatch]);

    // Effect to update localStorage when themeMode changes
    useEffect(() => {
        localStorage.setItem(THEME_MODE_STORAGE_KEY, themeMode);
    }, [themeMode]);

    // Note: We no longer save base color to localStorage since it's now saved per profile

    // Toggle theme mode
    const handleThemeToggle = () => {
        setThemeMode((prevMode) => (prevMode === ThemeModes.LIGHT ? ThemeModes.DARK : ThemeModes.LIGHT));
    };

    // Change base color
    const handleBaseColorChange = (newColor) => {

        if (Object.values(BaseColor).includes(newColor)) {
            setCurrentBaseColor(newColor);
        }
    };

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
                <DraggableProvider>
                    {/* <ScrollableProvider> */}
                    <Layout
                        theme={themeMode}
                        onThemeToggle={handleThemeToggle}
                        baseColor={currentBaseColor}
                        onBaseColorChange={handleBaseColorChange}
                        projectName={PROJECT_NAME}
                    />
                    {/* </ScrollableProvider> */}
                </DraggableProvider>
            </ErrorBoundary>
        </ThemeProvider>
    );
}

export default React.memo(App);
