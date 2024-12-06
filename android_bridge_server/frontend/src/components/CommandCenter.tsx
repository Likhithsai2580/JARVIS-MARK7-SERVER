import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  List,
  ListItem,
  ListItemText,
  Divider,
  Alert,
  Grid,
  Chip,
} from '@mui/material';
import { Send as SendIcon, Code as CodeIcon } from '@mui/icons-material';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:3000';

interface CommandLog {
  timestamp: Date;
  command: string;
  status: 'success' | 'error';
  response?: string;
}

const EXAMPLE_COMMANDS = [
  {
    name: 'Get Battery Level',
    command: 'getBatteryLevel',
    params: {},
  },
  {
    name: 'Take Screenshot',
    command: 'takeScreenshot',
    params: {},
  },
  {
    name: 'Launch App',
    command: 'launchApp',
    params: { packageName: 'com.example.app' },
  },
];

const CommandCenter: React.FC = () => {
  const [command, setCommand] = useState('');
  const [params, setParams] = useState('');
  const [deviceToken, setDeviceToken] = useState('');
  const [commandLogs, setCommandLogs] = useState<CommandLog[]>([]);
  const [error, setError] = useState<string>('');
  const [isValidJson, setIsValidJson] = useState(true);

  const validateJson = (jsonString: string): boolean => {
    if (!jsonString.trim()) return true;
    try {
      JSON.parse(jsonString);
      return true;
    } catch {
      return false;
    }
  };

  const handleParamsChange = (value: string) => {
    setParams(value);
    setIsValidJson(validateJson(value));
  };

  const handleExampleCommand = (example: typeof EXAMPLE_COMMANDS[0]) => {
    setCommand(example.command);
    setParams(JSON.stringify(example.params, null, 2));
  };

  const handleSendCommand = async () => {
    // Validate command format
    if (!isValidCommand(command)) {
      setError('Invalid command format');
      return;
    }
    
    // Sanitize parameters
    const sanitizedParams = sanitizeParams(params);
    
    // Rate limiting
    if (!checkRateLimit()) {
      setError('Too many requests. Please wait.');
      return;
    }
    
    try {
      setError('');
      const response = await axios.post(`${API_URL}/api/send-command`, {
        targetDevice: deviceToken,
        command,
        params: params ? JSON.parse(params) : {},
      });

      setCommandLogs((prev) => [
        {
          timestamp: new Date(),
          command,
          status: response.data.success ? 'success' : 'error',
          response: JSON.stringify(response.data),
        },
        ...prev,
      ]);

      // Clear command input after successful send
      setCommand('');
      setParams('');
    } catch (err) {
      setError('Failed to send command. Please check your inputs and try again.');
      console.error(err);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Typography variant="h4" gutterBottom>
            Command Center
          </Typography>
        </Grid>

        {error && (
          <Grid item xs={12}>
            <Alert severity="error">{error}</Alert>
          </Grid>
        )}

        {/* Command Input Section */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box
                component="form"
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 2,
                }}
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendCommand();
                }}
              >
                <TextField
                  label="Device Token"
                  value={deviceToken}
                  onChange={(e) => setDeviceToken(e.target.value)}
                  required
                  fullWidth
                />

                <TextField
                  label="Command"
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  required
                  fullWidth
                />

                <TextField
                  label="Parameters (JSON)"
                  value={params}
                  onChange={(e) => handleParamsChange(e.target.value)}
                  error={!isValidJson}
                  helperText={!isValidJson && 'Invalid JSON format'}
                  multiline
                  rows={4}
                  placeholder='{"param1": "value1", "param2": "value2"}'
                  fullWidth
                />

                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<SendIcon />}
                  onClick={handleSendCommand}
                  disabled={!command || !deviceToken || !isValidJson}
                >
                  Send Command
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Example Commands Section */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Example Commands
              </Typography>
              <List>
                {EXAMPLE_COMMANDS.map((example, index) => (
                  <ListItem
                    key={index}
                    button
                    onClick={() => handleExampleCommand(example)}
                  >
                    <ListItemText
                      primary={example.name}
                      secondary={
                        <>
                          <Typography component="span" variant="body2" color="text.secondary">
                            {example.command}
                          </Typography>
                          <br />
                          <Typography component="span" variant="body2">
                            {JSON.stringify(example.params)}
                          </Typography>
                        </>
                      }
                    />
                    <CodeIcon color="action" />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Command History Section */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Command History
              </Typography>
              <List>
                {commandLogs.map((log, index) => (
                  <React.Fragment key={index}>
                    <ListItem>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography
                              component="span"
                              color={log.status === 'success' ? 'success.main' : 'error.main'}
                            >
                              {log.command}
                            </Typography>
                            <Chip
                              label={log.status}
                              color={log.status === 'success' ? 'success' : 'error'}
                              size="small"
                            />
                          </Box>
                        }
                        secondary={
                          <>
                            <Typography component="span" variant="body2" color="text.secondary">
                              {log.timestamp.toLocaleTimeString()}
                            </Typography>
                            {log.response && (
                              <Typography component="p" variant="body2">
                                Response: {log.response}
                              </Typography>
                            )}
                          </>
                        }
                      />
                    </ListItem>
                    {index < commandLogs.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default CommandCenter; 