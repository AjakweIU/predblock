"""
Real-time Monitoring System
Integrates AI predictions with blockchain logging
"""

import time
import pandas as pd
import numpy as np
from datetime import datetime
import yaml
from typing import Dict, List
import joblib

from ai_layer.models.impurity_tracker import ImpurityTracker
from ai_layer.models.corrosion_predictor import CorrosionPredictor
from ai_layer.models.leakage_detector import LeakageDetector
from ai_layer.models.overpressure_controller import OverpressureController
from blockchain_layer.blockchain_interface import BlockchainInterface


class MonitoringSystem:
    """Real-time monitoring system combining AI and blockchain"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize monitoring system"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        print("Initializing PredBlock Monitoring System...")
        
        # Load AI models
        self.impurity_tracker = ImpurityTracker()
        self.corrosion_predictor = CorrosionPredictor()
        self.leakage_detector = LeakageDetector()
        self.overpressure_controller = OverpressureController()
        
        try:
            self.impurity_tracker.load_model()
            self.corrosion_predictor.load_model()
            self.leakage_detector.load_model()
            self.overpressure_controller.load_model()
            print("✓ AI models loaded successfully")
        except Exception as e:
            print(f"⚠ Warning: Could not load all models - {e}")
        
        # Initialize blockchain interface
        try:
            self.blockchain = BlockchainInterface()
            print("✓ Blockchain interface initialized")
        except Exception as e:
            print(f"⚠ Warning: Blockchain not connected - {e}")
            self.blockchain = None
        
        self.running = False
    
    def process_sensor_data(self, sensor_data: Dict) -> Dict:
        """Process sensor data through AI models"""
        
        # Convert to DataFrame
        df = pd.DataFrame([sensor_data])
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'sensor_id': sensor_data.get('sensor_id', 'unknown'),
            'raw_data': sensor_data,
            'predictions': {},
            'alerts': []
        }
        
        # Impurity tracking
        try:
            impurity_alert = self.impurity_tracker.predict(df)[0]
            impurity_prob = self.impurity_tracker.predict_proba(df)[0]
            
            results['predictions']['impurity_alert'] = bool(impurity_alert)
            results['predictions']['impurity_probability'] = float(impurity_prob)
            
            if impurity_alert:
                results['alerts'].append({
                    'type': 'IMPURITY',
                    'level': 'CRITICAL' if impurity_prob > 0.8 else 'WARNING',
                    'message': f'Impurity levels exceeded threshold (prob: {impurity_prob:.2f})'
                })
        except Exception as e:
            print(f"Impurity tracking error: {e}")
        
        # Leakage detection
        try:
            leakage_alert = self.leakage_detector.predict(df)[0]
            anomaly_score = self.leakage_detector.predict_anomaly_score(df)[0]
            
            results['predictions']['leakage_alert'] = bool(leakage_alert)
            results['predictions']['anomaly_score'] = float(anomaly_score)
            
            if leakage_alert:
                results['alerts'].append({
                    'type': 'LEAKAGE',
                    'level': 'CRITICAL',
                    'message': f'Potential leakage detected (score: {anomaly_score:.2f})'
                })
        except Exception as e:
            print(f"Leakage detection error: {e}")
        
        # Overpressure check
        pressure = sensor_data.get('pressure', 0)
        if pressure > self.config['pipeline']['alert_pressure']:
            level = 'CRITICAL' if pressure > self.config['pipeline']['critical_pressure'] else 'WARNING'
            results['alerts'].append({
                'type': 'OVERPRESSURE',
                'level': level,
                'message': f'Pressure {pressure} bar exceeds threshold'
            })
        
        return results
    
    def log_to_blockchain(self, sensor_data: Dict, predictions: Dict):
        """Log data and predictions to blockchain"""
        
        if self.blockchain is None:
            return
        
        try:
            # Log monitoring record
            tx_hash = self.blockchain.add_monitoring_record(
                pressure=sensor_data['pressure'],
                temperature=sensor_data['temperature'],
                flow_rate=sensor_data['flow_rate'],
                h2o=sensor_data['H2O'],
                h2s=sensor_data['H2S'],
                so2=sensor_data['SO2'],
                o2=sensor_data['O2'],
                nox=sensor_data['NOx'],
                sensor_id=sensor_data.get('sensor_id', 'sensor_1')
            )
            
            print(f"✓ Logged to blockchain: {tx_hash}")
            
            # Trigger alerts if needed
            for alert in predictions.get('alerts', []):
                if alert['level'] == 'CRITICAL':
                    alert_type = {'IMPURITY': 0, 'OVERPRESSURE': 1, 'LEAKAGE': 2, 'CORROSION': 3}
                    
                    self.blockchain.trigger_alert(
                        alert_type=alert_type.get(alert['type'], 0),
                        sensor_id=sensor_data.get('sensor_id', 'sensor_1'),
                        description=alert['message'],
                        value=sensor_data.get('pressure', 0)
                    )
        
        except Exception as e:
            print(f"Blockchain logging error: {e}")
    
    def start(self, data_source: str = None, interval: int = 60):
        """Start monitoring system"""
        
        print("\n" + "="*60)
        print("PredBlock Monitoring System Started")
        print("="*60)
        
        self.running = True
        
        # If data source provided, use it; otherwise simulate
        if data_source:
            data = pd.read_csv(data_source)
            print(f"Monitoring {len(data)} records from {data_source}")
            
            for idx, row in data.iterrows():
                if not self.running:
                    break
                
                sensor_data = row.to_dict()
                results = self.process_sensor_data(sensor_data)
                
                # Display results
                self.display_results(results)
                
                # Log to blockchain
                self.log_to_blockchain(sensor_data, results)
                
                time.sleep(interval)
        
        else:
            # Simulate real-time monitoring
            print("Running in simulation mode...")
            
            from ai_layer.data_simulator import PipelineDataSimulator
            simulator = PipelineDataSimulator()
            
            while self.running:
                # Generate one sample
                sample = simulator.generate_normal_data(1)
                sensor_data = sample.iloc[0].to_dict()
                sensor_data['sensor_id'] = 'sensor_sim_1'
                
                results = self.process_sensor_data(sensor_data)
                self.display_results(results)
                
                time.sleep(interval)
    
    def display_results(self, results: Dict):
        """Display monitoring results"""
        
        print(f"\n[{results['timestamp']}] Sensor: {results['sensor_id']}")
        print("-" * 60)
        
        # Display key metrics
        raw = results['raw_data']
        print(f"Pressure: {raw.get('pressure', 0):.2f} bar | "
              f"Temp: {raw.get('temperature', 0):.2f}°C | "
              f"Flow: {raw.get('flow_rate', 0):.2f} kg/s")
        
        print(f"H₂O: {raw.get('H2O', 0):.1f} ppm | "
              f"H₂S: {raw.get('H2S', 0):.1f} ppm | "
              f"SO₂: {raw.get('SO2', 0):.1f} ppm | "
              f"O₂: {raw.get('O2', 0):.1f} ppm")
        
        # Display predictions
        preds = results['predictions']
        if preds:
            print("\nAI Predictions:")
            for key, value in preds.items():
                print(f"  • {key}: {value}")
        
        # Display alerts
        if results['alerts']:
            print("\n⚠ ALERTS:")
            for alert in results['alerts']:
                symbol = "🔴" if alert['level'] == 'CRITICAL' else "🟡"
                print(f"  {symbol} [{alert['level']}] {alert['type']}: {alert['message']}")
        else:
            print("\n✓ All systems normal")
    
    def stop(self):
        """Stop monitoring system"""
        self.running = False
        print("\nMonitoring system stopped")


if __name__ == "__main__":
    system = MonitoringSystem()
    
    try:
        system.start(interval=5)  # Check every 5 seconds in demo
    except KeyboardInterrupt:
        system.stop()
