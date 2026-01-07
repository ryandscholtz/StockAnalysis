#!/usr/bin/env python3
"""
Local linting script for the backend
Run this script to check code quality before committing
"""
import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n🔍 {description}...")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} passed")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False
    except FileNotFoundError:
        print(f"❌ {description} failed - command not found: {cmd[0]}")
        print("Make sure you have installed the development dependencies:")
        print("pip install -r requirements-test.txt")
        return False

def main():
    """Run all linting checks"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("🚀 Running backend code quality checks...")
    
    checks = [
        (["flake8", "app", "tests", "--max-line-length=88", "--extend-ignore=E203,W503", "--count", "--statistics"], 
         "Flake8 linting"),
        (["black", "--check", "--diff", "app", "tests"], 
         "Black formatting check"),
        (["isort", "--check-only", "--diff", "app", "tests"], 
         "Import sorting check"),
        (["mypy", "app", "--ignore-missing-imports"], 
         "Type checking with mypy"),
    ]
    
    results = []
    for cmd, description in checks:
        success = run_command(cmd, description)
        results.append((description, success))
    
    print("\n" + "="*50)
    print("📊 SUMMARY")
    print("="*50)
    
    all_passed = True
    for description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {description}")
        if not success:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All checks passed! Your code is ready for commit.")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please fix the issues before committing.")
        return 1

if __name__ == "__main__":
    sys.exit(main())