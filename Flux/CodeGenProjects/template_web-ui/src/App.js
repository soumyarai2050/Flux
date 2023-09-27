/* react and third-party library imports */
import './colors.css';
import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Box, ThemeProvider, CssBaseline, useMediaQuery } from '@mui/material';
import { HashLoader } from 'react-spinners';
/* redux CRUD and additional helper actions */
import { getSchema } from './features/schemaSlice';
/* custom components */
import { getTheme } from './theme';
import ErrorBoundary from './components/ErrorBoundary';
import Layout from './components/Layout';
import './App.css';
import { useState } from 'react';


function App() {
  /* react states from redux */
  const { loading } = useSelector((state) => state.schema);
  const prefersDarkMode = useMediaQuery('(prefers-color-scheme: dark)');
  const [mode, setMode] = useState(prefersDarkMode ? 'dark' : 'light');
  /* dispatch to trigger redux actions */
  const dispatch = useDispatch();
  const theme = getTheme(mode);

  useEffect(() => {
    /* fetch project schema. to be triggered only once when the component loads */
    dispatch(getSchema());
  }, [])

  const onChangeMode = () => {
    if (mode === 'light') {
      setMode('dark');
    } else {
      setMode('light');
    }

  }

  /* render page loader while schema is loaded */
  if (loading) {
    return (
      <Box className="app">
        <HashLoader />
      </Box>
    )
  }

  return (
    <ThemeProvider theme={theme}> {/* override the default theme */}
      <CssBaseline /> {/* to set-up consistent css through */}
      <ErrorBoundary>
        <Layout mode={mode} onChangeMode={onChangeMode} />
      </ErrorBoundary>
    </ThemeProvider>
  );
}

export default App = React.memo(App);
