"""
Corrosion Risk Prediction Model
LSTM-based time series model for predicting corrosion risk
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
from typing import Dict, Tuple
import yaml


class CorrosionPredictor:
    """LSTM model for corrosion risk prediction"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize corrosion predictor"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        model_config = self.config['ai_models']['corrosion_prediction']
        self.features = model_config['features']
        self.target = model_config['target']
        self.sequence_length = model_config['sequence_length']
        
        self.model = None
        self.scaler = StandardScaler()
    
    def create_sequences(self, data: np.ndarray, target: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM input"""
        
        X, y = [], []
        
        for i in range(len(data) - self.sequence_length):
            X.append(data[i:i + self.sequence_length])
            y.append(target[i + self.sequence_length])
        
        return np.array(X), np.array(y)
    
    def build_model(self, input_shape: Tuple) -> keras.Model:
        """Build LSTM model architecture"""
        
        model = keras.Sequential([
            layers.LSTM(64, return_sequences=True, input_shape=input_shape),
            layers.Dropout(0.2),
            layers.LSTM(32, return_sequences=False),
            layers.Dropout(0.2),
            layers.Dense(16, activation='relu'),
            layers.Dense(1, activation='sigmoid')  # Binary classification
        ])
        
        model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy', 'AUC']
        )
        
        return model
    
    def prepare_data(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features and target"""
        
        # Select features
        X = data[self.features].values
        
        # Create target if not exists
        if self.target not in data.columns:
            # Use corrosion_risk column or create based on impurities
            if 'corrosion_risk' in data.columns:
                y = data['corrosion_risk'].values
            else:
                # Create based on impurity thresholds
                impurity_config = self.config['impurities']
                y = (
                    (data['H2O'] > impurity_config['H2O']['alert']) |
                    (data['H2S'] > impurity_config['H2S']['alert']) |
                    (data['SO2'] > impurity_config['SO2']['alert'])
                ).astype(int).values
        else:
            y = data[self.target].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Create sequences
        X_seq, y_seq = self.create_sequences(X_scaled, y)
        
        return X_seq, y_seq
    
    def train(self, data: pd.DataFrame, epochs: int = 50, batch_size: int = 32, test_size: float = 0.2) -> Dict:
        """Train the corrosion prediction model"""
        
        X, y = self.prepare_data(data)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        # Build model
        self.model = self.build_model(input_shape=(X_train.shape[1], X_train.shape[2]))
        
        print("Training Corrosion Predictor...")
        print(f"Input shape: {X_train.shape}")
        
        # Train
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_test, y_test),
            epochs=epochs,
            batch_size=batch_size,
            verbose=1,
            callbacks=[
                keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True),
                keras.callbacks.ReduceLROnPlateau(patience=5, factor=0.5)
            ]
        )
        
        # Evaluate
        y_pred = (self.model.predict(X_test) > 0.5).astype(int).flatten()
        y_pred_proba = self.model.predict(X_test).flatten()
        
        from sklearn.metrics import classification_report, roc_auc_score
        
        metrics = {
            'classification_report': classification_report(y_test, y_pred),
            'roc_auc': roc_auc_score(y_test, y_pred_proba),
            'history': history.history
        }
        
        print("\nClassification Report:")
        print(metrics['classification_report'])
        print(f"\nROC-AUC Score: {metrics['roc_auc']:.4f}")
        
        return metrics
    
    def predict(self, data: pd.DataFrame) -> np.ndarray:
        """Predict corrosion risk"""
        X = data[self.features].values
        X_scaled = self.scaler.transform(X)
        
        # Need to create sequences
        if len(X_scaled) < self.sequence_length:
            raise ValueError(f"Data length must be at least {self.sequence_length}")
        
        # Create sequences
        X_seq = []
        for i in range(len(X_scaled) - self.sequence_length + 1):
            X_seq.append(X_scaled[i:i + self.sequence_length])
        
        X_seq = np.array(X_seq)
        predictions = (self.model.predict(X_seq) > 0.5).astype(int).flatten()
        
        return predictions
    
    def save_model(self, model_path: str = "models/saved/corrosion_predictor.h5",
                   scaler_path: str = "models/saved/corrosion_scaler.pkl"):
        """Save trained model and scaler"""
        self.model.save(model_path)
        joblib.dump(self.scaler, scaler_path)
        print(f"Model saved to {model_path}")
        print(f"Scaler saved to {scaler_path}")
    
    def load_model(self, model_path: str = "models/saved/corrosion_predictor.h5",
                   scaler_path: str = "models/saved/corrosion_scaler.pkl"):
        """Load trained model and scaler"""
        self.model = keras.models.load_model(model_path)
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
    predictor = CorrosionPredictor()
    metrics = predictor.train(data, epochs=30)
    
    # Save model
    predictor.save_model()
