import React, { useState, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  Button,
  Typography,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Alert,
  TextField,
  Grid,
  Chip,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  CloudDownload as DownloadIcon,
  Delete as DeleteIcon,
  Folder as FolderIcon,
} from '@mui/icons-material';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:3000';

interface FileTransferLog {
  timestamp: Date;
  fileName: string;
  type: 'upload' | 'download';
  status: 'success' | 'error';
  size?: number;
}

const FileTransfer: React.FC = () => {
  const [deviceToken, setDeviceToken] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [downloadFileName, setDownloadFileName] = useState('');
  const [transferLogs, setTransferLogs] = useState<FileTransferLog[]>([]);
  const [error, setError] = useState<string>('');
  const [availableFiles, setAvailableFiles] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !deviceToken) return;

    setError('');
    setUploading(true);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('token', deviceToken);

      const response = await axios.post(`${API_URL}/api/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const progress = progressEvent.total
            ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
            : 0;
          setUploadProgress(progress);
        },
      });

      setTransferLogs((prev) => [
        {
          timestamp: new Date(),
          fileName: file.name,
          type: 'upload',
          status: response.data.success ? 'success' : 'error',
          size: file.size,
        },
        ...prev,
      ]);

      // Clear the file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err) {
      setError('Failed to upload file. Please try again.');
      console.error(err);
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleFileDownload = async () => {
    if (!downloadFileName || !deviceToken) return;

    setError('');
    try {
      const response = await axios.get(
        `${API_URL}/api/download/${downloadFileName}`,
        {
          params: { token: deviceToken },
          responseType: 'blob',
        }
      );

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', downloadFileName);
      document.body.appendChild(link);
      link.click();
      link.remove();

      setTransferLogs((prev) => [
        {
          timestamp: new Date(),
          fileName: downloadFileName,
          type: 'download',
          status: 'success',
        },
        ...prev,
      ]);

      setDownloadFileName('');
    } catch (err) {
      setError('Failed to download file. Please check the file name and try again.');
      console.error(err);
    }
  };

  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return '';
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`;
  };

  return (
    <Box sx={{ p: 3 }}>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Typography variant="h4" gutterBottom>
            File Transfer
          </Typography>
        </Grid>

        {error && (
          <Grid item xs={12}>
            <Alert severity="error">{error}</Alert>
          </Grid>
        )}

        {/* File Upload Section */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Upload File
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <TextField
                  label="Device Token"
                  value={deviceToken}
                  onChange={(e) => setDeviceToken(e.target.value)}
                  required
                  fullWidth
                />

                <input
                  type="file"
                  ref={fileInputRef}
                  style={{ display: 'none' }}
                  onChange={handleFileUpload}
                />

                <Button
                  variant="contained"
                  startIcon={<UploadIcon />}
                  onClick={() => fileInputRef.current?.click()}
                  disabled={!deviceToken || uploading}
                  fullWidth
                >
                  Select File to Upload
                </Button>

                {uploading && (
                  <Box sx={{ width: '100%' }}>
                    <LinearProgress variant="determinate" value={uploadProgress} />
                    <Typography variant="body2" color="text.secondary" align="center">
                      {uploadProgress}%
                    </Typography>
                  </Box>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* File Download Section */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Download File
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <TextField
                    label="File Name"
                    value={downloadFileName}
                    onChange={(e) => setDownloadFileName(e.target.value)}
                    fullWidth
                  />
                  <Button
                    variant="contained"
                    startIcon={<DownloadIcon />}
                    onClick={handleFileDownload}
                    disabled={!deviceToken || !downloadFileName}
                  >
                    Download
                  </Button>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Transfer History */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Transfer History
              </Typography>
              <List>
                {transferLogs.map((log, index) => (
                  <ListItem key={index}>
                    <ListItemIcon>
                      {log.type === 'upload' ? <UploadIcon /> : <DownloadIcon />}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography
                            component="span"
                            color={log.status === 'success' ? 'success.main' : 'error.main'}
                          >
                            {log.fileName}
                          </Typography>
                          <Chip
                            label={log.type}
                            color={log.type === 'upload' ? 'primary' : 'secondary'}
                            size="small"
                          />
                          {log.size && (
                            <Typography variant="body2" color="text.secondary">
                              ({formatFileSize(log.size)})
                            </Typography>
                          )}
                        </Box>
                      }
                      secondary={log.timestamp.toLocaleTimeString()}
                    />
                    <ListItemSecondaryAction>
                      <IconButton
                        edge="end"
                        onClick={() =>
                          setTransferLogs((prev) =>
                            prev.filter((item, i) => i !== index)
                          )
                        }
                      >
                        <DeleteIcon />
                      </IconButton>
                    </ListItemSecondaryAction>
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

export default FileTransfer; 