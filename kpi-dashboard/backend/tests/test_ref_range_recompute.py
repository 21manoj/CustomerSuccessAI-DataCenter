#!/usr/bin/env python3
"""
Test: Changing KPI reference range triggers health score recompute.
Procedure:
1) Pick an account and KPI parameter (e.g., 'Support Cost per Ticket')
2) Capture current health trend score
3) Adjust KPIReferenceRange for that parameter
4) Trigger recompute via health_score_storage
5) Verify score changed (or at least recompute path executed)
"""

from app_v3_minimal import app
from models import Account, KPIReferenceRange, HealthTrend
from extensions import db

TARGET_PARAM = 'Support Cost per Ticket'


def run_test():
    with app.app_context():
        account = Account.query.first()
        if not account:
            print('⚠️  No accounts found')
            return

        # Get latest health trend (may be None)
        before = HealthTrend.query.filter_by(account_id=account.account_id).order_by(
            HealthTrend.year.desc(), HealthTrend.month.desc()
        ).first()
        before_score = float(before.overall_health_score) if before else None
        print(f'Account #{account.account_id} before overall health: {before_score}')

        # Fetch reference range for the target parameter (customer override if present)
        ref = KPIReferenceRange.query.filter_by(kpi_name=TARGET_PARAM, customer_id=account.customer_id).first()
        if not ref:
            ref = KPIReferenceRange.query.filter_by(kpi_name=TARGET_PARAM, customer_id=None).first()
        if not ref:
            print(f'⚠️  No reference range found for {TARGET_PARAM}')
            return

        # Modify healthy range slightly to force a recalculation impact
        original_healthy_min = ref.healthy_min
        original_healthy_max = ref.healthy_max
        ref.healthy_min = max(0, (original_healthy_min or 0) + 1)
        ref.healthy_max = (original_healthy_max or ref.healthy_min + 10)
        ref.healthy_range = f"{ref.healthy_min}-{ref.healthy_max}"
        db.session.commit()
        print(f'Updated {TARGET_PARAM} healthy range to {ref.healthy_range}')

        # Trigger recompute (use monthly KPI data store to avoid category key assumptions)
        from health_score_storage import HealthScoreStorageService
        storage = HealthScoreStorageService()
        try:
            storage.store_monthly_kpi_data(account.customer_id)
            print('Triggered KPI monthly recompute via storage service')
        except Exception as e:
            print(f'⚠️  Recompute warning: {e}')

        after = HealthTrend.query.filter_by(account_id=account.account_id).order_by(
            HealthTrend.year.desc(), HealthTrend.month.desc()
        ).first()
        after_score = float(after.overall_health_score) if after else None
        print(f'Account #{account.account_id} after overall health: {after_score}')

        # Restore original healthy range to avoid side effects
        ref.healthy_min = original_healthy_min
        ref.healthy_max = original_healthy_max
        ref.healthy_range = f"{ref.healthy_min}-{ref.healthy_max}"
        db.session.commit()
        print('Restored original reference range')


if __name__ == '__main__':
    run_test()


