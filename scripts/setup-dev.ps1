# Development Environment Setup Script for Windows
# Sets up Docker development environment with all necessary tools

Write-Host "🚀 Setting up Stock Analysis Tool development environment..." -ForegroundColor Green

# Check if Docker is installed
try {
    docker --version | Out-Null
    Write-Host "✅ Docker is installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Check if Docker Compose is installed
try {
    docker-compose --version | Out-Null
    Write-Host "✅ Docker Compose is installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker Compose is not installed. Please install Docker Compose first." -ForegroundColor Red
    exit 1
}

# Create necessary directories
Write-Host "📁 Creating necessary directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "backend/data" | Out-Null
New-Item -ItemType Directory -Force -Path "backend/htmlcov" | Out-Null
New-Item -ItemType Directory -Force -Path "frontend/.next" | Out-Null
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

# Set up backend development environment
Write-Host "🐍 Setting up backend development environment..." -ForegroundColor Yellow
Push-Location backend

# Install pre-commit hooks if Python is available
try {
    python --version | Out-Null
    Write-Host "Installing pre-commit hooks..." -ForegroundColor Cyan
    python -m pip install pre-commit
    pre-commit install
} catch {
    Write-Host "⚠️ Python not found locally, skipping pre-commit setup" -ForegroundColor Yellow
}

Pop-Location

# Set up frontend development environment
Write-Host "⚛️ Setting up frontend development environment..." -ForegroundColor Yellow
Push-Location frontend

# Install dependencies if Node.js is available locally
try {
    npm --version | Out-Null
    Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
    npm install
} catch {
    Write-Host "⚠️ Node.js not found locally, skipping npm install" -ForegroundColor Yellow
}

Pop-Location

# Create environment files
Write-Host "🔧 Creating environment files..." -ForegroundColor Yellow

# Backend .env file
if (-not (Test-Path "backend/.env")) {
    @"
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
"@ | Out-File -FilePath "backend/.env" -Encoding UTF8
    Write-Host "✅ Created backend/.env file" -ForegroundColor Green
} else {
    Write-Host "ℹ️ Backend .env file already exists" -ForegroundColor Cyan
}

# Frontend .env.local file
if (-not (Test-Path "frontend/.env.local")) {
    @"
# Frontend Development Configuration
NODE_ENV=development
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_VERSION=2.0.0
"@ | Out-File -FilePath "frontend/.env.local" -Encoding UTF8
    Write-Host "✅ Created frontend/.env.local file" -ForegroundColor Green
} else {
    Write-Host "ℹ️ Frontend .env.local file already exists" -ForegroundColor Cyan
}

# Build and start services
Write-Host "🐳 Building and starting Docker services..." -ForegroundColor Yellow
docker-compose build
docker-compose up -d

# Wait for services to be ready
Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check service health
Write-Host "🏥 Checking service health..." -ForegroundColor Yellow

# Check backend health
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Backend is healthy" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️ Backend health check failed" -ForegroundColor Yellow
}

# Check Redis
try {
    docker-compose exec redis redis-cli ping | Out-Null
    Write-Host "✅ Redis is healthy" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Redis health check failed" -ForegroundColor Yellow
}

# Check frontend (might take longer to start)
Write-Host "⏳ Waiting for frontend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 20

try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Frontend is healthy" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️ Frontend health check failed (this is normal if it's still starting)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 Development environment setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Available services:" -ForegroundColor Cyan
Write-Host "  • Backend API: http://localhost:8000"
Write-Host "  • API Documentation: http://localhost:8000/docs"
Write-Host "  • Frontend: http://localhost:3000"
Write-Host "  • Redis: localhost:6379"
Write-Host "  • PostgreSQL: localhost:5432"
Write-Host ""
Write-Host "🔧 Useful commands:" -ForegroundColor Cyan
Write-Host "  • View logs: docker-compose logs -f"
Write-Host "  • Stop services: docker-compose down"
Write-Host "  • Restart services: docker-compose restart"
Write-Host "  • Run tests: docker-compose exec backend pytest"
Write-Host "  • Run linting: docker-compose exec backend black . && docker-compose exec backend flake8"
Write-Host ""
Write-Host "📚 Next steps:" -ForegroundColor Cyan
Write-Host "  1. Update API keys in backend/.env"
Write-Host "  2. Run tests: docker-compose exec backend pytest"
Write-Host "  3. Start developing!"