import { Socket } from 'socket.io';

export const authenticate = async (socket: Socket, next: (err?: Error) => void) => {
    const token = socket.handshake.auth.token;
    if (!token) {
        return next(new Error('Authentication token required'));
    }
    // Add your token validation logic here
    next();
}; 