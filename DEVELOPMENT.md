# Stock Analysis Tool - Development Guide

## Overview

This guide covers the development environment setup, coding standards, testing procedures, and deployment processes for the Stock Analysis Tool.

## Quick Start

### Prerequisites

- Docker Desktop
- Git
- (Optional) Python 3.11+ and Node.js 18+ for local development

### Setup Development Environment

#### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd stock-analysis-tool

# Run setup script
# On Windows:
.\scripts\setup-dev.ps1

# On Linux/Mac:
./scripts/setup-dev.sh

# Or manually:
docker-compose up -d
```

#### Option 2: Local Development

```bash
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt -r requirements-test.txt
pre-commit install

# Frontend setup
cd ../frontend
npm install

# Start services
cd ../backend && uvicorn app.main:app --reload
cd ../frontend && npm run dev
```

## Architecture

### Backend (FastAPI)

- **Framework**: FastAPI with async/await
- **Database**: DynamoDB (production) / SQLite (development)
- **Caching**: Redis
- **AI/ML**: AWS Bedrock, Textract, Ollama
- **Testing**: pytest, hypothesis (property-based testing)

### Frontend (Next.js)

- **Framework**: Next.js 14+ with App Router
- **State Management**: Zustand
- **Styling**: TailwindCSS
- **Testing**: Jest, React Testing Library

### Infrastructure

- **Cloud**: AWS (CDK for Infrastructure as Code)
- **Containerization**: Docker
- **Monitoring**: CloudWatch, X-Ray
- **CI/CD**: GitHub Actions

## Development Workflow

### Code Quality Standards

#### Backend (Python)

```bash
# Format code
black app tests
isort app tests

# Lint code
flake8 app tests
mypy app

# Run all quality checks
make lint
```

#### Frontend (TypeScript)

```bash
# Format code
npm run format

# Lint code
npm run lint

# Type check
npm run type-check
```

### Testing

#### Backend Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test types
pytest -m unit          # Unit tests only
pytest -m property      # Property-based tests only
pytest -m integration   # Integration tests only

# Using Make
make test-backend
make coverage
```

#### Frontend Testing

```bash
# Run tests
npm test

# Run with coverage
npm run test:coverage

# Run E2E tests
npm run test:e2e

# Using Make
make test-frontend
```

#### Property-Based Testing

The system uses property-based testing to verify universal correctness properties:

```python
from hypothesis import given, strategies as st

@given(
    ticker=st.text(min_size=1, max_size=10),
    price=st.floats(min_value=0.01, max_value=10000.0)
)
def test_stock_analysis_data_validation_property(ticker: str, price: float):
    """
    Feature: tech-stack-modernization, Property 1: Data Validation Consistency
    """
    # Test implementation
```

### API Documentation

The API is automatically documented using OpenAPI/Swagger:

- **Development**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

#### Adding API Documentation

```python
@router.get("/analyze/{ticker}")
async def analyze_stock(
    ticker: str = Path(..., description="Stock ticker symbol"),
    force_refresh: bool = Query(False, description="Force new analysis")
):
    """
    Perform comprehensive stock analysis for a given ticker.
    
    This endpoint analyzes a stock using value investing principles,
    calculating fair value, margin of safety, and investment recommendation.
    
    - **ticker**: Stock symbol (e.g., AAPL, MSFT)
    - **force_refresh**: Bypass cache and run fresh analysis
    
    Returns detailed analysis including valuation, financial health,
    and business quality scores.
    """
```

## Environment Configuration

### Backend Environment Variables

```bash
# Development
ENVIRONMENT=development
LOG_LEVEL=DEBUG
STRUCTURED_LOGGING=true

# Database
DATABASE_TYPE=sqlite  # or dynamodb for production
SQLITE_DB_PATH=/app/data/stock_analysis.db
DYNAMODB_TABLE_NAME=stock-analyses

# Cache
REDIS_URL=redis://localhost:6379/0

# External APIs
ALPHA_VANTAGE_API_KEY=your_key_here
YAHOO_FINANCE_ENABLED=true

# AI Services
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
AWS_REGION=us-east-1

# Security
JWT_SECRET_KEY=your_secret_here
ALLOWED_ORIGINS=http://localhost:3000
```

