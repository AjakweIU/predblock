"""
Comprehensive Evaluation Script for Research Paper
Generates all metrics, tables, and figures needed for publication
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score, roc_curve
)
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.svm import OneClassSVM
import time
import json
from loguru import logger


class PaperEvaluator:
    """Comprehensive evaluation for research paper"""
    
    def __init__(self, test_data_path: str):
        """Initialize evaluator with test data"""
        self.test_data = pd.read_csv(test_data_path)
        self.results = {}
        
        logger.info(f"Loaded test data: {len(self.test_data)} samples")
    
    def evaluate_data_quality(self):
        """Section 1: Dataset Validation"""
        
        logger.info("Evaluating data quality...")
        
        results = {
            'dataset_size': len(self.test_data),
            'temporal_coverage_days': len(self.test_data) / (60 * 24),
            'sampling_rate': '1 minute',
            'anomaly_distribution': {}
        }
        
        # Anomaly distribution
        if 'leakage_risk' in self.test_data.columns:
            results['anomaly_distribution']['leakage'] = {
                'count': int(self.test_data['leakage_risk'].sum()),
                'percentage': float(self.test_data['leakage_risk'].mean() * 100)
            }
        
        if 'corrosion_risk' in self.test_data.columns:
            results['anomaly_distribution']['corrosion'] = {
                'count': int(self.test_data['corrosion_risk'].sum()),
                'percentage': float(self.test_data['corrosion_risk'].mean() * 100)
            }
        
        if 'overpressure_risk' in self.test_data.columns:
            results['anomaly_distribution']['overpressure'] = {
                'count': int(self.test_data['overpressure_risk'].sum()),
                'percentage': float(self.test_data['overpressure_risk'].mean() * 100)
            }
        
        # Total anomaly rate
        total_anomalies = (
            self.test_data.get('leakage_risk', 0).sum() +
            self.test_data.get('corrosion_risk', 0).sum() +
            self.test_data.get('overpressure_risk', 0).sum()
        )
        results['total_anomaly_rate'] = float(total_anomalies / len(self.test_data) * 100)
        
        # Temporal autocorrelation
        results['autocorrelation'] = {}
        for var in ['pressure', 'temperature', 'H2O']:
            if var in self.test_data.columns:
                values = self.test_data[var].values
                if len(values) > 1:
                    autocorr = np.corrcoef(values[:-1], values[1:])[0, 1]
                    results['autocorrelation'][var] = float(autocorr)
        
        self.results['data_quality'] = results
        
        logger.success("Data quality evaluation complete")
        return results
    
    def evaluate_model_performance(self, model, X_test, y_test, model_name: str):
        """Section 2: AI Model Performance"""
        
        logger.info(f"Evaluating {model_name}...")
        
        # Predictions
        start_time = time.time()
        y_pred = model.predict(X_test)
        inference_time = (time.time() - start_time) / len(X_test) * 1000  # ms per sample
        
        # Get probabilities if available
        try:
            y_pred_proba = model.predict_proba(X_test)[:, 1]
        except:
            y_pred_proba = y_pred
        
        # Calculate metrics
        metrics = {
            'accuracy': float(accuracy_score(y_test, y_pred)),
            'precision': float(precision_score(y_test, y_pred, zero_division=0)),
            'recall': float(recall_score(y_test, y_pred, zero_division=0)),
            'f1_score': float(f1_score(y_test, y_pred, zero_division=0)),
            'inference_time_ms': float(inference_time)
        }
        
        # AUC-ROC if probabilities available
        try:
            metrics['auc_roc'] = float(roc_auc_score(y_test, y_pred_proba))
        except:
            metrics['auc_roc'] = None
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        metrics['confusion_matrix'] = {
            'TN': int(cm[0, 0]) if cm.shape == (2, 2) else 0,
            'FP': int(cm[0, 1]) if cm.shape == (2, 2) else 0,
            'FN': int(cm[1, 0]) if cm.shape == (2, 2) else 0,
            'TP': int(cm[1, 1]) if cm.shape == (2, 2) else 0
        }
        
        # False positive/negative rates
        if cm.shape == (2, 2):
            metrics['FPR'] = float(cm[0, 1] / (cm[0, 0] + cm[0, 1])) if (cm[0, 0] + cm[0, 1]) > 0 else 0
            metrics['FNR'] = float(cm[1, 0] / (cm[1, 0] + cm[1, 1])) if (cm[1, 0] + cm[1, 1]) > 0 else 0
        
        if model_name not in self.results:
            self.results[model_name] = {}
        self.results[model_name]['performance'] = metrics
        
        logger.success(f"{model_name} evaluation complete")
        return metrics
    
    def compare_baselines(self, X_test, y_test, task_name: str):
        """Section 3: Baseline Comparisons"""
        
        logger.info(f"Comparing baselines for {task_name}...")
        
        baselines = {}
        
        # 1. Threshold-based (simple rule)
        logger.info("Testing threshold-based detection...")
        if 'O2' in self.test_data.columns and task_name == 'leakage':
            y_pred_threshold = (self.test_data['O2'] > 10).astype(int).values
            baselines['Threshold-based'] = {
                'accuracy': float(accuracy_score(y_test, y_pred_threshold)),
                'precision': float(precision_score(y_test, y_pred_threshold, zero_division=0)),
                'recall': float(recall_score(y_test, y_pred_threshold, zero_division=0)),
                'f1_score': float(f1_score(y_test, y_pred_threshold, zero_division=0))
            }
        
        # 2. Isolation Forest
        logger.info("Testing Isolation Forest...")
        iso_forest = IsolationForest(contamination=0.05, random_state=42)
        start_time = time.time()
        iso_forest.fit(X_test)
        train_time_iso = time.time() - start_time
        
        y_pred_iso = (iso_forest.predict(X_test) == -1).astype(int)
        baselines['Isolation Forest'] = {
            'accuracy': float(accuracy_score(y_test, y_pred_iso)),
            'precision': float(precision_score(y_test, y_pred_iso, zero_division=0)),
            'recall': float(recall_score(y_test, y_pred_iso, zero_division=0)),
            'f1_score': float(f1_score(y_test, y_pred_iso, zero_division=0)),
            'training_time_s': float(train_time_iso)
        }
        
        # 3. One-Class SVM
        logger.info("Testing One-Class SVM...")
        ocsvm = OneClassSVM(nu=0.05)
        start_time = time.time()
        ocsvm.fit(X_test)
        train_time_svm = time.time() - start_time
        
        y_pred_svm = (ocsvm.predict(X_test) == -1).astype(int)
        baselines['One-Class SVM'] = {
            'accuracy': float(accuracy_score(y_test, y_pred_svm)),
            'precision': float(precision_score(y_test, y_pred_svm, zero_division=0)),
            'recall': float(recall_score(y_test, y_pred_svm, zero_division=0)),
            'f1_score': float(f1_score(y_test, y_pred_svm, zero_division=0)),
            'training_time_s': float(train_time_svm)
        }
        
        self.results[f'{task_name}_baselines'] = baselines
        
        logger.success("Baseline comparison complete")
        return baselines
    
    def generate_plots(self, output_dir: str = 'paper_figures'):
        """Generate publication-quality figures"""
        
        logger.info("Generating plots...")
        os.makedirs(output_dir, exist_ok=True)
        
        # Set publication style
        plt.style.use('seaborn-v0_8-paper')
        sns.set_palette("husl")
        
        # 1. Anomaly distribution
        fig, ax = plt.subplots(figsize=(8, 6))
        anomaly_data = self.results['data_quality']['anomaly_distribution']
        
        categories = list(anomaly_data.keys())
        percentages = [anomaly_data[cat]['percentage'] for cat in categories]
        
        ax.bar(categories, percentages, color=['#e74c3c', '#f39c12', '#3498db'])
        ax.set_ylabel('Percentage (%)', fontsize=12)
        ax.set_title('Anomaly Distribution in Test Dataset', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/anomaly_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved: {output_dir}/anomaly_distribution.png")
        
        # 2. Sensor data time series (sample)
        fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
        
        sample_data = self.test_data.iloc[:1000]  # First 1000 samples
        
        axes[0].plot(sample_data['pressure'], linewidth=0.8, color='#3498db')
        axes[0].set_ylabel('Pressure (bar)', fontsize=10)
        axes[0].grid(alpha=0.3)
        
        axes[1].plot(sample_data['temperature'], linewidth=0.8, color='#e74c3c')
        axes[1].set_ylabel('Temperature (°C)', fontsize=10)
        axes[1].grid(alpha=0.3)
        
        axes[2].plot(sample_data['O2'], linewidth=0.8, color='#2ecc71')
        axes[2].set_ylabel('O₂ (ppm)', fontsize=10)
        axes[2].set_xlabel('Time (minutes)', fontsize=10)
        axes[2].grid(alpha=0.3)
        
        plt.suptitle('Sample Sensor Data Time Series', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(f'{output_dir}/sensor_timeseries.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved: {output_dir}/sensor_timeseries.png")
        
        logger.success("Plots generated")
    
    def generate_latex_tables(self, output_dir: str = 'paper_tables'):
        """Generate LaTeX tables for paper"""
        
        logger.info("Generating LaTeX tables...")
        os.makedirs(output_dir, exist_ok=True)
        
        # Performance comparison table
        with open(f'{output_dir}/performance_table.tex', 'w') as f:
            f.write("\\begin{table}[h]\n")
            f.write("\\centering\n")
            f.write("\\caption{Model Performance Comparison}\n")
            f.write("\\begin{tabular}{lcccc}\n")
            f.write("\\hline\n")
            f.write("Model & Accuracy & Precision & Recall & F1-Score \\\\\n")
            f.write("\\hline\n")
            
            for model_name, data in self.results.items():
                if 'performance' in data:
                    perf = data['performance']
                    f.write(f"{model_name} & ")
                    f.write(f"{perf['accuracy']:.3f} & ")
                    f.write(f"{perf['precision']:.3f} & ")
                    f.write(f"{perf['recall']:.3f} & ")
                    f.write(f"{perf['f1_score']:.3f} \\\\\n")
            
            f.write("\\hline\n")
            f.write("\\end{tabular}\n")
            f.write("\\end{table}\n")
        
        logger.info(f"Saved: {output_dir}/performance_table.tex")
        logger.success("LaTeX tables generated")
    
    def save_results(self, output_path: str = 'paper_results.json'):
        """Save all results to JSON"""
        
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.success(f"Results saved to {output_path}")
    
    def generate_paper_report(self, output_path: str = 'paper_evaluation_report.txt'):
        """Generate comprehensive text report"""
        
        with open(output_path, 'w') as f:
            f.write("="*70 + "\n")
            f.write("PREDBLOCK EVALUATION REPORT FOR PUBLICATION\n")
            f.write("="*70 + "\n\n")
            
            # Data quality
            f.write("1. DATASET VALIDATION\n")
            f.write("-" * 70 + "\n")
            dq = self.results['data_quality']
            f.write(f"Dataset size: {dq['dataset_size']} samples\n")
            f.write(f"Temporal coverage: {dq['temporal_coverage_days']:.1f} days\n")
            f.write(f"Total anomaly rate: {dq['total_anomaly_rate']:.2f}%\n\n")
            
            f.write("Anomaly Distribution:\n")
            for anom_type, data in dq['anomaly_distribution'].items():
                f.write(f"  {anom_type}: {data['count']} ({data['percentage']:.2f}%)\n")
            
            f.write("\nTemporal Autocorrelation:\n")
            for var, corr in dq['autocorrelation'].items():
                f.write(f"  {var}: {corr:.4f}\n")
            
            # Model performance
            f.write("\n\n2. MODEL PERFORMANCE\n")
            f.write("-" * 70 + "\n")
            
            for model_name, data in self.results.items():
                if 'performance' in data:
                    f.write(f"\n{model_name}:\n")
                    perf = data['performance']
                    f.write(f"  Accuracy: {perf['accuracy']:.4f}\n")
                    f.write(f"  Precision: {perf['precision']:.4f}\n")
                    f.write(f"  Recall: {perf['recall']:.4f}\n")
                    f.write(f"  F1-Score: {perf['f1_score']:.4f}\n")
                    if perf.get('auc_roc'):
                        f.write(f"  AUC-ROC: {perf['auc_roc']:.4f}\n")
                    f.write(f"  Inference time: {perf['inference_time_ms']:.2f} ms/sample\n")
            
            f.write("\n" + "="*70 + "\n")
            f.write("Report generated successfully!\n")
        
        logger.success(f"Report saved to {output_path}")


def main():
    """Main evaluation function"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Evaluate PredBlock for research paper')
    parser.add_argument('--test-data', type=str, default='data/test_physics.csv',
                       help='Path to test dataset')
    parser.add_argument('--output-dir', type=str, default='paper_evaluation',
                       help='Output directory for results')
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Initialize evaluator
    evaluator = PaperEvaluator(args.test_data)
    
    # 1. Evaluate data quality
    evaluator.evaluate_data_quality()
    
    # 2. Generate plots
    evaluator.generate_plots(f'{args.output_dir}/figures')
    
    # 3. Generate LaTeX tables
    evaluator.generate_latex_tables(f'{args.output_dir}/tables')
    
    # 4. Save results
    evaluator.save_results(f'{args.output_dir}/results.json')
    
    # 5. Generate report
    evaluator.generate_paper_report(f'{args.output_dir}/evaluation_report.txt')
    
    print("\n" + "="*70)
    print("✓ EVALUATION COMPLETE")
    print("="*70)
    print(f"\nResults saved to: {args.output_dir}/")
    print(f"  - Figures: {args.output_dir}/figures/")
    print(f"  - Tables: {args.output_dir}/tables/")
    print(f"  - JSON: {args.output_dir}/results.json")
    print(f"  - Report: {args.output_dir}/evaluation_report.txt")


if __name__ == "__main__":
    main()
