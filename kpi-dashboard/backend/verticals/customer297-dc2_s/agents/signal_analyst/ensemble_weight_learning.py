#!/usr/bin/env python3
"""
Ensemble Weight Learning for Multi-Signal Predictor
====================================================

Learns optimal weights for combining:
- V3 quantitative predictions (KPI + Events)
- LLM qualitative reasoning
- Individual signal components

Uses multiple ensemble techniques:
1. Weighted Average Ensemble
2. Logistic Regression Meta-learner
3. Stacking with Cross-Validation
4. Bayesian Optimization

Usage:
    export OPENAI_API_KEY="sk-..."
    export DATABASE_URL="postgresql://..."
    python3 ensemble_weight_learning.py --method weighted_avg
"""

import os
import sys
import json
import argparse
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine, text
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
import pickle

# Import our predictors
from test_signal_analyst_v4_smart_override import (
    MultiSignalPredictorV3, 
    HybridPredictorV4
)


# ============================================================================
# ENSEMBLE METHODS
# ============================================================================

class WeightedAverageEnsemble:
    """Simple weighted average of predictor confidences"""
    
    def __init__(self):
        self.weights = {
            'v3_quantitative': 0.5,
            'llm_qualitative': 0.5
        }
        self.outcome_map = {
            'expansion': 4, 'healthy': 3, 'stable': 2, 'at_risk': 1, 'churn': 0
        }
        self.reverse_map = {v: k for k, v in self.outcome_map.items()}
    
    def fit(self, X_train, y_train):
        """
        Learn optimal weights using grid search
        X_train: list of (v3_pred, llm_pred, v3_confidence, llm_confidence, features)
        y_train: actual outcomes
        """
        print("Training Weighted Average Ensemble...")
        print(f"  Training samples: {len(X_train)}")
        
        best_accuracy = 0
        best_weights = None
        
        # Grid search over weight combinations
        for v3_weight in np.arange(0.0, 1.1, 0.1):
            llm_weight = 1.0 - v3_weight
            
            self.weights = {
                'v3_quantitative': v3_weight,
                'llm_qualitative': llm_weight
            }
            
            predictions = [self.predict_single(x) for x in X_train]
            accuracy = accuracy_score(y_train, predictions)
            
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_weights = self.weights.copy()
        
        self.weights = best_weights
        print(f"  Best weights found: V3={self.weights['v3_quantitative']:.2f}, LLM={self.weights['llm_qualitative']:.2f}")
        print(f"  Training accuracy: {best_accuracy:.1%}")
        
        return self
    
    def predict_single(self, x):
        """Predict single sample"""
        v3_pred, llm_pred, v3_conf, llm_conf, features = x
        
        # Convert predictions to numeric scores
        v3_score = self.outcome_map.get(v3_pred, 2)
        llm_score = self.outcome_map.get(llm_pred, 2)
        
        # Weight by confidence and ensemble weights
        weighted_score = (
            v3_score * v3_conf * self.weights['v3_quantitative'] +
            llm_score * llm_conf * self.weights['llm_qualitative']
        )
        
        # Normalize
        total_weight = (
            v3_conf * self.weights['v3_quantitative'] +
            llm_conf * self.weights['llm_qualitative']
        )
        
        if total_weight > 0:
            weighted_score = weighted_score / total_weight
        
        # Round to nearest outcome
        final_score = int(round(weighted_score))
        final_score = np.clip(final_score, 0, 4)
        
        return self.reverse_map[final_score]
    
    def predict(self, X):
        """Predict multiple samples"""
        return [self.predict_single(x) for x in X]


