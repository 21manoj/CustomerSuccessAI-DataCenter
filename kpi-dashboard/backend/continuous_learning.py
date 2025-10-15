#!/usr/bin/env python3
"""
Continuous Learning System for RAG Knowledge Base
Implements feedback collection, performance monitoring, and model updates
"""

import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import schedule

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FeedbackType(Enum):
    """Types of user feedback"""
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    PARTIALLY_HELPFUL = "partially_helpful"
    IRRELEVANT = "irrelevant"
    INCOMPLETE = "incomplete"

@dataclass
class Feedback:
    """User feedback data structure"""
    query: str
    response: str
    feedback_type: FeedbackType
    customer_id: int
    timestamp: datetime
    additional_notes: Optional[str] = None
    response_time: Optional[float] = None
    results_count: Optional[int] = None

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    helpfulness_rate: float
    query_success_rate: float
    response_relevance: float
    user_satisfaction: float
    avg_response_time: float
    avg_results_count: float
    query_volume: int
    timestamp: datetime

class FeedbackCollector:
    """Collects and stores user feedback"""
    
    def __init__(self):
        self.feedback_data = []
        self.feedback_lock = threading.Lock()
    
    def collect_feedback(self, feedback: Feedback):
        """Collect user feedback"""
        with self.feedback_lock:
            self.feedback_data.append(feedback)
        
        logger.info(f"Feedback collected: {feedback.feedback_type.value} for customer {feedback.customer_id}")
    
    def get_recent_feedback(self, days: int = 30) -> List[Feedback]:
        """Get recent feedback data"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self.feedback_lock:
            return [f for f in self.feedback_data if f.timestamp >= cutoff_date]
    
    def get_feedback_by_customer(self, customer_id: int, days: int = 30) -> List[Feedback]:
        """Get feedback for specific customer"""
        recent_feedback = self.get_recent_feedback(days)
        return [f for f in recent_feedback if f.customer_id == customer_id]
    
    def calculate_helpfulness_rate(self, feedback_data: List[Feedback]) -> float:
        """Calculate helpfulness rate from feedback"""
        if not feedback_data:
            return 0.0
        
        helpful_count = len([f for f in feedback_data if f.feedback_type == FeedbackType.HELPFUL])
        total_count = len(feedback_data)
        
        return helpful_count / total_count if total_count > 0 else 0.0
    
    def calculate_user_satisfaction(self, feedback_data: List[Feedback]) -> float:
        """Calculate user satisfaction score"""
        if not feedback_data:
            return 0.0
        
        # Weight different feedback types
        weights = {
            FeedbackType.HELPFUL: 1.0,
            FeedbackType.PARTIALLY_HELPFUL: 0.5,
            FeedbackType.NOT_HELPFUL: 0.0,
            FeedbackType.IRRELEVANT: 0.0,
            FeedbackType.INCOMPLETE: 0.2
        }
        
        total_score = sum(weights.get(f.feedback_type, 0.0) for f in feedback_data)
        total_count = len(feedback_data)
        
        return total_score / total_count if total_count > 0 else 0.0

class PerformanceMonitor:
    """Monitors RAG system performance"""
    
    def __init__(self):
        self.query_metrics = []
        self.metrics_lock = threading.Lock()
    
    def track_query(self, query: str, response: Dict, execution_time: float, customer_id: int):
        """Track query performance metrics"""
        metrics = {
            'query': query,
            'query_length': len(query),
            'response_length': len(response.get('response', '')),
            'execution_time': execution_time,
            'results_count': response.get('results_count', 0),
            'similarity_scores': [r.get('similarity', 0) for r in response.get('relevant_results', [])],
            'customer_id': customer_id,
            'timestamp': datetime.now()
        }
        
        with self.metrics_lock:
            self.query_metrics.append(metrics)
        
        logger.info(f"Query tracked: {execution_time:.2f}s, {metrics['results_count']} results")
    
    def get_recent_metrics(self, days: int = 7) -> List[Dict]:
        """Get recent performance metrics"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self.metrics_lock:
            return [m for m in self.query_metrics if m['timestamp'] >= cutoff_date]
    
    def calculate_performance_metrics(self, metrics_data: List[Dict]) -> PerformanceMetrics:
        """Calculate performance metrics from tracked data"""
        if not metrics_data:
            return PerformanceMetrics(
                helpfulness_rate=0.0,
                query_success_rate=0.0,
                response_relevance=0.0,
                user_satisfaction=0.0,
                avg_response_time=0.0,
                avg_results_count=0.0,
                query_volume=0,
                timestamp=datetime.now()
            )
        
        # Calculate metrics
        avg_response_time = sum(m['execution_time'] for m in metrics_data) / len(metrics_data)
        avg_results_count = sum(m['results_count'] for m in metrics_data) / len(metrics_data)
        
        # Calculate response relevance based on similarity scores
        all_similarities = []
        for m in metrics_data:
            all_similarities.extend(m['similarity_scores'])
        
        avg_similarity = sum(all_similarities) / len(all_similarities) if all_similarities else 0.0
        response_relevance = min(avg_similarity * 2, 1.0)  # Scale to 0-1
        
        # Calculate query success rate (queries with results)
        successful_queries = len([m for m in metrics_data if m['results_count'] > 0])
        query_success_rate = successful_queries / len(metrics_data)
        
        return PerformanceMetrics(
            helpfulness_rate=0.0,  # Will be calculated from feedback
            query_success_rate=query_success_rate,
            response_relevance=response_relevance,
            user_satisfaction=0.0,  # Will be calculated from feedback
            avg_response_time=avg_response_time,
            avg_results_count=avg_results_count,
            query_volume=len(metrics_data),
            timestamp=datetime.now()
        )

