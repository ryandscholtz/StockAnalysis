#!/usr/bin/env python3
"""
Production Secrets Setup Script for Stock Analysis API

This script creates and manages production secrets in AWS Secrets Manager.
It ensures all required secrets are properly configured for production deployment.
"""

import json
import os
import sys
import secrets
import string
from typing import Dict, Any, Optional

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("❌ boto3 is required. Install with: pip install boto3")
    sys.exit(1)


class ProductionSecretsManager:
    """Manages production secrets in AWS Secrets Manager"""
    
    def __init__(self, environment: str = "production", region: str = "eu-west-1"):
        self.environment = environment
        self.region = region
        self.secret_name = f"stock-analysis-secrets-{environment}"
        
        # Initialize AWS client
        try:
            self.secrets_client = boto3.client('secretsmanager', region_name=region)
            self.sts_client = boto3.client('sts', region_name=region)
            
            # Verify AWS credentials
            identity = self.sts_client.get_caller_identity()
            print(f"✅ AWS credentials configured for account: {identity['Account']}")
            
        except Exception as e:
            print(f"❌ Failed to initialize AWS clients: {e}")
            sys.exit(1)
    
    def generate_secure_key(self, length: int = 64) -> str:
        """Generate a cryptographically secure random key"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def get_existing_secret(self) -> Optional[Dict[str, Any]]:
        """Retrieve existing secret if it exists"""
        try:
            response = self.secrets_client.get_secret_value(SecretId=self.secret_name)
            return json.loads(response['SecretString'])
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return None
            else:
                print(f"❌ Error retrieving secret: {e}")
                return None
    
    def create_production_secrets(self, external_api_keys: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create production secrets with secure defaults"""
        
        # Get external API keys from environment or parameters
        api_keys = external_api_keys or {}
        
        # Try to get API keys from environment variables
        env_api_keys = {
            'alpha_vantage': os.getenv('ALPHA_VANTAGE_API_KEY'),
            'marketstack': os.getenv('MARKETSTACK_API_KEY'),
            'fred': os.getenv('FRED_API_KEY'),
            'fmp': os.getenv('FMP_API_KEY')
        }
        
        # Merge with provided keys, preferring provided ones
        for key, value in env_api_keys.items():
            if value and key not in api_keys:
                api_keys[key] = value
        
        # Create the secret structure
        secret_data = {
            'jwt_secret': self.generate_secure_key(64),
            'jwt_refresh_secret': self.generate_secure_key(64),
            'encryption_key': self.generate_secure_key(32),
            'external_api_keys': api_keys,
            'database': {
                'encryption_key': self.generate_secure_key(32)
            },
            'monitoring': {
                'webhook_secret': self.generate_secure_key(32)
            }
        }
        
        return secret_data
    
    def setup_secrets(self, force_update: bool = False) -> bool:
        """Set up production secrets in AWS Secrets Manager"""
        
        print(f"🔐 Setting up secrets for {self.environment} environment...")
        
        # Check if secret already exists
        existing_secret = self.get_existing_secret()
        
        if existing_secret and not force_update:
            print(f"✅ Secret '{self.secret_name}' already exists")
            print("   Use --force to update existing secrets")
            return True
        
        # Create new secret data
        secret_data = self.create_production_secrets()
        
        # If updating, preserve existing API keys
        if existing_secret and force_update:
            print("🔄 Updating existing secret...")
            # Preserve existing external API keys if they exist
            if 'external_api_keys' in existing_secret:
                for key, value in existing_secret['external_api_keys'].items():
                    if value:  # Only preserve non-empty values
                        secret_data['external_api_keys'][key] = value
        
        try:
            if existing_secret:
                # Update existing secret
                self.secrets_client.update_secret(
                    SecretId=self.secret_name,
                    SecretString=json.dumps(secret_data, indent=2)
                )
                print(f"✅ Updated secret: {self.secret_name}")
            else:
                # Create new secret
                self.secrets_client.create_secret(
                    Name=self.secret_name,
                    Description=f"Production secrets for Stock Analysis API ({self.environment})",
                    SecretString=json.dumps(secret_data, indent=2)
                )
                print(f"✅ Created secret: {self.secret_name}")
            
            # Display summary (without sensitive values)
            print("\n📋 Secret Summary:")
            print(f"   Secret Name: {self.secret_name}")
            print(f"   Region: {self.region}")
            print(f"   JWT Secret: {'✅ Generated' if secret_data['jwt_secret'] else '❌ Missing'}")
            print(f"   Encryption Key: {'✅ Generated' if secret_data['encryption_key'] else '❌ Missing'}")
            print(f"   External API Keys: {len([k for k, v in secret_data['external_api_keys'].items() if v])}/{len(secret_data['external_api_keys'])} configured")
            
            return True
            
        except ClientError as e:
            print(f"❌ Failed to create/update secret: {e}")
            return False
    
    def validate_secrets(self) -> bool:
        """Validate that all required secrets are properly configured"""
        
        print(f"🔍 Validating secrets for {self.environment} environment...")
        
        secret_data = self.get_existing_secret()
        if not secret_data:
            print(f"❌ Secret '{self.secret_name}' not found")
            return False
        
        # Required fields
        required_fields = [
            'jwt_secret',
            'encryption_key',
            'external_api_keys'
        ]
        
        validation_passed = True
        
        for field in required_fields:
            if field not in secret_data or not secret_data[field]:
                print(f"❌ Missing required field: {field}")
                validation_passed = False
            else:
                print(f"✅ {field}: configured")
        
        # Validate API keys
        api_keys = secret_data.get('external_api_keys', {})
        recommended_keys = ['alpha_vantage', 'marketstack']
        
        for key in recommended_keys:
            if key in api_keys and api_keys[key]:
                print(f"✅ API key '{key}': configured")
            else:
                print(f"⚠️  API key '{key}': not configured (recommended)")
        
        return validation_passed


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup production secrets for Stock Analysis API')
    parser.add_argument('--environment', default='production', choices=['staging', 'production'],
                       help='Environment to setup secrets for')
    parser.add_argument('--region', default='eu-west-1', help='AWS region')
    parser.add_argument('--force', action='store_true', help='Force update existing secrets')
    parser.add_argument('--validate-only', action='store_true', help='Only validate existing secrets')
    
    args = parser.parse_args()
    
    # Initialize secrets manager
    secrets_manager = ProductionSecretsManager(
        environment=args.environment,
        region=args.region
    )
    
    if args.validate_only:
        # Only validate existing secrets
        success = secrets_manager.validate_secrets()
        sys.exit(0 if success else 1)
    else:
        # Setup secrets
        success = secrets_manager.setup_secrets(force_update=args.force)
        
        if success:
            # Validate after setup
            print("\n🔍 Validating created secrets...")
            validation_success = secrets_manager.validate_secrets()
            
            if validation_success:
                print(f"\n🎉 Production secrets setup complete for {args.environment}!")
                print(f"\nSecret ARN: arn:aws:secretsmanager:{args.region}:*:secret:{secrets_manager.secret_name}")
                print("\nNext steps:")
                print("1. Update your backend .env.production file with the secret ARN")
                print("2. Ensure your Lambda execution role has secretsmanager:GetSecretValue permission")
                print("3. Deploy your infrastructure with the updated configuration")
            else:
                print("\n⚠️  Secrets created but validation failed. Please review the configuration.")
                sys.exit(1)
        else:
            print(f"\n❌ Failed to setup secrets for {args.environment}")
            sys.exit(1)


if __name__ == '__main__':
    main()