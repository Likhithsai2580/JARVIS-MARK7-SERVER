import { Handler } from '@netlify/functions';
import { Server } from 'socket.io';
import serverless from 'serverless-http';
import { app } from '../src/index';

const handler: Handler = async (event, context) => {
  if (event.httpMethod === 'GET') {
    // Handle WebSocket upgrade
    const io = new Server();
    return new Promise((resolve) => {
      io.on('connection', (socket) => {
        // WebSocket logic here
      });
    });
  }

  // Handle HTTP requests
  const handler = serverless(app);
  return handler(event, context);
};

export { handler }; 