class ModelUpdater:
    """Updates RAG models based on performance feedback"""
    
    def __init__(self):
        self.rag_system = None
        self.update_history = []
    
    def set_rag_system(self, rag_system):
        """Set the RAG system to update"""
        self.rag_system = rag_system
    
    def update_similarity_threshold(self, new_threshold: float):
        """Update similarity threshold based on performance"""
        if self.rag_system:
            try:
                self.rag_system.similarity_threshold = new_threshold
                logger.info(f"Similarity threshold updated to {new_threshold}")
                
                self.update_history.append({
                    'type': 'similarity_threshold',
                    'old_value': getattr(self.rag_system, 'similarity_threshold', 0.0),
                    'new_value': new_threshold,
                    'timestamp': datetime.now()
                })
                
            except Exception as e:
                logger.error(f"Error updating similarity threshold: {str(e)}")
    
    def update_prompt_templates(self, new_prompts: Dict[str, str]):
        """Update prompt templates based on feedback"""
        if self.rag_system:
            try:
                # Update prompt templates in RAG system
                if hasattr(self.rag_system, 'prompt_templates'):
                    self.rag_system.prompt_templates.update(new_prompts)
                
                logger.info("Prompt templates updated")
                
                self.update_history.append({
                    'type': 'prompt_templates',
                    'old_value': 'previous_templates',
                    'new_value': new_prompts,
                    'timestamp': datetime.now()
                })
                
            except Exception as e:
                logger.error(f"Error updating prompt templates: {str(e)}")
    
    def retrain_embeddings(self, kpi_data: List, account_data: List):
        """Retrain embedding model with new data"""
        if self.rag_system:
            try:
                logger.info("Retraining embedding model...")
                
                # Retrain embeddings
                self.rag_system.build_knowledge_base(
                    customer_id=1,  # Use customer 1 for retraining
                    kpi_data=kpi_data,
                    account_data=account_data
                )
                
                logger.info("Embedding model retrained successfully")
                
                self.update_history.append({
                    'type': 'embedding_retrain',
                    'old_value': 'previous_model',
                    'new_value': 'retrained_model',
                    'timestamp': datetime.now()
                })
                
            except Exception as e:
                logger.error(f"Error retraining embeddings: {str(e)}")

