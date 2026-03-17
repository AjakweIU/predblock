"""
Complete Evaluation for Publication
Generates ALL metrics needed for the paper
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


def load_data():
    """Load training and test data"""
    train_data = pd.read_csv('data/train_physics.csv')
    test_data = pd.read_csv('data/test_physics.csv')
    
    logger.info(f"Training data: {len(train_data)} samples")
    logger.info(f"Test data: {len(test_data)} samples")
    
    return train_data, test_data


def prepare_features(data):
    """Prepare features for ML models"""
    feature_cols = ['pressure', 'temperature', 'flow_rate', 'H2O', 'H2S', 'SO2', 'O2']
    
    if 'acoustic' in data.columns:
        feature_cols.append('acoustic')
    if 'vibration' in data.columns:
        feature_cols.append('vibration')
    
    X = data[feature_cols].values
    return X, feature_cols


def evaluate_leakage_detection(train_data, test_data):
    """Section 2.1: Leakage Detection Performance"""
    
    logger.info("="*70)
    logger.info("EVALUATING LEAKAGE DETECTION")
    logger.info("="*70)
    
    # Prepare data
    X_train, feature_cols = prepare_features(train_data)
    X_test, _ = prepare_features(test_data)
    y_train = train_data['leakage_risk'].values
    y_test = test_data['leakage_risk'].values
    
    # Train model
    logger.info("Training Random Forest classifier...")
    model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    
    start_time = time.time()
    model.fit(X_train, y_train)
    training_time = time.time() - start_time
    
    # Predictions
    start_time = time.time()
    y_pred = model.predict(X_test)
    inference_time = (time.time() - start_time) / len(X_test) * 1000  # ms per sample
    
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Calculate metrics
    metrics = {
        'model': 'Leakage Detector',
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
    
    # False positive/negative rates
    metrics['FPR'] = float(cm[0, 1] / (cm[0, 0] + cm[0, 1])) if (cm[0, 0] + cm[0, 1]) > 0 else 0
    metrics['FNR'] = float(cm[1, 0] / (cm[1, 0] + cm[1, 1])) if (cm[1, 0] + cm[1, 1]) > 0 else 0
    
    # Feature importance
    feature_importance = dict(zip(feature_cols, model.feature_importances_))
    metrics['feature_importance'] = {k: float(v) for k, v in feature_importance.items()}
    
    logger.success(f"Leakage Detection - Accuracy: {metrics['accuracy']:.4f}, F1: {metrics['f1_score']:.4f}")
    
    return metrics, model


def evaluate_corrosion_detection(train_data, test_data):
    """Section 2.1: Corrosion Detection Performance"""
    
    logger.info("="*70)
    logger.info("EVALUATING CORROSION DETECTION")
    logger.info("="*70)
    
    # Prepare data
    X_train, feature_cols = prepare_features(train_data)
    X_test, _ = prepare_features(test_data)
    y_train = train_data['corrosion_risk'].values
    y_test = test_data['corrosion_risk'].values
    
    # Train model
    logger.info("Training Random Forest classifier...")
    model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    
    start_time = time.time()
    model.fit(X_train, y_train)
    training_time = time.time() - start_time
    
    # Predictions
    start_time = time.time()
    y_pred = model.predict(X_test)
    inference_time = (time.time() - start_time) / len(X_test) * 1000
    
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Calculate metrics
    metrics = {
        'model': 'Corrosion Predictor',
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
    
    logger.success(f"Corrosion Detection - Accuracy: {metrics['accuracy']:.4f}, F1: {metrics['f1_score']:.4f}")
    
    return metrics, model


def evaluate_overpressure_detection(train_data, test_data):
    """Section 2.1: Overpressure Detection Performance"""
    
    logger.info("="*70)
    logger.info("EVALUATING OVERPRESSURE DETECTION")
    logger.info("="*70)
    
    # Prepare data
    X_train, feature_cols = prepare_features(train_data)
    X_test, _ = prepare_features(test_data)
    y_train = train_data['overpressure_risk'].values
    y_test = test_data['overpressure_risk'].values
    
    # Train model
    logger.info("Training Random Forest classifier...")
    model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    
    start_time = time.time()
    model.fit(X_train, y_train)
    training_time = time.time() - start_time
    
    # Predictions
    start_time = time.time()
    y_pred = model.predict(X_test)
    inference_time = (time.time() - start_time) / len(X_test) * 1000
    
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Calculate metrics
    metrics = {
        'model': 'Overpressure Detector',
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
    
    logger.success(f"Overpressure Detection - Accuracy: {metrics['accuracy']:.4f}, F1: {metrics['f1_score']:.4f}")
    
    return metrics, model


def evaluate_baselines(train_data, test_data, task='leakage'):
    """Section 3: Baseline Comparisons"""
    
    logger.info("="*70)
    logger.info(f"EVALUATING BASELINES FOR {task.upper()}")
    logger.info("="*70)
    
    X_train, _ = prepare_features(train_data)
    X_test, _ = prepare_features(test_data)
    y_test = test_data[f'{task}_risk'].values
    
    baselines = {}
    
    # 1. Threshold-based (simple rule)
    if task == 'leakage' and 'O2' in test_data.columns:
        logger.info("Testing threshold-based detection...")
        y_pred_threshold = (test_data['O2'] > 10).astype(int).values
        baselines['Threshold-based'] = {
            'accuracy': float(accuracy_score(y_test, y_pred_threshold)),
            'precision': float(precision_score(y_test, y_pred_threshold, zero_division=0)),
            'recall': float(recall_score(y_test, y_pred_threshold, zero_division=0)),
            'f1_score': float(f1_score(y_test, y_pred_threshold, zero_division=0)),
            'training_time_s': 0.0,
            'inference_time_ms': 0.001
        }
    
    # 2. Isolation Forest
    logger.info("Testing Isolation Forest...")
    iso_forest = IsolationForest(contamination=0.05, random_state=42, n_jobs=-1)
    start_time = time.time()
    iso_forest.fit(X_train)
    train_time_iso = time.time() - start_time
    
    start_time = time.time()
    y_pred_iso = (iso_forest.predict(X_test) == -1).astype(int)
    inference_time_iso = (time.time() - start_time) / len(X_test) * 1000
    
    baselines['Isolation Forest'] = {
        'accuracy': float(accuracy_score(y_test, y_pred_iso)),
        'precision': float(precision_score(y_test, y_pred_iso, zero_division=0)),
        'recall': float(recall_score(y_test, y_pred_iso, zero_division=0)),
        'f1_score': float(f1_score(y_test, y_pred_iso, zero_division=0)),
        'training_time_s': float(train_time_iso),
        'inference_time_ms': float(inference_time_iso)
    }
    
    # 3. One-Class SVM
    logger.info("Testing One-Class SVM...")
    ocsvm = OneClassSVM(nu=0.05)
    start_time = time.time()
    ocsvm.fit(X_train)
    train_time_svm = time.time() - start_time
    
    start_time = time.time()
    y_pred_svm = (ocsvm.predict(X_test) == -1).astype(int)
    inference_time_svm = (time.time() - start_time) / len(X_test) * 1000
    
    baselines['One-Class SVM'] = {
        'accuracy': float(accuracy_score(y_test, y_pred_svm)),
        'precision': float(precision_score(y_test, y_pred_svm, zero_division=0)),
        'recall': float(recall_score(y_test, y_pred_svm, zero_division=0)),
        'f1_score': float(f1_score(y_test, y_pred_svm, zero_division=0)),
        'training_time_s': float(train_time_svm),
        'inference_time_ms': float(inference_time_svm)
    }
    
    logger.success("Baseline comparison complete")
    
    return baselines


def generate_performance_tables(all_metrics, output_dir):
    """Generate performance comparison tables"""
    
    logger.info("Generating performance tables...")
    
    os.makedirs(f'{output_dir}/tables', exist_ok=True)
    
    # LaTeX table
    with open(f'{output_dir}/tables/model_performance.tex', 'w') as f:
        f.write("\\begin{table}[h]\n")
        f.write("\\centering\n")
        f.write("\\caption{AI Model Performance on Test Dataset}\n")
        f.write("\\begin{tabular}{lcccccc}\n")
        f.write("\\hline\n")
        f.write("Model & Accuracy & Precision & Recall & F1-Score & AUC-ROC & Inference (ms) \\\\\n")
        f.write("\\hline\n")
        
        for metrics in all_metrics:
            f.write(f"{metrics['model']} & ")
            f.write(f"{metrics['accuracy']:.3f} & ")
            f.write(f"{metrics['precision']:.3f} & ")
            f.write(f"{metrics['recall']:.3f} & ")
            f.write(f"{metrics['f1_score']:.3f} & ")
            f.write(f"{metrics['auc_roc']:.3f} & ")
            f.write(f"{metrics['inference_time_ms']:.2f} \\\\\n")
        
        f.write("\\hline\n")
        f.write("\\end{tabular}\n")
        f.write("\\label{tab:model_performance}\n")
        f.write("\\end{table}\n")
    
    logger.info(f"Saved: {output_dir}/tables/model_performance.tex")


def generate_confusion_matrix_plots(all_metrics, output_dir):
    """Generate confusion matrix visualizations"""
    
    logger.info("Generating confusion matrix plots...")
    
    os.makedirs(f'{output_dir}/figures', exist_ok=True)
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    
    for idx, metrics in enumerate(all_metrics):
        cm_data = metrics['confusion_matrix']
        cm = np.array([[cm_data['TN'], cm_data['FP']], 
                       [cm_data['FN'], cm_data['TP']]])
        
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[idx],
                   xticklabels=['Normal', 'Anomaly'],
                   yticklabels=['Normal', 'Anomaly'])
        axes[idx].set_title(f"{metrics['model']}\nAccuracy: {metrics['accuracy']:.3f}")
        axes[idx].set_ylabel('Actual')
        axes[idx].set_xlabel('Predicted')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/figures/confusion_matrices.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Saved: {output_dir}/figures/confusion_matrices.png")


def main():
    """Main evaluation function"""
    
    print("="*70)
    print("COMPLETE EVALUATION FOR PUBLICATION")
    print("="*70)
    
    output_dir = 'paper_evaluation_complete'
    os.makedirs(output_dir, exist_ok=True)
    
    # Load data
    logger.info("Loading data...")
    train_data, test_data = load_data()
    
    all_metrics = []
    all_baselines = {}
    
    # Evaluate Leakage Detection
    leakage_metrics, leakage_model = evaluate_leakage_detection(train_data, test_data)
    all_metrics.append(leakage_metrics)
    
    # Evaluate Corrosion Detection
    corrosion_metrics, corrosion_model = evaluate_corrosion_detection(train_data, test_data)
    all_metrics.append(corrosion_metrics)
    
    # Evaluate Overpressure Detection
    overpressure_metrics, overpressure_model = evaluate_overpressure_detection(train_data, test_data)
    all_metrics.append(overpressure_metrics)
    
    # Evaluate Baselines
    leakage_baselines = evaluate_baselines(train_data, test_data, 'leakage')
    all_baselines['leakage'] = leakage_baselines
    
    # Generate outputs
    generate_performance_tables(all_metrics, output_dir)
    generate_confusion_matrix_plots(all_metrics, output_dir)
    
    # Save all results
    results = {
        'model_performance': all_metrics,
        'baselines': all_baselines,
        'dataset_info': {
            'train_samples': len(train_data),
            'test_samples': len(test_data),
            'features': list(prepare_features(test_data)[1])
        }
    }
    
    with open(f'{output_dir}/complete_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "="*70)
    print("EVALUATION COMPLETE")
    print("="*70)
    print("\nModel Performance:")
    for metrics in all_metrics:
        print(f"\n{metrics['model']}:")
        print(f"  Accuracy:  {metrics['accuracy']:.4f}")
        print(f"  Precision: {metrics['precision']:.4f}")
        print(f"  Recall:    {metrics['recall']:.4f}")
        print(f"  F1-Score:  {metrics['f1_score']:.4f}")
        print(f"  AUC-ROC:   {metrics['auc_roc']:.4f}")
    
    print(f"\n\nResults saved to: {output_dir}/")
    print(f"  - complete_results.json")
    print(f"  - tables/model_performance.tex")
    print(f"  - figures/confusion_matrices.png")


if __name__ == "__main__":
    main()
