# Stock Analysis Tool - Developer Setup

## Quick Start

Get the development environment running in under 5 minutes:

```bash
# 1. Clone and enter directory
git clone <repository-url>
cd stock-analysis-tool

# 2. Run setup (choose your platform)
# Windows:
.\scripts\setup-dev.ps1

# Linux/Mac:
./scripts/setup-dev.sh

# 3. Access the application
# Backend API: http://localhost:8000
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

## What You Get

- ✅ **Backend**: FastAPI with async support, auto-reload
- ✅ **Frontend**: Next.js 14 with hot reload
- ✅ **Database**: SQLite (dev) with migration support
- ✅ **Cache**: Redis for performance
- ✅ **Testing**: pytest + Jest with coverage
- ✅ **Linting**: Black, ESLint, pre-commit hooks
- ✅ **API Docs**: Auto-generated OpenAPI/Swagger
- ✅ **Monitoring**: Health checks and metrics

## Development Commands

### Using Make (Recommended)

```bash
make help           # Show all available commands
make setup          # Initial setup
make up             # Start all services
make down           # Stop all services
make test           # Run all tests
make lint           # Run linting
make format         # Format code
make coverage       # Generate coverage report
make clean          # Clean up generated files
```

### Using Docker Compose

```bash
docker-compose up -d              # Start services
docker-compose logs -f            # View logs
docker-compose restart backend    # Restart specific service
docker-compose exec backend bash # Shell into container
```

### Manual Commands

```bash
# Backend
cd backend
pytest --cov=app                 # Run tests with coverage
black app tests                  # Format code
flake8 app tests                 # Lint code
uvicorn app.main:app --reload    # Start dev server

# Frontend
cd frontend
npm test                         # Run tests
npm run lint                     # Lint code
npm run dev                      # Start dev server
```

## Project Structure

```
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes and models
│   │   ├── core/           # Core functionality (auth, logging, etc.)
│   │   ├── data/           # Data fetching and processing
│   │   ├── analysis/       # Financial analysis logic
│   │   ├── valuation/      # Valuation models (DCF, EPV, etc.)
│   │   └── database/       # Database models and services
│   ├── tests/              # Test files
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile         # Container definition
├── frontend/               # Next.js frontend
│   ├── app/               # App router pages
│   ├── components/        # React components
│   ├── lib/              # Utilities and API client
│   ├── types/            # TypeScript type definitions
│   └── __tests__/        # Test files
├── infrastructure/        # AWS CDK infrastructure
├── scripts/              # Development scripts
└── docker-compose.yml   # Development environment
```

## Environment Variables

### Backend (.env)

```bash
# Required for development
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DATABASE_TYPE=sqlite
REDIS_URL=redis://redis:6379/0

# Optional API keys (for full functionality)
ALPHA_VANTAGE_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

### Frontend (.env.local)

```bash
NODE_ENV=development
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Testing

### Backend Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test types
pytest -m unit          # Unit tests
pytest -m property      # Property-based tests
pytest -m integration   # Integration tests

# Run specific test file
pytest tests/test_api_documentation.py -v
```

### Frontend Testing

```bash
# Run tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch
```

### Property-Based Testing

The system uses Hypothesis for property-based testing:

```python
from hypothesis import given, strategies as st

@given(ticker=st.text(min_size=1, max_size=10))
def test_ticker_validation(ticker):
    # Test that validates behavior across all possible ticker inputs
    result = validate_ticker(ticker)
    assert isinstance(result, bool)
```

## Code Quality

### Automated Formatting

```bash
# Backend (Python)
black app tests                    # Format code
isort app tests                   # Sort imports

# Frontend (TypeScript)
npm run format                    # Format with Prettier
```

### Linting

```bash
# Backend
flake8 app tests                  # Style checking
mypy app                         # Type checking
bandit -r app/                   # Security scanning

# Frontend
npm run lint                     # ESLint
npm run type-check              # TypeScript checking
```

### Pre-commit Hooks

Automatically run quality checks before commits:

```bash
cd backend
pre-commit install               # Install hooks
pre-commit run --all-files      # Run on all files
```

## API Documentation

The API is automatically documented and available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Adding Documentation

```python
@router.get("/analyze/{ticker}")
async def analyze_stock(
    ticker: str = Path(..., description="Stock ticker symbol"),
    force_refresh: bool = Query(False, description="Force new analysis")
):
    """
    Analyze a stock using value investing principles.
    
    Returns comprehensive analysis including:
    - Fair value calculation (DCF, EPV, Asset-based)
    - Margin of safety
    - Investment recommendation
    - Financial health scores
    """
```

## Database

### Development Database

- **Type**: SQLite (file-based, no setup required)
- **Location**: `backend/data/stock_analysis.db`
- **Migrations**: Automatic on startup

### Database Operations

```bash
# Reset database (development only)
make db-reset

# Run migrations manually
docker-compose exec backend python -m app.database.migrations

# Access database
sqlite3 backend/data/stock_analysis.db
```

## Debugging

### Backend Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with Python debugger
python -m pdb -m uvicorn app.main:app --reload

# Debug in VS Code
# Add breakpoints and use "Python: FastAPI" launch configuration
```

### Frontend Debugging

```bash
# Enable debug mode
export NODE_ENV=development

# Debug in browser
# Use browser dev tools, React DevTools extension
```

### Container Debugging

```bash
# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Shell into container
docker-compose exec backend bash
docker-compose exec frontend sh

# Check container status
docker-compose ps
```

## Performance

### Caching

- **Redis**: Automatic caching for API responses
- **Browser**: Static asset caching via CDN
- **Database**: Query result caching

### Monitoring

```bash
# Health checks
curl http://localhost:8000/health
curl http://localhost:8000/metrics

# Cache statistics
curl http://localhost:8000/api/cache/stats
```

## Troubleshooting

### Common Issues

#### "Port already in use"
```bash
# Find and kill process using port
lsof -ti:8000 | xargs kill -9  # Backend
lsof -ti:3000 | xargs kill -9  # Frontend
```

#### "Database locked"
```bash
# Reset SQLite database
rm backend/data/stock_analysis.db
docker-compose restart backend
```

#### "Module not found"
```bash
# Rebuild containers
docker-compose build --no-cache
docker-compose up -d
```

#### "Tests failing"
```bash
# Clear test cache
pytest --cache-clear
rm -rf backend/.pytest_cache

# Update dependencies
pip install -r requirements-test.txt
```

### Getting Help

1. Check logs: `docker-compose logs -f`
2. Verify services: `docker-compose ps`
3. Test connectivity: `curl http://localhost:8000/health`
4. Reset environment: `make clean && make setup`

## Contributing

### Development Workflow

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes with tests
3. Run quality checks: `make lint && make test`
4. Commit changes: `git commit -m "Add feature"`
5. Push and create PR: `git push origin feature/your-feature`

### Code Review Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code formatted and linted
- [ ] API documentation current
- [ ] No security vulnerabilities
- [ ] Performance considered

## Next Steps

After setup, try these tasks:

1. **Explore the API**: Visit http://localhost:8000/docs
2. **Run an analysis**: POST to `/api/analyze/AAPL`
3. **Check the frontend**: Visit http://localhost:3000
4. **Run tests**: `make test`
5. **Make a change**: Edit a file and see hot reload
6. **Add a feature**: Follow the contributing guide

## Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Next.js Docs](https://nextjs.org/docs)
- [Docker Compose Docs](https://docs.docker.com/compose/)
- [pytest Docs](https://docs.pytest.org/)
- [Project Architecture](./DEVELOPMENT.md)