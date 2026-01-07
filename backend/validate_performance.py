#!/usr/bin/env python3
"""
Performance Validation Script for Task 17.2
Validates performance requirements using FastAPI TestClient
"""
import time
import statistics
import sys
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient
import psutil
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the FastAPI app
try:
    from app.core.app import app
    logger.info("Successfully imported FastAPI app")
except ImportError as e:
    logger.error(f"Failed to import app: {e}")
    sys.exit(1)


class PerformanceValidator:
    """Performance validation for tech stack modernization completion"""
    
    def __init__(self):
        self.client = TestClient(app)
        self.results = {}
        
    def make_request(self, endpoint: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        """Make a single request and return timing/status info"""
        start_time = time.time()
        try:
            if method.upper() == "GET":
                response = self.client.get(endpoint, **kwargs)
            elif method.upper() == "POST":
                response = self.client.post(endpoint, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            end_time = time.time()
            return {
                "response_time": end_time - start_time,
                "status_code": response.status_code,
                "success": 200 <= response.status_code < 300,
                "error": None
            }
        except Exception as e:
            end_time = time.time()
            return {
                "response_time": end_time - start_time,
                "status_code": 500,
                "success": False,
                "error": str(e)
            }
    
    def run_concurrent_requests(self, endpoint: str, num_requests: int, num_workers: int = 10) -> List[Dict[str, Any]]:
        """Run concurrent requests against an endpoint"""
        results = []
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(self.make_request, endpoint)
                for _ in range(num_requests)
            ]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        return results
    
    def calculate_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance metrics from results"""
        if not results:
            return {"error": "No results to analyze"}
        
        response_times = [r["response_time"] for r in results]
        successful = [r for r in results if r["success"]]
        
        sorted_times = sorted(response_times)
        n = len(sorted_times)
        
        def percentile(p):
            index = int(p * n)
            if index >= n:
                index = n - 1
            return sorted_times[index]
        
        return {
            "total_requests": len(results),
            "successful_requests": len(successful),
            "success_rate": (len(successful) / len(results)) * 100,
            "avg_response_time": statistics.mean(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "p95_response_time": percentile(0.95),
            "p99_response_time": percentile(0.99),
            "response_times": response_times
        }
    
    def validate_cached_endpoints(self) -> bool:
        """
        Validate sub-200ms response times for cached data
        Requirements: 5.6 - Performance SLA compliance
        """
        logger.info("Validating cached endpoint performance...")
        
        cached_endpoints = [
            "/health",
            "/api/version",
            "/api/analysis-presets"
        ]
        
        all_passed = True
        
        for endpoint in cached_endpoints:
            logger.info(f"Testing endpoint: {endpoint}")
            
            # Run multiple rounds to simulate cache warming
            for round_num in range(3):
                results = self.run_concurrent_requests(endpoint, num_requests=20, num_workers=5)
                
                if round_num == 2:  # Use final round (cache should be warm)
                    metrics = self.calculate_metrics(results)
                    self.results[f"cached_{endpoint}"] = metrics
                    
                    # Validate requirements
                    p95_ms = metrics["p95_response_time"] * 1000
                    avg_ms = metrics["avg_response_time"] * 1000
                    
                    print(f"\n{endpoint} Performance:")
                    print(f"  Requests: {metrics['total_requests']}")
                    print(f"  Success Rate: {metrics['success_rate']:.1f}%")
                    print(f"  Average: {avg_ms:.1f}ms")
                    print(f"  95th Percentile: {p95_ms:.1f}ms")
                    
                    # Check sub-200ms requirement for cached data
                    if p95_ms > 200:
                        print(f"  ❌ FAILED: P95 {p95_ms:.1f}ms exceeds 200ms requirement")
                        all_passed = False
                    else:
                        print(f"  ✅ PASSED: P95 {p95_ms:.1f}ms meets sub-200ms requirement")
                    
                    if metrics["success_rate"] < 95:
                        print(f"  ❌ FAILED: Success rate {metrics['success_rate']:.1f}% below 95%")
                        all_passed = False
                    else:
                        print(f"  ✅ PASSED: Success rate {metrics['success_rate']:.1f}% meets requirement")
        
        return all_passed
    
    def validate_production_load(self) -> bool:
        """
        Validate system behavior under production load
        Requirements: System handles expected production load
        """
        logger.info("Validating production load handling...")
        
        # Test with increasing load levels
        load_tests = [
            ("Light Load", 25, 5),    # 25 requests, 5 concurrent
            ("Medium Load", 50, 10),  # 50 requests, 10 concurrent
            ("Heavy Load", 100, 20),  # 100 requests, 20 concurrent
        ]
        
        all_passed = True
        
        for test_name, num_requests, concurrency in load_tests:
            logger.info(f"Running {test_name} test...")
            
            results = self.run_concurrent_requests("/health", num_requests, concurrency)
            metrics = self.calculate_metrics(results)
            self.results[f"load_{test_name.lower().replace(' ', '_')}"] = metrics
            
            avg_ms = metrics["avg_response_time"] * 1000
            p95_ms = metrics["p95_response_time"] * 1000
            
            print(f"\n{test_name} Results:")
            print(f"  Requests: {metrics['total_requests']}")
            print(f"  Concurrency: {concurrency}")
            print(f"  Success Rate: {metrics['success_rate']:.1f}%")
            print(f"  Average: {avg_ms:.1f}ms")
            print(f"  95th Percentile: {p95_ms:.1f}ms")
            
            # Validate requirements (more lenient for higher loads)
            success_threshold = 95.0 if concurrency <= 10 else 90.0
            response_threshold = 500 if concurrency <= 10 else 1000  # ms
            
            if metrics["success_rate"] < success_threshold:
                print(f"  ❌ FAILED: Success rate {metrics['success_rate']:.1f}% below {success_threshold}%")
                all_passed = False
            else:
                print(f"  ✅ PASSED: Success rate {metrics['success_rate']:.1f}% meets requirement")
            
            if avg_ms > response_threshold:
                print(f"  ❌ FAILED: Average response time {avg_ms:.1f}ms exceeds {response_threshold}ms")
                all_passed = False
            else:
                print(f"  ✅ PASSED: Average response time {avg_ms:.1f}ms meets requirement")
        
        return all_passed
    
    def validate_memory_usage(self) -> bool:
        """
        Validate memory usage remains stable under load
        Requirements: System resource efficiency
        """
        logger.info("Validating memory usage stability...")
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run sustained load
        results = self.run_concurrent_requests("/health", num_requests=200, num_workers=20)
        metrics = self.calculate_metrics(results)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"\nMemory Usage Validation:")
        print(f"  Initial Memory: {initial_memory:.1f}MB")
        print(f"  Final Memory: {final_memory:.1f}MB")
        print(f"  Memory Increase: {memory_increase:.1f}MB")
        print(f"  Requests Processed: {metrics['total_requests']}")
        print(f"  Success Rate: {metrics['success_rate']:.1f}%")
        
        # Validate memory usage (should not increase by more than 50MB)
        memory_passed = memory_increase < 50
        performance_passed = metrics["success_rate"] >= 95
        
        if not memory_passed:
            print(f"  ❌ FAILED: Memory increased by {memory_increase:.1f}MB (threshold: 50MB)")
        else:
            print(f"  ✅ PASSED: Memory increase {memory_increase:.1f}MB within acceptable range")
        
        if not performance_passed:
            print(f"  ❌ FAILED: Success rate {metrics['success_rate']:.1f}% below 95%")
        else:
            print(f"  ✅ PASSED: Success rate {metrics['success_rate']:.1f}% meets requirement")
        
        self.results["memory_validation"] = {
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_increase_mb": memory_increase,
            "performance_metrics": metrics
        }
        
        return memory_passed and performance_passed
    
    def validate_concurrent_scenarios(self) -> bool:
        """
        Validate concurrent user scenarios
        Requirements: System handles concurrent users effectively
        """
        logger.info("Validating concurrent user scenarios...")
        
        # Mixed workload simulation
        endpoints = [
            ("/health", 10),
            ("/api/version", 5),
            ("/api/analysis-presets", 2)
        ]
        
        # Create weighted request list
        request_list = []
        for endpoint, weight in endpoints:
            request_list.extend([endpoint] * weight)
        
        # Run concurrent mixed workload
        all_results = []
        
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = []
            
            # Submit 100 mixed requests
            for i in range(100):
                endpoint = request_list[i % len(request_list)]
                future = executor.submit(self.make_request, endpoint)
                futures.append((future, endpoint))
            
            # Collect results by endpoint
            endpoint_results = {}
            for future, endpoint in futures:
                result = future.result()
                all_results.append(result)
                
                if endpoint not in endpoint_results:
                    endpoint_results[endpoint] = []
                endpoint_results[endpoint].append(result)
        
        # Analyze results
        all_passed = True
        
        print(f"\nConcurrent User Scenarios:")
        
        for endpoint, results in endpoint_results.items():
            metrics = self.calculate_metrics(results)
            avg_ms = metrics["avg_response_time"] * 1000
            
            print(f"  {endpoint}:")
            print(f"    Requests: {metrics['total_requests']}")
            print(f"    Success Rate: {metrics['success_rate']:.1f}%")
            print(f"    Average: {avg_ms:.1f}ms")
            
            # Validate per endpoint
            if metrics["success_rate"] < 95:
                print(f"    ❌ FAILED: Success rate below 95%")
                all_passed = False
            else:
                print(f"    ✅ PASSED: Success rate meets requirement")
        
        # Overall metrics
        overall_metrics = self.calculate_metrics(all_results)
        self.results["concurrent_scenarios"] = {
            "overall": overall_metrics,
            "by_endpoint": {ep: self.calculate_metrics(res) for ep, res in endpoint_results.items()}
        }
        
        return all_passed
    
    def run_all_validations(self) -> bool:
        """Run all performance validations"""
        print("="*80)
        print("PERFORMANCE VALIDATION FOR TECH STACK MODERNIZATION")
        print("Task 17.2: Complete performance benchmarking")
        print("="*80)
        
        validations = [
            ("Cached Endpoints (Sub-200ms)", self.validate_cached_endpoints),
            ("Production Load Handling", self.validate_production_load),
            ("Memory Usage Stability", self.validate_memory_usage),
            ("Concurrent User Scenarios", self.validate_concurrent_scenarios)
        ]
        
        all_passed = True
        results_summary = []
        
        for validation_name, validation_func in validations:
            print(f"\n{'='*60}")
            print(f"VALIDATION: {validation_name}")
            print(f"{'='*60}")
            
            try:
                passed = validation_func()
                results_summary.append((validation_name, passed))
                
                if not passed:
                    all_passed = False
                    
            except Exception as e:
                logger.error(f"Validation {validation_name} failed with error: {e}")
                results_summary.append((validation_name, False))
                all_passed = False
        
        # Final summary
        print(f"\n{'='*80}")
        print("FINAL VALIDATION SUMMARY")
        print(f"{'='*80}")
        
        for validation_name, passed in results_summary:
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{validation_name:<40} {status}")
        
        print(f"\n{'OVERALL RESULT':<40} {'✅ ALL PASSED' if all_passed else '❌ SOME FAILED'}")
        
        if all_passed:
            print("\n🎉 ALL PERFORMANCE REQUIREMENTS VALIDATED!")
            print("✓ Sub-200ms response times for cached data")
            print("✓ System handles production load successfully")
            print("✓ Memory usage remains stable under load")
            print("✓ Concurrent user scenarios work effectively")
            print("\nTask 17.2 - Performance benchmarking: COMPLETE ✅")
        else:
            print("\n❌ SOME PERFORMANCE REQUIREMENTS NOT MET")
            print("Please review the failed validations above")
        
        return all_passed


def main():
    """Main validation function"""
    validator = PerformanceValidator()
    
    try:
        success = validator.run_all_validations()
        
        if not success:
            sys.exit(1)
            
        print("\nPerformance validation completed successfully!")
        
    except Exception as e:
        logger.error(f"Performance validation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()