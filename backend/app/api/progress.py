"""
Progress tracking utilities for analysis
"""
from typing import Callable, Optional
import asyncio


class ProgressTracker:
    """Track and report progress of analysis"""
    
    def __init__(self, total_steps: int = 7):
        self.total_steps = total_steps
        self.current_step = 0
        self.current_task = ""
        self.callback: Optional[Callable] = None
    
    def set_callback(self, callback: Callable):
        """Set callback function to report progress"""
        self.callback = callback
    
    async def update(self, step: int, task: str):
        """Update progress"""
        self.current_step = step
        self.current_task = task
        if self.callback:
            try:
                progress_data = {
                    'step': step,
                    'total': self.total_steps,
                    'task': task,
                    'progress': (step / self.total_steps) * 100
                }
                print(f"ProgressTracker.update: Step {step}/{self.total_steps} - {task}")  # Debug log
                await self.callback(progress_data)
            except Exception as e:
                print(f"Error in progress callback: {e}")
                import traceback
                traceback.print_exc()
    
    async def step(self, task: str):
        """Increment step and update"""
        self.current_step += 1
        await self.update(self.current_step, task)

