#!/usr/bin/env python3
"""
Development Environment Validation Script
Checks that all development tools and dependencies are properly configured
"""

import subprocess
import sys
import os
import json
from pathlib import Path
from typing import List, Tuple, Dict, Any

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}=== {text} ==={Colors.END}")

def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def run_command(cmd: List[str], capture_output: bool = True) -> Tuple[bool, str]:
    """Run a command and return success status and output"""
    try:
        result = subprocess.run(
            cmd, 
            capture_output=capture_output, 
            text=True, 
            timeout=30
        )
        return result.returncode == 0, result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return False, str(e)

def check_docker():
    """Check Docker installation and status"""
    print_header("Docker Environment")
    
    # Check Docker installation
    success, output = run_command(["docker", "--version"])
    if success:
        print_success(f"Docker installed: {output}")
    else:
        print_error("Docker not installed or not in PATH")
        return False
    
    # Check Docker Compose
    success, output = run_command(["docker-compose", "--version"])
    if success:
        print_success(f"Docker Compose installed: {output}")
    else:
        print_error("Docker Compose not installed or not in PATH")
        return False
    
    # Check Docker daemon
    success, _ = run_command(["docker", "info"])
    if success:
        print_success("Docker daemon is running")
    else:
        print_error("Docker daemon is not running")
        return False
    
    return True

def check_python_environment():
    """Check Python environment and dependencies"""
    print_header("Python Environment")
    
    # Check Python version
    version = sys.version.split()[0]
    major, minor = map(int, version.split('.')[:2])
    
    if major == 3 and minor >= 11:
        print_success(f"Python version: {version}")
    else:
        print_error(f"Python 3.11+ required, found: {version}")
        return False
    
    # Check if we're in backend directory or can find it
    backend_dir = Path("backend")
    if not backend_dir.exists():
        backend_dir = Path("../backend")
        if not backend_dir.exists():
            print_error("Backend directory not found")
            return False
    
    # Check requirements files
    req_files = ["requirements.txt", "requirements-test.txt"]
    for req_file in req_files:
        req_path = backend_dir / req_file
        if req_path.exists():
            print_success(f"Found {req_file}")
        else:
            print_error(f"Missing {req_file}")
            return False
    
    # Check if virtual environment is active
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print_success("Virtual environment is active")
    else:
        print_warning("No virtual environment detected (recommended for local development)")
    
    # Check key Python packages
    packages = ["fastapi", "pytest", "black", "flake8"]
    for package in packages:
        try:
            __import__(package)
            print_success(f"Package {package} is installed")
        except ImportError:
            print_error(f"Package {package} is not installed")
    
    return True

def check_node_environment():
    """Check Node.js environment"""
    print_header("Node.js Environment")
    
    # Check Node.js version
    success, output = run_command(["node", "--version"])
    if success:
        version = output.replace('v', '')
        major = int(version.split('.')[0])
        if major >= 18:
            print_success(f"Node.js version: {output}")
        else:
            print_error(f"Node.js 18+ required, found: {output}")
            return False
    else:
        print_warning("Node.js not installed (optional for Docker-only development)")
        return True
    
    # Check npm
    success, output = run_command(["npm", "--version"])
    if success:
        print_success(f"npm version: {output}")
    else:
        print_error("npm not found")
        return False
    
    # Check if frontend directory exists
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        frontend_dir = Path("../frontend")
        if not frontend_dir.exists():
            print_error("Frontend directory not found")
            return False
    
    # Check package.json
    package_json = frontend_dir / "package.json"
    if package_json.exists():
        print_success("Found package.json")
        
        # Check if node_modules exists
        node_modules = frontend_dir / "node_modules"
        if node_modules.exists():
            print_success("Dependencies installed (node_modules exists)")
        else:
            print_warning("Dependencies not installed (run 'npm install')")
    else:
        print_error("Missing package.json")
        return False
    
    return True

