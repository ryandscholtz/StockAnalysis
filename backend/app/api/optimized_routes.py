"""
Optimized API routes with background processing and advanced caching
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends
from typing import Optional, Dict
import asyncio
import logging
from datetime import datetime

from app.background_tasks import task_manager, fetch_live_prices_background, analyze_stock_background
from app.cache_manager import cache_manager, cache_fastapi_endpoint
from app.database.db_service import DatabaseService
from app.core.dependencies import get_yahoo_client
from app.data.api_client import YahooFinanceClient

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/watchlist/live-prices-async")
async def get_watchlist_live_prices_async():
    """
    Start background task for live price fetching - returns immediately with task ID
    Frontend can poll /api/tasks/{task_id} for status and results
    """
    try:
        db_service = DatabaseService(db_path="stock_analysis.db")
        watchlist_items = db_service.get_watchlist()
        tickers = [item['ticker'] for item in watchlist_items]

        if not tickers:
            return {"live_prices": {}, "message": "No tickers in watchlist"}

        # Check cache first
        cache_key = f"live_prices:{'_'.join(sorted(tickers))}"
        cached_result = cache_manager.get(cache_key)

        if cached_result:
            return {
                "live_prices": cached_result,
                "cached": True,
                "message": "Returned cached live prices"
            }

        # Start background task
        task_id = task_manager.create_task(
            "live_prices",
            fetch_live_prices_background,
            tickers,
            metadata={"tickers": tickers, "cache_key": cache_key}
        )

        return {
            "task_id": task_id,
            "status": "started",
            "message": f"Started background task to fetch prices for {len(tickers)} tickers",
            "poll_url": f"/api/tasks/{task_id}"
        }

    except Exception as e:
        logger.error(f"Error starting live prices task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analyze/{ticker}/async")
async def analyze_stock_async(
    ticker: str,
    business_type: Optional[str] = Query(None),
    analysis_weights: Optional[str] = Query(None)  # JSON string
):
    """
    Start background task for stock analysis - returns immediately with task ID
    """
    try:
        # Parse analysis weights if provided
        weights_dict = None
        if analysis_weights:
            import json
            try:
                weights_dict = json.loads(analysis_weights)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid analysis_weights JSON")

        # Check cache first
        cache_key = cache_manager._generate_key(
            "stock_analysis",
            ticker=ticker.upper(),
            business_type=business_type,
            weights=weights_dict
        )

        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return {
                "analysis": cached_result,
                "cached": True,
                "message": f"Returned cached analysis for {ticker.upper()}"
            }

        # Start background task
        task_id = task_manager.create_task(
            "stock_analysis",
            analyze_stock_background,
            ticker.upper(),
            business_type=business_type,
            analysis_weights=weights_dict,
            metadata={
                "ticker": ticker.upper(),
                "business_type": business_type,
                "cache_key": cache_key
            }
        )

        return {
            "task_id": task_id,
            "status": "started",
            "message": f"Started background analysis for {ticker.upper()}",
            "poll_url": f"/api/tasks/{task_id}"
        }

    except Exception as e:
        logger.error(f"Error starting analysis task for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    Get the status and results of a background task
    """
    task_status = task_manager.get_task_status(task_id)

    if not task_status:
        raise HTTPException(status_code=404, detail="Task not found")

    # If task is completed and has results, cache them
    if (task_status['status'] == 'completed' and
        task_status['result'] and
        task_status.get('metadata', {}).get('cache_key')):

        cache_key = task_status['metadata']['cache_key']
        cache_manager.set(cache_key, task_status['result'], ttl_minutes=30)

    return task_status

@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """
    Cancel a running background task
    """
    success = task_manager.cancel_task(task_id)

    if not success:
        raise HTTPException(status_code=404, detail="Task not found or not running")

    return {"message": f"Task {task_id} cancelled successfully"}

@router.get("/tasks")
async def list_tasks(status: Optional[str] = Query(None)):
    """
    List all background tasks, optionally filtered by status
    """
    all_tasks = []

    for task_id in task_manager.tasks:
        task_status = task_manager.get_task_status(task_id)
        if status is None or task_status['status'] == status:
            # Don't include full result in list view
            task_summary = task_status.copy()
            if 'result' in task_summary:
                task_summary['has_result'] = task_summary['result'] is not None
                del task_summary['result']
            all_tasks.append(task_summary)

    return {"tasks": all_tasks, "total": len(all_tasks)}

@router.get("/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics and performance metrics
    """
    return cache_manager.get_stats()

@router.delete("/cache")
async def clear_cache():
    """
    Clear all cached data
    """
    cache_manager.clear()
    return {"message": "Cache cleared successfully"}

@router.delete("/cache/{key_prefix}")
async def clear_cache_by_prefix(key_prefix: str):
    """
    Clear cached data by key prefix
    """
    keys_to_delete = [key for key in cache_manager.cache.keys() if key.startswith(key_prefix)]

    for key in keys_to_delete:
        cache_manager.delete(key)

    return {
        "message": f"Cleared {len(keys_to_delete)} cache entries with prefix '{key_prefix}'",
        "deleted_count": len(keys_to_delete)
    }

# Fast cached endpoints for immediate responses
@router.get("/cache/watchlist")
async def get_cached_watchlist():
    """
    Get watchlist data with aggressive caching for instant response
    """
    try:
        db_service = DatabaseService(db_path="stock_analysis.db")
        watchlist_items = db_service.get_watchlist()

        return {
            "items": watchlist_items,
            "total": len(watchlist_items),
            "cached": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting cached watchlist: {e}")
        # Return empty watchlist instead of 500 error
        return {
            "items": [],
            "total": 0,
            "cached": True,
            "error": "Watchlist temporarily unavailable",
            "timestamp": datetime.now().isoformat()
        }

@router.get("/quote/{ticker}/cached")
async def get_cached_quote(
    ticker: str,
    yahoo_client: YahooFinanceClient = Depends(get_yahoo_client)
):
    """
    Get basic quote data with caching - for instant price display
    """
    try:
        # Get quote synchronously to avoid thread pool issues
        quote = yahoo_client.get_quote(ticker.upper())

        if quote and quote.get('success'):
            return {
                "ticker": ticker.upper(),
                "price": quote.get('price'),
                "company_name": quote.get('company_name'),
                "cached": True,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "ticker": ticker.upper(),
                "error": quote.get('error', 'No data available') if quote else 'No response',
                "cached": True,
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"Error getting cached quote for {ticker}: {e}")
        # Return error response instead of 500
        return {
            "ticker": ticker.upper(),
            "error": "Quote temporarily unavailable",
            "cached": True,
            "timestamp": datetime.now().isoformat()
        }

@router.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check including background tasks and cache status
    """
    try:
        # Check database
        db_service = DatabaseService(db_path="stock_analysis.db")
        watchlist_count = len(db_service.get_watchlist())

        # Check background tasks
        running_tasks = len(task_manager.running_tasks)
        total_tasks = len(task_manager.tasks)

        # Check cache
        cache_stats = cache_manager.get_stats()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": {
                "accessible": True,
                "watchlist_items": watchlist_count
            },
            "background_tasks": {
                "running": running_tasks,
                "total": total_tasks
            },
            "cache": cache_stats,
            "memory_usage": {
                "cache_mb": cache_stats['current_size_mb'],
                "cache_utilization": f"{cache_stats['utilization_percent']}%"
            }
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
