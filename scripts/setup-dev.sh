#!/bin/bash

# Development Environment Setup Script
# Sets up Docker development environment with all necessary tools

set -e

echo "🚀 Setting up Stock Analysis Tool development environment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p backend/data
mkdir -p backend/htmlcov
mkdir -p frontend/.next
mkdir -p logs

# Set up backend development environment
echo "🐍 Setting up backend development environment..."
cd backend

# Install pre-commit hooks if not in Docker
if command -v python3 &> /dev/null; then
    echo "Installing pre-commit hooks..."
    python3 -m pip install pre-commit
    pre-commit install
fi

cd ..

# Set up frontend development environment
echo "⚛️ Setting up frontend development environment..."
cd frontend

# Install dependencies if Node.js is available locally
if command -v npm &> /dev/null; then
    echo "Installing frontend dependencies..."
    npm install
fi

cd ..

# Create environment files
echo "🔧 Creating environment files..."

# Backend .env file
if [ ! -f backend/.env ]; then
    cat > backend/.env << EOF
# Development Environment Configuration
ENVIRONMENT=development
LOG_LEVEL=DEBUG
STRUCTURED_LOGGING=true

# Database Configuration
DATABASE_TYPE=sqlite
SQLITE_DB_PATH=/app/data/stock_analysis.db

# Cache Configuration
REDIS_URL=redis://redis:6379/0

# API Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000

# AWS Configuration (for development)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=dummy
AWS_SECRET_ACCESS_KEY=dummy

# EC2 Configuration
EC2_AUTO_STOP=false

# External APIs
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
YAHOO_FINANCE_ENABLED=true

# AI Configuration
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
EOF
    echo "✅ Created backend/.env file"
else
    echo "ℹ️ Backend .env file already exists"
fi

# Frontend .env.local file
if [ ! -f frontend/.env.local ]; then
    cat > frontend/.env.local << EOF
# Frontend Development Configuration
NODE_ENV=development
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_VERSION=2.0.0
EOF
    echo "✅ Created frontend/.env.local file"
else
    echo "ℹ️ Frontend .env.local file already exists"
fi

# Build and start services
echo "🐳 Building and starting Docker services..."
docker-compose build
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🏥 Checking service health..."

# Check backend health
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "⚠️ Backend health check failed"
fi

# Check Redis
if docker-compose exec redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is healthy"
else
    echo "⚠️ Redis health check failed"
fi

# Check frontend (might take longer to start)
echo "⏳ Waiting for frontend to start..."
sleep 20

if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend is healthy"
else
    echo "⚠️ Frontend health check failed (this is normal if it's still starting)"
fi

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "📋 Available services:"
echo "  • Backend API: http://localhost:8000"
echo "  • API Documentation: http://localhost:8000/docs"
echo "  • Frontend: http://localhost:3000"
echo "  • Redis: localhost:6379"
echo "  • PostgreSQL: localhost:5432"
echo ""
echo "🔧 Useful commands:"
echo "  • View logs: docker-compose logs -f"
echo "  • Stop services: docker-compose down"
echo "  • Restart services: docker-compose restart"
echo "  • Run tests: docker-compose exec backend pytest"
echo "  • Run linting: docker-compose exec backend black . && docker-compose exec backend flake8"
echo ""
echo "📚 Next steps:"
echo "  1. Update API keys in backend/.env"
echo "  2. Run tests: docker-compose exec backend pytest"
echo "  3. Start developing!"