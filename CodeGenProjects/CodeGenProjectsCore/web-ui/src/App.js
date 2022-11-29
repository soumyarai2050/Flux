import './App.css';
import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { getSchema } from './features/schemaSlice';
import { CssBaseline } from '@mui/material';
import { ThemeProvider } from '@mui/material/styles';
import Layout from './components/Layout';
import { HashLoader } from 'react-spinners';
import { Box } from '@mui/material';
import { makeStyles } from '@mui/styles';
import { theme } from './theme';

const useStyles = makeStyles({
  root: {
    height: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  }
})

function App() {

  const dispatch = useDispatch();
  const { schema, loading } = useSelector((state) => state.schema);
  const classes = useStyles();

  useEffect(() => {
    dispatch(getSchema());
  }, [])

  if (loading) {
    return (
      <Box className={classes.root}>
        <HashLoader />
      </Box>

    )
  }

  return (
    <>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Layout schema={schema} />
      </ThemeProvider>
    </>
  );
}

export default App;
