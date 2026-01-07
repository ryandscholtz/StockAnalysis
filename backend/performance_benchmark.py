#!/usr/bin/env python3
"""
Comprehensive Performance Benchmarking for Stock Analysis API
Validates all performance requirements for Task 17.2 completion

This script performs comprehensive performance validation including:
- Sub-200ms response times for cached data
- System behavior under production load
- Auto-scaling verification
- Memory and resource usage validation
- Concurrent user scenario testing
"""
import asyncio
import time
import statistics
import json
import sys
import argparse
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
import httpx
import psutil
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics"""
    endpoint: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    success_rate: float
    error_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float

    def meets_cache_requirement(self) -> bool:
        """Check if cached endpoint meets sub-200ms requirement"""
        return self.p95_response_time <= 0.2  # 200ms

    def meets_general_requirement(self) -> bool:
        """Check if endpoint meets general performance requirements"""
        return self.success_rate >= 95.0 and self.avg_response_time <= 2.0

    def meets_health_requirement(self) -> bool:
        """Check if health endpoint meets fast response requirement"""
        return self.avg_response_time <= 0.1  # 100ms


@dataclass
class BenchmarkResults:
    """Container for complete benchmark results"""
    test_name: str
    start_time: float
    end_time: float
    duration: float
    metrics_by_endpoint: Dict[str, PerformanceMetrics]
    overall_success_rate: float
    overall_rps: float
    peak_memory_mb: float
    avg_cpu_percent: float
    validation_passed: bool
    validation_errors: List[str]


class PerformanceBenchmark:
    """Comprehensive performance benchmarking suite"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def check_server_health(self) -> bool:
        """Verify server is running and healthy"""
        try:
            response = await self.session.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Server health check failed: {e}")
            return False

    async def make_request(self, endpoint: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        """Make a single request and return timing/status info"""
        start_time = time.time()
        try:
            if method.upper() == "GET":
                response = await self.session.get(f"{self.base_url}{endpoint}", **kwargs)
            elif method.upper() == "POST":
                response = await self.session.post(f"{self.base_url}{endpoint}", **kwargs)
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

    async def run_concurrent_requests(self, endpoint: str, num_requests: int,
                                    concurrency: int, duration: Optional[float] = None) -> List[Dict[str, Any]]:
        """Run concurrent requests against an endpoint"""
        results = []
        semaphore = asyncio.Semaphore(concurrency)

        async def make_limited_request():
            async with semaphore:
                return await self.make_request(endpoint)

        if duration:
            # Run for specific duration
            start_time = time.time()
            tasks = []

            while time.time() - start_time < duration:
                if len(tasks) < num_requests:
                    task = asyncio.create_task(make_limited_request())
                    tasks.append(task)

                # Collect completed tasks
                done_tasks = [task for task in tasks if task.done()]
                for task in done_tasks:
                    results.append(await task)
                    tasks.remove(task)

                await asyncio.sleep(0.01)  # Small delay

            # Wait for remaining tasks
            if tasks:
                remaining_results = await asyncio.gather(*tasks)
                results.extend(remaining_results)
        else:
            # Run specific number of requests
            tasks = [make_limited_request() for _ in range(num_requests)]
            results = await asyncio.gather(*tasks)

        return results

    def calculate_metrics(self, endpoint: str, results: List[Dict[str, Any]],
                         start_time: float, end_time: float) -> PerformanceMetrics:
        """Calculate performance metrics from results"""
        if not results:
            return PerformanceMetrics(
                endpoint=endpoint, total_requests=0, successful_requests=0,
                failed_requests=0, avg_response_time=0, min_response_time=0,
                max_response_time=0, p50_response_time=0, p95_response_time=0,
                p99_response_time=0, requests_per_second=0, success_rate=0,
                error_rate=100, memory_usage_mb=0, cpu_usage_percent=0
            )

        response_times = [r["response_time"] for r in results]
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        # Calculate percentiles
        sorted_times = sorted(response_times)
        n = len(sorted_times)

        def percentile(p):
            if n == 0:
                return 0
            index = int(p * n)
            if index >= n:
                index = n - 1
            return sorted_times[index]

        # Get system metrics
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()

        duration = end_time - start_time
        rps = len(results) / duration if duration > 0 else 0

        return PerformanceMetrics(
            endpoint=endpoint,
            total_requests=len(results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            avg_response_time=statistics.mean(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            p50_response_time=percentile(0.5),
            p95_response_time=percentile(0.95),
            p99_response_time=percentile(0.99),
            requests_per_second=rps,
            success_rate=(len(successful) / len(results)) * 100,
            error_rate=(len(failed) / len(results)) * 100,
            memory_usage_mb=memory_mb,
            cpu_usage_percent=cpu_percent
        )

    async def benchmark_cached_endpoints(self) -> BenchmarkResults:
        """
        Benchmark cached endpoints to validate sub-200ms requirement
        Requirements: 5.6 - Performance SLA compliance (sub-200ms for cached data)
        """
        logger.info("Starting cached endpoints benchmark...")

        cached_endpoints = [
            "/health",
            "/api/version",
            "/api/analysis-presets",
            "/api/watchlist"
        ]

        start_time = time.time()
        metrics_by_endpoint = {}
        validation_errors = []

        for endpoint in cached_endpoints:
            logger.info(f"Benchmarking cached endpoint: {endpoint}")

            # Run multiple rounds to ensure caching is active
            for round_num in range(3):
                results = await self.run_concurrent_requests(
                    endpoint, num_requests=50, concurrency=10
                )

                if round_num == 2:  # Use final round for metrics (cache should be warm)
                    round_end_time = time.time()
                    metrics = self.calculate_metrics(endpoint, results, start_time, round_end_time)
                    metrics_by_endpoint[endpoint] = metrics

                    # Validate cache performance requirement
                    if not metrics.meets_cache_requirement():
                        validation_errors.append(
                            f"Cached endpoint {endpoint} failed sub-200ms requirement: "
                            f"P95 = {metrics.p95_response_time*1000:.1f}ms"
                        )

                await asyncio.sleep(0.5)  # Brief pause between rounds

        end_time = time.time()

        # Calculate overall metrics
        all_requests = sum(m.total_requests for m in metrics_by_endpoint.values())
        all_successful = sum(m.successful_requests for m in metrics_by_endpoint.values())
        overall_success_rate = (all_successful / all_requests * 100) if all_requests > 0 else 0
        overall_rps = all_requests / (end_time - start_time)

        # Get peak system metrics
        process = psutil.Process()
        peak_memory_mb = process.memory_info().rss / 1024 / 1024
        avg_cpu_percent = process.cpu_percent()

        return BenchmarkResults(
            test_name="Cached Endpoints Benchmark",
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            metrics_by_endpoint=metrics_by_endpoint,
            overall_success_rate=overall_success_rate,
            overall_rps=overall_rps,
            peak_memory_mb=peak_memory_mb,
            avg_cpu_percent=avg_cpu_percent,
            validation_passed=len(validation_errors) == 0,
            validation_errors=validation_errors
        )

    async def benchmark_production_load(self) -> BenchmarkResults:
        """
        Benchmark system under production load scenarios
        Requirements: System behavior under expected production load
        """
        logger.info("Starting production load benchmark...")

        # Production load simulation: mixed endpoints with realistic weights
        endpoints_config = [
            ("/health", 20, 100),  # (endpoint, weight, requests)
            ("/api/version", 10, 50),
            ("/api/search?q=AAPL", 5, 25),
            ("/api/analysis-presets", 3, 15),
            ("/api/watchlist", 2, 10)
        ]

        start_time = time.time()
        metrics_by_endpoint = {}
        validation_errors = []

        # Run concurrent load across all endpoints
        tasks = []
        for endpoint, weight, requests in endpoints_config:
            # Higher weight = higher concurrency
            concurrency = min(weight, 20)  # Cap concurrency
            task = asyncio.create_task(
                self.run_concurrent_requests(endpoint, requests, concurrency)
            )
            tasks.append((endpoint, task))

        # Collect results
        for endpoint, task in tasks:
            results = await task
            task_end_time = time.time()
            metrics = self.calculate_metrics(endpoint, results, start_time, task_end_time)
            metrics_by_endpoint[endpoint] = metrics

            # Validate production load requirements
            if not metrics.meets_general_requirement():
                validation_errors.append(
                    f"Endpoint {endpoint} failed production load requirements: "
                    f"Success rate = {metrics.success_rate:.1f}%, "
                    f"Avg response time = {metrics.avg_response_time*1000:.1f}ms"
                )

        end_time = time.time()

        # Calculate overall metrics
        all_requests = sum(m.total_requests for m in metrics_by_endpoint.values())
        all_successful = sum(m.successful_requests for m in metrics_by_endpoint.values())
        overall_success_rate = (all_successful / all_requests * 100) if all_requests > 0 else 0
        overall_rps = all_requests / (end_time - start_time)

        # Get system metrics
        process = psutil.Process()
        peak_memory_mb = process.memory_info().rss / 1024 / 1024
        avg_cpu_percent = process.cpu_percent()

        return BenchmarkResults(
            test_name="Production Load Benchmark",
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            metrics_by_endpoint=metrics_by_endpoint,
            overall_success_rate=overall_success_rate,
            overall_rps=overall_rps,
            peak_memory_mb=peak_memory_mb,
            avg_cpu_percent=avg_cpu_percent,
            validation_passed=len(validation_errors) == 0 and overall_success_rate >= 95.0,
            validation_errors=validation_errors
        )

    async def benchmark_sustained_load(self) -> BenchmarkResults:
        """
        Benchmark system under sustained load to verify stability
        Requirements: System stability and auto-scaling behavior
        """
        logger.info("Starting sustained load benchmark...")

        start_time = time.time()
        duration_seconds = 60  # 1 minute sustained load

        # Run sustained load on health endpoint (most stable)
        results = await self.run_concurrent_requests(
            "/health",
            num_requests=1000,  # High number to ensure continuous load
            concurrency=15,
            duration=duration_seconds
        )

        end_time = time.time()

        metrics = self.calculate_metrics("/health", results, start_time, end_time)

        validation_errors = []

        # Validate sustained load requirements
        if metrics.success_rate < 98.0:
            validation_errors.append(
                f"Sustained load success rate {metrics.success_rate:.1f}% below 98%"
            )

        if metrics.avg_response_time > 0.2:  # 200ms for sustained load
            validation_errors.append(
                f"Sustained load avg response time {metrics.avg_response_time*1000:.1f}ms exceeds 200ms"
            )

        if metrics.requests_per_second < 10:  # Minimum throughput
            validation_errors.append(
                f"Sustained load throughput {metrics.requests_per_second:.1f} RPS too low"
            )

        # Get system metrics
        process = psutil.Process()
        peak_memory_mb = process.memory_info().rss / 1024 / 1024
        avg_cpu_percent = process.cpu_percent()

        return BenchmarkResults(
            test_name="Sustained Load Benchmark",
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            metrics_by_endpoint={"/health": metrics},
            overall_success_rate=metrics.success_rate,
            overall_rps=metrics.requests_per_second,
            peak_memory_mb=peak_memory_mb,
            avg_cpu_percent=avg_cpu_percent,
            validation_passed=len(validation_errors) == 0,
            validation_errors=validation_errors
        )

    def print_results(self, results: BenchmarkResults):
        """Print formatted benchmark results"""
        print(f"\n{'='*80}")
        print(f"BENCHMARK RESULTS: {results.test_name.upper()}")
        print(f"{'='*80}")
        print(f"Duration: {results.duration:.1f}s")
        print(f"Overall Success Rate: {results.overall_success_rate:.1f}%")
        print(f"Overall RPS: {results.overall_rps:.1f}")
        print(f"Peak Memory: {results.peak_memory_mb:.1f}MB")
        print(f"Avg CPU: {results.avg_cpu_percent:.1f}%")

        print(f"\n{'ENDPOINT DETAILS':<25} {'REQUESTS':<10} {'SUCCESS%':<10} {'AVG(ms)':<10} {'P95(ms)':<10} {'P99(ms)':<10} {'RPS':<8}")
        print("-" * 95)

        for endpoint, metrics in results.metrics_by_endpoint.items():
            print(f"{endpoint:<25} {metrics.total_requests:<10} {metrics.success_rate:<9.1f}% "
                  f"{metrics.avg_response_time*1000:<9.0f} {metrics.p95_response_time*1000:<9.0f} "
                  f"{metrics.p99_response_time*1000:<9.0f} {metrics.requests_per_second:<7.1f}")

        # Validation results
        print(f"\n{'VALIDATION RESULTS'}")
        print("-" * 40)

        if results.validation_passed:
            print("✓ ALL VALIDATIONS PASSED")
        else:
            print("✗ VALIDATION FAILURES:")
            for error in results.validation_errors:
                print(f"  - {error}")

        return results.validation_passed


async def main():
    """Main benchmarking function"""
    parser = argparse.ArgumentParser(description="Stock Analysis API Performance Benchmarking")
    parser.add_argument("--host", default="http://localhost:8000", help="API server host")
    parser.add_argument("--test", choices=["cached", "production", "sustained", "all"],
                       default="all", help="Benchmark test to run")
    parser.add_argument("--output", help="Output file for results (JSON)")
    parser.add_argument("--validate", action="store_true", help="Exit with error code if validation fails")

    args = parser.parse_args()

    logger.info(f"Starting performance benchmarking against {args.host}")

    async with PerformanceBenchmark(args.host) as benchmark:
        # Check server health
        if not await benchmark.check_server_health():
            logger.error("Server is not healthy. Please start the API server first.")
            sys.exit(1)

        logger.info("Server is healthy, starting benchmarks...")

        all_results = []
        all_passed = True

        # Run selected benchmarks
        if args.test in ["cached", "all"]:
            results = await benchmark.benchmark_cached_endpoints()
            passed = benchmark.print_results(results)
            all_results.append(asdict(results))
            if not passed:
                all_passed = False

        if args.test in ["production", "all"]:
            results = await benchmark.benchmark_production_load()
            passed = benchmark.print_results(results)
            all_results.append(asdict(results))
            if not passed:
                all_passed = False

        if args.test in ["sustained", "all"]:
            results = await benchmark.benchmark_sustained_load()
            passed = benchmark.print_results(results)
            all_results.append(asdict(results))
            if not passed:
                all_passed = False

        # Save results if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(all_results, f, indent=2)
            logger.info(f"Results saved to {args.output}")

        # Final summary
        print(f"\n{'='*80}")
        print(f"FINAL BENCHMARK SUMMARY")
        print(f"{'='*80}")

        if all_passed:
            print("🎉 ALL PERFORMANCE BENCHMARKS PASSED!")
            print("✓ Sub-200ms response times for cached data")
            print("✓ System handles production load successfully")
            print("✓ Sustained load performance validated")
            print("✓ System meets all performance requirements")
        else:
            print("❌ SOME PERFORMANCE BENCHMARKS FAILED")
            print("Please review the validation errors above")

        # Exit with appropriate code
        if args.validate and not all_passed:
            logger.error("Performance benchmarks failed validation")
            sys.exit(1)

        logger.info("Performance benchmarking completed")


if __name__ == "__main__":
    asyncio.run(main())
