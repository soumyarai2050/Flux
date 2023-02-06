import './App.css';
import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { getSchema } from './features/schemaSlice';
import { CssBaseline } from '@mui/material';
import { ThemeProvider } from '@mui/material/styles';
import Layout from './components/Layout';
import { HashLoader } from 'react-spinners';
import { Box } from '@mui/material';
import { theme } from './theme';
import ErrorBoundary from './components/ErrorBoundary';

function App() {

  const dispatch = useDispatch();
  const { schema, loading } = useSelector((state) => state.schema);

  useEffect(() => {
    dispatch(getSchema());
  }, [])

  if (loading) {
    return (
      <Box className="app">
        <HashLoader />
      </Box>
    )
  }

  return (
    <>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <ErrorBoundary>
          <Layout schema={schema} />
        </ErrorBoundary>
      </ThemeProvider>
    </>
  );
}

export default App;