def check_configuration_files():
    """Check that configuration files exist"""
    print_header("Configuration Files")
    
    config_files = [
        ("docker-compose.yml", "Docker Compose configuration"),
        ("backend/pytest.ini", "pytest configuration"),
        ("backend/pyproject.toml", "Python project configuration"),
        ("frontend/.eslintrc.json", "ESLint configuration"),
        ("frontend/.prettierrc", "Prettier configuration"),
        (".github/workflows/ci.yml", "GitHub Actions CI/CD"),
        ("Makefile", "Development commands"),
    ]
    
    all_exist = True
    for file_path, description in config_files:
        if Path(file_path).exists():
            print_success(f"{description}: {file_path}")
        else:
            print_error(f"Missing {description}: {file_path}")
            all_exist = False
    
    return all_exist

def check_docker_services():
    """Check if Docker services are running"""
    print_header("Docker Services")
    
    # Check if docker-compose.yml exists
    if not Path("docker-compose.yml").exists():
        print_error("docker-compose.yml not found")
        return False
    
    # Check running services
    success, output = run_command(["docker-compose", "ps"])
    if success:
        if "Up" in output:
            print_success("Docker services are running")
            print(f"Services status:\n{output}")
        else:
            print_warning("Docker services are not running (run 'docker-compose up -d')")
    else:
        print_error("Failed to check Docker services")
        return False
    
    return True

def check_api_endpoints():
    """Check if API endpoints are accessible"""
    print_header("API Endpoints")
    
    try:
        import requests
        
        endpoints = [
            ("http://localhost:8000/health", "Backend health check"),
            ("http://localhost:8000/docs", "API documentation"),
            ("http://localhost:8000/openapi.json", "OpenAPI schema"),
        ]
        
        for url, description in endpoints:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print_success(f"{description}: {url}")
                else:
                    print_error(f"{description} returned {response.status_code}: {url}")
            except requests.exceptions.RequestException:
                print_warning(f"{description} not accessible: {url}")
        
        # Check frontend
        try:
            response = requests.get("http://localhost:3000", timeout=5)
            if response.status_code == 200:
                print_success("Frontend accessible: http://localhost:3000")
            else:
                print_error(f"Frontend returned {response.status_code}")
        except requests.exceptions.RequestException:
            print_warning("Frontend not accessible: http://localhost:3000")
            
    except ImportError:
        print_warning("requests package not available, skipping API checks")
    
    return True

def run_basic_tests():
    """Run basic tests to verify functionality"""
    print_header("Basic Tests")
    
    # Check if we can run pytest
    backend_dir = Path("backend")
    if backend_dir.exists():
        os.chdir(backend_dir)
        
        # Run a simple test
        success, output = run_command([
            sys.executable, "-m", "pytest", 
            "tests/test_coverage_thresholds.py::TestCoverageThresholds::test_test_discovery_works",
            "-v"
        ])
        
        if success:
            print_success("Basic pytest test passed")
        else:
            print_error("Basic pytest test failed")
            print(f"Output: {output}")
        
        os.chdir("..")
    else:
        print_warning("Backend directory not found, skipping tests")
    
    return True

def main():
    """Main validation function"""
    print(f"{Colors.BOLD}Stock Analysis Tool - Development Environment Validation{Colors.END}")
    print("This script checks that your development environment is properly configured.\n")
    
    checks = [
        ("Docker Environment", check_docker),
        ("Python Environment", check_python_environment),
        ("Node.js Environment", check_node_environment),
        ("Configuration Files", check_configuration_files),
        ("Docker Services", check_docker_services),
        ("API Endpoints", check_api_endpoints),
        ("Basic Tests", run_basic_tests),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print_error(f"Error during {name}: {e}")
            results[name] = False
    
    # Summary
    print_header("Summary")
    
    passed = sum(results.values())
    total = len(results)
    
    for name, result in results.items():
        if result:
            print_success(name)
        else:
            print_error(name)
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} checks passed{Colors.END}")
    
    if passed == total:
        print_success("✨ Development environment is ready!")
        print("\nNext steps:")
        print("1. Visit http://localhost:8000/docs to explore the API")
        print("2. Visit http://localhost:3000 to see the frontend")
        print("3. Run 'make test' to execute the full test suite")
        print("4. Check out DEVELOPMENT.md for detailed documentation")
    else:
        print_error("❌ Some checks failed. Please fix the issues above.")
        print("\nCommon solutions:")
        print("- Run 'docker-compose up -d' to start services")
        print("- Run 'pip install -r requirements-test.txt' in backend/")
        print("- Run 'npm install' in frontend/")
        print("- Check that Docker Desktop is running")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)