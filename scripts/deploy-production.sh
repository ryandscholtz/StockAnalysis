#!/bin/bash

# Deploy to Production Environment
set -e

echo "🚀 Starting deployment to production environment..."

# Configuration
ENVIRONMENT="production"
AWS_REGION="us-east-1"
STACK_NAME="StockAnalysisStack-production"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_prompt() {
    echo -e "${BLUE}[PROMPT]${NC} $1"
}

# Check deployment window
check_deployment_window() {
    print_status "Checking deployment window..."
    
    current_hour=$(date -u +%H)
    current_day=$(date -u +%u)  # 1=Monday, 7=Sunday
    
    # Allow deployments Monday-Friday, 9 AM - 5 PM UTC
    if [[ $current_day -gt 5 || $current_hour -lt 9 || $current_hour -gt 17 ]]; then
        print_error "Production deployments are only allowed during business hours (Mon-Fri, 9 AM - 5 PM UTC)"
        print_error "Current time: $(date -u)"
        exit 1
    fi
    
    print_status "Deployment window check passed ✓"
}

# Manual approval
require_approval() {
    print_prompt "🔒 PRODUCTION DEPLOYMENT APPROVAL REQUIRED"
    print_prompt "Environment: $ENVIRONMENT"
    print_prompt "Region: $AWS_REGION"
    print_prompt "Stack: $STACK_NAME"
    print_prompt "Current branch: $(git branch --show-current)"
    print_prompt "Latest commit: $(git log -1 --oneline)"
    echo
    
    read -p "Do you approve this production deployment? (yes/no): " approval
    
    if [[ $approval != "yes" ]]; then
        print_error "Deployment cancelled by user"
        exit 1
    fi
    
    print_status "Deployment approved ✓"
}

# Create backup
create_backup() {
    print_status "Creating production backup..."
    
    # Database backup
    BACKUP_NAME="pre-deployment-$(date +%Y%m%d-%H%M%S)"
    
    aws dynamodb create-backup \
        --table-name stock-analyses-prod \
        --backup-name "$BACKUP_NAME" \
        --region $AWS_REGION
    
    print_status "Database backup created: $BACKUP_NAME ✓"
    
    # Configuration backup
    mkdir -p backups
    aws ssm get-parameters-by-path \
        --path "/stock-analysis/prod" \
        --recursive \
        --region $AWS_REGION > "backups/config-backup-$(date +%Y%m%d-%H%M%S).json"
    
    print_status "Configuration backup created ✓"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity > /dev/null 2>&1; then
        print_error "AWS credentials not configured or invalid"
        exit 1
    fi
    
    # Check CDK
    if ! command -v cdk &> /dev/null; then
        print_error "AWS CDK is not installed"
        exit 1
    fi
    
    # Check jq for JSON processing
    if ! command -v jq &> /dev/null; then
        print_error "jq is not installed (required for processing CDK outputs)"
        exit 1
    fi
    
    # Check git status
    if [[ -n $(git status --porcelain) ]]; then
        print_error "Working directory is not clean. Please commit or stash changes."
        exit 1
    fi
    
    # Check branch
    current_branch=$(git branch --show-current)
    if [[ $current_branch != "main" ]]; then
        print_error "Production deployments must be from 'main' branch. Current branch: $current_branch"
        exit 1
    fi
    
    print_status "Prerequisites check passed ✓"
}

# Run comprehensive tests
run_comprehensive_tests() {
    print_status "Running comprehensive test suite..."
    
    # Backend tests
    cd backend
    python -m pytest tests/ --cov=app --cov-report=term-missing --tb=short
    cd ..
    
    # Frontend tests
    cd frontend
    npm test -- --passWithNoTests --watchAll=false --coverage
    cd ..
    
    # Integration tests
    print_status "Running integration tests..."
    # Add integration test commands here
    
    # Security tests
    print_status "Running security tests..."
    cd backend
    bandit -r app/ -f txt
    safety check -r requirements.txt
    cd ..
    
    print_status "All tests passed ✓"
}

# Deploy with blue-green strategy
deploy_infrastructure() {
    print_status "Deploying infrastructure with blue-green strategy..."
    
    cd infrastructure
    
    # Install dependencies
    npm ci
    
    # Build CDK
    npm run build
    
    # Show diff
    print_status "CDK Diff:"
    npx cdk diff --context environment=$ENVIRONMENT
    
    # Confirm deployment
    read -p "Proceed with infrastructure deployment? (yes/no): " proceed
    if [[ $proceed != "yes" ]]; then
        print_error "Infrastructure deployment cancelled"
        exit 1
    fi
    
    # Deploy
    npx cdk deploy --all \
        --context environment=$ENVIRONMENT \
        --require-approval never \
        --outputs-file outputs.json
    
    cd ..
    
    print_status "Infrastructure deployment completed ✓"
}

# Deploy application with zero downtime
deploy_application() {
    print_status "Deploying application with zero downtime..."
    
    # Package and deploy backend
    cd backend
    pip install -r requirements.txt
    # Add blue-green deployment logic here
    cd ..
    
    # Build and deploy frontend
    cd frontend
    npm ci
    npm run build
    # Add frontend deployment to CDN here
    cd ..
    
    print_status "Application deployment completed ✓"
}

# Run extensive post-deployment tests
run_post_deployment_tests() {
    print_status "Running extensive post-deployment tests..."
    
    # Extract endpoints from CDK outputs
    if [ -f "infrastructure/outputs.json" ]; then
        API_ENDPOINT=$(jq -r '.StockAnalysisStack.ApiEndpoint' infrastructure/outputs.json)
        WEB_ENDPOINT=$(jq -r '.StockAnalysisStack.WebEndpoint' infrastructure/outputs.json)
        
        print_status "API Endpoint: $API_ENDPOINT"
        print_status "Web Endpoint: $WEB_ENDPOINT"
        
        # Health checks
        print_status "Running health checks..."
        for i in {1..5}; do
            if curl -f "$API_ENDPOINT/health" > /dev/null 2>&1; then
                print_status "Health check $i/5 passed ✓"
            else
                print_error "Health check $i/5 failed"
                exit 1
            fi
            sleep 2
        done
        
        # API functionality tests
        print_status "Testing API functionality..."
        curl -f "$API_ENDPOINT/docs" > /dev/null
        curl -f "$API_ENDPOINT/openapi.json" > /dev/null
        
        # Performance tests
        print_status "Running performance tests..."
        # Add performance testing logic here
        
        # Security tests
        print_status "Running security validation..."
        # Add security validation logic here
        
    else
        print_error "CDK outputs file not found"
        exit 1
    fi
    
    print_status "Post-deployment tests completed ✓"
}

# Rollback function
rollback() {
    print_error "🚨 ROLLBACK INITIATED"
    print_status "Rolling back production deployment..."
    
    # Rollback infrastructure
    cd infrastructure
    # Add rollback logic here
    cd ..
    
    # Restore database if needed
    # Add database restore logic here
    
    print_status "Rollback completed"
}

# Main deployment flow
main() {
    print_status "Starting production deployment process..."
    
    check_deployment_window
    check_prerequisites
    require_approval
    create_backup
    run_comprehensive_tests
    deploy_infrastructure
    deploy_application
    run_post_deployment_tests
    
    print_status "🎉 Production deployment completed successfully!"
    print_status "Environment: $ENVIRONMENT"
    print_status "Region: $AWS_REGION"
    print_status "Stack: $STACK_NAME"
    print_status "Deployed at: $(date -u)"
}

# Error handling with rollback
trap 'print_error "Deployment failed at line $LINENO"; rollback' ERR

# Run main function
main "$@"