"""
Locust load testing configuration for Stock Analysis API
Simulates realistic user behavior patterns for performance validation
"""
from locust import HttpUser, task, between, events
import random
import json
import logging
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StockAnalysisUser(HttpUser):
    """
    Simulates a typical user of the Stock Analysis API
    Models realistic usage patterns with appropriate wait times
    """
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests

    def on_start(self):
        """Called when a user starts - setup user session"""
        self.tickers = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA",
            "BRK.B", "JPM", "V", "JNJ", "WMT", "PG", "UNH", "HD",
            "MA", "DIS", "PYPL", "ADBE", "NFLX", "CRM", "INTC",
            "VZ", "KO", "PFE", "T", "XOM", "CVX", "ABT", "TMO"
        ]
        self.user_watchlist = random.sample(self.tickers, k=random.randint(3, 8))
        logger.info(f"User started with watchlist: {self.user_watchlist}")

    @task(10)
    def check_health(self):
        """Health check - most frequent operation"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(8)
    def get_version(self):
        """Get API version information"""
        with self.client.get("/api/version", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Version check failed: {response.status_code}")

    @task(6)
    def search_ticker(self):
        """Search for ticker symbols"""
        # Simulate partial typing - search with 1-4 characters
        search_terms = ["A", "AP", "APP", "APPL", "M", "MS", "MSF", "G", "GO", "GOO"]
        query = random.choice(search_terms)

        with self.client.get(f"/api/search?q={query}", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "results" in data:
                        response.success()
                    else:
                        response.failure("Search response missing results")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Search failed: {response.status_code}")

    @task(5)
    def get_cached_quote(self):
        """Get cached quote for popular stocks"""
        ticker = random.choice(self.tickers[:10])  # Focus on popular stocks for caching

        with self.client.get(f"/api/quote/{ticker}/cached", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Quote not found is acceptable
                response.success()
            else:
                response.failure(f"Cached quote failed: {response.status_code}")

    @task(4)
    def get_watchlist(self):
        """Get user's watchlist"""
        with self.client.get("/api/watchlist", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Watchlist failed: {response.status_code}")

    @task(3)
    def get_watchlist_live_prices(self):
        """Get live prices for watchlist items"""
        with self.client.get("/api/watchlist/live-prices", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Live prices failed: {response.status_code}")

    @task(3)
    def get_analysis_presets(self):
        """Get available analysis presets"""
        with self.client.get("/api/analysis-presets", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "presets" in data and "business_types" in data:
                        response.success()
                    else:
                        response.failure("Analysis presets response missing required fields")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Analysis presets failed: {response.status_code}")

    @task(2)
    def add_to_watchlist(self):
        """Add a stock to watchlist"""
        ticker = random.choice(self.tickers)
        if ticker not in self.user_watchlist:
            with self.client.post(f"/api/watchlist/{ticker}", catch_response=True) as response:
                if response.status_code in [200, 201]:
                    self.user_watchlist.append(ticker)
                    response.success()
                else:
                    response.failure(f"Add to watchlist failed: {response.status_code}")

    @task(1)
    def remove_from_watchlist(self):
        """Remove a stock from watchlist"""
        if self.user_watchlist:
            ticker = random.choice(self.user_watchlist)
            with self.client.delete(f"/api/watchlist/{ticker}", catch_response=True) as response:
                if response.status_code in [200, 204]:
                    self.user_watchlist.remove(ticker)
                    response.success()
                else:
                    response.failure(f"Remove from watchlist failed: {response.status_code}")

    @task(1)
    def get_quote(self):
        """Get real-time quote (slower operation)"""
        ticker = random.choice(self.tickers[:5])  # Limit to popular stocks

        with self.client.get(f"/api/quote/{ticker}", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.success()  # Not found is acceptable
            else:
                response.failure(f"Quote failed: {response.status_code}")

    @task(1)
    def analyze_stock_light(self):
        """Perform stock analysis (heaviest operation - limited frequency)"""
        ticker = random.choice(self.tickers[:3])  # Only test with very popular stocks

        # Use longer timeout for analysis
        with self.client.get(f"/api/analyze/{ticker}",
                           catch_response=True,
                           timeout=30) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "ticker" in data and "fairValue" in data:
                        response.success()
                    else:
                        response.failure("Analysis response missing required fields")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 404:
                response.success()  # Ticker not found is acceptable
            elif response.status_code == 429:
                response.success()  # Rate limiting is acceptable under load
            else:
                response.failure(f"Analysis failed: {response.status_code}")


class PowerUser(HttpUser):
    """
    Simulates a power user who performs more intensive operations
    Lower frequency but more demanding requests
    """
    wait_time = between(5, 10)  # Longer wait times
    weight = 1  # Lower weight means fewer of these users

    def on_start(self):
        """Setup power user session"""
        self.tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        logger.info("Power user started")

    @task(5)
    def analyze_stock(self):
        """Perform detailed stock analysis"""
        ticker = random.choice(self.tickers)

        with self.client.get(f"/api/analyze/{ticker}",
                           catch_response=True,
                           timeout=60) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code in [404, 429]:
                response.success()  # Acceptable responses
            else:
                response.failure(f"Power user analysis failed: {response.status_code}")

    @task(3)
    def compare_stocks(self):
        """Compare multiple stocks"""
        tickers = random.sample(self.tickers, k=2)

        payload = {
            "tickers": tickers,
            "metrics": ["fairValue", "marginOfSafety", "recommendation"]
        }

        with self.client.post("/api/compare",
                            json=payload,
                            catch_response=True,
                            timeout=30) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code in [404, 429]:
                response.success()
            else:
                response.failure(f"Stock comparison failed: {response.status_code}")

    @task(2)
    def check_ai_data(self):
        """Check AI-extracted data availability"""
        ticker = random.choice(self.tickers)

        with self.client.get(f"/api/check-ai-data/{ticker}", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"AI data check failed: {response.status_code}")


class CacheTestUser(HttpUser):
    """
    Specialized user for testing cache performance
    Focuses on cached endpoints to validate sub-200ms requirement
    """
    wait_time = between(0.1, 0.5)  # Very fast requests to test cache
    weight = 2

    def on_start(self):
        """Setup cache test user"""
        self.cached_tickers = ["AAPL", "MSFT", "GOOGL"]  # Popular stocks likely to be cached
        logger.info("Cache test user started")

    @task(10)
    def get_cached_quotes_rapid(self):
        """Rapidly request cached quotes to test performance"""
        ticker = random.choice(self.cached_tickers)

        with self.client.get(f"/api/quote/{ticker}/cached", catch_response=True) as response:
            if response.status_code == 200:
                # Check if response time meets cache performance requirement
                if response.elapsed.total_seconds() > 0.2:  # 200ms threshold
                    response.failure(f"Cached response too slow: {response.elapsed.total_seconds():.3f}s")
                else:
                    response.success()
            else:
                response.failure(f"Cached quote failed: {response.status_code}")

    @task(5)
    def get_cached_watchlist(self):
        """Test cached watchlist performance"""
        with self.client.get("/api/cache/watchlist", catch_response=True) as response:
            if response.status_code == 200:
                if response.elapsed.total_seconds() > 0.2:
                    response.failure(f"Cached watchlist too slow: {response.elapsed.total_seconds():.3f}s")
                else:
                    response.success()
            else:
                response.failure(f"Cached watchlist failed: {response.status_code}")


# Event handlers for custom metrics
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Custom request handler to track performance metrics"""
    if exception:
        logger.warning(f"Request failed: {name} - {exception}")
    elif response_time > 200:  # Log slow requests
        logger.info(f"Slow request: {name} took {response_time}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts"""
    logger.info("Load test starting...")
    logger.info(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops"""
    logger.info("Load test completed")

    # Print summary statistics
    stats = environment.stats
    logger.info(f"Total requests: {stats.total.num_requests}")
    logger.info(f"Total failures: {stats.total.num_failures}")
    logger.info(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    logger.info(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    logger.info(f"99th percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    logger.info(f"Requests per second: {stats.total.current_rps:.2f}")


# Custom user classes for different test scenarios
class HealthCheckUser(HttpUser):
    """User that only performs health checks - for baseline testing"""
    wait_time = between(0.1, 1.0)
    weight = 5

    @task
    def health_check(self):
        self.client.get("/health")


class APIOnlyUser(HttpUser):
    """User that focuses on API endpoints without heavy analysis"""
    wait_time = between(1, 2)
    weight = 3

    @task(5)
    def search(self):
        query = random.choice(["A", "AP", "AAPL", "M", "MS", "MSFT"])
        self.client.get(f"/api/search?q={query}")

    @task(3)
    def get_version(self):
        self.client.get("/api/version")

    @task(2)
    def get_presets(self):
        self.client.get("/api/analysis-presets")

    @task(1)
    def get_watchlist(self):
        self.client.get("/api/watchlist")


if __name__ == "__main__":
    # Instructions for running the load tests
    print("Stock Analysis API Load Testing with Locust")
    print("=" * 50)
    print()
    print("To run load tests:")
    print("1. Start the API server:")
    print("   cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
    print()
    print("2. Run Locust load tests:")
    print("   cd backend && locust -f locustfile.py --host=http://localhost:8000")
    print()
    print("3. Open web interface:")
    print("   http://localhost:8089")
    print()
    print("Recommended test configurations:")
    print("- Light load: 10 users, 2 spawn rate")
    print("- Medium load: 50 users, 5 spawn rate")
    print("- Heavy load: 100 users, 10 spawn rate")
    print("- Cache test: 20 users, 10 spawn rate, use CacheTestUser")
    print()
    print("Performance targets:")
    print("- Health endpoints: <100ms average")
    print("- Cached data: <200ms (95th percentile)")
    print("- API endpoints: <2s average")
    print("- Success rate: >95%")
