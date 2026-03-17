"""
System Evaluation Script
Evaluates AI models and blockchain performance
"""

import pandas as pd
import numpy as np
import time
import json
from typing import Dict, List
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve

from ai_layer.models.impurity_tracker import ImpurityTracker
from ai_layer.models.corrosion_predictor import CorrosionPredictor
from ai_layer.models.leakage_detector import LeakageDetector
from blockchain_layer.blockchain_interface import BlockchainInterface


class SystemEvaluator:
    """Evaluate PredBlock system performance"""
    
    def __init__(self):
        """Initialize evaluator"""
        self.results = {
            'ai_metrics': {},
            'blockchain_metrics': {},
            'comparison': {}
        }
    
    def evaluate_ai_models(self, test_data_path: str):
        """Evaluate all AI models"""
        
        print("="*60)
        print("AI Model Evaluation")
        print("="*60)
        
        # Load test data
        data = pd.read_csv(test_data_path)
        print(f"\nLoaded {len(data)} test samples")
        
        # Evaluate Impurity Tracker
        print("\n--- Impurity Tracker ---")
        tracker = ImpurityTracker()
        tracker.load_model()
        
        X, y_true = tracker.prepare_data(data)
        y_pred = tracker.predict(data)
        y_pred_proba = tracker.predict_proba(data)
        
        self.results['ai_metrics']['impurity_tracker'] = {
            'classification_report': classification_report(y_true, y_pred, output_dict=True),
            'confusion_matrix': confusion_matrix(y_true, y_pred).tolist(),
            'roc_auc': roc_auc_score(y_true, y_pred_proba)
        }
        
        print(classification_report(y_true, y_pred))
        print(f"ROC-AUC: {self.results['ai_metrics']['impurity_tracker']['roc_auc']:.4f}")
        
        # Evaluate Leakage Detector
        print("\n--- Leakage Detector ---")
        detector = LeakageDetector()
        detector.load_model()
        
        y_pred = detector.predict(data)
        anomaly_scores = detector.predict_anomaly_score(data)
        
        if 'leakage_risk' in data.columns:
            y_true = data['leakage_risk'].values
            
            self.results['ai_metrics']['leakage_detector'] = {
                'classification_report': classification_report(y_true, y_pred, output_dict=True),
                'confusion_matrix': confusion_matrix(y_true, y_pred).tolist(),
                'roc_auc': roc_auc_score(y_true, anomaly_scores)
            }
            
            print(classification_report(y_true, y_pred))
            print(f"ROC-AUC: {self.results['ai_metrics']['leakage_detector']['roc_auc']:.4f}")
    
    def evaluate_blockchain_performance(self, n_transactions: int = 100):
        """Evaluate blockchain performance metrics"""
        
        print("\n" + "="*60)
        print("Blockchain Performance Evaluation")
        print("="*60)
        
        blockchain = BlockchainInterface()
        
        latencies = []
        gas_costs = []
        
        print(f"\nSending {n_transactions} test transactions...")
        
        for i in range(n_transactions):
            # Simulate monitoring record
            start_time = time.time()
            
            try:
                tx_hash = blockchain.add_monitoring_record(
                    pressure=75.0 + np.random.normal(0, 2),
                    temperature=25.0 + np.random.normal(0, 3),
                    flow_rate=50.0 + np.random.normal(0, 5),
                    h2o=30.0,
                    h2s=5.0,
                    so2=20.0,
                    o2=8.0,
                    nox=30.0,
                    sensor_id=f"test_sensor_{i}"
                )
                
                latency = time.time() - start_time
                latencies.append(latency)
                
                # Get gas cost
                gas_used = blockchain.get_gas_used(tx_hash)
                gas_costs.append(gas_used)
                
                if (i + 1) % 10 == 0:
                    print(f"  Completed {i + 1}/{n_transactions} transactions")
            
            except Exception as e:
                print(f"  Error in transaction {i}: {e}")
        
        # Calculate metrics
        self.results['blockchain_metrics'] = {
            'latency': {
                'mean': np.mean(latencies),
                'std': np.std(latencies),
                'min': np.min(latencies),
                'max': np.max(latencies)
            },
            'gas_cost': {
                'mean': np.mean(gas_costs),
                'std': np.std(gas_costs),
                'min': int(np.min(gas_costs)),
                'max': int(np.max(gas_costs))
            },
            'throughput': n_transactions / sum(latencies)
        }
        
        print(f"\nLatency: {self.results['blockchain_metrics']['latency']['mean']:.3f}s "
              f"± {self.results['blockchain_metrics']['latency']['std']:.3f}s")
        print(f"Gas Cost: {self.results['blockchain_metrics']['gas_cost']['mean']:.0f} "
              f"± {self.results['blockchain_metrics']['gas_cost']['std']:.0f}")
        print(f"Throughput: {self.results['blockchain_metrics']['throughput']:.2f} tx/s")
    
    def compare_with_without_integration(self, test_data_path: str):
        """Compare system performance with and without AI-Blockchain integration"""
        
        print("\n" + "="*60)
        print("Integration Comparison")
        print("="*60)
        
        data = pd.read_csv(test_data_path)
        
        # Without integration: Simple threshold-based detection
        print("\n--- Without AI-Blockchain Integration ---")
        
        # Simple threshold detection
        simple_alerts = (
            (data['H2O'] > 100) |
            (data['H2S'] > 20) |
            (data['SO2'] > 100) |
            (data['O2'] > 15) |
            (data['pressure'] > 90)
        ).astype(int)
        
        # With integration: AI-based detection
        print("\n--- With AI-Blockchain Integration ---")
        
        tracker = ImpurityTracker()
        tracker.load_model()
        ai_alerts = tracker.predict(data)
        
        # Compare
        if 'leakage_risk' in data.columns or 'corrosion_risk' in data.columns:
            # Create combined ground truth
            y_true = np.maximum(
                data.get('leakage_risk', 0).values,
                data.get('corrosion_risk', 0).values
            )
            
            # Metrics for simple approach
            simple_metrics = {
                'accuracy': (simple_alerts == y_true).mean(),
                'precision': classification_report(y_true, simple_alerts, output_dict=True)['1']['precision'],
                'recall': classification_report(y_true, simple_alerts, output_dict=True)['1']['recall'],
                'f1_score': classification_report(y_true, simple_alerts, output_dict=True)['1']['f1-score']
            }
            
            # Metrics for AI approach
            ai_metrics = {
                'accuracy': (ai_alerts == y_true).mean(),
                'precision': classification_report(y_true, ai_alerts, output_dict=True)['1']['precision'],
                'recall': classification_report(y_true, ai_alerts, output_dict=True)['1']['recall'],
                'f1_score': classification_report(y_true, ai_alerts, output_dict=True)['1']['f1-score']
            }
            
            self.results['comparison'] = {
                'without_integration': simple_metrics,
                'with_integration': ai_metrics,
                'improvement': {
                    'accuracy': ai_metrics['accuracy'] - simple_metrics['accuracy'],
                    'precision': ai_metrics['precision'] - simple_metrics['precision'],
                    'recall': ai_metrics['recall'] - simple_metrics['recall'],
                    'f1_score': ai_metrics['f1_score'] - simple_metrics['f1_score']
                }
            }
            
            print("\nSimple Threshold Approach:")
            for metric, value in simple_metrics.items():
                print(f"  {metric}: {value:.4f}")
            
            print("\nAI-Blockchain Approach:")
            for metric, value in ai_metrics.items():
                print(f"  {metric}: {value:.4f}")
            
            print("\nImprovement:")
            for metric, value in self.results['comparison']['improvement'].items():
                print(f"  {metric}: {value:+.4f}")
    
    def save_results(self, output_path: str = "evaluation_results.json"):
        """Save evaluation results"""
        
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n✓ Results saved to {output_path}")
    
    def plot_results(self):
        """Plot evaluation results"""
        
        # Create comparison plot
        if 'comparison' in self.results and self.results['comparison']:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            metrics = ['accuracy', 'precision', 'recall', 'f1_score']
            without = [self.results['comparison']['without_integration'][m] for m in metrics]
            with_int = [self.results['comparison']['with_integration'][m] for m in metrics]
            
            x = np.arange(len(metrics))
            width = 0.35
            
            ax.bar(x - width/2, without, width, label='Without Integration')
            ax.bar(x + width/2, with_int, width, label='With AI-Blockchain')
            
            ax.set_ylabel('Score')
            ax.set_title('Performance Comparison')
            ax.set_xticks(x)
            ax.set_xticklabels(metrics)
            ax.legend()
            ax.grid(axis='y', alpha=0.3)
            
            plt.tight_layout()
            plt.savefig('comparison_plot.png', dpi=300)
            print("✓ Comparison plot saved to comparison_plot.png")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Evaluate PredBlock system')
    parser.add_argument('--test-data', type=str, default='data/simulated_pipeline_data.csv',
                       help='Path to test data')
    parser.add_argument('--blockchain-test', action='store_true',
                       help='Run blockchain performance test')
    parser.add_argument('--n-transactions', type=int, default=100,
                       help='Number of transactions for blockchain test')
    
    args = parser.parse_args()
    
    evaluator = SystemEvaluator()
    
    # Evaluate AI models
    evaluator.evaluate_ai_models(args.test_data)
    
    # Evaluate blockchain (if enabled)
    if args.blockchain_test:
        evaluator.evaluate_blockchain_performance(args.n_transactions)
    
    # Compare approaches
    evaluator.compare_with_without_integration(args.test_data)
    
    # Save and plot results
    evaluator.save_results()
    evaluator.plot_results()
