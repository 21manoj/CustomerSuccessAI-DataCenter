#!/usr/bin/env python3
"""
Auto Ensemble Learning - Automatically picks the right method
==============================================================

Detects your dataset size and uses the appropriate ensemble method:
- Small (< 10 samples) → Simple Weighted Average
- Medium (10-20 samples) → Logistic Meta-Learner  
- Large (20+ samples) → Stacking Ensemble

Usage:
    export OPENAI_API_KEY="sk-..."
    export DATABASE_URL="postgresql://..."
    python3 auto_ensemble.py
"""

import os
import sys
from sqlalchemy import create_engine, text


def count_training_samples(db_url):
    """Count available training samples"""
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) 
            FROM journey_milestones
        """))
        count = result.scalar()
    
    return count


def main():
    db_url = os.environ.get('DATABASE_URL')
    api_key = os.environ.get('OPENAI_API_KEY')
    
    if not db_url:
        print("❌ ERROR: Set DATABASE_URL environment variable")
        sys.exit(1)
    
    if not api_key:
        print("❌ ERROR: Set OPENAI_API_KEY environment variable")
        sys.exit(1)
    
    print("="*70)
    print("AUTO ENSEMBLE LEARNING")
    print("="*70)
    print()
    
    # Count samples
    print("Detecting dataset size...")
    sample_count = count_training_samples(db_url)
    print(f"Found {sample_count} training samples")
    print()
    
    # Recommend method
    if sample_count < 10:
        method = "simple"
        script = "simple_ensemble_learning.py"
        reason = "Small dataset - using simple weighted average for best results"
        print(f"✅ Recommendation: {reason}")
        print()
        print("="*70)
        print()
        
        # Run simple version
        import subprocess
        result = subprocess.run([
            'python3', 
            script
        ], env=os.environ.copy())
        
        sys.exit(result.returncode)
        
    elif sample_count < 20:
        method = "logistic"
        script = "ensemble_weight_learning_fixed.py"
        reason = "Medium dataset - using logistic meta-learner"
        args = ['--method', 'logistic']
        
    else:
        method = "stacking"
        script = "ensemble_weight_learning_fixed.py"
        reason = "Large dataset - using stacking ensemble for maximum performance"
        args = ['--method', 'stacking']
    
    print(f"✅ Recommendation: {reason}")
    print(f"   Running: python3 {script} {' '.join(args)}")
    print()
    print("="*70)
    print()
    
    # Run appropriate script
    import subprocess
    result = subprocess.run([
        'python3', 
        script,
        '--db-url', db_url,
        '--api-key', api_key
    ] + args, env=os.environ.copy())
    
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
