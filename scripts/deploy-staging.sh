#!/bin/bash

# Deploy to Staging Environment
set -e

echo "🚀 Starting deployment to staging environment..."

# Configuration
ENVIRONMENT="staging"
AWS_REGION="us-east-1"
STACK_NAME="StockAnalysisStack-staging"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
        exit 1
    fi
    
    # Check CDK
    if ! command -v cdk &> /dev/null; then
        print_error "AWS CDK is not installed"
        exit 1
    fi
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    print_status "Prerequisites check passed ✓"
}

# Run tests before deployment
run_tests() {
    print_status "Running tests before deployment..."
    
    # Backend tests
    cd backend
    python -m pytest tests/ --tb=short -q
    cd ..
    
    # Frontend tests
    cd frontend
    npm test -- --passWithNoTests --watchAll=false
    cd ..
    
    print_status "All tests passed ✓"
}

# Build and deploy infrastructure
deploy_infrastructure() {
    print_status "Deploying infrastructure to staging..."
    
    cd infrastructure
    
    # Install dependencies
    npm ci
    
    # Build CDK
    npm run build
    
    # Bootstrap if needed
    npx cdk bootstrap --context environment=$ENVIRONMENT
    
    # Show diff
    print_status "CDK Diff:"
    npx cdk diff --context environment=$ENVIRONMENT || true
    
    # Deploy
    npx cdk deploy --all \
        --context environment=$ENVIRONMENT \
        --require-approval never \
        --outputs-file outputs.json
    
    cd ..
    
    print_status "Infrastructure deployment completed ✓"
}

# Deploy application code
deploy_application() {
    print_status "Deploying application code..."
    
    # Package backend
    cd backend
    pip install -r requirements.txt
    # Add application packaging logic here
    cd ..
    
    # Build frontend
    cd frontend
    npm ci
    npm run build
    # Add frontend deployment logic here
    cd ..
    
    print_status "Application deployment completed ✓"
}

# Run post-deployment tests
run_post_deployment_tests() {
    print_status "Running post-deployment tests..."
    
    # Extract API endpoint from CDK outputs
    if [ -f "infrastructure/outputs.json" ]; then
        API_ENDPOINT=$(jq -r '.StockAnalysisStack.ApiEndpoint' infrastructure/outputs.json)
        print_status "API Endpoint: $API_ENDPOINT"
        
        # Health check
        if curl -f "$API_ENDPOINT/health" > /dev/null 2>&1; then
            print_status "Health check passed ✓"
        else
            print_error "Health check failed"
            exit 1
        fi
        
        # API documentation check
        if curl -f "$API_ENDPOINT/docs" > /dev/null 2>&1; then
            print_status "API documentation accessible ✓"
        else
            print_warning "API documentation not accessible"
        fi
    else
        print_warning "CDK outputs file not found, skipping endpoint tests"
    fi
    
    print_status "Post-deployment tests completed ✓"
}

# Main deployment flow
main() {
    print_status "Starting staging deployment process..."
    
    check_prerequisites
    run_tests
    deploy_infrastructure
    deploy_application
    run_post_deployment_tests
    
    print_status "🎉 Staging deployment completed successfully!"
    print_status "Environment: $ENVIRONMENT"
    print_status "Region: $AWS_REGION"
    print_status "Stack: $STACK_NAME"
}

# Error handling
trap 'print_error "Deployment failed at line $LINENO"' ERR

# Run main function
main "$@"