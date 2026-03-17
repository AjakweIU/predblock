"""
Leakage Detection Model
Anomaly detection using Isolation Forest for pipeline leakage detection
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib
from typing import Dict, Tuple
import yaml


class LeakageDetector:
    """Isolation Forest model for leakage anomaly detection"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize leakage detector"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        model_config = self.config['ai_models']['leakage_detection']
        self.features = model_config['features']
        self.contamination = model_config['contamination']
        
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=42,
            n_estimators=100,
            max_samples='auto'
        )
        
        self.scaler = StandardScaler()
    
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare features"""
        X = data[self.features].copy()
        return X
    
    def train(self, data: pd.DataFrame) -> Dict:
        """Train the leakage detection model"""
        
        X = self.prepare_data(data)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        print("Training Leakage Detector...")
        self.model.fit(X_scaled)
        
        # Predict on training data for evaluation
        predictions = self.model.predict(X_scaled)
        # Convert to binary: -1 (anomaly) -> 1, 1 (normal) -> 0
        predictions_binary = (predictions == -1).astype(int)
        
        # Get anomaly scores
        anomaly_scores = -self.model.score_samples(X_scaled)
        
        metrics = {
            'n_anomalies_detected': predictions_binary.sum(),
            'anomaly_rate': predictions_binary.mean(),
            'anomaly_scores_mean': anomaly_scores.mean(),
            'anomaly_scores_std': anomaly_scores.std()
        }
        
        # If ground truth available
        if 'leakage_risk' in data.columns:
            y_true = data['leakage_risk'].values
            
            metrics['classification_report'] = classification_report(y_true, predictions_binary)
            metrics['confusion_matrix'] = confusion_matrix(y_true, predictions_binary)
            
            # ROC-AUC using anomaly scores
            try:
                metrics['roc_auc'] = roc_auc_score(y_true, anomaly_scores)
            except:
                metrics['roc_auc'] = None
            
            print("\nClassification Report:")
            print(metrics['classification_report'])
            if metrics['roc_auc']:
                print(f"\nROC-AUC Score: {metrics['roc_auc']:.4f}")
        
        print(f"\nAnomalies detected: {metrics['n_anomalies_detected']} ({metrics['anomaly_rate']*100:.2f}%)")
        
        return metrics
    
    def predict(self, data: pd.DataFrame) -> np.ndarray:
        """Predict leakage anomalies"""
        X = self.prepare_data(data)
        X_scaled = self.scaler.transform(X)
        
        predictions = self.model.predict(X_scaled)
        # Convert to binary: -1 (anomaly) -> 1, 1 (normal) -> 0
        return (predictions == -1).astype(int)
    
    def predict_anomaly_score(self, data: pd.DataFrame) -> np.ndarray:
        """Get anomaly scores (higher = more anomalous)"""
        X = self.prepare_data(data)
        X_scaled = self.scaler.transform(X)
        
        # Negative score_samples gives anomaly score
        return -self.model.score_samples(X_scaled)
    
    def save_model(self, model_path: str = "models/saved/leakage_detector.pkl",
                   scaler_path: str = "models/saved/leakage_scaler.pkl"):
        """Save trained model and scaler"""
        joblib.dump(self.model, model_path)
        joblib.dump(self.scaler, scaler_path)
        print(f"Model saved to {model_path}")
        print(f"Scaler saved to {scaler_path}")
    
    def load_model(self, model_path: str = "models/saved/leakage_detector.pkl",
                   scaler_path: str = "models/saved/leakage_scaler.pkl"):
        """Load trained model and scaler"""
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        print(f"Model loaded from {model_path}")
        print(f"Scaler loaded from {scaler_path}")


if __name__ == "__main__":
    # Example usage
    from ai_layer.data_simulator import PipelineDataSimulator
    
    # Generate data
    simulator = PipelineDataSimulator()
    data = simulator.generate_dataset(n_samples=10000, anomaly_prob=0.05)
    
    # Train model
    detector = LeakageDetector()
    metrics = detector.train(data)
    
    # Save model
    detector.save_model()