class LogisticMetaLearner:
    """Logistic regression meta-learner on top of base predictors"""
    
    def __init__(self):
        self.model = LogisticRegression(max_iter=1000, class_weight='balanced')
        self.scaler = StandardScaler()
        self.feature_names = [
            'v3_pred_numeric',
            'llm_pred_numeric', 
            'v3_confidence',
            'llm_confidence',
            'predictions_agree',
            'kpi_health',
            'adjusted_health',
            'event_risk',
            'event_count',
            'avg_sentiment',
            'sentiment_trend'
        ]
    
    def fit(self, X_train, y_train):
        """Train meta-learner"""
        print("Training Logistic Meta-Learner...")
        print(f"  Training samples: {len(X_train)}")
        
        # Extract features
        X_features = self._extract_features(X_train)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X_features)
        
        # Train model
        self.model.fit(X_scaled, y_train)
        
        # Cross-validation score
        cv_scores = cross_val_score(self.model, X_scaled, y_train, cv=3)
        print(f"  Cross-val accuracy: {cv_scores.mean():.1%} (+/- {cv_scores.std():.1%})")
        
        # Feature importance
        self._print_feature_importance()
        
        return self
    
    def _extract_features(self, X):
        """Extract feature matrix from prediction data"""
        outcome_map = {'expansion': 4, 'healthy': 3, 'stable': 2, 'at_risk': 1, 'churn': 0}
        
        features = []
        for x in X:
            v3_pred, llm_pred, v3_conf, llm_conf, feature_dict = x
            
            feature_vector = [
                outcome_map.get(v3_pred, 2),
                outcome_map.get(llm_pred, 2),
                v3_conf,
                llm_conf,
                1.0 if v3_pred == llm_pred else 0.0,
                feature_dict.get('kpi_health', 50.0),
                feature_dict.get('adjusted_health', 50.0),
                feature_dict.get('event_risk', 0.0),
                feature_dict.get('event_count', 0),
                feature_dict.get('avg_sentiment', 0.0),
                feature_dict.get('sentiment_trend', 0.0)
            ]
            features.append(feature_vector)
        
        return np.array(features)
    
    def _print_feature_importance(self):
        """Print feature importance from coefficients"""
        # Average absolute coefficients across classes
        coef_avg = np.abs(self.model.coef_).mean(axis=0)
        
        importance = sorted(
            zip(self.feature_names, coef_avg),
            key=lambda x: x[1],
            reverse=True
        )
        
        print("\n  Feature Importance:")
        for name, score in importance[:5]:
            print(f"    {name:25s} {score:.3f}")
    
    def predict(self, X):
        """Predict with meta-learner"""
        X_features = self._extract_features(X)
        X_scaled = self.scaler.transform(X_features)
        return self.model.predict(X_scaled)


class StackingEnsemble:
    """Stacking ensemble with multiple base models"""
    
    def __init__(self):
        self.base_models = [
            ('logistic', LogisticRegression(max_iter=1000, class_weight='balanced')),
            ('rf', RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42))
        ]
        self.meta_learner = LogisticRegression(max_iter=1000)
        self.scaler = StandardScaler()
    
    def fit(self, X_train, y_train):
        """Train stacking ensemble with cross-validation"""
        print("Training Stacking Ensemble...")
        print(f"  Training samples: {len(X_train)}")
        
        # Extract features
        X_features = self._extract_features(X_train)
        X_scaled = self.scaler.fit_transform(X_features)
        
        # Train base models
        print("  Training base models...")
        for name, model in self.base_models:
            model.fit(X_scaled, y_train)
            score = model.score(X_scaled, y_train)
            print(f"    {name}: {score:.1%}")
        
        # Generate meta-features using cross-validation
        print("  Generating meta-features...")
        meta_features = self._generate_meta_features(X_scaled, y_train)
        
        # Train meta-learner
        print("  Training meta-learner...")
        self.meta_learner.fit(meta_features, y_train)
        
        return self
    
    def _extract_features(self, X):
        """Extract feature matrix"""
        outcome_map = {'expansion': 4, 'healthy': 3, 'stable': 2, 'at_risk': 1, 'churn': 0}
        
        features = []
        for x in X:
            v3_pred, llm_pred, v3_conf, llm_conf, feature_dict = x
            
            feature_vector = [
                outcome_map.get(v3_pred, 2),
                outcome_map.get(llm_pred, 2),
                v3_conf,
                llm_conf,
                feature_dict.get('kpi_health', 50.0),
                feature_dict.get('adjusted_health', 50.0),
                feature_dict.get('event_risk', 0.0),
                feature_dict.get('event_count', 0),
                feature_dict.get('avg_sentiment', 0.0),
                feature_dict.get('sentiment_trend', 0.0)
            ]
            features.append(feature_vector)
        
        return np.array(features)
    
    def _generate_meta_features(self, X, y):
        """Generate meta-features using cross-validation predictions"""
        n_samples = len(X)
        n_models = len(self.base_models)
        n_classes = len(np.unique(y))
        
        meta_features = np.zeros((n_samples, n_models * n_classes))
        
        skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
        
        for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X, y)):
            X_fold_train, X_fold_val = X[train_idx], X[val_idx]
            y_fold_train = y[train_idx]
            
            for model_idx, (name, model) in enumerate(self.base_models):
                # Clone and train model on fold
                fold_model = type(model)(**model.get_params())
                fold_model.fit(X_fold_train, y_fold_train)
                
                # Get probability predictions for validation set
                probas = fold_model.predict_proba(X_fold_val)
                
                # Store in meta-features
                start_col = model_idx * n_classes
                end_col = start_col + n_classes
                meta_features[val_idx, start_col:end_col] = probas
        
        return meta_features
    
    def predict(self, X):
        """Predict with stacking ensemble"""
        X_features = self._extract_features(X)
        X_scaled = self.scaler.transform(X_features)
        
        # Get predictions from base models
        n_models = len(self.base_models)
        n_classes = len(self.base_models[0][1].classes_)
        meta_features = np.zeros((len(X), n_models * n_classes))
        
        for model_idx, (name, model) in enumerate(self.base_models):
            probas = model.predict_proba(X_scaled)
            start_col = model_idx * n_classes
            end_col = start_col + n_classes
            meta_features[:, start_col:end_col] = probas
        
        # Predict with meta-learner
        return self.meta_learner.predict(meta_features)


