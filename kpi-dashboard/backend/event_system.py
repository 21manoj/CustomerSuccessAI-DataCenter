#!/usr/bin/env python3
"""
Event-Driven System for RAG Knowledge Base Management
Handles automatic RAG rebuilds when data changes
"""

import threading
import time
from datetime import datetime
from typing import Dict, List, Callable, Any
from dataclasses import dataclass
from enum import Enum
import queue
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventType(Enum):
    """Event types for the system"""
    KPI_DATA_UPLOADED = "kpi_data_uploaded"
    KPI_DATA_UPDATED = "kpi_data_updated"
    KPI_DATA_DELETED = "kpi_data_deleted"
    ACCOUNT_DATA_CHANGED = "account_data_changed"
    HEALTH_SCORES_UPDATED = "health_scores_updated"
    TEMPORAL_DATA_ADDED = "temporal_data_added"
    CUSTOMER_DATA_CHANGED = "customer_data_changed"
    RAG_REBUILD_REQUESTED = "rag_rebuild_requested"

@dataclass
class Event:
    """Event data structure"""
    event_type: EventType
    customer_id: int
    data: Dict[str, Any]
    timestamp: datetime
    priority: int = 1  # 1=high, 2=medium, 3=low

class EventPublisher:
    """Publishes events to subscribers"""
    
    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable]] = {}
        self.event_queue = queue.PriorityQueue()
        self.is_running = False
        self.worker_thread = None
        
    def start(self):
        """Start the event processing worker"""
        if not self.is_running:
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._process_events, daemon=True)
            self.worker_thread.start()
            logger.info("Event publisher started")
    
    def stop(self):
        """Stop the event processing worker"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join()
        logger.info("Event publisher stopped")
    
    def publish(self, event_type: EventType, customer_id: int, data: Dict[str, Any], priority: int = 1):
        """Publish an event"""
        event = Event(
            event_type=event_type,
            customer_id=customer_id,
            data=data,
            timestamp=datetime.now(),
            priority=priority
        )
        
        # Add to queue with priority
        self.event_queue.put((priority, event))
        logger.info(f"Published event: {event_type.value} for customer {customer_id}")
    
    def subscribe(self, event_type: EventType, subscriber: Callable):
        """Subscribe to specific event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        
        self.subscribers[event_type].append(subscriber)
        logger.info(f"Subscribed to event: {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, subscriber: Callable):
        """Unsubscribe from specific event type"""
        if event_type in self.subscribers:
            if subscriber in self.subscribers[event_type]:
                self.subscribers[event_type].remove(subscriber)
                logger.info(f"Unsubscribed from event: {event_type.value}")
    
    def _process_events(self):
        """Process events from the queue"""
        while self.is_running:
            try:
                # Get event from queue with timeout
                priority, event = self.event_queue.get(timeout=1)
                
                # Notify subscribers
                if event.event_type in self.subscribers:
                    for subscriber in self.subscribers[event.event_type]:
                        try:
                            subscriber(event)
                        except Exception as e:
                            logger.error(f"Error in subscriber for {event.event_type.value}: {str(e)}")
                
                self.event_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing event: {str(e)}")

class RAGRebuildSubscriber:
    """Subscriber that handles RAG knowledge base rebuilds"""
    
    def __init__(self):
        self.rebuild_in_progress = {}
        self.rebuild_lock = threading.Lock()
    
    def handle_event(self, event: Event):
        """Handle RAG rebuild events"""
        customer_id = event.customer_id
        
        # Check if rebuild is already in progress for this customer
        with self.rebuild_lock:
            if customer_id in self.rebuild_in_progress:
                logger.info(f"RAG rebuild already in progress for customer {customer_id}")
                return
            
            self.rebuild_in_progress[customer_id] = True
        
        try:
            logger.info(f"🔄 Starting RAG rebuild for customer {customer_id}")
            
            # Import here to avoid circular imports
            from enhanced_rag_qdrant import get_qdrant_rag_system
            
            # Get RAG system for customer
            rag_system = get_qdrant_rag_system(customer_id)
            
            # Rebuild knowledge base
            start_time = time.time()
            rag_system.build_knowledge_base(customer_id)
            rebuild_time = time.time() - start_time
            
            # Update status
            self._update_knowledge_base_status(customer_id, 'ready')
            
            logger.info(f"✅ RAG rebuild completed for customer {customer_id} in {rebuild_time:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ RAG rebuild failed for customer {customer_id}: {str(e)}")
            self._update_knowledge_base_status(customer_id, 'error')
            
        finally:
            # Remove from in-progress list
            with self.rebuild_lock:
                if customer_id in self.rebuild_in_progress:
                    del self.rebuild_in_progress[customer_id]
    
    def _update_knowledge_base_status(self, customer_id: int, status: str):
        """Update knowledge base status in database"""
        try:
            from models import db, RAGKnowledgeBase
            
            # Update or create status record
            kb_status = RAGKnowledgeBase.query.filter_by(customer_id=customer_id).first()
            if not kb_status:
                kb_status = RAGKnowledgeBase(customer_id=customer_id)
                db.session.add(kb_status)
            
            kb_status.status = status
            kb_status.last_updated = datetime.now()
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error updating knowledge base status: {str(e)}")

class DataIngestionSubscriber:
    """Subscriber that handles real-time data ingestion"""
    
    def __init__(self):
        self.ingestion_queue = queue.Queue()
        self.is_processing = False
        self.worker_thread = None
    
    def start(self):
        """Start the data ingestion worker"""
        if not self.is_processing:
            self.is_processing = True
            self.worker_thread = threading.Thread(target=self._process_ingestion, daemon=True)
            self.worker_thread.start()
            logger.info("Data ingestion subscriber started")
    
    def stop(self):
        """Stop the data ingestion worker"""
        self.is_processing = False
        if self.worker_thread:
            self.worker_thread.join()
        logger.info("Data ingestion subscriber stopped")
    
    def handle_event(self, event: Event):
        """Handle data ingestion events"""
        # Add to ingestion queue for processing
        self.ingestion_queue.put(event)
    
    def _process_ingestion(self):
        """Process data ingestion events"""
        while self.is_processing:
            try:
                event = self.ingestion_queue.get(timeout=1)
                
                if event.event_type == EventType.TEMPORAL_DATA_ADDED:
                    self._process_temporal_data(event)
                elif event.event_type == EventType.KPI_DATA_UPDATED:
                    self._process_kpi_update(event)
                
                self.ingestion_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing ingestion event: {str(e)}")
    
    def _process_temporal_data(self, event: Event):
        """Process temporal data ingestion"""
        try:
            from models import db, KPITimeSeries
            
            data = event.data
            time_series = KPITimeSeries(
                customer_id=event.customer_id,
                kpi_parameter=data['parameter'],
                value=data['value'],
                timestamp=data['timestamp'],
                category=data.get('category', 'General'),
                source=data.get('source', 'real_time')
            )
            
            db.session.add(time_series)
            db.session.commit()
            
            logger.info(f"Temporal data ingested for customer {event.customer_id}")
            
        except Exception as e:
            logger.error(f"Error processing temporal data: {str(e)}")
    
    def _process_kpi_update(self, event: Event):
        """Process KPI data update"""
        try:
            from models import db, KPI
            
            data = event.data
            kpi = KPI.query.get(data['kpi_id'])
            
            if kpi:
                kpi.data = data['new_value']
                kpi.updated_at = datetime.now()
                db.session.commit()
                
                logger.info(f"KPI updated for customer {event.customer_id}")
            
        except Exception as e:
            logger.error(f"Error processing KPI update: {str(e)}")

class EventManager:
    """Manages the event system"""
    
    def __init__(self):
        self.publisher = EventPublisher()
        self.rag_subscriber = RAGRebuildSubscriber()
        self.data_subscriber = DataIngestionSubscriber()
        
        # Subscribe to events
        self._setup_subscriptions()
    
    def start(self):
        """Start the event system"""
        self.publisher.start()
        self.data_subscriber.start()
        logger.info("Event system started")
    
    def stop(self):
        """Stop the event system"""
        self.publisher.stop()
        self.data_subscriber.stop()
        logger.info("Event system stopped")
    
    def _setup_subscriptions(self):
        """Setup event subscriptions"""
        # RAG rebuild events
        self.publisher.subscribe(EventType.KPI_DATA_UPLOADED, self.rag_subscriber.handle_event)
        self.publisher.subscribe(EventType.KPI_DATA_UPDATED, self.rag_subscriber.handle_event)
        self.publisher.subscribe(EventType.ACCOUNT_DATA_CHANGED, self.rag_subscriber.handle_event)
        self.publisher.subscribe(EventType.TEMPORAL_DATA_ADDED, self.rag_subscriber.handle_event)
        self.publisher.subscribe(EventType.RAG_REBUILD_REQUESTED, self.rag_subscriber.handle_event)
        
        # Data ingestion events
        self.publisher.subscribe(EventType.TEMPORAL_DATA_ADDED, self.data_subscriber.handle_event)
        self.publisher.subscribe(EventType.KPI_DATA_UPDATED, self.data_subscriber.handle_event)
    
    def publish_kpi_upload(self, customer_id: int, upload_id: int, kpi_count: int):
        """Publish KPI upload event"""
        self.publisher.publish(
            EventType.KPI_DATA_UPLOADED,
            customer_id,
            {
                'upload_id': upload_id,
                'kpi_count': kpi_count,
                'action': 'upload'
            },
            priority=1
        )
    
    def publish_kpi_update(self, customer_id: int, kpi_id: int, new_value: str):
        """Publish KPI update event"""
        self.publisher.publish(
            EventType.KPI_DATA_UPDATED,
            customer_id,
            {
                'kpi_id': kpi_id,
                'new_value': new_value,
                'action': 'update'
            },
            priority=2
        )
    
    def publish_temporal_data(self, customer_id: int, parameter: str, value: float, timestamp: datetime):
        """Publish temporal data event"""
        self.publisher.publish(
            EventType.TEMPORAL_DATA_ADDED,
            customer_id,
            {
                'parameter': parameter,
                'value': value,
                'timestamp': timestamp,
                'action': 'add'
            },
            priority=2
        )
    
    def publish_account_change(self, customer_id: int, account_id: int, changes: Dict[str, Any]):
        """Publish account change event"""
        self.publisher.publish(
            EventType.ACCOUNT_DATA_CHANGED,
            customer_id,
            {
                'account_id': account_id,
                'changes': changes,
                'action': 'update'
            },
            priority=2
        )
    
    def request_rag_rebuild(self, customer_id: int, reason: str = "manual"):
        """Request RAG rebuild for customer"""
        self.publisher.publish(
            EventType.RAG_REBUILD_REQUESTED,
            customer_id,
            {
                'reason': reason,
                'action': 'rebuild'
            },
            priority=1
        )

# Global event manager instance
event_manager = EventManager()

# Example usage
if __name__ == "__main__":
    # Start event system
    event_manager.start()
    
    # Simulate events
    event_manager.publish_kpi_upload(6, 123, 25)
    event_manager.publish_temporal_data(6, "Revenue", 1000000, datetime.now())
    event_manager.request_rag_rebuild(6, "testing")
    
    # Wait for processing
    time.sleep(5)
    
    # Stop event system
    event_manager.stop()
