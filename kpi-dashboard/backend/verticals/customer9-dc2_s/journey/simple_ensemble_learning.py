#!/usr/bin/env python3
"""
Simple Ensemble Weight Learning - Quick Start
==============================================

Learns optimal weights using simple grid search.
Perfect for understanding the basics before using the full version.

Usage:
    python3 simple_ensemble_learning.py
"""

import os
import numpy as np
from sqlalchemy import create_engine, text
from test_signal_analyst_v4_smart_override import MultiSignalPredictorV3, HybridPredictorV4


def simple_weighted_ensemble(v3_pred, llm_pred, v3_conf, llm_conf, weights):
    """
    Simple weighted ensemble prediction
    
    Args:
        v3_pred: V3 prediction (string: 'churn', 'at_risk', etc.)
        llm_pred: LLM prediction
        v3_conf: V3 confidence (0-1)
        llm_conf: LLM confidence (0-1)
        weights: dict with 'v3' and 'llm' keys (should sum to 1.0)
    
    Returns:
        Final prediction (string)
    """
    outcome_scores = {
        'churn': 0,
        'at_risk': 1,
        'stable': 2,
        'healthy': 3,
        'expansion': 4
    }
    reverse_map = {v: k for k, v in outcome_scores.items()}
    
    # Convert to numeric scores
    v3_score = outcome_scores.get(v3_pred, 2)
    llm_score = outcome_scores.get(llm_pred, 2)
    
    # Weighted combination
    combined_score = (
        v3_score * v3_conf * weights['v3'] +
        llm_score * llm_conf * weights['llm']
    )
    
    # Normalize
    total_weight = v3_conf * weights['v3'] + llm_conf * weights['llm']
    if total_weight > 0:
        combined_score = combined_score / total_weight
    
    # Round to nearest outcome
    final_score = int(round(combined_score))
    final_score = np.clip(final_score, 0, 4)
    
    return reverse_map[final_score]


