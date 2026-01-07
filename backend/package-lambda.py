#!/usr/bin/env python3
"""
Lambda Packaging Script for Stock Analysis API

This script packages the FastAPI application for AWS Lambda deployment.
It creates a deployment-ready zip file with all dependencies.
"""

import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import List, Set


class LambdaPackager:
    """Packages FastAPI application for Lambda deployment"""
    
    def __init__(self, source_dir: str = ".", output_dir: str = "dist"):
        self.source_dir = Path(source_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.package_name = "lambda-package.zip"
        
        # Directories to exclude from packaging
        self.exclude_dirs = {
            '__pycache__',
            '.pytest_cache',
            '.hypothesis',
            'tests',
            'venv',
            'env',
            '.env',
            '.git',
            'node_modules',
            'dist',
            'build',
            '.coverage',
            'htmlcov',
            'batch_results'
        }
        
        # File patterns to exclude
        self.exclude_patterns = {
            '*.pyc',
            '*.pyo',
            '*.pyd',
            '.DS_Store',
            '*.log',
            '*.db',
            '*.sqlite',
            '*.pkl',
            '.env*',
            'pytest.ini',
            'pyproject.toml',
            'requirements-test.txt',
            '*.md',
            'Dockerfile',
            '*.ps1',
            '*.sh'
        }
    
    def clean_output_dir(self):
        """Clean the output directory"""
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Cleaned output directory: {self.output_dir}")
    
    def install_dependencies(self):
        """Install production dependencies to a temporary directory"""
        deps_dir = self.output_dir / "dependencies"
        deps_dir.mkdir(exist_ok=True)
        
        print("📦 Installing production dependencies...")
        
        # Install dependencies
        cmd = [
            sys.executable, "-m", "pip", "install",
            "-r", "requirements.txt",
            "--target", str(deps_dir),
            "--no-deps",  # Don't install sub-dependencies automatically
            "--upgrade"
        ]
        
        try:
            subprocess.run(cmd, check=True, cwd=self.source_dir)
            print("✅ Dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            sys.exit(1)
        
        return deps_dir
    
    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if a file should be excluded from packaging"""
        # Check if in excluded directory
        for part in file_path.parts:
            if part in self.exclude_dirs:
                return True
        
        # Check file patterns
        for pattern in self.exclude_patterns:
            if file_path.match(pattern):
                return True
        
        return False
    
    def copy_application_code(self, temp_dir: Path):
        """Copy application code to temporary directory"""
        print("📁 Copying application code...")
        
        app_dir = temp_dir / "app"
        app_dir.mkdir(exist_ok=True)
        
        # Copy app directory
        source_app = self.source_dir / "app"
        if source_app.exists():
            for item in source_app.rglob("*"):
                if item.is_file() and not self.should_exclude_file(item):
                    rel_path = item.relative_to(source_app)
                    dest_path = app_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_path)
        
        # Copy main files
        main_files = ["main.py", "lambda_handler.py"]
        for filename in main_files:
            source_file = self.source_dir / filename
            if source_file.exists():
                shutil.copy2(source_file, temp_dir / filename)
        
        print("✅ Application code copied")
    
    def create_lambda_handler(self, temp_dir: Path):
        """Create Lambda handler if it doesn't exist"""
        handler_file = temp_dir / "lambda_handler.py"
        
        if not handler_file.exists():
            print("📝 Creating Lambda handler...")
            
            handler_code = '''"""
AWS Lambda handler for Stock Analysis API
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import the FastAPI app
from app.main import app
from mangum import Mangum

# Create the Lambda handler
handler = Mangum(app, lifespan="off")

def lambda_handler(event, context):
    """AWS Lambda handler function"""
    return handler(event, context)
'''
            
            handler_file.write_text(handler_code)
            print("✅ Lambda handler created")
    
    def create_deployment_package(self):
        """Create the deployment package"""
        print("📦 Creating deployment package...")
        
        # Create temporary directory
        temp_dir = self.output_dir / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        try:
            # Install dependencies
            deps_dir = self.install_dependencies()
            
            # Copy dependencies to temp directory
            if deps_dir.exists():
                for item in deps_dir.iterdir():
                    if item.is_dir():
                        shutil.copytree(item, temp_dir / item.name, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, temp_dir)
            
            # Copy application code
            self.copy_application_code(temp_dir)
            
            # Create Lambda handler
            self.create_lambda_handler(temp_dir)
            
            # Create zip file
            package_path = self.output_dir / self.package_name
            with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    # Filter out excluded directories
                    dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                    
                    for file in files:
                        file_path = Path(root) / file
                        if not self.should_exclude_file(file_path):
                            arcname = file_path.relative_to(temp_dir)
                            zipf.write(file_path, arcname)
            
            # Get package size
            package_size = package_path.stat().st_size / (1024 * 1024)  # MB
            
            print(f"✅ Deployment package created: {package_path}")
            print(f"📊 Package size: {package_size:.2f} MB")
            
            if package_size > 50:
                print("⚠️  Warning: Package size exceeds 50MB. Consider optimizing dependencies.")
            
            return package_path
            
        finally:
            # Clean up temporary directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    def validate_package(self, package_path: Path):
        """Validate the created package"""
        print("🔍 Validating package...")
        
        required_files = [
            "lambda_handler.py",
            "app/main.py",
            "mangum"  # Should be a directory
        ]
        
        with zipfile.ZipFile(package_path, 'r') as zipf:
            file_list = zipf.namelist()
            
            for required in required_files:
                found = any(f.startswith(required) for f in file_list)
                if found:
                    print(f"✅ {required}: found")
                else:
                    print(f"❌ {required}: missing")
                    return False
        
        print("✅ Package validation passed")
        return True
    
    def package(self) -> Path:
        """Main packaging method"""
        print("🚀 Starting Lambda packaging process...")
        print(f"Source directory: {self.source_dir}")
        print(f"Output directory: {self.output_dir}")
        
        # Clean output directory
        self.clean_output_dir()
        
        # Create deployment package
        package_path = self.create_deployment_package()
        
        # Validate package
        if self.validate_package(package_path):
            print(f"🎉 Lambda package created successfully: {package_path}")
            return package_path
        else:
            print("❌ Package validation failed")
            sys.exit(1)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Package FastAPI app for AWS Lambda')
    parser.add_argument('--source', default='.', help='Source directory (default: current)')
    parser.add_argument('--output', default='dist', help='Output directory (default: dist)')
    parser.add_argument('--validate-only', action='store_true', help='Only validate existing package')
    
    args = parser.parse_args()
    
    packager = LambdaPackager(source_dir=args.source, output_dir=args.output)
    
    if args.validate_only:
        package_path = Path(args.output) / "lambda-package.zip"
        if package_path.exists():
            packager.validate_package(package_path)
        else:
            print(f"❌ Package not found: {package_path}")
            sys.exit(1)
    else:
        packager.package()


if __name__ == '__main__':
    main()