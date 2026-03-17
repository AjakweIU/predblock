"""
Impurity Tracking Model
Classification/forecasting model to detect abnormal impurity levels
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib
from typing import Dict, Tuple
import yaml


class ImpurityTracker:
    """Random Forest model for impurity anomaly detection"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize impurity tracker"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        model_config = self.config['ai_models']['impurity_tracking']
        self.features = model_config['features']
        self.target = model_config['target']
        
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        
        self.impurity_thresholds = self.config['impurities']
    
    def create_impurity_alert(self, data: pd.DataFrame) -> pd.Series:
        """Create binary alert based on impurity thresholds"""
        
        alert = pd.Series(0, index=data.index)
        
        # Check each impurity against thresholds
        if 'H2O' in data.columns:
            alert |= (data['H2O'] > self.impurity_thresholds['H2O']['alert']).astype(int)
        
        if 'H2S' in data.columns:
            alert |= (data['H2S'] > self.impurity_thresholds['H2S']['alert']).astype(int)
        
        if 'SO2' in data.columns:
            alert |= (data['SO2'] > self.impurity_thresholds['SO2']['alert']).astype(int)
        
        if 'O2' in data.columns:
            alert |= (data['O2'] > self.impurity_thresholds['O2']['alert']).astype(int)
        
        if 'NOx' in data.columns:
            alert |= (data['NOx'] > self.impurity_thresholds['NOx']['alert']).astype(int)
        
        return alert
    
    def prepare_data(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare features and target"""
        
        # Create target if not exists
        if self.target not in data.columns:
            y = self.create_impurity_alert(data)
        else:
            y = data[self.target]
        
        # Select features
        X = data[self.features].copy()
        
        return X, y
    
    def train(self, data: pd.DataFrame, test_size: float = 0.2) -> Dict:
        """Train the impurity tracking model"""
        
        X, y = self.prepare_data(data)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Train model
        print("Training Impurity Tracker...")
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        
        metrics = {
            'classification_report': classification_report(y_test, y_pred),
            'confusion_matrix': confusion_matrix(y_test, y_pred),
            'roc_auc': roc_auc_score(y_test, y_pred_proba),
            'feature_importance': dict(zip(self.features, self.model.feature_importances_))
        }
        
        print("\nClassification Report:")
        print(metrics['classification_report'])
        print(f"\nROC-AUC Score: {metrics['roc_auc']:.4f}")
        
        return metrics
    
    def predict(self, data: pd.DataFrame) -> np.ndarray:
        """Predict impurity alerts"""
        X = data[self.features]
        return self.model.predict(X)
    
    def predict_proba(self, data: pd.DataFrame) -> np.ndarray:
        """Predict probability of impurity alert"""
        X = data[self.features]
        return self.model.predict_proba(X)[:, 1]
    
    def save_model(self, path: str = "models/saved/impurity_tracker.pkl"):
        """Save trained model"""
        joblib.dump(self.model, path)
        print(f"Model saved to {path}")
    
    def load_model(self, path: str = "models/saved/impurity_tracker.pkl"):
        """Load trained model"""
        self.model = joblib.load(path)
        print(f"Model loaded from {path}")


if __name__ == "__main__":
    # Example usage
    from ai_layer.data_simulator import PipelineDataSimulator
    
    # Generate data
    simulator = PipelineDataSimulator()
    data = simulator.generate_dataset(n_samples=10000, anomaly_prob=0.05)
    
    # Train model
    tracker = ImpurityTracker()
    metrics = tracker.train(data)
    
    # Save model
    tracker.save_model()
