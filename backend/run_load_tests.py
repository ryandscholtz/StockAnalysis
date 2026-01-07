#!/usr/bin/env python3
"""
Performance load testing runner for Stock Analysis API
Provides automated load testing with configurable scenarios
"""
import asyncio
import argparse
import json
import time
import statistics
import sys
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LoadTestConfig:
    """Configuration for load tests"""
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.scenarios = {
            "light": {"users": 10, "requests_per_user": 20, "duration": 30},
            "medium": {"users": 25, "requests_per_user": 40, "duration": 60},
            "heavy": {"users": 50, "requests_per_user": 60, "duration": 120},
            "cache": {"users": 20, "requests_per_user": 100, "duration": 60},
            "spike": {"users": 100, "requests_per_user": 10, "duration": 30}
        }
        self.endpoints = {
            "health": {"path": "/health", "weight": 10, "timeout": 5},
            "version": {"path": "/api/version", "weight": 8, "timeout": 5},
            "search": {"path": "/api/search?q=AAPL", "weight": 6, "timeout": 10},
            "cached_quote": {"path": "/api/quote/AAPL/cached", "weight": 5, "timeout": 10},
            "watchlist": {"path": "/api/watchlist", "weight": 4, "timeout": 15},
            "presets": {"path": "/api/analysis-presets", "weight": 3, "timeout": 10}
        }


class LoadTestResults:
    """Container for load test results with analysis"""
    def __init__(self, scenario_name: str):
        self.scenario_name = scenario_name
        self.start_time = 0
        self.end_time = 0
        self.results_by_endpoint: Dict[str, List[Dict[str, Any]]] = {}
        self.total_requests = 0
        self.total_errors = 0
    
    def add_result(self, endpoint: str, result: Dict[str, Any]):
        """Add a single request result"""
        if endpoint not in self.results_by_endpoint:
            self.results_by_endpoint[endpoint] = []
        self.results_by_endpoint[endpoint].append(result)
        self.total_requests += 1
        if result.get("error") or result.get("status_code", 200) >= 400:
            self.total_errors += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive test summary"""
        duration = self.end_time - self.start_time
        
        summary = {
            "scenario": self.scenario_name,
            "duration_seconds": duration,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "success_rate": ((self.total_requests - self.total_errors) / self.total_requests * 100) if self.total_requests > 0 else 0,
            "requests_per_second": self.total_requests / duration if duration > 0 else 0,
            "endpoints": {}
        }
        
        # Analyze each endpoint
        for endpoint, results in self.results_by_endpoint.items():
            if not results:
                continue
                
            response_times = [r["response_time"] for r in results if r.get("response_time")]
            status_codes = [r["status_code"] for r in results if r.get("status_code")]
            errors = [r for r in results if r.get("error") or r.get("status_code", 200) >= 400]
            
            endpoint_summary = {
                "requests": len(results),
                "errors": len(errors),
                "success_rate": ((len(results) - len(errors)) / len(results) * 100) if results else 0,
                "avg_response_time": statistics.mean(response_times) if response_times else 0,
                "min_response_time": min(response_times) if response_times else 0,
                "max_response_time": max(response_times) if response_times else 0,
                "p95_response_time": statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else (max(response_times) if response_times else 0),
                "p99_response_time": statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else (max(response_times) if response_times else 0),
                "status_codes": list(set(status_codes))
            }
            
            summary["endpoints"][endpoint] = endpoint_summary
        
        return summary
    
    def print_summary(self):
        """Print formatted test results"""
        summary = self.get_summary()
        
        print(f"\n{'='*60}")
        print(f"LOAD TEST RESULTS: {summary['scenario'].upper()}")
        print(f"{'='*60}")
        print(f"Duration: {summary['duration_seconds']:.1f}s")
        print(f"Total Requests: {summary['total_requests']}")
        print(f"Total Errors: {summary['total_errors']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Requests/Second: {summary['requests_per_second']:.1f}")
        
        print(f"\n{'ENDPOINT BREAKDOWN':<20} {'REQUESTS':<10} {'SUCCESS%':<10} {'AVG(ms)':<10} {'P95(ms)':<10} {'P99(ms)':<10}")
        print("-" * 80)
        
        for endpoint, stats in summary["endpoints"].items():
            print(f"{endpoint:<20} {stats['requests']:<10} {stats['success_rate']:<9.1f}% {stats['avg_response_time']*1000:<9.0f} {stats['p95_response_time']*1000:<9.0f} {stats['p99_response_time']*1000:<9.0f}")
        
        # Performance validation
        print(f"\n{'PERFORMANCE VALIDATION'}")
        print("-" * 40)
        
        validation_passed = True
        for endpoint, stats in summary["endpoints"].items():
            # Define performance thresholds
            if "health" in endpoint or "version" in endpoint:
                threshold_ms = 100
            elif "cached" in endpoint:
                threshold_ms = 200
            else:
                threshold_ms = 2000
            
            avg_ms = stats['avg_response_time'] * 1000
            p95_ms = stats['p95_response_time'] * 1000
            
            status = "✓ PASS" if avg_ms <= threshold_ms else "✗ FAIL"
            if avg_ms > threshold_ms:
                validation_passed = False
            
            print(f"{endpoint:<20} {status:<8} (avg: {avg_ms:.0f}ms, threshold: {threshold_ms}ms)")
        
        overall_status = "✓ PASSED" if validation_passed and summary['success_rate'] >= 95 else "✗ FAILED"
        print(f"\nOVERALL: {overall_status}")
        
        return validation_passed and summary['success_rate'] >= 95


async def make_request_async(session: httpx.AsyncClient, url: str, timeout: float = 10) -> Dict[str, Any]:
    """Make an async HTTP request and return timing/status info"""
    start_time = time.time()
    try:
        response = await session.get(url, timeout=timeout)
        end_time = time.time()
        return {
            "response_time": end_time - start_time,
            "status_code": response.status_code,
            "error": None
        }
    except Exception as e:
        end_time = time.time()
        return {
            "response_time": end_time - start_time,
            "status_code": 500,
            "error": str(e)
        }


async def run_user_session(user_id: int, config: LoadTestConfig, scenario: Dict[str, Any], results: LoadTestResults):
    """Run a single user session with mixed requests"""
    # Create weighted endpoint list
    endpoint_list = []
    for name, endpoint_config in config.endpoints.items():
        endpoint_list.extend([name] * endpoint_config["weight"])
    
    async with httpx.AsyncClient() as session:
        for request_num in range(scenario["requests_per_user"]):
            # Select endpoint based on weights
            endpoint_name = endpoint_list[request_num % len(endpoint_list)]
            endpoint_config = config.endpoints[endpoint_name]
            
            url = f"{config.base_url}{endpoint_config['path']}"
            timeout = endpoint_config["timeout"]
            
            # Make request
            result = await make_request_async(session, url, timeout)
            results.add_result(endpoint_name, result)
            
            # Small delay between requests to simulate user behavior
            await asyncio.sleep(0.1)


async def run_load_test_scenario(config: LoadTestConfig, scenario_name: str) -> LoadTestResults:
    """Run a complete load test scenario"""
    scenario = config.scenarios[scenario_name]
    results = LoadTestResults(scenario_name)
    
    logger.info(f"Starting {scenario_name} load test scenario")
    logger.info(f"Users: {scenario['users']}, Requests per user: {scenario['requests_per_user']}")
    
    results.start_time = time.time()
    
    # Create tasks for all users
    tasks = []
    for user_id in range(scenario["users"]):
        task = run_user_session(user_id, config, scenario, results)
        tasks.append(task)
    
    # Run all user sessions concurrently
    await asyncio.gather(*tasks)
    
    results.end_time = time.time()
    
    logger.info(f"Completed {scenario_name} load test scenario")
    return results


async def check_server_health(base_url: str) -> bool:
    """Check if the server is running and healthy"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/health", timeout=5)
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Server health check failed: {e}")
        return False