class ContinuousLearningSystem:
    """Main continuous learning system"""
    
    def __init__(self):
        self.feedback_collector = FeedbackCollector()
        self.performance_monitor = PerformanceMonitor()
        self.model_updater = ModelUpdater()
        self.is_running = False
        self.learning_thread = None
        
        # Learning thresholds
        self.thresholds = {
            'min_helpfulness_rate': 0.7,
            'min_query_success_rate': 0.8,
            'min_response_relevance': 0.6,
            'min_user_satisfaction': 0.5,
            'max_avg_response_time': 5.0
        }
    
    def start(self):
        """Start the continuous learning system"""
        if not self.is_running:
            self.is_running = True
            self.learning_thread = threading.Thread(target=self._learning_loop, daemon=True)
            self.learning_thread.start()
            logger.info("Continuous learning system started")
    
    def stop(self):
        """Stop the continuous learning system"""
        self.is_running = False
        if self.learning_thread:
            self.learning_thread.join()
        logger.info("Continuous learning system stopped")
    
    def collect_feedback(self, query: str, response: str, feedback_type: FeedbackType, 
                        customer_id: int, additional_notes: str = None, 
                        response_time: float = None, results_count: int = None):
        """Collect user feedback"""
        feedback = Feedback(
            query=query,
            response=response,
            feedback_type=feedback_type,
            customer_id=customer_id,
            timestamp=datetime.now(),
            additional_notes=additional_notes,
            response_time=response_time,
            results_count=results_count
        )
        
        self.feedback_collector.collect_feedback(feedback)
    
    def track_query_performance(self, query: str, response: Dict, execution_time: float, customer_id: int):
        """Track query performance"""
        self.performance_monitor.track_query(query, response, execution_time, customer_id)
    
    def analyze_performance(self) -> PerformanceMetrics:
        """Analyze current performance"""
        # Get recent feedback and metrics
        recent_feedback = self.feedback_collector.get_recent_feedback(days=7)
        recent_metrics = self.performance_monitor.get_recent_metrics(days=7)
        
        # Calculate performance metrics
        performance_metrics = self.performance_monitor.calculate_performance_metrics(recent_metrics)
        
        # Add feedback-based metrics
        performance_metrics.helpfulness_rate = self.feedback_collector.calculate_helpfulness_rate(recent_feedback)
        performance_metrics.user_satisfaction = self.feedback_collector.calculate_user_satisfaction(recent_feedback)
        
        return performance_metrics
    
    def should_update_models(self, metrics: PerformanceMetrics) -> bool:
        """Determine if models should be updated based on metrics"""
        return (
            metrics.helpfulness_rate < self.thresholds['min_helpfulness_rate'] or
            metrics.query_success_rate < self.thresholds['min_query_success_rate'] or
            metrics.response_relevance < self.thresholds['min_response_relevance'] or
            metrics.user_satisfaction < self.thresholds['min_user_satisfaction'] or
            metrics.avg_response_time > self.thresholds['max_avg_response_time']
        )
    
    def update_models(self, metrics: PerformanceMetrics):
        """Update models based on performance metrics"""
        logger.info("Updating models based on performance metrics")
        
        # Update similarity threshold if response relevance is low
        if metrics.response_relevance < self.thresholds['min_response_relevance']:
            new_threshold = max(0.1, metrics.response_relevance * 0.8)
            self.model_updater.update_similarity_threshold(new_threshold)
        
        # Update prompt templates if user satisfaction is low
        if metrics.user_satisfaction < self.thresholds['min_user_satisfaction']:
            new_prompts = self._generate_improved_prompts(metrics)
            self.model_updater.update_prompt_templates(new_prompts)
        
        # Retrain embeddings if helpfulness rate is low
        if metrics.helpfulness_rate < self.thresholds['min_helpfulness_rate']:
            self._retrain_embeddings()
    
    def _generate_improved_prompts(self, metrics: PerformanceMetrics) -> Dict[str, str]:
        """Generate improved prompt templates based on performance"""
        # This would analyze feedback patterns and generate better prompts
        # For now, return example improved prompts
        
        improved_prompts = {
            'general_query': f"""
            Based on the following customer data, provide a comprehensive analysis:
            
            Query: {{query}}
            
            Context: The customer has {metrics.query_volume} queries this week with an average response time of {metrics.avg_response_time:.2f}s.
            
            Please provide:
            1. Direct answer to the query
            2. Relevant data points and metrics
            3. Actionable insights and recommendations
            4. Context about performance trends
            
            Focus on clarity and actionable insights.
            """,
            
            'revenue_analysis': f"""
            Analyze revenue data with the following context:
            
            Query: {{query}}
            
            Performance Context:
            - Average response time: {metrics.avg_response_time:.2f}s
            - Query success rate: {metrics.query_success_rate:.1%}
            - User satisfaction: {metrics.user_satisfaction:.1%}
            
            Provide detailed revenue analysis including:
            1. Current revenue metrics
            2. Trends and patterns
            3. Comparison to benchmarks
            4. Recommendations for improvement
            """
        }
        
        return improved_prompts
    
    def _retrain_embeddings(self):
        """Retrain embeddings with all available data"""
        try:
            from models import KPI, Account
            
            # Get all data for retraining
            all_kpis = KPI.query.all()
            all_accounts = Account.query.all()
            
            self.model_updater.retrain_embeddings(all_kpis, all_accounts)
            
        except Exception as e:
            logger.error(f"Error retraining embeddings: {str(e)}")
    
    def _learning_loop(self):
        """Main learning loop"""
        while self.is_running:
            try:
                # Analyze performance every hour
                time.sleep(3600)  # 1 hour
                
                if self.is_running:
                    metrics = self.analyze_performance()
                    
                    if self.should_update_models(metrics):
                        logger.info("Performance below thresholds, updating models")
                        self.update_models(metrics)
                    else:
                        logger.info("Performance within acceptable thresholds")
                
            except Exception as e:
                logger.error(f"Error in learning loop: {str(e)}")
                time.sleep(60)  # Wait 1 minute before retrying

# Global continuous learning system instance
learning_system = ContinuousLearningSystem()

# Example usage
if __name__ == "__main__":
    # Start continuous learning system
    learning_system.start()
    
    # Simulate feedback collection
    learning_system.collect_feedback(
        query="What are the top revenue accounts?",
        response="Here are the top revenue accounts...",
        feedback_type=FeedbackType.HELPFUL,
        customer_id=6,
        response_time=2.5,
        results_count=5
    )
    
    # Simulate query performance tracking
    learning_system.track_query_performance(
        query="Show me customer satisfaction scores",
        response={"results_count": 3, "response": "Customer satisfaction scores..."},
        execution_time=1.8,
        customer_id=6
    )
    
    # Wait for processing
    time.sleep(5)
    
    # Stop learning system
    learning_system.stop()