def learn_weights_grid_search(db_url, api_key):
    """
    Learn optimal weights using simple grid search
    """
    print("="*70)
    print("SIMPLE ENSEMBLE WEIGHT LEARNING")
    print("="*70)
    print()
    
    # Initialize predictors
    engine = create_engine(db_url)
    v3_predictor = MultiSignalPredictorV3(engine)
    v4_predictor = HybridPredictorV4(engine, api_key)
    
    # Get training data
    print("Collecting training data...")
    with engine.connect() as conn:
        milestones = conn.execute(text("""
            SELECT 
                jm.journey_account_id,
                ja.account_name,
                jm.week_number,
                jm.milestone_type
            FROM journey_milestones jm
            JOIN journey_accounts ja ON jm.journey_account_id = ja.journey_account_id
        """)).fetchall()
    
    # Collect predictions
    samples = []
    print(f"Making predictions for {len(milestones)} milestones...")
    
    for milestone in milestones:
        account_id, account_name, week, milestone_type = milestone
        test_week = max(1, week - 1)
        
        try:
            # Get predictions
            v3_result = v3_predictor.predict_with_events(account_id, test_week)
            v4_result = v4_predictor.predict(account_id, test_week, force_llm=True)
            
            v3_pred = v3_result['prediction']['outcome']
            llm_pred = v4_result.get('llm_prediction', v3_pred)
            v3_conf = 0.75
            llm_conf = v4_result.get('confidence', 0.75)
            
            # Actual outcome
            milestone_lower = milestone_type.lower()
            if 'expansion' in milestone_lower:
                actual = 'expansion'
            elif 'churn' in milestone_lower and 'terminated' in milestone_lower:
                actual = 'churn'
            elif 'risk' in milestone_lower or 'crisis' in milestone_lower:
                actual = 'at_risk'
            elif 'churn' in milestone_lower:
                actual = 'churn'
            else:
                actual = 'stable'
            
            samples.append({
                'account_name': account_name,
                'v3_pred': v3_pred,
                'llm_pred': llm_pred,
                'v3_conf': v3_conf,
                'llm_conf': llm_conf,
                'actual': actual
            })
            
            print(f"  ✓ {account_name[:30]:30s} V3={v3_pred:10s} LLM={llm_pred:10s} Actual={actual}")
            
        except Exception as e:
            print(f"  ✗ {account_name[:30]:30s} Error: {e}")
    
    print()
    print(f"Collected {len(samples)} samples")
    print()
    
    # Grid search for optimal weights
    print("="*70)
    print("GRID SEARCH FOR OPTIMAL WEIGHTS")
    print("="*70)
    print()
    
    best_accuracy = 0
    best_weights = None
    results = []
    
    for v3_weight in np.arange(0.0, 1.1, 0.1):
        llm_weight = 1.0 - v3_weight
        weights = {'v3': v3_weight, 'llm': llm_weight}
        
        # Make predictions with these weights
        correct = 0
        for sample in samples:
            pred = simple_weighted_ensemble(
                sample['v3_pred'],
                sample['llm_pred'],
                sample['v3_conf'],
                sample['llm_conf'],
                weights
            )
            if pred == sample['actual']:
                correct += 1
        
        accuracy = correct / len(samples) if samples else 0
        results.append((v3_weight, llm_weight, accuracy))
        
        print(f"V3={v3_weight:.1f}, LLM={llm_weight:.1f} → Accuracy: {accuracy:.1%} ({correct}/{len(samples)})")
        
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_weights = weights
    
    print()
    print("="*70)
    print("OPTIMAL WEIGHTS FOUND")
    print("="*70)
    print(f"V3 Weight: {best_weights['v3']:.2f}")
    print(f"LLM Weight: {best_weights['llm']:.2f}")
    print(f"Accuracy: {best_accuracy:.1%}")
    print()
    
    # Compare with baselines
    print("="*70)
    print("BASELINE COMPARISON")
    print("="*70)
    
    # V3 only accuracy
    v3_correct = sum(1 for s in samples if s['v3_pred'] == s['actual'])
    v3_accuracy = v3_correct / len(samples)
    print(f"V3 Only: {v3_accuracy:.1%} ({v3_correct}/{len(samples)})")
    
    # LLM only accuracy
    llm_correct = sum(1 for s in samples if s['llm_pred'] == s['actual'])
    llm_accuracy = llm_correct / len(samples)
    print(f"LLM Only: {llm_accuracy:.1%} ({llm_correct}/{len(samples)})")
    
    # Ensemble
    print(f"Ensemble (Optimal): {best_accuracy:.1%}")
    
    improvement = best_accuracy - max(v3_accuracy, llm_accuracy)
    if improvement > 0:
        print(f"\n🎯 Improvement: +{improvement:.1%}")
    
    print()
    
    # Show weight sensitivity
    print("="*70)
    print("WEIGHT SENSITIVITY ANALYSIS")
    print("="*70)
    print()
    print("V3 Weight | LLM Weight | Accuracy | Diff from Optimal")
    print("-" * 70)
    for v3_w, llm_w, acc in results:
        diff = acc - best_accuracy
        marker = " ←" if abs(diff) < 0.01 else ""
        print(f"{v3_w:9.1f} | {llm_w:10.1f} | {acc:8.1%} | {diff:+7.1%}{marker}")
    
    return best_weights, best_accuracy


if __name__ == "__main__":
    db_url = os.environ.get('DATABASE_URL')
    api_key = os.environ.get('OPENAI_API_KEY')
    
    if not db_url or not api_key:
        print("❌ ERROR: Set DATABASE_URL and OPENAI_API_KEY environment variables")
        exit(1)
    
    try:
        weights, accuracy = learn_weights_grid_search(db_url, api_key)
        
        # Save weights to file
        import json
        with open('learned_weights.json', 'w') as f:
            json.dump({
                'weights': weights,
                'accuracy': accuracy,
                'timestamp': str(np.datetime64('now'))
            }, f, indent=2)
        
        print("✅ Weights saved to: learned_weights.json")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
