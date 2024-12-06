# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build TypeScript code
RUN npm run build

# Production stage
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install production dependencies only
RUN npm ci --only=production

# Copy built files from builder stage
COPY --from=builder /app/dist ./dist

# Create uploads directory
RUN mkdir -p uploads && chown -R node:node uploads

# Set environment variables
ENV NODE_ENV=production
ENV PORT=3000

# Switch to non-root user
USER node

# Expose port
EXPOSE 3000

# Start the server
CMD ["node", "dist/index.js"] 