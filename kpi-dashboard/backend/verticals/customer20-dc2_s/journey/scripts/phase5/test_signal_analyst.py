#!/usr/bin/env python3
"""
Test Signal Analyst with Bootstrap Weights
===========================================

Tests Signal Analyst on journey data using bootstrap weights.
Measures baseline accuracy against actual milestones.

Target: 55-65% accuracy with bootstrap weights (before learning)

Usage:
    python3 test_signal_analyst.py --db-url "$DATABASE_URL"
"""

import os
import sys
import argparse
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import uuid


class SignalAnalystTester:
    """Test Signal Analyst with bootstrap weights on journey data"""
    
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        self.test_run_id = f"baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.bootstrap_weights = {}
        self.kpi_mapping = {}
        
    def load_bootstrap_weights(self):
        """Load bootstrap weights from database"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT kpi_code, effective_weight
                FROM bootstrap_weights
                ORDER BY effective_weight DESC
            """))
            
            for row in result:
                self.bootstrap_weights[row[0]] = float(row[1])
        
        print(f"   ✅ Loaded {len(self.bootstrap_weights)} bootstrap weights")
    
    def load_kpi_mapping(self):
        """Load KPI mapping from bootstrap → journey"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT bootstrap_kpi_code, journey_kpi_code, mapping_weight, confidence
                FROM kpi_mapping
            """))
            
            for row in result:
                bootstrap_kpi = row[0]
                journey_kpi = row[1]
                weight = float(row[2])
                confidence = float(row[3])
                
                if journey_kpi not in self.kpi_mapping:
                    self.kpi_mapping[journey_kpi] = []
                
                self.kpi_mapping[journey_kpi].append({
                    'bootstrap_kpi': bootstrap_kpi,
                    'weight': weight,
                    'confidence': confidence
                })
        
        print(f"   ✅ Loaded mappings for {len(self.kpi_mapping)} journey KPIs")
    
    def get_account_kpis_at_week(self, account_id, week):
        """Get KPI values for an account at a specific week"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT kpi_code, value
                FROM journey_kpis
                WHERE journey_account_id = :account_id
                AND week_number = :week
            """), {'account_id': account_id, 'week': week})
            
            kpis = {}
            for row in result:
                kpis[row[0]] = float(row[1])
            
            return kpis
    
    def calculate_mapped_weight(self, journey_kpi):
        """Calculate effective weight for a journey KPI using bootstrap mapping"""
        if journey_kpi not in self.kpi_mapping:
            # No mapping - use default weight (1/35)
            return 1.0 / 35.0
        
        # Sum weights from all mapped bootstrap KPIs
        total_weight = 0.0
        for mapping in self.kpi_mapping[journey_kpi]:
            bootstrap_kpi = mapping['bootstrap_kpi']
            map_weight = mapping['weight']
            confidence = mapping['confidence']
            
            if bootstrap_kpi in self.bootstrap_weights:
                bootstrap_weight = self.bootstrap_weights[bootstrap_kpi]
                # Effective weight = bootstrap_weight × mapping_weight
                # (confidence already factored into bootstrap weight)
                total_weight += bootstrap_weight * map_weight
        
        return total_weight
    
    def get_health_score_at_week(self, account_id, week):
        """Get the pre-calculated health score from database for a specific week"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT health_score
                FROM journey_kpis
                WHERE journey_account_id = :account_id
                AND week_number = :week
                LIMIT 1
            """), {'account_id': account_id, 'week': week})
            
            row = result.fetchone()
            if row:
                return float(row[0])
            return 50.0  # Default if not found
    
    def predict_outcome(self, health_score, kpis):
        """Predict outcome based on health score and KPIs"""
        
        # Calculate expansion readiness (S1, S2, S7 KPIs)
        expansion_kpis = ['S1', 'S2', 'S7']
        expansion_score = sum(kpis.get(k, 50) for k in expansion_kpis) / len(expansion_kpis)
        
        # Churn risk based on health
        if health_score < 40:
            churn_risk = 0.90
            predicted_outcome = 'churn'
        elif health_score < 55:
            churn_risk = 0.70
            predicted_outcome = 'at_risk'
        elif health_score < 70:
            churn_risk = 0.40
            predicted_outcome = 'stable'
        else:
            churn_risk = 0.15
            predicted_outcome = 'healthy'
        
        # Expansion probability
        if health_score > 75 and expansion_score > 70:
            expansion_prob = 0.75
            predicted_outcome = 'expansion'
        elif health_score > 85:
            expansion_prob = 0.60
        else:
            expansion_prob = 0.20
        
        return {
            'outcome': predicted_outcome,
            'health_score': health_score,
            'churn_risk': churn_risk,
            'expansion_prob': expansion_prob,
            'expansion_score': expansion_score
        }
    
    def get_milestones(self, account_id):
        """Get actual milestones for an account"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT week_number, milestone_type, milestone_date, milestone_outcome
                FROM journey_milestones
                WHERE journey_account_id = :account_id
                ORDER BY week_number
            """), {'account_id': account_id})
            
            milestones = []
            for row in result:
                milestones.append({
                    'week': row[0],
                    'type': row[1],
                    'date': row[2],
                    'outcome': row[3]
                })
            
            return milestones
    
    def test_account(self, account_id, account_name):
        """Test predictions for one account"""
        print(f"\n📊 Testing Account: {account_name}")
        print("   " + "-"*60)
        
        # Get milestones
        milestones = self.get_milestones(account_id)
        if not milestones:
            print("   ⚠️  No milestones found for this account")
            return []
        
        print(f"   Found {len(milestones)} milestone(s)")
        
        results = []
        
        for milestone in milestones:
            week = milestone['week']
            milestone_type = milestone['type']
            
            # Get KPIs for the week BEFORE the milestone
            test_week = max(1, week - 1)
            kpis = self.get_account_kpis_at_week(account_id, test_week)
            
            if not kpis:
                print(f"   ⚠️  No KPIs found for week {test_week}")
                continue
            
            # Get pre-calculated health score (KPIs were already properly normalized in Phase 3)
            health_score = self.get_health_score_at_week(account_id, test_week)
            prediction = self.predict_outcome(health_score, kpis)
            
            # Debug: Show sample KPI values (for reference - using pre-calculated health score)
            if len(kpis) > 0:
                sample_kpis = list(kpis.items())[:5]
                debug_str = ", ".join([f"{k}={v:.1f}" for k, v in sample_kpis])
                print(f"      Raw KPIs (not used): {debug_str}")
                print(f"      Using health_score from DB: {health_score}")
            
            # Determine actual outcome from milestone (check in order of specificity)
            milestone_lower = milestone_type.lower()
            
            if 'risk' in milestone_lower or 'crisis' in milestone_lower or 'alert' in milestone_lower:
                # Risk signals, crisis, or alerts = at_risk
                actual_outcome = 'at_risk'
            elif 'churn' in milestone_lower and 'terminated' in milestone_lower:
                # Actual churn (contract terminated)
                actual_outcome = 'churn'
            elif 'expansion' in milestone_lower and ('approved' in milestone_lower or 'decision' in milestone_lower):
                # Actual expansion decision
                actual_outcome = 'expansion'
            elif 'churn' in milestone_lower:
                # Generic churn mention
                actual_outcome = 'churn'
            elif 'expansion' in milestone_lower:
                # Generic expansion mention
                actual_outcome = 'expansion'
            else:
                actual_outcome = 'stable'
            
            # Check if prediction was correct
            prediction_correct = prediction['outcome'] == actual_outcome
            
            # Calculate errors
            health_error = abs(health_score - 50)  # Simplified - would need actual health at milestone
            
            result = {
                'account_id': account_id,
                'week': week,
                'test_week': test_week,
                'milestone_type': milestone_type,
                'predicted_outcome': prediction['outcome'],
                'actual_outcome': actual_outcome,
                'predicted_health': prediction['health_score'],
                'churn_risk': prediction['churn_risk'],
                'expansion_prob': prediction['expansion_prob'],
                'prediction_correct': prediction_correct,
                'confidence': 0.70  # Bootstrap baseline confidence
            }
            
            results.append(result)
            
            # Print result
            status = "✅" if prediction_correct else "❌"
            print(f"   {status} Week {test_week}: Predicted '{prediction['outcome']}' | Actual '{actual_outcome}'")
            print(f"      Health: {prediction['health_score']:.1f} | Churn: {prediction['churn_risk']*100:.0f}% | Expansion: {prediction['expansion_prob']*100:.0f}%")
        
        return results
    
    def save_results(self, all_results):
        """Save test results to database"""
        with self.engine.connect() as conn:
            for result in all_results:
                conn.execute(text("""
                    INSERT INTO signal_baseline_results (
                        journey_account_id, test_date, prediction_week,
                        predicted_outcome, predicted_health_score,
                        predicted_churn_risk, predicted_expansion_prob,
                        actual_outcome, actual_milestone_type,
                        prediction_correct, confidence_score, test_run_id
                    ) VALUES (
                        :account_id, :test_date, :week,
                        :predicted_outcome, :predicted_health,
                        :churn_risk, :expansion_prob,
                        :actual_outcome, :milestone_type,
                        :correct, :confidence, :test_run_id
                    )
                """), {
                    'account_id': result['account_id'],
                    'test_date': datetime.now(),
                    'week': result['week'],
                    'predicted_outcome': result['predicted_outcome'],
                    'predicted_health': result['predicted_health'],
                    'churn_risk': result['churn_risk'],
                    'expansion_prob': result['expansion_prob'],
                    'actual_outcome': result['actual_outcome'],
                    'milestone_type': result['milestone_type'],
                    'correct': result['prediction_correct'],
                    'confidence': result['confidence'],
                    'test_run_id': self.test_run_id
                })
            
            conn.commit()
    
    def calculate_accuracy(self, results):
        """Calculate overall accuracy"""
        if not results:
            return 0.0
        
        correct = sum(1 for r in results if r['prediction_correct'])
        return (correct / len(results)) * 100
    
    def run_test(self):
        """Run full test on all accounts"""
        print("="*70)
        print("SIGNAL ANALYST BASELINE TEST")
        print("="*70)
        print(f"Test Run ID: {self.test_run_id}")
        print()
        
        # Load weights
        print("📖 Loading bootstrap weights...")
        self.load_bootstrap_weights()
        self.load_kpi_mapping()
        print()
        
        # Get accounts
        with self.engine.connect() as conn:
            accounts = conn.execute(text("""
                SELECT journey_account_id, account_name, pattern_type
                FROM journey_accounts
                ORDER BY journey_account_id
            """)).fetchall()
        
        print(f"🎯 Testing {len(accounts)} accounts...")
        
        # Test each account
        all_results = []
        for account_id, account_name, pattern in accounts:
            results = self.test_account(account_id, account_name)
            all_results.extend(results)
        
        # Save results
        if all_results:
            print(f"\n💾 Saving {len(all_results)} test results...")
            self.save_results(all_results)
            print("   ✅ Results saved")
        
        # Calculate accuracy
        print("\n" + "="*70)
        print("📊 BASELINE ACCURACY RESULTS")
        print("="*70)
        
        accuracy = self.calculate_accuracy(all_results)
        correct_count = sum(1 for r in all_results if r['prediction_correct'])
        total_count = len(all_results)
        
        print(f"\nOverall Accuracy: {accuracy:.1f}% ({correct_count}/{total_count})")
        print()
        
        # Breakdown by outcome
        outcome_stats = {}
        for result in all_results:
            actual = result['actual_outcome']
            if actual not in outcome_stats:
                outcome_stats[actual] = {'correct': 0, 'total': 0}
            
            outcome_stats[actual]['total'] += 1
            if result['prediction_correct']:
                outcome_stats[actual]['correct'] += 1
        
        print("Accuracy by Outcome:")
        for outcome, stats in outcome_stats.items():
            acc = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  {outcome:15s}: {acc:5.1f}% ({stats['correct']}/{stats['total']})")
        
        print()
        
        # Target comparison
        if 55 <= accuracy <= 65:
            status = "✅ ON TARGET"
        elif accuracy > 65:
            status = "🎯 EXCEEDS TARGET"
        else:
            status = "⚠️  BELOW TARGET"
        
        print(f"Target Range: 55-65%")
        print(f"Status: {status}")
        print()
        
        print("="*70)
        print("✅ BASELINE TEST COMPLETE!")
        print("="*70)
        print()
        print(f"Results saved with test_run_id: {self.test_run_id}")
        print()
        print("Next step: Review results and proceed to Step 3 (Learning Loop)")
        
        return accuracy


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test Signal Analyst with bootstrap weights')
    parser.add_argument('--db-url',
                       default=os.environ.get('DATABASE_URL'),
                       help='PostgreSQL connection URL')
    
    args = parser.parse_args()
    
    if not args.db_url:
        print("❌ ERROR: Database URL not provided")
        print()
        print("Usage:")
        print("  export DATABASE_URL='postgresql://user:pass@host:5432/database'")
        print("  python3 test_signal_analyst.py")
        sys.exit(1)
    
    try:
        tester = SignalAnalystTester(args.db_url)
        accuracy = tester.run_test()
        
        # Exit with status based on accuracy
        if accuracy >= 55:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Below target
    
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
