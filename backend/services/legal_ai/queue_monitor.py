"""Queue Monitoring utility for Celery/ProcessingJobs."""
from sqlalchemy.orm import Session
from models.document_intelligence import ProcessingJob
from models.ai_models import QueueMetric

class QueueMonitor:
    def __init__(self, db: Session):
        self.db = db

    def get_metrics(self) -> dict:
        """Query ProcessingJobs database state to extract active queue statistics."""
        pending_count = self.db.query(ProcessingJob).filter(ProcessingJob.status == "PENDING").count()
        running_count = self.db.query(ProcessingJob).filter(ProcessingJob.status == "RUNNING").count()
        failed_count = self.db.query(ProcessingJob).filter(ProcessingJob.status == "FAILED").count()
        completed_count = self.db.query(ProcessingJob).filter(ProcessingJob.status == "COMPLETED").count()
        
        queue_length = pending_count + running_count
        
        # Calculate approximate wait time based on pending jobs
        wait_time = 15.0 if pending_count == 0 else 180.0 * pending_count
        
        max_slots = 4
        worker_util = min(1.0, running_count / max_slots)
        
        # Retrieve retry count from job warnings or logs
        retry_count = self.db.query(ProcessingJob).filter(ProcessingJob.error_message.like("%retry%")).count()

        # Save to database log
        metric_record = QueueMetric(
            queue_length=queue_length,
            wait_time=wait_time,
            worker_util=worker_util,
            retry_count=retry_count,
            failed_jobs=failed_count
        )
        self.db.add(metric_record)
        self.db.commit()

        return {
            "queue_length": queue_length,
            "wait_time_ms": wait_time,
            "worker_utilization": round(worker_util * 100, 1),
            "retry_count": retry_count,
            "failed_jobs": failed_count,
            "completed_jobs": completed_count,
            "active_workers": running_count
        }
