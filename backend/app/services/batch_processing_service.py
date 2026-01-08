"""
Batch processing service for large-scale stock analysis
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)


class BatchJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecordStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BatchRecord:
    id: str
    data: Dict[str, Any]
    status: str = "pending"
    error_message: Optional[str] = None
    processed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None


@dataclass
class BatchJobResult:
    job_id: str
    status: BatchJobStatus
    total_records: int
    successful_records: int
    failed_records: int
    skipped_records: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_summary: List[str] = field(default_factory=list)
    records: List[BatchRecord] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_records == 0:
            return 0.0
        return (self.successful_records / self.total_records) * 100.0


class BatchProcessingService:
    def __init__(self, data_quality_service=None, max_workers: int = 4, batch_size: int = 100):
        self.data_quality_service = data_quality_service
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.active_jobs: Dict[str, BatchJobResult] = {}

    async def process_batch(
        self,
        dataset: List[Dict[str, Any]],
        processor_func: Callable[[Dict[str, Any]], Dict[str, Any]],
        job_id: Optional[str] = None,
        validate_input: bool = True
    ) -> BatchJobResult:
        job_id = job_id or str(uuid.uuid4())
        started_at = datetime.utcnow()

        job_result = BatchJobResult(
            job_id=job_id,
            status=BatchJobStatus.RUNNING,
            total_records=len(dataset),
            successful_records=0,
            failed_records=0,
            skipped_records=0,
            started_at=started_at
        )

        self.active_jobs[job_id] = job_result

        try:
            records = []
            for i, data in enumerate(dataset):
                record = BatchRecord(
                    id=f"{job_id}_{i}",
                    data=data
                )
                records.append(record)

            job_result.records = records

            # Simple processing for now
            for record in records:
                try:
                    result = processor_func(record.data)
                    record.result = result
                    record.status = RecordStatus.SUCCESS.value
                    record.processed_at = datetime.utcnow()
                except Exception as e:
                    record.status = RecordStatus.FAILED.value
                    record.error_message = f"Processing error: {str(e)}"
                    record.processed_at = datetime.utcnow()

            job_result.successful_records = sum(1 for r in records if r.status == RecordStatus.SUCCESS.value)
            job_result.failed_records = sum(1 for r in records if r.status == RecordStatus.FAILED.value)
            job_result.skipped_records = sum(1 for r in records if r.status == RecordStatus.SKIPPED.value)

            job_result.error_summary = [
                f"Record {r.id}: {r.error_message}"
                for r in records
                if r.error_message
            ]

            job_result.status = BatchJobStatus.COMPLETED
            job_result.completed_at = datetime.utcnow()

        except Exception as e:
            job_result.status = BatchJobStatus.FAILED
            job_result.completed_at = datetime.utcnow()
            job_result.error_summary.append(f"Job failed: {str(e)}")
            raise

        return job_result
