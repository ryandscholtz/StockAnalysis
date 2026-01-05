"""
Background task processing for non-blocking API operations
"""
import asyncio
import logging
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
import json
import uuid
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class BackgroundTask:
    id: str
    task_type: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict] = None

class BackgroundTaskManager:
    """Manages background tasks for non-blocking operations"""
    
    def __init__(self):
        self.tasks: Dict[str, BackgroundTask] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.max_concurrent_tasks = 10
        self.task_timeout = 300  # 5 minutes
        
    def create_task(self, task_type: str, task_func: Callable, *args, **kwargs) -> str:
        """Create a new background task"""
        task_id = str(uuid.uuid4())
        
        # Create task record
        bg_task = BackgroundTask(
            id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            metadata=kwargs.get('metadata', {})
        )
        
        self.tasks[task_id] = bg_task
        
        # Start the task
        asyncio_task = asyncio.create_task(self._run_task(task_id, task_func, *args, **kwargs))
        self.running_tasks[task_id] = asyncio_task
        
        logger.info(f"Created background task {task_id} of type {task_type}")
        return task_id
    
    async def _run_task(self, task_id: str, task_func: Callable, *args, **kwargs):
        """Run a background task with error handling and progress tracking"""
        task = self.tasks[task_id]
        
        try:
            # Update status to running
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            # Execute the task function
            if asyncio.iscoroutinefunction(task_func):
                result = await task_func(*args, **kwargs)
            else:
                # Run synchronous function in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, task_func, *args, **kwargs)
            
            # Task completed successfully
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            task.progress = 100.0
            
            logger.info(f"Background task {task_id} completed successfully")
            
        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            logger.info(f"Background task {task_id} was cancelled")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error = str(e)
            logger.error(f"Background task {task_id} failed: {e}")
            
        finally:
            # Clean up running task reference
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get the status of a background task"""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        return {
            'id': task.id,
            'task_type': task.task_type,
            'status': task.status.value,
            'progress': task.progress,
            'created_at': task.created_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'result': task.result,
            'error': task.error,
            'metadata': task.metadata
        }
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running background task"""
        if task_id in self.running_tasks:
            asyncio_task = self.running_tasks[task_id]
            asyncio_task.cancel()
            return True
        return False
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old completed/failed tasks"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        tasks_to_remove = []
        for task_id, task in self.tasks.items():
            if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                task.completed_at and task.completed_at < cutoff_time):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
        
        if tasks_to_remove:
            logger.info(f"Cleaned up {len(tasks_to_remove)} old background tasks")

# Global task manager instance
task_manager = BackgroundTaskManager()

# Background task functions for common operations
async def fetch_live_prices_background(tickers: list) -> Dict:
    """Background task for fetching live prices"""
    from app.data.api_client import YahooFinanceClient
    
    yahoo_client = YahooFinanceClient()
    live_prices = {}
    
    # Process tickers with limited concurrency
    semaphore = asyncio.Semaphore(3)  # Max 3 concurrent API calls
    
    async def fetch_single_price(ticker: str):
        async with semaphore:
            try:
                loop = asyncio.get_event_loop()
                quote = await loop.run_in_executor(None, yahoo_client.get_quote, ticker)
                return ticker, quote
            except Exception as e:
                logger.warning(f"Error fetching price for {ticker}: {e}")
                return ticker, {'error': str(e)}
    
    # Fetch all prices concurrently
    tasks = [fetch_single_price(ticker) for ticker in tickers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Task failed: {result}")
            continue
        
        ticker, quote = result
        if quote:
            if quote.get('success'):
                live_prices[ticker] = {
                    'price': quote.get('price'),
                    'company_name': quote.get('company_name', ticker),
                    'success': True,
                    'comment': 'Successfully fetched from background task'
                }
            else:
                live_prices[ticker] = {
                    'error': quote.get('error', 'Unknown error'),
                    'success': False,
                    'comment': quote.get('error_detail', 'Background task failed')
                }
        else:
            live_prices[ticker] = {
                'error': 'No data returned',
                'success': False,
                'comment': 'Background task returned no data'
            }
    
    return {'live_prices': live_prices}

async def analyze_stock_background(ticker: str, business_type: str = None, analysis_weights: dict = None) -> Dict:
    """Background task for stock analysis"""
    from app.api.routes import _analyze_stock_with_progress
    from app.api.progress import ProgressTracker
    
    # Create a progress tracker for the background task
    progress_tracker = ProgressTracker()
    
    try:
        result = await _analyze_stock_with_progress(
            ticker=ticker,
            progress_tracker=progress_tracker,
            business_type=business_type,
            analysis_weights=analysis_weights
        )
        
        # Convert to dict for JSON serialization
        return result.dict() if hasattr(result, 'dict') else result
        
    except Exception as e:
        logger.error(f"Background stock analysis failed for {ticker}: {e}")
        raise