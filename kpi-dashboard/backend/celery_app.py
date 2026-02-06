"""
Celery Application Configuration
=================================

Celery configuration for async task processing.

Usage:
    # Start Celery worker
    celery -A celery_app worker --loglevel=info
    
    # Start with multiple workers
    celery -A celery_app worker --loglevel=info --concurrency=4
"""

from celery import Celery
import os

# Initialize Celery
celery = Celery(
    'wizard_tasks',
    broker=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
)

# Configuration
celery.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task execution
    task_track_started=True,
    task_time_limit=7200,  # 2 hours max per task
    task_soft_time_limit=6900,  # Soft limit at 1h 55min
    
    # Result backend
    result_expires=86400,  # Results expire after 24 hours
    result_persistent=True,
    
    # Worker
    worker_prefetch_multiplier=1,  # One task at a time
    worker_max_tasks_per_child=10,  # Restart worker after 10 tasks
    
    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Rate limiting
    task_default_rate_limit='10/m',  # 10 tasks per minute
)

# Import tasks (so Celery can discover them)
#from wizard_tasks import (
 #   generate_journey_data_task,
 #   test_predictions_task,
 #   learn_ensemble_weights_task,
 #   generate_visualizations_task,
 #   extract_learnings_task
#)#


if __name__ == '__main__':
    celery.start()

# Import tasks AFTER celery is defined (avoid circular imports)
import wizard_tasks
