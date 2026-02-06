#!/usr/bin/env python3
"""
DC2_S Score Calculator
Calculates L1 (KPI) → L2 (Pillar) → L3 (Health) scores
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime, date
from decimal import Decimal
import json
from pathlib import Path

from models import db, DC2SKPI, CustomerConfig, KPIScore, PillarScore, HealthScore, Account
from sqlalchemy import func
from utils.config_validator import ConfigValidator

class ScoreCalculator:
    """
    Calculates health scores based on customer configuration
    
    Supports both catalog KPIs (AI-KPI1, CH-KPI4, etc.) and custom KPIs (CUSTOM-*)
    """
    
    def __init__(self, customer_id: int):
        self.customer_id = customer_id
        self.config = self._load_config()
        self.validator = ConfigValidator()
    
    def _load_config(self) -> Dict:
        """Load customer configuration from database"""
        config = CustomerConfig.query.filter_by(customer_id=self.customer_id).first()
        
        if not config or config.vertical != 'dc2_s':
            raise ValueError(f"No DC2_S config found for customer {self.customer_id}")
        
        return {
            'pillar_weights': config.dc2s_pillar_weights or {},
            'enabled_kpis': config.dc2s_enabled_kpis or [],
            'kpi_definitions': config.dc2s_kpi_definitions or {},
            'kpi_overrides': config.dc2s_kpi_overrides or {},
            'kpi_weights': config.dc2s_kpi_weights or {}
        }
    
    def _get_kpi_definition(self, kpi_code: str) -> Optional[Dict]:
        """Get KPI definition (catalog or custom)"""
        
        # Check if custom KPI
        if kpi_code.startswith('CUSTOM-'):
            return self.config['kpi_definitions'].get(kpi_code)
        
        # Check catalog KPIs - extract pillar from code (e.g., "AI-KPI1" -> "AI")
        if '-' in kpi_code:
            pillar = kpi_code.split('-')[0]
            if pillar in ['AI', 'CH', 'DV', 'EX', 'OS']:
                # Create a default definition for catalog KPIs
                # Use overrides if available
                override = self.config['kpi_overrides'].get(kpi_code, {})
                
                # Default catalog KPI definition
                kpi_def = {
                    'pillar': pillar,
                    'name': kpi_code,
                    'unit': 'numeric',
                    'target': override.get('target', 85.0),  # Default target
                    'operator': override.get('operator', '>'),  # Default: higher is better
                    'range': override.get('range', [0.0, 100.0])  # Default range
                }
                
                # Apply any other overrides
                for key, value in override.items():
                    if key not in ['target', 'operator', 'range']:
                        kpi_def[key] = value
                
                return kpi_def
        
        return None
    
    # ================================================================
    # L1: KPI SCORE CALCULATION
    # ================================================================
    
    def calculate_kpi_score(self, kpi_code: str, actual_value: float) -> Tuple[float, str]:
        """
        Calculate normalized score (0-100) for a KPI
        
        Returns:
            (score, status) tuple
        """
        
        kpi_def = self._get_kpi_definition(kpi_code)
        
        if not kpi_def:
            raise ValueError(f"No definition found for KPI: {kpi_code}")
        
        target = float(kpi_def['target'])
        range_min, range_max = kpi_def['range']
        operator = kpi_def['operator']
        
        # Calculate score based on operator
        if operator in ['>', '>=']:
            # Higher is better
            if actual_value >= target:
                score = 100.0
            elif actual_value <= range_min:
                score = 0.0
            else:
                score = ((actual_value - range_min) / (target - range_min)) * 100
        
        elif operator in ['<', '<=']:
            # Lower is better
            if actual_value <= target:
                score = 100.0
            elif actual_value >= range_max:
                score = 0.0
            else:
                score = ((range_max - actual_value) / (range_max - target)) * 100
        
        elif operator == '=':
            # Exact match
            tolerance = (range_max - range_min) * 0.05  # 5% tolerance
            if abs(actual_value - target) <= tolerance:
                score = 100.0
            else:
                distance = abs(actual_value - target)
                max_distance = max(abs(target - range_min), abs(target - range_max))
                score = max(0, 100 - (distance / max_distance) * 100)
        
        else:
            raise ValueError(f"Unknown operator: {operator}")
        
        # Clamp to 0-100
        score = min(100.0, max(0.0, score))
        
        # Determine status
        status = self._determine_status(score)
        
        return score, status
    
    def _determine_status(self, score: float) -> str:
        """Determine status based on score"""
        if score >= 85:
            return 'excellent'
        elif score >= 70:
            return 'good'
        elif score >= 50:
            return 'warning'
        else:
            return 'critical'
    
    # ================================================================
    # L2: PILLAR SCORE CALCULATION
    # ================================================================
    
    def calculate_pillar_score(self, pillar_code: str, kpi_scores: Dict[str, float]) -> Tuple[float, str, Dict]:
        """
        Calculate pillar score as weighted average of KPI scores
        
        Args:
            pillar_code: AI, CH, DV, EX, or OS
            kpi_scores: {kpi_code: score} for KPIs in this pillar
        
        Returns:
            (pillar_score, status, contributing_kpis) tuple
        """
        
        # Get KPI weights for this pillar
        kpi_weights = self.config['kpi_weights'].get(pillar_code, {})
        
        if not kpi_weights:
            raise ValueError(f"No KPI weights configured for pillar {pillar_code}")
        
        # Calculate weighted average
        weighted_sum = 0.0
        total_weight = 0.0
        contributing_kpis = {}
        
        for kpi_code, score in kpi_scores.items():
            weight = kpi_weights.get(kpi_code, 0)
            if weight > 0:
                weighted_sum += score * weight
                total_weight += weight
                contributing_kpis[kpi_code] = score
        
        if total_weight == 0:
            raise ValueError(f"No valid KPI weights for pillar {pillar_code}")
        
        pillar_score = weighted_sum / total_weight
        status = self._determine_status(pillar_score)
        
        return pillar_score, status, contributing_kpis
    
    # ================================================================
    # L3: HEALTH SCORE CALCULATION
    # ================================================================
    
    def calculate_health_score(self, pillar_scores: Dict[str, float]) -> Tuple[float, str, Optional[float], Optional[str]]:
        """
        Calculate overall health score as weighted average of pillar scores
        
        Args:
            pillar_scores: {pillar_code: score} for all 5 pillars
        
        Returns:
            (health_score, status, change_from_last, trend) tuple
        """
        
        pillar_weights = self.config['pillar_weights']
        
        # Calculate weighted average
        weighted_sum = 0.0
        total_weight = 0.0
        
        for pillar_code, score in pillar_scores.items():
            weight = pillar_weights.get(pillar_code, 0)
            weighted_sum += score * weight
            total_weight += weight
        
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Pillar weights must sum to 1.0, got {total_weight}")
        
        health_score = weighted_sum
        status = self._determine_status(health_score)
        
        # Note: Trend calculation requires account_id and measurement_month
        # Will be calculated in calculate_scores_for_account method
        
        return health_score, status, None, None
    
    def _calculate_trend(self, current_score: float, account_id: int, measurement_month: date) -> Tuple[Optional[float], Optional[str]]:
        """Calculate trend compared to previous month"""
        
        # Get previous month
        if measurement_month.month == 1:
            prev_month = date(measurement_month.year - 1, 12, 1)
        else:
            prev_month = date(measurement_month.year, measurement_month.month - 1, 1)
        
        # Get previous month's health score
        prev_health = HealthScore.query.filter_by(
            account_id=account_id,
            measurement_month=prev_month
        ).first()
        
        if not prev_health:
            return None, None
        
        change = current_score - float(prev_health.health_score)
        
        if change >= 5:
            trend = 'improving'
        elif change <= -5:
            trend = 'declining'
        else:
            trend = 'stable'
        
        return change, trend
    
    # ================================================================
    # BATCH CALCULATION FOR ACCOUNT
    # ================================================================
    
    def calculate_scores_for_account(self, account_id: int, measurement_month: date) -> Dict:
        """
        Calculate all scores (L1, L2, L3) for an account for a given month
        
        Args:
            account_id: Account ID
            measurement_month: Date (use first day of month)
        
        Returns:
            Dictionary with kpi_scores, pillar_scores, health_score
        """
        
        print(f"\n{'='*70}")
        print(f"CALCULATING SCORES FOR ACCOUNT {account_id}")
        print(f"Month: {measurement_month.strftime('%Y-%m')}")
        print(f"{'='*70}\n")
        
        # Step 1: Get KPI measurements for this month
        kpi_measurements = self._get_kpi_measurements(account_id, measurement_month)
        
        if not kpi_measurements:
            print(f"⚠️  No KPI measurements found for account {account_id} in {measurement_month.strftime('%Y-%m')}")
            return None
        
        print(f"📊 Found {len(kpi_measurements)} KPI measurements")
        
        # Step 2: Calculate L1 (KPI scores)
        print("\n🔹 L1: Calculating KPI Scores...")
        kpi_scores = {}
        kpi_scores_records = []
        
        for kpi_code, actual_value in kpi_measurements.items():
            try:
                score, status = self.calculate_kpi_score(kpi_code, actual_value)
                kpi_scores[kpi_code] = score
                
                kpi_def = self._get_kpi_definition(kpi_code)
                is_custom = kpi_code.startswith('CUSTOM-')
                
                kpi_scores_records.append({
                    'account_id': account_id,
                    'measurement_month': measurement_month,
                    'kpi_code': kpi_code,
                    'kpi_value': Decimal(str(actual_value)),
                    'kpi_target': Decimal(str(kpi_def['target'])),
                    'kpi_score': Decimal(str(round(score, 2))),
                    'kpi_status': status
                })
                
                print(f"  ✅ {kpi_code}: {actual_value} → Score: {score:.1f} ({status})")
                
            except Exception as e:
                print(f"  ❌ {kpi_code}: Error - {e}")
        
        # Step 3: Calculate L2 (Pillar scores)
        print("\n🔹 L2: Calculating Pillar Scores...")
        pillar_scores = {}
        pillar_scores_records = []
        
        # Group KPIs by pillar
        kpis_by_pillar = self._group_kpis_by_pillar(kpi_scores.keys())
        
        for pillar_code, kpi_codes in kpis_by_pillar.items():
            # Get scores for KPIs in this pillar
            pillar_kpi_scores = {k: kpi_scores[k] for k in kpi_codes if k in kpi_scores}
            
            if pillar_kpi_scores:
                try:
                    score, status, contributing = self.calculate_pillar_score(pillar_code, pillar_kpi_scores)
                    pillar_scores[pillar_code] = score
                    
                    pillar_scores_records.append({
                        'account_id': account_id,
                        'measurement_month': measurement_month,
                        'pillar_code': pillar_code,
                        'pillar_score': Decimal(str(round(score, 2))),
                        'pillar_status': status,
                        'contributing_kpis': {k: round(v, 2) for k, v in contributing.items()},
                        'kpi_weights': self.config['kpi_weights'].get(pillar_code, {})
                    })
                    
                    print(f"  ✅ {pillar_code}: Score: {score:.1f} ({status}) - {len(contributing)} KPIs")
                    
                except Exception as e:
                    print(f"  ❌ {pillar_code}: Error - {e}")
        
        # Step 4: Calculate L3 (Health score)
        print("\n🔹 L3: Calculating Health Score...")
        
        if len(pillar_scores) == 5:  # All pillars present
            try:
                health_score, health_status, change, trend = self.calculate_health_score(pillar_scores)
                
                # Calculate trend with account context (override with actual trend calculation)
                change, trend = self._calculate_trend(health_score, account_id, measurement_month)
                
                health_score_record = {
                    'account_id': account_id,
                    'measurement_month': measurement_month,
                    'health_score': Decimal(str(round(health_score, 2))),
                    'health_status': health_status,
                    'trend': trend,
                    'change_from_last_month': Decimal(str(round(change, 2))) if change else None,
                    'contributing_pillars': {k: round(v, 2) for k, v in pillar_scores.items()},
                    'pillar_weights': self.config['pillar_weights']
                }
                
                print(f"  ✅ Health Score: {health_score:.1f} ({health_status})")
                if trend:
                    print(f"     Trend: {trend} ({change:+.1f} from last month)")
                
            except Exception as e:
                print(f"  ❌ Health Score: Error - {e}")
                health_score_record = None
        else:
            print(f"  ⚠️  Incomplete pillar data ({len(pillar_scores)}/5 pillars)")
            health_score_record = None
        
        # Step 5: Save to database
        print("\n💾 Saving scores to database...")
        self._save_scores(kpi_scores_records, pillar_scores_records, health_score_record)
        
        print(f"\n{'='*70}")
        print("✅ SCORE CALCULATION COMPLETE")
        print(f"{'='*70}\n")
        
        return {
            'kpi_scores': kpi_scores_records,
            'pillar_scores': pillar_scores_records,
            'health_score': health_score_record
        }
    
    def _get_kpi_measurements(self, account_id: int, measurement_month: date) -> Dict[str, float]:
        """Get KPI measurements for account in given month"""
        
        # Query dc2s_kpis table for measurements
        # Get latest measurement for each KPI in the month
        
        start_date = measurement_month
        if measurement_month.month == 12:
            end_date = date(measurement_month.year + 1, 1, 1)
        else:
            end_date = date(measurement_month.year, measurement_month.month + 1, 1)
        
        kpis = db.session.query(
            DC2SKPI.kpi_code,
            func.avg(DC2SKPI.value).label('avg_value')
        ).filter(
            DC2SKPI.account_id == account_id,
            DC2SKPI.measured_at >= start_date,
            DC2SKPI.measured_at < end_date
        ).group_by(
            DC2SKPI.kpi_code
        ).all()
        
        return {kpi_code: float(avg_value) for kpi_code, avg_value in kpis}
    
    def _group_kpis_by_pillar(self, kpi_codes: List[str]) -> Dict[str, List[str]]:
        """Group KPI codes by their pillar"""
        
        kpis_by_pillar = {'AI': [], 'CH': [], 'DV': [], 'EX': [], 'OS': []}
        
        for kpi_code in kpi_codes:
            kpi_def = self._get_kpi_definition(kpi_code)
            if kpi_def:
                pillar = kpi_def['pillar']
                if pillar in kpis_by_pillar:
                    kpis_by_pillar[pillar].append(kpi_code)
        
        return kpis_by_pillar
    
    def _save_scores(self, kpi_scores: List[Dict], pillar_scores: List[Dict], health_score: Optional[Dict]):
        """Save calculated scores to database"""
        
        try:
            # Delete existing scores for this month (if recalculating)
            if kpi_scores:
                account_id = kpi_scores[0]['account_id']
                month = kpi_scores[0]['measurement_month']
                
                KPIScore.query.filter_by(account_id=account_id, measurement_month=month).delete()
                PillarScore.query.filter_by(account_id=account_id, measurement_month=month).delete()
                HealthScore.query.filter_by(account_id=account_id, measurement_month=month).delete()
            
            # Insert KPI scores
            for kpi_score in kpi_scores:
                db.session.add(KPIScore(**kpi_score))
            
            # Insert pillar scores
            for pillar_score in pillar_scores:
                db.session.add(PillarScore(**pillar_score))
            
            # Insert health score
            if health_score:
                db.session.add(HealthScore(**health_score))
            
            db.session.commit()
            print("  ✅ Scores saved successfully")
            
        except Exception as e:
            db.session.rollback()
            print(f"  ❌ Error saving scores: {e}")
            raise
    
    # ================================================================
    # BATCH PROCESSING
    # ================================================================
    
    def calculate_scores_for_all_accounts(self, measurement_month: date) -> Dict[int, Dict]:
        """Calculate scores for all accounts belonging to this customer"""
        
        accounts = Account.query.filter_by(customer_id=self.customer_id).all()
        
        print(f"\n{'='*70}")
        print(f"BATCH SCORE CALCULATION - CUSTOMER {self.customer_id}")
        print(f"Month: {measurement_month.strftime('%Y-%m')}")
        print(f"Accounts: {len(accounts)}")
        print(f"{'='*70}\n")
        
        results = {}
        
        for account in accounts:
            try:
                result = self.calculate_scores_for_account(account.account_id, measurement_month)
                results[account.account_id] = result
            except Exception as e:
                print(f"❌ Error processing account {account.account_id}: {e}")
                results[account.account_id] = {'error': str(e)}
        
        return results


# ================================================================
# CONVENIENCE FUNCTIONS
# ================================================================

def calculate_customer_scores(customer_id: int, measurement_month: date) -> Dict:
    """
    Calculate scores for all accounts of a customer
    
    Usage:
        from utils.score_calculator import calculate_customer_scores
        from datetime import date
        
        results = calculate_customer_scores(9, date(2024, 12, 1))
    """
    calculator = ScoreCalculator(customer_id)
    return calculator.calculate_scores_for_all_accounts(measurement_month)


def calculate_account_scores(customer_id: int, account_id: int, measurement_month: date) -> Dict:
    """
    Calculate scores for a single account
    
    Usage:
        results = calculate_account_scores(9, 1001, date(2024, 12, 1))
    """
    calculator = ScoreCalculator(customer_id)
    return calculator.calculate_scores_for_account(account_id, measurement_month)
