#!/usr/bin/env python3
"""
Product Health Subscriber
Automatically calculates and stores product health scores on KPI upload/data changes
"""

from event_system import EventSubscriber, EventType, Event
from extensions import db
from models import Account, KPIUpload
from product_health_calculator import calculate_and_store_product_health
import logging

logger = logging.getLogger(__name__)


class ProductHealthSubscriber(EventSubscriber):
    """Subscriber that automatically calculates product health scores on data changes"""
    
    def __init__(self):
        self.last_calculation_times = {}  # Track last calculation time per account
        self.calculation_cooldown = 60  # 1 minute cooldown between calculations for same account
    
    def handle_event(self, event: Event):
        """Handle events and calculate product health when appropriate"""
        try:
            customer_id = event.customer_id
            event_data = event.data
            
            # Determine which accounts need product health calculation
            account_ids_to_calculate = []
            
            if event.event_type == EventType.KPI_DATA_UPLOADED:
                # Get account_id from upload_id
                upload_id = event_data.get('upload_id')
                if upload_id:
                    kpi_upload = db.session.get(KPIUpload, upload_id)
                    if kpi_upload and kpi_upload.account_id:
                        account_ids_to_calculate.append(kpi_upload.account_id)
            
            elif event.event_type == EventType.ACCOUNT_DATA_CHANGED:
                # Get account_id from event data
                account_id = event_data.get('account_id')
                if account_id:
                    account_ids_to_calculate.append(account_id)
            
            elif event.event_type == EventType.HEALTH_SCORES_UPDATED:
                # Get account_id from event data
                account_id = event_data.get('account_id')
                if account_id:
                    account_ids_to_calculate.append(account_id)
            
            # Calculate product health for affected accounts (with cooldown check)
            for account_id in account_ids_to_calculate:
                # Check cooldown to avoid calculating too frequently
                account_key = f"{customer_id}_{account_id}"
                last_calc_time = self.last_calculation_times.get(account_key)
                
                if last_calc_time:
                    from datetime import datetime, timedelta
                    time_since_last = (datetime.now() - last_calc_time).total_seconds()
                    if time_since_last < self.calculation_cooldown:
                        logger.debug(f"Skipping product health calculation for account {account_id} (cooldown: {int(self.calculation_cooldown - time_since_last)}s remaining)")
                        continue
                
                try:
                    logger.info(f"Calculating product health for account {account_id} (customer {customer_id})")
                    calculate_and_store_product_health(account_id, customer_id)
                    self.last_calculation_times[account_key] = datetime.now()
                    logger.info(f"✅ Product health calculated for account {account_id}")
                except Exception as e:
                    logger.error(f"❌ Error calculating product health for account {account_id}: {str(e)}")
                    # Continue with other accounts even if one fails
                    continue
                    
        except Exception as e:
            logger.error(f"Error in ProductHealthSubscriber: {str(e)}")
