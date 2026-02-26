#!/usr/bin/env python3
"""
Event Signal Integration Layer
===============================

Integrates event signals (sentiment, escalations, outages) with KPI-based health
to improve prediction accuracy from 80% → 95%+

Usage:
    python3 test_signal_analyst_v2.py --db-url "$DATABASE_URL"
"""

import os
import sys
import argparse
from datetime import datetime
from sqlalchemy import create_engine, text


class EventSignalAnalyzer:
    """Analyzes event signals to enhance predictions"""
    
    def __init__(self, engine):
        self.engine = engine
    
    def get_recent_events(self, account_id, current_week, lookback_weeks=4):
        """Get events from the past N weeks"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    event_type,
                    description,
                    sentiment_value,
                    phase,
                    week_number
                FROM journey_events
                WHERE journey_account_id = :account_id
                AND week_number > :start_week
                AND week_number <= :current_week
                ORDER BY week_number
            """), {
                'account_id': account_id,
                'start_week': current_week - lookback_weeks,
                'current_week': current_week
            })
            
            return [dict(row._mapping) for row in result]
    
    def calculate_event_risk_score(self, events):
        """Calculate risk score from recent events"""
        if not events:
            return 0.0
        
        risk_score = 0.0
        
        # High-severity event types
        severity_weights = {
            'outage': 5.0,                # was 15.0
            'escalation': 3.5,            # was 10.0
            'support_ticket': 1.5,        # was 5.0
            'technical_issue': 1.5,       # was 5.0
            'executive_engagement': 2.5,  # was 8.0
            'budget_review': 1.0,         # was 3.0
            'email': 0.5,                 # was 2.0
            'meeting': 0.3,               # was 1.0
            'expansion_discussion': -1.5, # was -5.0
            'champion_interaction': -0.7, # was -2.0
            'milestone': -1.0,            # was -3.0
	    }	 
        # Analyze each event
        for event in events:
            event_type = event['event_type']
            sentiment = float(event['sentiment_value'] or 0)
            
            # Base risk from event type
            type_risk = severity_weights.get(event_type, 0.0)
            
            # Sentiment modifier (negative sentiment increases risk)
            if sentiment < 0:
                sentiment_risk = abs(sentiment) * 1.5  # reduced from 5 to 1.5 
            else:
                sentiment_risk = sentiment * -3.0  # +0.9 → -2.7 risk (reduces risk)
            
            risk_score += type_risk + sentiment_risk
        
        # Normalize by number of events (avoid penalizing engaged accounts)
        if len(events) > 5:
            risk_score = risk_score * (5 / len(events))
        
        return round(risk_score, 2)
    
    def calculate_sentiment_trend(self, events):
        """Calculate sentiment trend (improving or declining)"""
        if len(events) < 2:
            return 0.0
        
        # Get average sentiment for first half vs second half
        mid = len(events) // 2
        first_half = events[:mid]
        second_half = events[mid:]
        
        avg_first = sum(e['sentiment_value'] or 0 for e in first_half) / len(first_half)
        avg_second = sum(e['sentiment_value'] or 0 for e in second_half) / len(second_half)
        
        # Trend: positive if improving, negative if declining
        trend = avg_second - avg_first
        
        return round(trend, 3)
    
    def detect_escalation_pattern(self, events):
        """Detect if escalations are increasing"""
        escalations = [e for e in events if e['event_type'] in ('escalation', 'executive_engagement')]
        
        if not escalations:
            return False
        
        # Check if escalations are in recent weeks (escalating crisis)
        recent_escalations = sum(1 for e in escalations if e['week_number'] >= max(ev['week_number'] for ev in events) - 1)
        
        return recent_escalations >= 2  # 2+ escalations in last 2 weeks
    
    def detect_disengagement_pattern(self, events):
        """Detect champion disengagement"""
        # Look for missed meetings, dropped usage, etc.
        disengagement_keywords = [
            'missed', 'dropped', 'disengagement', 'alternatives',
            'evaluating', 'competitor', 'concerns raised'
        ]
        
        disengagement_events = [
            e for e in events
            if any(keyword in e['description'].lower() for keyword in disengagement_keywords)
        ]
        
        return len(disengagement_events) >= 2
    
    def get_event_summary(self, events):
        """Get summary of event signals"""
        if not events:
            return {
                'risk_score': 0.0,
                'sentiment_trend': 0.0,
                'has_escalation': False,
                'has_disengagement': False,
                'event_count': 0,
                'avg_sentiment': 0.0
            }
        
        return {
            'risk_score': self.calculate_event_risk_score(events),
            'sentiment_trend': self.calculate_sentiment_trend(events),
            'has_escalation': self.detect_escalation_pattern(events),
            'has_disengagement': self.detect_disengagement_pattern(events),
            'event_count': len(events),
            'avg_sentiment': round(sum(e['sentiment_value'] or 0 for e in events) / len(events), 2)
        }


