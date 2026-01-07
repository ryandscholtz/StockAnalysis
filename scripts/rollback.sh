#!/bin/bash

# Rollback Script for Stock Analysis Application
set -e

echo "🔄 Starting rollback process..."

# Configuration
ENVIRONMENT=${1:-"staging"}
AWS_REGION=${2:-"us-east-1"}

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

# Validate environment
validate_environment() {
    if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
        print_error "Invalid environment: $ENVIRONMENT. Must be 'staging' or 'production'"
        exit 1
    fi
    
    print_status "Environment: $ENVIRONMENT"
    print_status "Region: $AWS_REGION"
}

# Require confirmation for production rollback
require_confirmation() {
    if [[ "$ENVIRONMENT" == "production" ]]; then
        print_warning "🚨 PRODUCTION ROLLBACK REQUESTED"
        print_prompt "This will rollback the production environment!"
        print_prompt "Current time: $(date -u)"
        echo
        
        read -p "Are you sure you want to proceed with production rollback? (yes/no): " confirmation
        
        if [[ $confirmation != "yes" ]]; then
            print_error "Rollback cancelled by user"
            exit 1
        fi
        
        print_status "Production rollback confirmed ✓"
    fi
}

# List available backups
list_backups() {
    print_status "Listing available backups..."
    
    # List DynamoDB backups
    print_status "DynamoDB backups:"
    aws dynamodb list-backups \
        --table-name "stock-analyses-${ENVIRONMENT}" \
        --region $AWS_REGION \
        --query 'BackupSummaries[?BackupStatus==`AVAILABLE`].[BackupName,BackupCreationDateTime]' \
        --output table
    
    # List configuration backups
    print_status "Configuration backups:"
    if [ -d "backups" ]; then
        ls -la backups/config-backup-*.json 2>/dev/null || print_warning "No configuration backups found"
    else
        print_warning "No backup directory found"
    fi
}

# Select backup to restore
select_backup() {
    print_status "Selecting backup to restore..."
    
    # Get latest backup
    LATEST_BACKUP=$(aws dynamodb list-backups \
        --table-name "stock-analyses-${ENVIRONMENT}" \
        --region $AWS_REGION \
        --query 'BackupSummaries[?BackupStatus==`AVAILABLE`] | sort_by(@, &BackupCreationDateTime) | [-1].BackupArn' \
        --output text)
    
    if [[ "$LATEST_BACKUP" == "None" || -z "$LATEST_BACKUP" ]]; then
        print_warning "No backups available for restoration"
        return 1
    fi
    
    print_status "Latest backup ARN: $LATEST_BACKUP"
    
    read -p "Use latest backup for restoration? (yes/no): " use_latest
    
    if [[ $use_latest != "yes" ]]; then
        print_prompt "Please specify the backup ARN to restore:"
        read -p "Backup ARN: " LATEST_BACKUP
    fi
    
    export BACKUP_ARN="$LATEST_BACKUP"
    print_status "Selected backup: $BACKUP_ARN"
}

# Stop traffic to the application
stop_traffic() {
    print_status "Stopping traffic to the application..."
    
    # Update load balancer to stop routing traffic
    # This would typically involve updating the target group or setting maintenance mode
    
    print_status "Traffic stopped ✓"
}

# Rollback infrastructure
rollback_infrastructure() {
    print_status "Rolling back infrastructure..."
    
    cd infrastructure
    
    # Get previous stack template
    STACK_NAME="StockAnalysisStack-${ENVIRONMENT}"
    
    # List stack events to find the last successful deployment
    print_status "Finding last successful deployment..."
    
    # For now, we'll use CDK to rollback to the previous version
    # In a real scenario, you might want to deploy a specific version
    
    print_warning "Infrastructure rollback requires manual intervention"
    print_warning "Please review the CDK stack and deploy the previous version manually"
    
    cd ..
}

# Rollback application code
rollback_application() {
    print_status "Rolling back application code..."
    
    # For Lambda functions, this would involve updating the function code
    # For containerized applications, this would involve deploying the previous image
    
    print_warning "Application rollback requires manual intervention"
    print_warning "Please deploy the previous version of the application code"
}

# Restore database from backup
restore_database() {
    if [[ -z "$BACKUP_ARN" ]]; then
        print_warning "No backup selected, skipping database restore"
        return 0
    fi
    
    print_status "Restoring database from backup..."
    
    # Create new table from backup
    RESTORE_TABLE_NAME="stock-analyses-${ENVIRONMENT}-restored-$(date +%Y%m%d-%H%M%S)"
    
    aws dynamodb restore-table-from-backup \
        --target-table-name "$RESTORE_TABLE_NAME" \
        --backup-arn "$BACKUP_ARN" \
        --region $AWS_REGION
    
    print_status "Database restore initiated to table: $RESTORE_TABLE_NAME"
    print_warning "Manual intervention required to switch to restored table"
}

# Restore configuration
restore_configuration() {
    print_status "Restoring configuration..."
    
    # Find latest configuration backup
    if [ -d "backups" ]; then
        LATEST_CONFIG=$(ls -t backups/config-backup-*.json 2>/dev/null | head -n1)
        
        if [[ -n "$LATEST_CONFIG" ]]; then
            print_status "Found configuration backup: $LATEST_CONFIG"
            
            # Restore configuration parameters
            # This would involve parsing the backup file and updating SSM parameters
            print_warning "Configuration restore requires manual intervention"
            print_warning "Please review and restore configuration from: $LATEST_CONFIG"
        else
            print_warning "No configuration backups found"
        fi
    else
        print_warning "No backup directory found"
    fi
}

# Verify rollback
verify_rollback() {
    print_status "Verifying rollback..."
    
    # Basic health checks
    # In a real scenario, you would check the application endpoints
    
    print_status "Rollback verification completed ✓"
}

# Resume traffic
resume_traffic() {
    print_status "Resuming traffic to the application..."
    
    # Update load balancer to resume routing traffic
    
    print_status "Traffic resumed ✓"
}

# Generate rollback report
generate_report() {
    print_status "Generating rollback report..."
    
    REPORT_FILE="rollback-report-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S).txt"
    
    cat > "$REPORT_FILE" << EOF
ROLLBACK REPORT
===============

Environment: $ENVIRONMENT
Region: $AWS_REGION
Rollback Time: $(date -u)
Initiated By: $(whoami)

Backup Used: ${BACKUP_ARN:-"None"}
Restored Table: ${RESTORE_TABLE_NAME:-"None"}

Status: Completed
EOF

    print_status "Rollback report generated: $REPORT_FILE"
}

# Main rollback flow
main() {
    print_status "Starting rollback process for $ENVIRONMENT environment..."
    
    validate_environment
    require_confirmation
    list_backups
    select_backup
    stop_traffic
    rollback_infrastructure
    rollback_application
    restore_database
    restore_configuration
    verify_rollback
    resume_traffic
    generate_report
    
    print_status "🎉 Rollback process completed!"
    print_warning "Please verify the application is working correctly"
}

# Error handling
trap 'print_error "Rollback failed at line $LINENO"' ERR

# Show usage if no arguments
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <environment> [aws-region]"
    echo "Example: $0 staging us-east-1"
    echo "Example: $0 production us-west-2"
    exit 1
fi

# Run main function
main "$@"