### Frontend Environment Variables

```bash
NODE_ENV=development
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_VERSION=2.0.0
```

## Docker Development

### Services

- **backend**: FastAPI application
- **frontend**: Next.js application
- **redis**: Caching layer
- **postgres**: Development database (optional)

### Common Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Restart specific service
docker-compose restart backend

# Run commands in containers
docker-compose exec backend pytest
docker-compose exec frontend npm test

# Clean up
docker-compose down
make clean
```

## Database Management

### Migrations

```bash
# Run migrations
python -m app.database.migrations

# Reset database (development only)
make db-reset
```

### Data Models

```python
from app.database.models import StockAnalysis

# Create new analysis
analysis = StockAnalysis(
    ticker="AAPL",
    fair_value=180.00,
    current_price=150.00
)
```

## Monitoring and Observability

### Structured Logging

```python
import logging
from app.core.logging import app_logger

app_logger.info(
    "Analysis completed",
    extra={
        "ticker": "AAPL",
        "fair_value": 180.00,
        "correlation_id": "abc-123"
    }
)
```

### Metrics and Tracing

- **Health Checks**: `/health`, `/metrics`
- **Distributed Tracing**: AWS X-Ray integration
- **Custom Metrics**: CloudWatch integration

## Security

### Authentication

```python
from app.core.auth import require_auth

@router.get("/protected")
@require_auth
async def protected_endpoint(current_user: User = Depends(get_current_user)):
    return {"user": current_user.username}
```

### Data Encryption

- **At Rest**: AWS KMS encryption
- **In Transit**: TLS 1.3
- **Secrets**: AWS Secrets Manager

## Performance Optimization

### Caching Strategy

```python
from app.core.cache import cache_async_result

@cache_async_result("stock_quote", ttl_minutes=15)
async def get_stock_quote(ticker: str):
    # Expensive operation
    return quote_data
```

### Database Optimization

- **Indexing**: Proper DynamoDB GSI design
- **Connection Pooling**: SQLAlchemy async pools
- **Query Optimization**: Efficient data access patterns

## Deployment

### Development Deployment

```bash
# Build and deploy to development
make build
docker-compose -f docker-compose.dev.yml up -d
```

### Production Deployment

```bash
# Deploy infrastructure
cd infrastructure
cdk deploy

# Build production images
make build-prod

# Deploy application
./deploy.sh production
```

## Troubleshooting

### Common Issues

#### Backend Issues

```bash
# Check logs
docker-compose logs backend

# Debug database connection
docker-compose exec backend python -c "from app.database.factory import get_database; print(get_database())"

# Test API endpoints
curl http://localhost:8000/health
```

#### Frontend Issues

```bash
# Check build errors
docker-compose logs frontend

# Clear Next.js cache
docker-compose exec frontend rm -rf .next
docker-compose restart frontend
```

#### Performance Issues

```bash
# Check Redis connection
docker-compose exec redis redis-cli ping

# Monitor resource usage
docker stats

# Check API response times
curl -w "@curl-format.txt" http://localhost:8000/analyze/AAPL
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with debugger
python -m debugpy --listen 5678 --wait-for-client -m uvicorn app.main:app --reload
```

## Contributing

### Code Review Checklist

- [ ] Code follows style guidelines (Black, Prettier)
- [ ] Tests added for new functionality
- [ ] API documentation updated
- [ ] Security considerations addressed
- [ ] Performance impact assessed
- [ ] Error handling implemented
- [ ] Logging added for debugging

### Pull Request Process

1. Create feature branch from `main`
2. Implement changes with tests
3. Run full test suite
4. Update documentation
5. Submit pull request
6. Address review feedback
7. Merge after approval

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [Docker Documentation](https://docs.docker.com/)
- [pytest Documentation](https://docs.pytest.org/)

## Support

For development questions or issues:

1. Check this documentation
2. Search existing issues
3. Create new issue with:
   - Environment details
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant logs