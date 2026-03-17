"""
Realistic Evaluation with Challenging Conditions
Adds noise, drift, and realistic complexities to avoid overfitting
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import json
import time
from pathlib import Path
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score, roc_curve
)
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import seaborn as sns
from loguru import logger


def add_realistic_noise(data, noise_level=0.05):
    """
    Add realistic sensor noise and imperfections
    
    Args:
        data: DataFrame
        noise_level: Noise level (0.05 = 5% noise)
    """
    logger.info(f"Adding realistic sensor noise (level={noise_level})...")
    
    noisy_data = data.copy()
    
    # Add Gaussian noise to all sensor readings
    sensor_cols = ['pressure', 'temperature', 'flow_rate', 'H2O', 'H2S', 'SO2', 'O2']
    
    for col in sensor_cols:
        if col in noisy_data.columns:
            # Add proportional noise
            noise = np.random.normal(0, noise_level * noisy_data[col].std(), len(noisy_data))
            noisy_data[col] = noisy_data[col] + noise
            
            # Ensure non-negative values
            noisy_data[col] = noisy_data[col].clip(lower=0)
    
    # Add sensor drift (gradual bias over time)
    for col in sensor_cols:
        if col in noisy_data.columns:
            drift = np.linspace(0, 0.02 * noisy_data[col].mean(), len(noisy_data))
            noisy_data[col] = noisy_data[col] + drift
    
    # Add random missing values (sensor failures)
    missing_rate = 0.01  # 1% missing
    for col in sensor_cols:
        if col in noisy_data.columns:
            mask = np.random.random(len(noisy_data)) < missing_rate
            noisy_data.loc[mask, col] = np.nan
    
    # Forward fill missing values (realistic interpolation)
    noisy_data = noisy_data.fillna(method='ffill').fillna(method='bfill')
    
    logger.success("Realistic noise added")
    
    return noisy_data


def make_anomalies_subtle(data, subtlety=0.5):
    """
    Make anomalies more subtle and gradual (harder to detect)
    
    Args:
        data: DataFrame
        subtlety: 0=very obvious, 1=very subtle
    """
    logger.info(f"Making anomalies more subtle (level={subtlety})...")
    
    subtle_data = data.copy()
    
    # For leakage events, reduce O2 spike magnitude
    leakage_mask = subtle_data['leakage_risk'] == 1
    if leakage_mask.sum() > 0:
        # Instead of large O2 spike, make it gradual and smaller
        o2_reduction = subtlety * 0.7  # Reduce spike by 70% at max subtlety
        subtle_data.loc[leakage_mask, 'O2'] = (
            subtle_data.loc[leakage_mask, 'O2'] * (1 - o2_reduction) +
            subtle_data['O2'].mean() * o2_reduction
        )
    
    # For corrosion events, make impurity changes more gradual
    corrosion_mask = subtle_data['corrosion_risk'] == 1
    if corrosion_mask.sum() > 0:
        impurity_reduction = subtlety * 0.5
        for col in ['H2O', 'H2S', 'SO2']:
            if col in subtle_data.columns:
                subtle_data.loc[corrosion_mask, col] = (
                    subtle_data.loc[corrosion_mask, col] * (1 - impurity_reduction) +
                    subtle_data[col].mean() * impurity_reduction
                )
    
    logger.success("Anomalies made more subtle")
    
    return subtle_data


def create_realistic_test_set(test_data, noise_level=0.05, subtlety=0.5):
    """
    Create realistic test set with noise and subtle anomalies
    """
    logger.info("Creating realistic test set...")
    
    # Add noise
    realistic_data = add_realistic_noise(test_data, noise_level)
    
    # Make anomalies subtle
    realistic_data = make_anomalies_subtle(realistic_data, subtlety)
    
    logger.success("Realistic test set created")
    
    return realistic_data


def prepare_features(data):
    """Prepare features for ML models"""
    feature_cols = ['pressure', 'temperature', 'flow_rate', 'H2O', 'H2S', 'SO2', 'O2']
    
    if 'acoustic' in data.columns:
        feature_cols.append('acoustic')
    if 'vibration' in data.columns:
        feature_cols.append('vibration')
    
    X = data[feature_cols].values
    return X, feature_cols


def evaluate_model(model_name, X_train, y_train, X_test, y_test):
    """Evaluate a single model"""
    
    logger.info(f"Training {model_name}...")
    
    # Train
    model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    start_time = time.time()
    model.fit(X_train, y_train)
    training_time = time.time() - start_time
    
    # Predict
    start_time = time.time()
    y_pred = model.predict(X_test)
    inference_time = (time.time() - start_time) / len(X_test) * 1000
    
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Metrics
    metrics = {
        'model': model_name,
        'accuracy': float(accuracy_score(y_test, y_pred)),
        'precision': float(precision_score(y_test, y_pred, zero_division=0)),
        'recall': float(recall_score(y_test, y_pred, zero_division=0)),
        'f1_score': float(f1_score(y_test, y_pred, zero_division=0)),
        'auc_roc': float(roc_auc_score(y_test, y_pred_proba)),
        'training_time_s': float(training_time),
        'inference_time_ms': float(inference_time)
    }
    
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    metrics['confusion_matrix'] = {
        'TN': int(cm[0, 0]),
        'FP': int(cm[0, 1]),
        'FN': int(cm[1, 0]),
        'TP': int(cm[1, 1])
    }
    
    metrics['FPR'] = float(cm[0, 1] / (cm[0, 0] + cm[0, 1])) if (cm[0, 0] + cm[0, 1]) > 0 else 0
    metrics['FNR'] = float(cm[1, 0] / (cm[1, 0] + cm[1, 1])) if (cm[1, 0] + cm[1, 1]) > 0 else 0
    
    logger.success(f"{model_name} - Accuracy: {metrics['accuracy']:.4f}, F1: {metrics['f1_score']:.4f}")
    
    return metrics, model


def evaluate_baselines(X_train, X_test, y_test, task_name):
    """Evaluate baseline methods"""
    
    logger.info(f"Evaluating baselines for {task_name}...")
    
    baselines = {}
    
    # 1. Threshold-based (O2 > threshold for leakage)
    if task_name == 'leakage' and X_test.shape[1] >= 7:
        o2_values = X_test[:, 6]  # O2 is 7th column
        threshold = np.percentile(o2_values, 95)  # 95th percentile
        y_pred_threshold = (o2_values > threshold).astype(int)
        
        baselines['Threshold-based'] = {
            'accuracy': float(accuracy_score(y_test, y_pred_threshold)),
            'precision': float(precision_score(y_test, y_pred_threshold, zero_division=0)),
            'recall': float(recall_score(y_test, y_pred_threshold, zero_division=0)),
            'f1_score': float(f1_score(y_test, y_pred_threshold, zero_division=0)),
            'training_time_s': 0.0,
            'inference_time_ms': 0.001
        }
    
    # 2. Isolation Forest
    iso_forest = IsolationForest(contamination=0.05, random_state=42, n_jobs=-1)
    start_time = time.time()
    iso_forest.fit(X_train)
    train_time = time.time() - start_time
    
    start_time = time.time()
    y_pred_iso = (iso_forest.predict(X_test) == -1).astype(int)
    inference_time = (time.time() - start_time) / len(X_test) * 1000
    
    baselines['Isolation Forest'] = {
        'accuracy': float(accuracy_score(y_test, y_pred_iso)),
        'precision': float(precision_score(y_test, y_pred_iso, zero_division=0)),
        'recall': float(recall_score(y_test, y_pred_iso, zero_division=0)),
        'f1_score': float(f1_score(y_test, y_pred_iso, zero_division=0)),
        'training_time_s': float(train_time),
        'inference_time_ms': float(inference_time)
    }
    
    logger.success("Baselines evaluated")
    
    return baselines


def generate_comparison_table(results, output_dir):
    """Generate comparison table with baselines"""
    
    os.makedirs(f'{output_dir}/tables', exist_ok=True)
    
    # LaTeX table with baselines
    with open(f'{output_dir}/tables/model_comparison.tex', 'w') as f:
        f.write("\\begin{table}[h]\n")
        f.write("\\centering\n")
        f.write("\\caption{Model Performance Comparison (Realistic Test Conditions)}\n")
        f.write("\\begin{tabular}{lcccccc}\n")
        f.write("\\hline\n")
        f.write("Method & Accuracy & Precision & Recall & F1-Score & Training (s) & Inference (ms) \\\\\n")
        f.write("\\hline\n")
        
        # PredBlock models
        for metrics in results['model_performance']:
            f.write(f"\\textbf{{{metrics['model']}}} & ")
            f.write(f"{metrics['accuracy']:.3f} & ")
            f.write(f"{metrics['precision']:.3f} & ")
            f.write(f"{metrics['recall']:.3f} & ")
            f.write(f"{metrics['f1_score']:.3f} & ")
            f.write(f"{metrics['training_time_s']:.2f} & ")
            f.write(f"{metrics['inference_time_ms']:.3f} \\\\\n")
        
        f.write("\\hline\n")
        f.write("\\multicolumn{7}{c}{\\textit{Baseline Methods}} \\\\\n")
        f.write("\\hline\n")
        
        # Baselines
        for method_name, metrics in results['baselines']['leakage'].items():
            f.write(f"{method_name} & ")
            f.write(f"{metrics['accuracy']:.3f} & ")
            f.write(f"{metrics['precision']:.3f} & ")
            f.write(f"{metrics['recall']:.3f} & ")
            f.write(f"{metrics['f1_score']:.3f} & ")
            f.write(f"{metrics['training_time_s']:.2f} & ")
            f.write(f"{metrics['inference_time_ms']:.3f} \\\\\n")
        
        f.write("\\hline\n")
        f.write("\\end{tabular}\n")
        f.write("\\label{tab:model_comparison}\n")
        f.write("\\end{table}\n")
    
    logger.info(f"Saved: {output_dir}/tables/model_comparison.tex")


def main():
    """Main evaluation with realistic conditions"""
    
    print("="*70)
    print("REALISTIC EVALUATION FOR PUBLICATION")
    print("Adds noise, drift, and subtle anomalies")
    print("="*70)
    
    output_dir = 'paper_evaluation_realistic'
    os.makedirs(output_dir, exist_ok=True)
    
    # Load data
    logger.info("Loading data...")
    train_data = pd.read_csv('data/train_physics.csv')
    test_data = pd.read_csv('data/test_physics.csv')
    
    logger.info(f"Training: {len(train_data)} samples")
    logger.info(f"Test: {len(test_data)} samples")
    
    # Create realistic test set
    realistic_test = create_realistic_test_set(
        test_data, 
        noise_level=0.08,  # 8% noise
        subtlety=0.6       # 60% more subtle
    )
    
    # Prepare features
    X_train, feature_cols = prepare_features(train_data)
    X_test, _ = prepare_features(realistic_test)
    
    all_metrics = []
    
    # Evaluate each task
    for task in ['leakage', 'corrosion', 'overpressure']:
        logger.info("="*70)
        logger.info(f"EVALUATING {task.upper()} DETECTION")
        logger.info("="*70)
        
        y_train = train_data[f'{task}_risk'].values
        y_test = realistic_test[f'{task}_risk'].values
        
        metrics, model = evaluate_model(
            f"{task.capitalize()} Detector",
            X_train, y_train, X_test, y_test
        )
        all_metrics.append(metrics)
    
    # Evaluate baselines
    y_test_leakage = realistic_test['leakage_risk'].values
    baselines = evaluate_baselines(X_train, X_test, y_test_leakage, 'leakage')
    
    # Save results
    results = {
        'model_performance': all_metrics,
        'baselines': {'leakage': baselines},
        'test_conditions': {
            'noise_level': 0.08,
            'subtlety': 0.6,
            'missing_data_rate': 0.01,
            'sensor_drift': True
        },
        'dataset_info': {
            'train_samples': len(train_data),
            'test_samples': len(realistic_test),
            'features': feature_cols
        }
    }
    
    with open(f'{output_dir}/realistic_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Generate tables
    generate_comparison_table(results, output_dir)
    
    # Print summary
    print("\n" + "="*70)
    print("REALISTIC EVALUATION COMPLETE")
    print("="*70)
    print("\nModel Performance (with noise, drift, subtle anomalies):")
    for metrics in all_metrics:
        print(f"\n{metrics['model']}:")
        print(f"  Accuracy:  {metrics['accuracy']:.4f}")
        print(f"  Precision: {metrics['precision']:.4f}")
        print(f"  Recall:    {metrics['recall']:.4f}")
        print(f"  F1-Score:  {metrics['f1_score']:.4f}")
        print(f"  AUC-ROC:   {metrics['auc_roc']:.4f}")
    
    print("\n\nBaseline Comparison:")
    for method, metrics in baselines.items():
        print(f"\n{method}:")
        print(f"  Accuracy:  {metrics['accuracy']:.4f}")
        print(f"  F1-Score:  {metrics['f1_score']:.4f}")
    
    print(f"\n\nResults saved to: {output_dir}/")
    print(f"  - realistic_results.json")
    print(f"  - tables/model_comparison.tex")
    
    # Analysis
    print("\n" + "="*70)
    print("ANALYSIS")
    print("="*70)
    
    predblock_f1 = all_metrics[0]['f1_score']
    threshold_f1 = baselines.get('Threshold-based', {}).get('f1_score', 0)
    iso_f1 = baselines['Isolation Forest']['f1_score']
    
    print(f"\nPredBlock F1-Score: {predblock_f1:.4f}")
    print(f"Threshold F1-Score: {threshold_f1:.4f}")
    print(f"Isolation Forest F1: {iso_f1:.4f}")
    
    if predblock_f1 > threshold_f1:
        improvement = ((predblock_f1 - threshold_f1) / threshold_f1) * 100
        print(f"\n✓ PredBlock outperforms threshold by {improvement:.1f}%")
    
    if predblock_f1 > iso_f1:
        improvement = ((predblock_f1 - iso_f1) / iso_f1) * 100
        print(f"✓ PredBlock outperforms Isolation Forest by {improvement:.1f}%")


if __name__ == "__main__":
    main()