async def main():
    """Main load testing function"""
    parser = argparse.ArgumentParser(description="Stock Analysis API Load Testing")
    parser.add_argument("--scenario", choices=["light", "medium", "heavy", "cache", "spike", "all"], 
                       default="light", help="Load test scenario to run")
    parser.add_argument("--host", default="http://localhost:8000", help="API server host")
    parser.add_argument("--output", help="Output file for results (JSON)")
    parser.add_argument("--validate", action="store_true", help="Exit with error code if performance thresholds not met")
    
    args = parser.parse_args()
    
    # Setup configuration
    config = LoadTestConfig()
    config.base_url = args.host
    
    # Check server health
    logger.info(f"Checking server health at {config.base_url}")
    if not await check_server_health(config.base_url):
        logger.error("Server is not healthy or not running. Please start the API server first.")
        sys.exit(1)
    
    logger.info("Server is healthy, starting load tests")
    
    # Determine scenarios to run
    scenarios_to_run = [args.scenario] if args.scenario != "all" else list(config.scenarios.keys())
    
    all_results = []
    all_passed = True
    
    # Run each scenario
    for scenario_name in scenarios_to_run:
        try:
            results = await run_load_test_scenario(config, scenario_name)
            passed = results.print_summary()
            all_results.append(results.get_summary())
            
            if not passed:
                all_passed = False
                
        except Exception as e:
            logger.error(f"Error running scenario {scenario_name}: {e}")
            all_passed = False
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(all_results, f, indent=2)
        logger.info(f"Results saved to {args.output}")
    
    # Exit with appropriate code
    if args.validate and not all_passed:
        logger.error("Load tests failed performance validation")
        sys.exit(1)
    
    logger.info("Load testing completed successfully")


if __name__ == "__main__":
    asyncio.run(main())