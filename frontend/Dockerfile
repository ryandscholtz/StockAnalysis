# Multi-stage Docker build for Stock Analysis Frontend
FROM node:18-alpine as base

# Set working directory
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

# Development stage
FROM node:18-alpine as development

WORKDIR /app

# Install all dependencies (including dev dependencies)
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Development command
CMD ["npm", "run", "dev"]

# Build stage
FROM base as builder

WORKDIR /app

# Copy source code
COPY . .

# Install dev dependencies for build
RUN npm ci

# Build the application
RUN npm run build

# Production stage
FROM node:18-alpine as production

WORKDIR /app

# Copy built application
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/next.config.js ./

# Install only production dependencies
RUN npm ci --only=production && npm cache clean --force

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001

# Change ownership
RUN chown -R nextjs:nodejs /app
USER nextjs

# Expose port
EXPOSE 3000

# Production command
CMD ["npm", "start"]