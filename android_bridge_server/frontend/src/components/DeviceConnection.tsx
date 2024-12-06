import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  Grid,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
} from '@mui/material';
import {
  QrCode,
  Code,
  CloudUpload,
  CloudDownload,
  Circle as StatusIcon,
} from '@mui/icons-material';
import { QRCodeSVG } from 'qrcode.react';
import axios from 'axios';
import { io, Socket } from 'socket.io-client';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:3000';

interface Endpoint {
  name: string;
  path: string;
  method: string;
  description: string;
  icon: React.ReactNode;
}

const endpoints: Endpoint[] = [
  {
    name: 'Generate Connection Code',
    path: '/api/generate-connection-code',
    method: 'GET',
    description: 'Generate a QR code for device connection',
    icon: <QrCode />,
  },
  {
    name: 'Send Command',
    path: '/api/send-command',
    method: 'POST',
    description: 'Send commands to connected device',
    icon: <Code />,
  },
  {
    name: 'Upload File',
    path: '/api/upload',
    method: 'POST',
    description: 'Upload files to the server',
    icon: <CloudUpload />,
  },
  {
    name: 'Download File',
    path: '/api/download/:filename',
    method: 'GET',
    description: 'Download files from the server',
    icon: <CloudDownload />,
  },
];

const DeviceConnection: React.FC = () => {
  const [qrCode, setQrCode] = useState<string>('');
  const [socket, setSocket] = useState<Socket | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected');
  const [error, setError] = useState<string>('');
  const [apiStatus, setApiStatus] = useState<'online' | 'offline'>('offline');

  useEffect(() => {
    // Check API Status
    const checkApiStatus = async () => {
      try {
        await axios.get(`${API_URL}/api/generate-connection-code`);
        setApiStatus('online');
      } catch (err) {
        setApiStatus('offline');
        console.error('API Status Check Failed:', err);
      }
    };

    // Generate QR code
    const generateQR = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/generate-connection-code`);
        setQrCode(response.data.qrCode);
        
        // Initialize socket connection
        const newSocket = io(API_URL);
        setSocket(newSocket);

        newSocket.on('connect', () => {
          setConnectionStatus('connecting');
        });

        newSocket.on('authenticated', (data) => {
          if (data.success) {
            setConnectionStatus('connected');
          }
        });

        newSocket.on('disconnect', () => {
          setConnectionStatus('disconnected');
        });

        return () => {
          newSocket.close();
        };
      } catch (err) {
        setError('Failed to generate connection code');
        console.error(err);
      }
    };

    checkApiStatus();
    generateQR();

    // Poll API status every 30 seconds
    const statusInterval = setInterval(checkApiStatus, 30000);
    return () => clearInterval(statusInterval);
  }, []);

  return (
    <Box sx={{ p: 3 }}>
      <Grid container spacing={3}>
        {/* API Status Section */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <StatusIcon
                  sx={{
                    color: apiStatus === 'online' ? 'success.main' : 'error.main',
                  }}
                />
                <Typography variant="h6">
                  API Status: {apiStatus.toUpperCase()}
                </Typography>
                <Chip
                  label={`${API_URL}`}
                  variant="outlined"
                  size="small"
                  sx={{ ml: 2 }}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* QR Code Section */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Device Connection
              </Typography>
              {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}
              <Box
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 2,
                }}
              >
                {qrCode ? (
                  <Box sx={{ p: 2, bgcolor: 'white' }}>
                    <QRCodeSVG value={qrCode} size={200} />
                  </Box>
                ) : (
                  <CircularProgress />
                )}
                <Typography
                  variant="body1"
                  color={
                    connectionStatus === 'connected'
                      ? 'success.main'
                      : connectionStatus === 'connecting'
                      ? 'warning.main'
                      : 'error.main'
                  }
                >
                  Status: {connectionStatus.charAt(0).toUpperCase() + connectionStatus.slice(1)}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Available Endpoints Section */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Available Endpoints
              </Typography>
              <List>
                {endpoints.map((endpoint) => (
                  <ListItem key={endpoint.path}>
                    <ListItemIcon>{endpoint.icon}</ListItemIcon>
                    <ListItemText
                      primary={endpoint.name}
                      secondary={
                        <>
                          <Typography component="span" variant="body2" color="text.secondary">
                            {endpoint.method} {endpoint.path}
                          </Typography>
                          <br />
                          <Typography component="span" variant="body2">
                            {endpoint.description}
                          </Typography>
                        </>
                      }
                    />
                    <Chip
                      label={endpoint.method}
                      color={endpoint.method === 'GET' ? 'success' : 'primary'}
                      size="small"
                      sx={{ ml: 1 }}
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DeviceConnection; 