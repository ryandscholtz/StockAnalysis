#!/usr/bin/env python3
"""
Create Lambda deployment package with proper dependencies
"""
import os
import zipfile
import shutil
from pathlib import Path

def create_lambda_package():
    print("=== Creating Lambda Deployment Package ===")
    
    build_dir = Path("lambda_build")
    zip_file = Path("lambda_deployment_fixed.zip")
    
    # Remove old zip if exists
    if zip_file.exists():
        print(f"Removing old zip file: {zip_file}")
        zip_file.unlink()
    
    # Check if build directory exists
    if not build_dir.exists():
        print(f"Error: Build directory {build_dir} does not exist")
        print("Please run the pip install command first")
        return False
    
    print(f"Creating zip file from {build_dir}...")
    
    # Create zip file
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Walk through all files in build directory
        for root, dirs, files in os.walk(build_dir):
            for file in files:
                file_path = Path(root) / file
                # Calculate archive name (relative to build_dir)
                arcname = file_path.relative_to(build_dir)
                print(f"Adding: {arcname}")
                zf.write(file_path, arcname)
    
    # Get file size
    size_mb = zip_file.stat().st_size / (1024 * 1024)
    print(f"\nPackage created successfully!")
    print(f"File: {zip_file}")
    print(f"Size: {size_mb:.2f} MB")
    
    if size_mb > 250:
        print("WARNING: Package exceeds Lambda limit (250 MB)")
        return False
    elif size_mb > 50:
        print("WARNING: Package is large. Consider using Lambda Layers.")
    
    return True

if __name__ == "__main__":
    success = create_lambda_package()
    exit(0 if success else 1)
