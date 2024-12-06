import React from 'react';
import { ThemeProvider, CssBaseline, createTheme } from '@mui/material';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import DeviceConnection from './components/DeviceConnection';
import CommandCenter from './components/CommandCenter';
import FileTransfer from './components/FileTransfer';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#2196f3',
    },
    secondary: {
      main: '#f50057',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<DeviceConnection />} />
            <Route path="/command-center" element={<CommandCenter />} />
            <Route path="/file-transfer" element={<FileTransfer />} />
          </Routes>
        </Layout>
      </Router>
    </ThemeProvider>
  );
}

export default App;
