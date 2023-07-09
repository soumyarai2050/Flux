/* react and third-party library imports */
import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Box, ThemeProvider, CssBaseline } from '@mui/material';
import { HashLoader } from 'react-spinners';
/* redux CRUD and additional helper actions */
import { getSchema } from './features/schemaSlice';
/* custom components */
import { theme } from './theme';
import ErrorBoundary from './components/ErrorBoundary';
import Layout from './components/Layout';
import './App.css';


function App() {
  /* react states from redux */
  const { loading } = useSelector((state) => state.schema);
  /* dispatch to trigger redux actions */
  const dispatch = useDispatch();

  useEffect(() => {
    /* fetch project schema. to be triggered only once when the component loads */
    dispatch(getSchema());
  }, [])

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
        <Layout />
      </ErrorBoundary>
    </ThemeProvider>
  );
}

export default App = React.memo(App);