# ============================================================================
# DATA PREPARATION
# ============================================================================

def collect_training_data(engine, v3_predictor, v4_predictor, force_llm=False):
    """
    Collect training data from journey milestones
    Returns: X (features), y (labels), metadata
    """
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
            ORDER BY ja.account_name, jm.week_number
        """)).fetchall()
    
    X = []
    y = []
    metadata = []
    
    for milestone in milestones:
        account_id, account_name, week, milestone_type = milestone
        test_week = max(1, week - 1)
        
        try:
            # Get V3 prediction
            v3_result = v3_predictor.predict_with_events(account_id, test_week)
            v3_prediction = v3_result['prediction']['outcome']
            v3_confidence = 0.75  # V3 baseline confidence
            
            # Get V4 (hybrid) prediction
            v4_result = v4_predictor.predict(account_id, test_week, force_llm=force_llm)
            llm_prediction = v4_result.get('llm_prediction', v3_prediction)
            llm_confidence = v4_result.get('confidence', 0.75)
            
            # Extract features
            features = {
                'kpi_health': v3_result['kpi_health'],
                'adjusted_health': v3_result['adjusted_health'],
                'event_risk': v3_result['event_risk_score'],
                'event_count': v3_result['event_summary']['event_count'],
                'avg_sentiment': v3_result['event_summary']['avg_sentiment'],
                'sentiment_trend': v3_result['event_summary']['sentiment_trend']
            }
            
            # Determine actual outcome
            milestone_lower = milestone_type.lower()
            if 'expansion' in milestone_lower:
                actual_outcome = 'expansion'
            elif 'churn' in milestone_lower and 'terminated' in milestone_lower:
                actual_outcome = 'churn'
            elif 'risk' in milestone_lower or 'crisis' in milestone_lower or 'alert' in milestone_lower:
                actual_outcome = 'at_risk'
            elif 'churn' in milestone_lower:
                actual_outcome = 'churn'
            else:
                actual_outcome = 'stable'
            
            # Store sample
            X.append((v3_prediction, llm_prediction, v3_confidence, llm_confidence, features))
            y.append(actual_outcome)
            metadata.append({
                'account_id': account_id,
                'account_name': account_name,
                'week': test_week,
                'milestone_type': milestone_type
            })
            
        except Exception as e:
            print(f"  Warning: Skipped {account_name} week {test_week}: {e}")
            continue
    
    print(f"  Collected {len(X)} training samples")
    
    return X, y, metadata


# ============================================================================
# MAIN TRAINING PIPELINE
# ============================================================================

def train_ensemble(db_url, api_key, method='weighted_avg', test_size=0.3):
    """
    Train ensemble with specified method
    """
    print("="*70)
    print("ENSEMBLE WEIGHT LEARNING")
    print("="*70)
    print(f"Method: {method}")
    print(f"Test size: {test_size:.0%}")
    print()
    
    # Initialize predictors
    engine = create_engine(db_url)
    v3_predictor = MultiSignalPredictorV3(engine)
    v4_predictor = HybridPredictorV4(engine, api_key)
    
    # Collect training data
    X, y, metadata = collect_training_data(engine, v3_predictor, v4_predictor, force_llm=True)
    
    if len(X) < 10:
        print("❌ ERROR: Not enough training data (need at least 10 samples)")
        return None
    
    # Train/test split
    X_train, X_test, y_train, y_test, meta_train, meta_test = train_test_split(
        X, y, metadata, test_size=test_size, random_state=42, stratify=y
    )
    
    print(f"Training set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")
    print()
    
    # Train ensemble
    if method == 'weighted_avg':
        ensemble = WeightedAverageEnsemble()
    elif method == 'logistic':
        ensemble = LogisticMetaLearner()
    elif method == 'stacking':
        ensemble = StackingEnsemble()
    else:
        raise ValueError(f"Unknown method: {method}")
    
    ensemble.fit(X_train, y_train)
    print()
    
    # Evaluate
    print("="*70)
    print("EVALUATION RESULTS")
    print("="*70)
    
    # Training performance
    y_train_pred = ensemble.predict(X_train)
    train_accuracy = accuracy_score(y_train, y_train_pred)
    print(f"Training Accuracy: {train_accuracy:.1%}")
    
    # Test performance
    y_test_pred = ensemble.predict(X_test)
    test_accuracy = accuracy_score(y_test, y_test_pred)
    print(f"Test Accuracy: {test_accuracy:.1%}")
    print()
    
    # Detailed metrics
    print("Classification Report:")
    print(classification_report(y_test, y_test_pred))
    
    print("Confusion Matrix:")
    cm = confusion_matrix(y_test, y_test_pred, labels=['churn', 'at_risk', 'stable', 'healthy', 'expansion'])
    print(cm)
    print()
    
    # Compare with baseline
    print("="*70)
    print("BASELINE COMPARISON")
    print("="*70)
    
    # V3 only
    y_test_v3 = [x[0] for x in X_test]
    v3_accuracy = accuracy_score(y_test, y_test_v3)
    print(f"V3 Quantitative Only: {v3_accuracy:.1%}")
    
    # LLM only
    y_test_llm = [x[1] for x in X_test]
    llm_accuracy = accuracy_score(y_test, y_test_llm)
    print(f"LLM Only: {llm_accuracy:.1%}")
    
    # Ensemble
    print(f"Ensemble ({method}): {test_accuracy:.1%}")
    
    improvement = test_accuracy - max(v3_accuracy, llm_accuracy)
    if improvement > 0:
        print(f"\n🎯 Improvement: +{improvement:.1%} over best baseline")
    
    print()
    
    # Save model
    model_filename = f'ensemble_{method}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pkl'
    with open(model_filename, 'wb') as f:
        pickle.dump(ensemble, f)
    print(f"✅ Model saved: {model_filename}")
    
    return ensemble, test_accuracy


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Train ensemble predictor with weight learning')
    parser.add_argument('--db-url',
                       default=os.environ.get('DATABASE_URL'),
                       help='PostgreSQL connection URL')
    parser.add_argument('--api-key',
                       default=os.environ.get('OPENAI_API_KEY'),
                       help='OpenAI API key')
    parser.add_argument('--method',
                       choices=['weighted_avg', 'logistic', 'stacking'],
                       default='weighted_avg',
                       help='Ensemble method to use')
    parser.add_argument('--test-size',
                       type=float,
                       default=0.3,
                       help='Test set size (0.0-1.0)')
    
    args = parser.parse_args()
    
    if not args.db_url:
        print("❌ ERROR: Database URL not provided")
        print("Usage: export DATABASE_URL='postgresql://...'")
        sys.exit(1)
    
    if not args.api_key:
        print("❌ ERROR: OpenAI API key not provided")
        print("Usage: export OPENAI_API_KEY='sk-...'")
        sys.exit(1)
    
    try:
        ensemble, accuracy = train_ensemble(
            args.db_url,
            args.api_key,
            method=args.method,
            test_size=args.test_size
        )
        
        sys.exit(0 if accuracy >= 0.85 else 1)
    
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
