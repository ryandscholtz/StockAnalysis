#!/usr/bin/env python3
"""
Test runner script for the backend test suite
"""
import pytest
import sys
import os
from pathlib import Path

def main():
    """Run the test suite with appropriate configuration"""

    # Get the directory containing this script
    script_dir = Path(__file__).parent
    test_dir = script_dir / "tests"

    # Ensure test directory exists
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return 1

    # Default pytest arguments
    pytest_args = [
        str(test_dir),  # Test directory
        "-v",           # Verbose output
        "--tb=short",   # Short traceback format
        "--strict-markers",  # Strict marker checking
        "-x",           # Stop on first failure
        "--disable-warnings",  # Disable warnings for cleaner output
    ]

    # Add coverage if available
    try:
        import coverage
        pytest_args.extend([
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])
        print("📊 Running tests with coverage analysis")
    except ImportError:
        print("📋 Running tests without coverage (install pytest-cov for coverage)")

    # Parse command line arguments
    if len(sys.argv) > 1:
        if "help" in sys.argv[1] or "-h" in sys.argv[1]:
            print_help()
            return 0
        elif "fast" in sys.argv[1]:
            pytest_args.extend(["-m", "not slow"])
            print("🏃 Running fast tests only")
        elif "slow" in sys.argv[1]:
            pytest_args.extend(["-m", "slow"])
            print("🐌 Running slow tests only")
        elif "integration" in sys.argv[1]:
            pytest_args.extend(["-m", "integration"])
            print("🔗 Running integration tests only")
        elif "unit" in sys.argv[1]:
            pytest_args.extend(["-m", "not integration and not slow"])
            print("🧪 Running unit tests only")
        else:
            # Treat as specific test file or pattern
            pytest_args = [sys.argv[1]] + pytest_args[1:]
            print(f"🎯 Running specific tests: {sys.argv[1]}")

    print(f"🚀 Starting test suite...")
    print(f"📁 Test directory: {test_dir}")
    print(f"⚙️  Pytest args: {' '.join(pytest_args)}")
    print("-" * 60)

    # Run pytest
    exit_code = pytest.main(pytest_args)

    print("-" * 60)
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ Tests failed with exit code: {exit_code}")

    return exit_code

def print_help():
    """Print help information"""
    print("""
🧪 Backend Test Runner

Usage:
    python run_tests.py [option]

Options:
    help        Show this help message
    fast        Run only fast tests (exclude slow tests)
    slow        Run only slow tests
    unit        Run only unit tests (exclude integration and slow)
    integration Run only integration tests
    <pattern>   Run tests matching the pattern (file or test name)

Examples:
    python run_tests.py                    # Run all tests
    python run_tests.py fast              # Run fast tests only
    python run_tests.py test_cache_manager.py  # Run specific test file
    python run_tests.py -k "test_cache"   # Run tests with 'cache' in name

Test Categories:
    📋 Unit Tests      - Fast, isolated tests of individual functions
    🔗 Integration     - Tests that involve multiple components
    🐌 Slow Tests      - Tests that take longer (API calls, etc.)

Coverage Report:
    If pytest-cov is installed, coverage reports will be generated:
    - Terminal: Shows missing lines
    - HTML: Open htmlcov/index.html in browser
    """)

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
