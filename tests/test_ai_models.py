"""
Unit tests for AI models
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_layer.data_simulator import PipelineDataSimulator
from ai_layer.models.impurity_tracker import ImpurityTracker
from ai_layer.models.leakage_detector import LeakageDetector


class TestDataSimulator(unittest.TestCase):
    """Test data simulator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.simulator = PipelineDataSimulator()
    
    def test_generate_normal_data(self):
        """Test normal data generation"""
        data = self.simulator.generate_normal_data(100)
        
        self.assertEqual(len(data), 100)
        self.assertIn('pressure', data.columns)
        self.assertIn('temperature', data.columns)
        self.assertIn('H2O', data.columns)
        
        # Check pressure is in normal range
        self.assertTrue(data['pressure'].mean() > 70)
        self.assertTrue(data['pressure'].mean() < 80)
    
    def test_inject_anomalies(self):
        """Test anomaly injection"""
        data = self.simulator.generate_normal_data(1000)
        data_with_anomalies = self.simulator.inject_anomalies(data, anomaly_prob=0.1)
        
        # Check that anomalies were injected
        anomaly_count = (
            data_with_anomalies['leakage_risk'].sum() +
            data_with_anomalies['corrosion_risk'].sum() +
            data_with_anomalies['overpressure_risk'].sum()
        )
        
        self.assertGreater(anomaly_count, 0)
        self.assertLess(anomaly_count, len(data) * 0.2)  # Should be around 10%
    
    def test_generate_dataset(self):
        """Test complete dataset generation"""
        data = self.simulator.generate_dataset(n_samples=500, anomaly_prob=0.05)
        
        self.assertEqual(len(data), 500)
        self.assertIn('timestamp', data.columns)
        self.assertIn('leakage_risk', data.columns)


class TestImpurityTracker(unittest.TestCase):
    """Test impurity tracking model"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tracker = ImpurityTracker()
        self.simulator = PipelineDataSimulator()
        self.data = self.simulator.generate_dataset(n_samples=1000, anomaly_prob=0.1)
    
    def test_create_impurity_alert(self):
        """Test impurity alert creation"""
        alerts = self.tracker.create_impurity_alert(self.data)
        
        self.assertEqual(len(alerts), len(self.data))
        self.assertTrue(alerts.isin([0, 1]).all())
    
    def test_prepare_data(self):
        """Test data preparation"""
        X, y = self.tracker.prepare_data(self.data)
        
        self.assertEqual(len(X), len(self.data))
        self.assertEqual(len(y), len(self.data))
        self.assertEqual(len(X.columns), len(self.tracker.features))
    
    def test_train_predict(self):
        """Test training and prediction"""
        # Train
        metrics = self.tracker.train(self.data, test_size=0.3)
        
        self.assertIn('roc_auc', metrics)
        self.assertGreater(metrics['roc_auc'], 0.5)  # Better than random
        
        # Predict
        predictions = self.tracker.predict(self.data.head(10))
        
        self.assertEqual(len(predictions), 10)
        self.assertTrue(np.isin(predictions, [0, 1]).all())


class TestLeakageDetector(unittest.TestCase):
    """Test leakage detection model"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = LeakageDetector()
        self.simulator = PipelineDataSimulator()
        self.data = self.simulator.generate_dataset(n_samples=1000, anomaly_prob=0.1)
    
    def test_prepare_data(self):
        """Test data preparation"""
        X = self.detector.prepare_data(self.data)
        
        self.assertEqual(len(X), len(self.data))
        self.assertEqual(len(X.columns), len(self.detector.features))
    
    def test_train_predict(self):
        """Test training and prediction"""
        # Train
        metrics = self.detector.train(self.data)
        
        self.assertIn('n_anomalies_detected', metrics)
        self.assertGreater(metrics['n_anomalies_detected'], 0)
        
        # Predict
        predictions = self.detector.predict(self.data.head(10))
        anomaly_scores = self.detector.predict_anomaly_score(self.data.head(10))
        
        self.assertEqual(len(predictions), 10)
        self.assertEqual(len(anomaly_scores), 10)
        self.assertTrue(np.isin(predictions, [0, 1]).all())


class TestDataQuality(unittest.TestCase):
    """Test data quality and consistency"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.simulator = PipelineDataSimulator()
    
    def test_no_missing_values(self):
        """Test that generated data has no missing values"""
        data = self.simulator.generate_dataset(n_samples=500)
        
        self.assertEqual(data.isnull().sum().sum(), 0)
    
    def test_value_ranges(self):
        """Test that values are within expected ranges"""
        data = self.simulator.generate_dataset(n_samples=500)
        
        # Pressure should be positive and reasonable
        self.assertTrue((data['pressure'] > 0).all())
        self.assertTrue((data['pressure'] < 150).all())
        
        # Temperature should be reasonable
        self.assertTrue((data['temperature'] > 0).all())
        self.assertTrue((data['temperature'] < 100).all())
        
        # Impurities should be non-negative
        self.assertTrue((data['H2O'] >= 0).all())
        self.assertTrue((data['H2S'] >= 0).all())
        self.assertTrue((data['SO2'] >= 0).all())
        self.assertTrue((data['O2'] >= 0).all())


if __name__ == '__main__':
    unittest.main()
