#!/usr/bin/env python3
"""
Health Score Rollup Subscriber

Automatically calculates Level 1/2/3 health score rollups when KPIs are uploaded.
Stores results in health_trends table for use by Signal Analyst and dashboards.
"""

from datetime import datetime, timedelta
from typing import Dict
import logging
from extensions import db
from models import Account, KPI, KPIUpload, HealthTrend
from health_score_storage import HealthScoreStorageService
from event_system import Event, EventType

logger = logging.getLogger(__name__)


class HealthScoreRollupSubscriber:
    """Subscriber that automatically calculates health scores on KPI upload"""
    
    def __init__(self):
        self.storage_service = HealthScoreStorageService()
        logger.info("HealthScoreRollupSubscriber initialized")
    
    def handle_event(self, event: Event):
        """Handle KPI_DATA_UPLOADED events and calculate health scores"""
        try:
            if event.event_type != EventType.KPI_DATA_UPLOADED:
                return  # Only handle KPI upload events
            
            customer_id = event.customer_id
            event_data = event.data
            
            # Get upload_id from event data
            upload_id = event_data.get('upload_id')
            if not upload_id:
                logger.warning(f"No upload_id in event data for customer {customer_id}")
                return
            
            # Get KPIUpload to find account_id
            kpi_upload = db.session.get(KPIUpload, upload_id)
            if not kpi_upload:
                logger.warning(f"KPIUpload {upload_id} not found")
                return
            
            account_id = kpi_upload.account_id
            if not account_id:
                logger.warning(f"No account_id in KPIUpload {upload_id}")
                return
            
            # Verify account belongs to customer (security check)
            account = Account.query.filter_by(
                account_id=account_id,
                customer_id=customer_id
            ).first()
            
            if not account:
                logger.warning(f"Account {account_id} not found or doesn't belong to customer {customer_id}")
                return
            
            logger.info(f"Calculating health scores for account {account.account_name} (ID: {account_id}) after KPI upload")
            
            # Calculate Level 1/2/3 health scores
            health_scores = self.storage_service._calculate_account_health_scores(account, customer_id)
            
            # Get current month/year for storage
            now = datetime.utcnow()
            month = now.month
            year = now.year
            
            # Check if trend already exists for this month
            existing_trend = HealthTrend.query.filter_by(
                account_id=account_id,
                month=month,
                year=year
            ).first()
            
            if existing_trend:
                # Update existing trend
                existing_trend.overall_health_score = health_scores['overall']
                existing_trend.product_usage_score = health_scores.get('product_usage', 0)
                existing_trend.support_score = health_scores.get('support', 0)
                existing_trend.customer_sentiment_score = health_scores.get('customer_sentiment', 0)
                existing_trend.business_outcomes_score = health_scores.get('business_outcomes', 0)
                existing_trend.relationship_strength_score = health_scores.get('relationship_strength', 0)
                existing_trend.total_kpis = health_scores.get('total_kpis', 0)
                existing_trend.valid_kpis = health_scores.get('valid_kpis', 0)
                existing_trend.updated_at = now
                trend = existing_trend
                logger.info(f"✅ Updated health score for account {account.account_name}: {health_scores['overall']:.1f}/100")
            else:
                # Create new trend
                trend = HealthTrend(
                    account_id=account_id,
                    customer_id=customer_id,
                    month=month,
                    year=year,
                    overall_health_score=health_scores['overall'],
                    product_usage_score=health_scores.get('product_usage', 0),
                    support_score=health_scores.get('support', 0),
                    customer_sentiment_score=health_scores.get('customer_sentiment', 0),
                    business_outcomes_score=health_scores.get('business_outcomes', 0),
                    relationship_strength_score=health_scores.get('relationship_strength', 0),
                    total_kpis=health_scores.get('total_kpis', 0),
                    valid_kpis=health_scores.get('valid_kpis', 0)
                )
                db.session.add(trend)
                logger.info(f"✅ Created health score for account {account.account_name}: {health_scores['overall']:.1f}/100")
            
            db.session.commit()
            
            # Publish HEALTH_SCORES_UPDATED event (for other subscribers like snapshots)
            try:
                from event_system import event_manager
                event_manager.publisher.publish(
                    EventType.HEALTH_SCORES_UPDATED,
                    customer_id,
                    {
                        'account_id': account_id,
                        'overall_health_score': float(health_scores['overall']),
                        'trigger': 'kpi_upload'
                    },
                    priority=2
                )
                logger.debug(f"Published HEALTH_SCORES_UPDATED event for account {account_id}")
            except Exception as e:
                logger.warning(f"Failed to publish HEALTH_SCORES_UPDATED event: {e}")
            
        except Exception as e:
            logger.error(f"Error calculating health scores after KPI upload: {e}", exc_info=True)
            db.session.rollback()
