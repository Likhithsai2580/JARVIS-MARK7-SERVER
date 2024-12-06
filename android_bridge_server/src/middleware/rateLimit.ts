import { Socket } from 'socket.io';
import { RateLimiterMemory } from 'rate-limiter-flexible';

const rateLimiter = new RateLimiterMemory({
    points: 100, // Number of points
    duration: 60, // Per 60 seconds
});

export async function rateLimit(socket: Socket, next: (err?: Error) => void) {
    try {
        await rateLimiter.consume(socket.handshake.address);
        next();
    } catch (error) {
        next(new Error('Too many requests'));
    }
} 