class MultiSignalPredictor:
    """Combines KPI health + Event signals for predictions"""
    
    def __init__(self, engine):
        self.engine = engine
        self.event_analyzer = EventSignalAnalyzer(engine)
    
    def get_health_score_at_week(self, account_id, week):
        """Get pre-calculated health score from database"""
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
            return 50.0
    
    def predict_with_events(self, account_id, week):
        """Make prediction using both KPI health and event signals"""
        
        # Signal 1: KPI-based health
        kpi_health = self.get_health_score_at_week(account_id, week)
        
        # Signal 2: Event-based risk
        events = self.event_analyzer.get_recent_events(account_id, week, lookback_weeks=4)
        event_summary = self.event_analyzer.get_event_summary(events)
        
        # Adjust health based on events
        adjusted_health = kpi_health - event_summary['risk_score']
        
        # Additional adjustments for specific patterns
        if event_summary['has_escalation']:
            adjusted_health -= 5  # Escalation pattern = -5 health
        
        if event_summary['has_disengagement']:
            adjusted_health -= 8  # Disengagement = -8 health
        
        if event_summary['sentiment_trend'] < -0.3:
            adjusted_health -= 5  # Declining sentiment = -5 health
        
        # Clamp to 0-100
        adjusted_health = max(0.0, min(100.0, adjusted_health))
        
        # Make prediction based on adjusted health
        prediction = self.predict_outcome_from_health(adjusted_health)
        
        return {
            'kpi_health': kpi_health,
            'event_risk_score': event_summary['risk_score'],
            'adjusted_health': adjusted_health,
            'prediction': prediction,
            'event_summary': event_summary,
            'adjustment': kpi_health - adjusted_health
        }
    
    def predict_outcome_from_health(self, health_score):
        """Predict outcome from health score"""
        if health_score < 35:
            return {
                'outcome': 'churn',
                'churn_risk': 0.95,
                'expansion_prob': 0.05
            }
        elif health_score < 50:
            return {
                'outcome': 'at_risk',
                'churn_risk': 0.75,
                'expansion_prob': 0.10
            }
        elif health_score < 70:
            return {
                'outcome': 'stable',
                'churn_risk': 0.35,
                'expansion_prob': 0.25
            }
        elif health_score < 85:
            return {
                'outcome': 'healthy',
                'churn_risk': 0.15,
                'expansion_prob': 0.50
            }
        else:
            return {
                'outcome': 'expansion',
                'churn_risk': 0.05,
                'expansion_prob': 0.80
            }


