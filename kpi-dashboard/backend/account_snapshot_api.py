#!/usr/bin/env python3
"""
Account Snapshot API
Creates and retrieves unified account snapshots capturing complete account state at specific points in time.
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import (
    Account, AccountSnapshot, AccountNote, Product, KPI, HealthTrend,
    PlaybookExecution, PlaybookReport, PlaybookTrigger
)
from datetime import datetime, timedelta
from playbook_recommendations_api import calculate_health_score_proxy
import json

account_snapshot_api = Blueprint('account_snapshot_api', __name__)


def _parse_date(date_value):
    """Helper to parse date from string or return None"""
    if not date_value:
        return None
    if isinstance(date_value, str):
        try:
            return datetime.strptime(date_value, '%Y-%m-%d').date()
        except:
            return None
    return date_value if hasattr(date_value, 'date') else None


def calculate_health_score_trend(account_id, customer_id, current_score):
    """Calculate health score trend (improving, declining, stable) based on last 3 snapshots"""
    try:
        recent_snapshots = AccountSnapshot.query.filter_by(
            account_id=account_id,
            customer_id=customer_id
        ).order_by(AccountSnapshot.snapshot_timestamp.desc()).limit(3).all()
        
        if len(recent_snapshots) < 2:
            return 'stable'  # Not enough history
        
        scores = [float(s.overall_health_score) for s in recent_snapshots if s.overall_health_score]
        if len(scores) < 2:
            return 'stable'
        
        # Calculate trend
        score_diff = scores[0] - scores[-1]  # Most recent - oldest
        
        if score_diff > 3:
            return 'improving'
        elif score_diff < -3:
            return 'declining'
        else:
            return 'stable'
    except:
        return 'stable'


def create_account_snapshot(account_id, customer_id, snapshot_type='manual', snapshot_reason=None, trigger_event=None, created_by=None, force_create=False):
    """
    Create a comprehensive account snapshot capturing all account state.
    
    Args:
        account_id: Account ID to snapshot
        customer_id: Customer ID (for security)
        snapshot_type: Type of snapshot (manual, scheduled, event_driven, post_upload, post_health_calc, rag_auto)
        snapshot_reason: Optional reason for snapshot
        trigger_event: Optional event that triggered snapshot
        created_by: User ID who created the snapshot (optional)
        force_create: If True, bypass duplicate check and always create (default: False)
    
    Returns:
        AccountSnapshot object or None if error or duplicate prevented
    """
    try:
        from datetime import timedelta
        
        # Get account
        account = Account.query.filter_by(
            account_id=account_id,
            customer_id=customer_id
        ).first()
        
        if not account:
            return None
        
        # Get previous snapshot for change calculations and duplicate check
        previous_snapshot = AccountSnapshot.query.filter_by(
            account_id=account_id,
            customer_id=customer_id
        ).order_by(AccountSnapshot.snapshot_timestamp.desc()).first()
        
        # SAFEGUARD: Prevent duplicate snapshot creation (unless forced or manual)
        if not force_create and previous_snapshot:
            # For event-driven snapshots: Only create if last snapshot is older than 1 hour
            if snapshot_type == 'event_driven':
                time_since_last = datetime.now() - previous_snapshot.snapshot_timestamp
                if time_since_last < timedelta(hours=1):
                    print(f"⏸️  Skipping snapshot creation for account {account.account_name}: "
                          f"Snapshot exists from {time_since_last.total_seconds()/60:.1f} minutes ago "
                          f"(event-driven snapshots require 1 hour minimum interval)")
                    return None  # Return None to indicate skip (not error)
            
            # For RAG auto snapshots: Only create if last snapshot is older than 30 minutes
            elif snapshot_type == 'rag_auto':
                time_since_last = datetime.now() - previous_snapshot.snapshot_timestamp
                if time_since_last < timedelta(minutes=30):
                    print(f"⏸️  Skipping snapshot creation for account {account.account_name}: "
                          f"Snapshot exists from {time_since_last.total_seconds()/60:.1f} minutes ago "
                          f"(RAG auto snapshots require 30 minutes minimum interval)")
                    return None  # Return None to indicate skip (not error)
            
            # For scheduled snapshots: Only create if last snapshot is older than 24 hours
            elif snapshot_type == 'scheduled':
                time_since_last = datetime.now() - previous_snapshot.snapshot_timestamp
                if time_since_last < timedelta(hours=24):
                    print(f"⏸️  Skipping snapshot creation for account {account.account_name}: "
                          f"Snapshot exists from {time_since_last.total_seconds()/3600:.1f} hours ago "
                          f"(scheduled snapshots require 24 hours minimum interval)")
                    return None  # Return None to indicate skip (not error)
            
            # For manual snapshots: Always allow (user-initiated, no restriction)
            # This allows users to create snapshots on-demand regardless of existing ones
        
        # If we get here, either:
        # 1. No previous snapshot exists (first snapshot)
        # 2. Previous snapshot is old enough (time interval passed)
        # 3. Manual snapshot (always allowed)
        # 4. force_create=True (bypass check)
        
        # SAFEGUARD: Check if snapshot already exists and prevent duplicate creation
        # (unless it's a manual snapshot or force_create is True)
        if not force_create and previous_snapshot:
            time_since_last = datetime.now() - previous_snapshot.snapshot_timestamp
            
            # For event-driven snapshots: Only create if last snapshot is older than 1 hour
            if snapshot_type == 'event_driven':
                if time_since_last < timedelta(hours=1):
                    print(f"⏸️  Skipping snapshot creation for account {account.account_name}: "
                          f"Snapshot exists from {time_since_last.total_seconds()/60:.1f} minutes ago "
                          f"(event-driven snapshots require 1 hour minimum interval)")
                    return None  # Return None to indicate skip (not error)
            
            # For RAG auto snapshots: Only create if last snapshot is older than 30 minutes
            elif snapshot_type == 'rag_auto':
                if time_since_last < timedelta(minutes=30):
                    print(f"⏸️  Skipping snapshot creation for account {account.account_name}: "
                          f"Snapshot exists from {time_since_last.total_seconds()/60:.1f} minutes ago "
                          f"(RAG auto snapshots require 30 minutes minimum interval)")
                    return None  # Return None to indicate skip (not error)
            
            # For scheduled snapshots: Only create if last snapshot is older than 24 hours
            elif snapshot_type == 'scheduled':
                if time_since_last < timedelta(hours=24):
                    print(f"⏸️  Skipping snapshot creation for account {account.account_name}: "
                          f"Snapshot exists from {time_since_last.total_seconds()/3600:.1f} hours ago "
                          f"(scheduled snapshots require 24 hours minimum interval)")
                    return None  # Return None to indicate skip (not error)
            
            # For manual snapshots: Always allow (user-initiated, no restriction)
            # This allows users to create snapshots on-demand regardless of existing ones
        
        # Get sequence number
        sequence_number = 1
        days_since_last_snapshot = None
        if previous_snapshot:
            sequence_number = (previous_snapshot.snapshot_sequence_number or 0) + 1
            days_since_last_snapshot = (datetime.now() - previous_snapshot.snapshot_timestamp).days
        
        # Get health scores
        latest_trend = HealthTrend.query.filter_by(
            account_id=account_id,
            customer_id=customer_id
        ).order_by(HealthTrend.year.desc(), HealthTrend.month.desc()).first()
        
        if latest_trend and latest_trend.overall_health_score:
            overall_health_score = float(latest_trend.overall_health_score)
            product_usage_score = float(latest_trend.product_usage_score) if latest_trend.product_usage_score else None
            support_score = float(latest_trend.support_score) if latest_trend.support_score else None
            customer_sentiment_score = float(latest_trend.customer_sentiment_score) if latest_trend.customer_sentiment_score else None
            business_outcomes_score = float(latest_trend.business_outcomes_score) if latest_trend.business_outcomes_score else None
            relationship_strength_score = float(latest_trend.relationship_strength_score) if latest_trend.relationship_strength_score else None
        else:
            # Calculate on-the-fly
            overall_health_score = calculate_health_score_proxy(account_id)
            product_usage_score = None
            support_score = None
            customer_sentiment_score = None
            business_outcomes_score = None
            relationship_strength_score = None
        
        # Calculate health score change and trend
        health_score_change_from_last = None
        if previous_snapshot and previous_snapshot.overall_health_score:
            health_score_change_from_last = overall_health_score - float(previous_snapshot.overall_health_score)
        
        health_score_trend = calculate_health_score_trend(account_id, customer_id, overall_health_score)
        
        # Get revenue and calculate change
        revenue = float(account.revenue) if account.revenue else 0
        revenue_change_from_last = None
        revenue_change_percent = None
        if previous_snapshot and previous_snapshot.revenue:
            prev_revenue = float(previous_snapshot.revenue)
            revenue_change_from_last = revenue - prev_revenue
            if prev_revenue > 0:
                revenue_change_percent = (revenue_change_from_last / prev_revenue) * 100
        
        # Get profile metadata
        profile_metadata = account.profile_metadata or {}
        
        # Get products
        products = Product.query.filter_by(account_id=account_id).all()
        products_used = [p.product_name for p in products] if products else []
        if not products_used and profile_metadata.get('products_used'):
            # Fallback to profile_metadata
            products_used = profile_metadata.get('products_used', '').split(',') if isinstance(profile_metadata.get('products_used'), str) else profile_metadata.get('products_used', [])
            products_used = [p.strip() for p in products_used if p.strip()] if isinstance(products_used, list) else []
        
        primary_product = products_used[0] if products_used else None
        
        # Get playbook data
        running_executions = PlaybookExecution.query.filter_by(
            account_id=account_id,
            customer_id=customer_id,
            status='in-progress'
        ).all()
        playbooks_running = [e.playbook_id for e in running_executions]
        
        completed_executions = PlaybookExecution.query.filter_by(
            account_id=account_id,
            customer_id=customer_id,
            status='completed'
        ).all()
        playbooks_completed_count = len(completed_executions)
        
        # Last 30 days completed
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_completed = [e for e in completed_executions if e.completed_at and e.completed_at >= thirty_days_ago]
        playbooks_completed_last_30_days = len(recent_completed)
        
        # Last playbook executed
        last_execution = PlaybookExecution.query.filter_by(
            account_id=account_id,
            customer_id=customer_id
        ).order_by(PlaybookExecution.started_at.desc()).first()
        last_playbook_executed = None
        if last_execution:
            last_playbook_executed = {
                'playbook_id': last_execution.playbook_id,
                'date': last_execution.started_at.isoformat() if last_execution.started_at else None
            }
        
        # Active playbook recommendations
        active_triggers = PlaybookTrigger.query.filter_by(
            customer_id=customer_id,
            auto_trigger_enabled=True
        ).all()
        playbook_recommendations_active = [t.playbook_type for t in active_triggers]
        
        # Get recent playbook reports (last 3)
        recent_reports = PlaybookReport.query.filter_by(
            account_id=account_id,
            customer_id=customer_id
        ).order_by(PlaybookReport.report_generated_at.desc()).limit(3).all()
        recent_playbook_report_ids = [r.report_id for r in recent_reports]
        
        # Get KPI summary
        all_kpis = KPI.query.filter_by(account_id=account_id).all()
        total_kpis = len(all_kpis)
        account_level_kpis = len([k for k in all_kpis if k.product_id is None])
        product_level_kpis = len([k for k in all_kpis if k.product_id is not None])
        
        # Count KPIs by health status (need to calculate)
        from health_score_engine import HealthScoreEngine
        critical_kpis = []
        at_risk_kpis = []
        healthy_kpis = []
        
        for kpi in all_kpis:
            try:
                health_info = HealthScoreEngine.calculate_health_status(
                    HealthScoreEngine.parse_kpi_value(kpi.data, kpi.kpi_parameter),
                    kpi.kpi_parameter
                )
                if health_info['status'] == 'low':
                    critical_kpis.append(kpi)
                elif health_info['status'] == 'medium':
                    at_risk_kpis.append(kpi)
                else:
                    healthy_kpis.append(kpi)
            except:
                pass  # Skip if can't calculate
        
        critical_kpis_count = len(critical_kpis)
        at_risk_kpis_count = len(at_risk_kpis)
        healthy_kpis_count = len(healthy_kpis)
        
        # Top 5 critical KPIs
        top_critical_kpis = []
        for kpi in critical_kpis[:5]:
            top_critical_kpis.append({
                'kpi_name': kpi.kpi_parameter,
                'value': kpi.data,
                'health_status': 'Critical',
                'category': kpi.category
            })
        
        # Get engagement metrics from profile_metadata
        engagement = profile_metadata.get('engagement', {})
        lifecycle_stage = engagement.get('lifecycle_stage')
        onboarding_status = engagement.get('onboarding_status')
        last_qbr_date = engagement.get('last_qbr_date')
        next_qbr_date = engagement.get('next_qbr_date')
        engagement_score = engagement.get('score')
        
        # Get champions from profile_metadata
        champions = profile_metadata.get('champions', [])
        primary_champion = None
        champion_status = None
        if champions and len(champions) > 0:
            primary_champion = champions[0].get('name') if isinstance(champions[0], dict) else str(champions[0])
            champion_status = champions[0].get('status') if isinstance(champions[0], dict) else None
        
        stakeholder_count = len(champions) if champions else 0
        
        # Get recent CSM notes (last 5)
        recent_notes = AccountNote.query.filter_by(
            account_id=account_id,
            customer_id=customer_id
        ).order_by(AccountNote.created_at.desc()).limit(5).all()
        recent_csm_note_ids = [n.note_id for n in recent_notes]
        
        # Check for significant change
        is_significant_change = False
        if previous_snapshot:
            if health_score_change_from_last and abs(health_score_change_from_last) > 5:
                is_significant_change = True
            if revenue_change_percent and abs(revenue_change_percent) > 10:
                is_significant_change = True
        
        # Create snapshot
        snapshot = AccountSnapshot(
            account_id=account_id,
            customer_id=customer_id,
            snapshot_timestamp=datetime.now(),
            snapshot_type=snapshot_type,
            snapshot_reason=snapshot_reason,
            snapshot_version=1,
            created_by=get_current_user_id(),
            trigger_event=trigger_event,
            
            # Financial
            revenue=revenue,
            revenue_change_from_last=revenue_change_from_last,
            revenue_change_percent=revenue_change_percent,
            
            # Health Scores
            overall_health_score=overall_health_score,
            product_usage_score=product_usage_score,
            support_score=support_score,
            customer_sentiment_score=customer_sentiment_score,
            business_outcomes_score=business_outcomes_score,
            relationship_strength_score=relationship_strength_score,
            health_score_change_from_last=health_score_change_from_last,
            health_score_trend=health_score_trend,
            
            # Account Status
            account_status=account.account_status,
            industry=account.industry,
            region=account.region,
            account_tier=profile_metadata.get('account_tier'),
            external_account_id=account.external_account_id,
            
            # CSM & Team
            assigned_csm=profile_metadata.get('assigned_csm'),
            csm_manager=profile_metadata.get('csm_manager'),
            account_owner=profile_metadata.get('account_owner'),
            
            # Products
            products_used=products_used,
            product_count=len(products_used),
            primary_product=primary_product,
            
            # Playbooks
            playbooks_running=playbooks_running,
            playbooks_running_count=len(playbooks_running),
            playbooks_completed_count=playbooks_completed_count,
            playbooks_completed_last_30_days=playbooks_completed_last_30_days,
            last_playbook_executed=last_playbook_executed,
            playbook_recommendations_active=playbook_recommendations_active,
            recent_playbook_report_ids=recent_playbook_report_ids,
            
            # KPI Summary
            total_kpis=total_kpis,
            account_level_kpis=account_level_kpis,
            product_level_kpis=product_level_kpis,
            critical_kpis_count=critical_kpis_count,
            at_risk_kpis_count=at_risk_kpis_count,
            healthy_kpis_count=healthy_kpis_count,
            top_critical_kpis=top_critical_kpis,
            
            # Engagement
            lifecycle_stage=lifecycle_stage,
            onboarding_status=onboarding_status,
            last_qbr_date=_parse_date(last_qbr_date),
            next_qbr_date=_parse_date(next_qbr_date),
            engagement_score=engagement_score,
            
            # Champions
            primary_champion=primary_champion,
            champion_status=champion_status,
            stakeholder_count=stakeholder_count,
            
            # References
            recent_csm_note_ids=recent_csm_note_ids,
            
            # Calculated
            days_since_last_snapshot=days_since_last_snapshot,
            snapshot_sequence_number=sequence_number,
            is_significant_change=is_significant_change
        )
        
        db.session.add(snapshot)
        db.session.commit()
        
        return snapshot
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating account snapshot: {e}")
        import traceback
        traceback.print_exc()
        return None


@account_snapshot_api.route('/api/account-snapshots/create', methods=['POST'])
def create_snapshot():
    """Create account snapshot(s) - can create for single account or all accounts"""
    try:
        customer_id = get_current_customer_id()
        user_id = get_current_user_id()
        
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.json or {}
        account_id = data.get('account_id')  # Optional - if not provided, creates for all accounts
        snapshot_type = data.get('snapshot_type', 'manual')
        snapshot_reason = data.get('reason')
        trigger_event = data.get('trigger_event')
        
        created_snapshots = []
        
        if account_id:
            # Create snapshot for specific account
            force_create = data.get('force_create', False)  # Allow bypassing safeguard
            snapshot = create_account_snapshot(
                account_id=int(account_id),
                customer_id=customer_id,
                snapshot_type=snapshot_type,
                snapshot_reason=snapshot_reason,
                trigger_event=trigger_event,
                created_by=user_id,
                force_create=force_create
            )
            
            if snapshot:
                created_snapshots.append({
                    'snapshot_id': snapshot.snapshot_id,
                    'account_id': snapshot.account_id,
                    'account_name': (account.account_name if (account := db.session.get(Account, snapshot.account_id)) else None),
                    'snapshot_timestamp': snapshot.snapshot_timestamp.isoformat(),
                    'overall_health_score': float(snapshot.overall_health_score) if snapshot.overall_health_score else None
                })
            elif snapshot is None:
                # Snapshot creation was skipped due to safeguard (not an error)
                return jsonify({
                    'message': 'Snapshot creation skipped: A recent snapshot already exists',
                    'skipped': True,
                    'account_id': account_id
                }), 200
            else:
                return jsonify({'error': 'Failed to create snapshot'}), 500
        else:
            # Create snapshots for all accounts
            accounts = Account.query.filter_by(customer_id=customer_id).all()
            
            for account in accounts:
                snapshot = create_account_snapshot(
                    account_id=account.account_id,
                    customer_id=customer_id,
                    snapshot_type=snapshot_type,
                    snapshot_reason=snapshot_reason,
                    trigger_event=trigger_event,
                    created_by=user_id,
                    force_create=False  # Respect safeguard for bulk operations
                )
                
                if snapshot:
                    created_snapshots.append({
                        'snapshot_id': snapshot.snapshot_id,
                        'account_id': snapshot.account_id,
                        'account_name': account.account_name,
                        'snapshot_timestamp': snapshot.snapshot_timestamp.isoformat(),
                        'overall_health_score': float(snapshot.overall_health_score) if snapshot.overall_health_score else None
                    })
        
        return jsonify({
            'status': 'success',
            'message': f'Created {len(created_snapshots)} snapshot(s)',
            'snapshots': created_snapshots
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'error': f'Failed to create snapshot: {str(e)}'
        }), 500


@account_snapshot_api.route('/api/account-snapshots', methods=['GET'])
def get_snapshots():
    """Get account snapshots with optional filters"""
    try:
        customer_id = get_current_customer_id()
        
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        account_id = request.args.get('account_id', type=int)
        limit = request.args.get('limit', type=int, default=10)
        start_date = request.args.get('start_date')  # YYYY-MM-DD format
        
        query = AccountSnapshot.query.filter_by(customer_id=customer_id)
        
        if account_id:
            query = query.filter_by(account_id=account_id)
        
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(AccountSnapshot.snapshot_timestamp >= start_datetime)
            except:
                pass
        
        snapshots = query.order_by(AccountSnapshot.snapshot_timestamp.desc()).limit(limit).all()
        
        result = []
        for snapshot in snapshots:
            account = db.session.get(Account, snapshot.account_id)
            result.append({
                'snapshot_id': snapshot.snapshot_id,
                'account_id': snapshot.account_id,
                'account_name': account.account_name if account else None,
                'snapshot_timestamp': snapshot.snapshot_timestamp.isoformat(),
                'snapshot_type': snapshot.snapshot_type,
                'overall_health_score': float(snapshot.overall_health_score) if snapshot.overall_health_score else None,
                'health_score_trend': snapshot.health_score_trend,
                'revenue': float(snapshot.revenue) if snapshot.revenue else None,
                'revenue_change_percent': float(snapshot.revenue_change_percent) if snapshot.revenue_change_percent else None,
                'playbooks_running_count': snapshot.playbooks_running_count,
                'playbooks_completed_count': snapshot.playbooks_completed_count,
                'critical_kpis_count': snapshot.critical_kpis_count,
                'is_significant_change': snapshot.is_significant_change
            })
        
        return jsonify({
            'status': 'success',
            'snapshots': result,
            'total': len(result)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': f'Failed to fetch snapshots: {str(e)}'
        }), 500


@account_snapshot_api.route('/api/account-snapshots/latest', methods=['GET'])
def get_latest_snapshot():
    """Get latest snapshot for an account"""
    try:
        customer_id = get_current_customer_id()
        account_id = request.args.get('account_id', type=int)
        
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        if not account_id:
            return jsonify({'error': 'account_id is required'}), 400
        
        snapshot = AccountSnapshot.query.filter_by(
            account_id=account_id,
            customer_id=customer_id
        ).order_by(AccountSnapshot.snapshot_timestamp.desc()).first()
        
        if not snapshot:
            return jsonify({
                'status': 'not_found',
                'message': 'No snapshot found for this account'
            }), 404
        
        account = db.session.get(Account, account_id)
        
        return jsonify({
            'status': 'success',
            'snapshot': {
                'snapshot_id': snapshot.snapshot_id,
                'account_id': snapshot.account_id,
                'account_name': account.account_name if account else None,
                'snapshot_timestamp': snapshot.snapshot_timestamp.isoformat(),
                'snapshot_type': snapshot.snapshot_type,
                'overall_health_score': float(snapshot.overall_health_score) if snapshot.overall_health_score else None,
                'health_score_trend': snapshot.health_score_trend,
                'revenue': float(snapshot.revenue) if snapshot.revenue else None,
                'revenue_change_percent': float(snapshot.revenue_change_percent) if snapshot.revenue_change_percent else None,
                'assigned_csm': snapshot.assigned_csm,
                'products_used': snapshot.products_used,
                'playbooks_running': snapshot.playbooks_running,
                'playbooks_running_count': snapshot.playbooks_running_count,
                'playbooks_completed_count': snapshot.playbooks_completed_count,
                'critical_kpis_count': snapshot.critical_kpis_count,
                'total_kpis': snapshot.total_kpis,
                'recent_csm_note_ids': snapshot.recent_csm_note_ids,
                'recent_playbook_report_ids': snapshot.recent_playbook_report_ids
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': f'Failed to fetch latest snapshot: {str(e)}'
        }), 500


@account_snapshot_api.route('/api/account-snapshots/history', methods=['GET'])
def get_snapshot_history():
    """Get account snapshot history for RAG context"""
    try:
        customer_id = get_current_customer_id()
        account_id = request.args.get('account_id', type=int)
        months = request.args.get('months', type=int, default=3)
        
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        if not account_id:
            return jsonify({'error': 'account_id is required'}), 400
        
        cutoff_date = datetime.now() - timedelta(days=months*30)
        
        snapshots = AccountSnapshot.query.filter_by(
            account_id=account_id,
            customer_id=customer_id
        ).filter(
            AccountSnapshot.snapshot_timestamp >= cutoff_date
        ).order_by(AccountSnapshot.snapshot_timestamp.desc()).all()
        
        result = []
        for snapshot in snapshots:
            result.append({
                'snapshot_timestamp': snapshot.snapshot_timestamp.isoformat(),
                'overall_health_score': float(snapshot.overall_health_score) if snapshot.overall_health_score else None,
                'health_score_trend': snapshot.health_score_trend,
                'revenue': float(snapshot.revenue) if snapshot.revenue else None,
                'account_status': snapshot.account_status,
                'playbooks_running_count': snapshot.playbooks_running_count,
                'playbooks_completed_count': snapshot.playbooks_completed_count
            })
        
        return jsonify({
            'status': 'success',
            'history': result,
            'total': len(result)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': f'Failed to fetch snapshot history: {str(e)}'
        }), 500