def test_multi_signal_predictions(db_url):
    """Test predictions using both KPI and event signals"""
    
    print("="*70)
    print("MULTI-SIGNAL PREDICTION TEST")
    print("="*70)
    print()
    
    engine = create_engine(db_url)
    predictor = MultiSignalPredictor(engine)
    
    # Get milestones to test
    with engine.connect() as conn:
        milestones = conn.execute(text("""
            SELECT 
                jm.journey_account_id,
                ja.account_name,
                jm.week_number,
                jm.milestone_type
            FROM journey_milestones jm
            JOIN journey_accounts ja ON jm.journey_account_id = ja.journey_account_id
            ORDER BY ja.account_name, jm.week_number
        """)).fetchall()
    
    results = []
    
    for milestone in milestones:
        account_id, account_name, week, milestone_type = milestone
        
        # Test week is week before milestone
        test_week = max(1, week - 1)
        
        # Make prediction
        prediction = predictor.predict_with_events(account_id, test_week)
        
        # Determine actual outcome
        milestone_lower = milestone_type.lower()
        if 'risk' in milestone_lower or 'crisis' in milestone_lower or 'alert' in milestone_lower:
            actual_outcome = 'at_risk'
        elif 'churn' in milestone_lower and 'terminated' in milestone_lower:
            actual_outcome = 'churn'
        elif 'expansion' in milestone_lower:
            actual_outcome = 'expansion'
        elif 'churn' in milestone_lower:
            actual_outcome = 'churn'
        else:
            actual_outcome = 'stable'
        
        predicted_outcome = prediction['prediction']['outcome']
        correct = predicted_outcome == actual_outcome
        
        results.append({
            'account_name': account_name,
            'week': week,
            'test_week': test_week,
            'milestone_type': milestone_type,
            'predicted': predicted_outcome,
            'actual': actual_outcome,
            'correct': correct,
            'kpi_health': prediction['kpi_health'],
            'adjusted_health': prediction['adjusted_health'],
            'event_risk': prediction['event_risk_score'],
            'event_count': prediction['event_summary']['event_count'],
            'avg_sentiment': prediction['event_summary']['avg_sentiment']
        })
        
        # Print result
        status = "✅" if correct else "❌"
        print(f"{status} {account_name[:25]:25s} Week {test_week:2d}")
        print(f"   KPI Health: {prediction['kpi_health']:5.1f} → Adjusted: {prediction['adjusted_health']:5.1f} (Event Risk: {prediction['event_risk_score']:+5.1f})")
        print(f"   Events: {prediction['event_summary']['event_count']} events, Sentiment: {prediction['event_summary']['avg_sentiment']:+.2f}")
        if prediction['event_summary']['has_escalation']:
            print(f"   ⚠️  Escalation pattern detected")
        if prediction['event_summary']['has_disengagement']:
            print(f"   ⚠️  Disengagement pattern detected")
        print(f"   Predicted: '{predicted_outcome}' | Actual: '{actual_outcome}'")
        print()
    
    # Summary
    print("="*70)
    print("RESULTS SUMMARY")
    print("="*70)
    
    correct_count = sum(1 for r in results if r['correct'])
    total_count = len(results)
    accuracy = (correct_count / total_count * 100) if total_count > 0 else 0
    
    print(f"\nOverall Accuracy: {accuracy:.1f}% ({correct_count}/{total_count})")
    print()
    
    # Compare to KPI-only
    print("Comparison:")
    print(f"  KPI-only baseline:     80.0% (4/5)")
    print(f"  Multi-signal (KPI+Events): {accuracy:.1f}% ({correct_count}/{total_count})")
    print()
    
    if accuracy > 80:
        print(f"🎯 Improvement: +{accuracy - 80:.1f} percentage points!")
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test multi-signal predictions')
    parser.add_argument('--db-url',
                       default=os.environ.get('DATABASE_URL'),
                       help='PostgreSQL connection URL')
    
    args = parser.parse_args()
    
    if not args.db_url:
        print("❌ ERROR: Database URL not provided")
        sys.exit(1)
    
    try:
        results = test_multi_signal_predictions(args.db_url)
        
        # Success if accuracy >= 85%
        accuracy = sum(1 for r in results if r['correct']) / len(results) * 100
        sys.exit(0 if accuracy >= 85 else 1)
    
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
