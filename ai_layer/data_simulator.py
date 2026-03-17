"""
Data Simulator for CCS Pipeline Monitoring
Generates synthetic sensor data for training and testing
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import yaml


class PipelineDataSimulator:
    """Simulates realistic CCS pipeline sensor data"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize simulator with configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.pipeline_config = self.config['pipeline']
        self.impurity_config = self.config['impurities']
        self.sim_config = self.config['simulation']
    
    def generate_normal_data(self, n_samples: int) -> pd.DataFrame:
        """Generate normal operating condition data"""
        
        # Time series
        start_time = datetime.now()
        timestamps = [start_time + timedelta(seconds=i*self.sim_config['sampling_interval_seconds']) 
                     for i in range(n_samples)]
        
        # Pressure (bar) - normal around 75 bar with small variations
        pressure = np.random.normal(
            self.pipeline_config['normal_pressure'], 
            2, 
            n_samples
        )
        
        # Temperature (°C) - normal around 25°C
        temperature = np.random.normal(
            self.pipeline_config['normal_temperature'], 
            3, 
            n_samples
        )
        
        # Flow rate (kg/s)
        flow_rate = np.random.uniform(
            self.pipeline_config['flow_rate_min'],
            self.pipeline_config['flow_rate_max'],
            n_samples
        )
        
        # Impurities (ppmv or mol%)
        H2O = np.random.uniform(0, self.impurity_config['H2O']['normal_max'], n_samples)
        H2S = np.random.uniform(0, self.impurity_config['H2S']['normal_max'], n_samples)
        SO2 = np.random.uniform(0, self.impurity_config['SO2']['normal_max'], n_samples)
        O2 = np.random.uniform(0, self.impurity_config['O2']['normal_max'], n_samples)
        NOx = np.random.uniform(0, self.impurity_config['NOx']['normal_max'], n_samples)
        N2 = np.random.uniform(0, self.impurity_config['N2']['normal_max'], n_samples)
        CH4 = np.random.uniform(0, self.impurity_config['CH4']['normal_max'], n_samples)
        
        # Acoustic emissions and vibration (arbitrary units)
        acoustic_emission = np.random.normal(50, 5, n_samples)
        vibration = np.random.normal(10, 2, n_samples)
        
        # Create DataFrame
        data = pd.DataFrame({
            'timestamp': timestamps,
            'pressure': pressure,
            'temperature': temperature,
            'flow_rate': flow_rate,
            'H2O': H2O,
            'H2S': H2S,
            'SO2': SO2,
            'O2': O2,
            'NOx': NOx,
            'N2': N2,
            'CH4': CH4,
            'acoustic_emission': acoustic_emission,
            'vibration': vibration,
            'leakage_risk': 0,  # Normal condition
            'corrosion_risk': 0,
            'overpressure_risk': 0
        })
        
        return data
    
    def inject_anomalies(self, data: pd.DataFrame, anomaly_prob: float = 0.05) -> pd.DataFrame:
        """Inject realistic anomalies into the data"""
        
        n_samples = len(data)
        data = data.copy()
        
        # Determine anomaly indices
        n_anomalies = int(n_samples * anomaly_prob)
        anomaly_indices = np.random.choice(n_samples, n_anomalies, replace=False)
        
        for idx in anomaly_indices:
            anomaly_type = np.random.choice(['leakage', 'corrosion', 'overpressure'])
            
            if anomaly_type == 'leakage':
                # Leakage: increased O2, pressure drop, acoustic emission spike
                data.loc[idx, 'O2'] = np.random.uniform(
                    self.impurity_config['O2']['alert'],
                    self.impurity_config['O2']['critical']
                )
                data.loc[idx, 'pressure'] -= np.random.uniform(5, 15)
                data.loc[idx, 'acoustic_emission'] += np.random.uniform(20, 50)
                data.loc[idx, 'vibration'] += np.random.uniform(5, 15)
                data.loc[idx, 'leakage_risk'] = 1
                
            elif anomaly_type == 'corrosion':
                # Corrosion: high H2O, H2S, SO2
                data.loc[idx, 'H2O'] = np.random.uniform(
                    self.impurity_config['H2O']['alert'],
                    self.impurity_config['H2O']['critical']
                )
                data.loc[idx, 'H2S'] = np.random.uniform(
                    self.impurity_config['H2S']['alert'],
                    self.impurity_config['H2S']['critical']
                )
                data.loc[idx, 'SO2'] = np.random.uniform(
                    self.impurity_config['SO2']['alert'],
                    self.impurity_config['SO2']['critical']
                )
                data.loc[idx, 'corrosion_risk'] = 1
                
            elif anomaly_type == 'overpressure':
                # Overpressure: pressure spike
                data.loc[idx, 'pressure'] = np.random.uniform(
                    self.pipeline_config['alert_pressure'],
                    self.pipeline_config['critical_pressure']
                )
                data.loc[idx, 'temperature'] += np.random.uniform(5, 15)
                data.loc[idx, 'overpressure_risk'] = 1
        
        return data
    
    def generate_dataset(self, 
                        n_samples: int = 10000,
                        anomaly_prob: float = 0.05,
                        save_path: str = None) -> pd.DataFrame:
        """Generate complete dataset with normal and anomalous data"""
        
        # Generate normal data
        data = self.generate_normal_data(n_samples)
        
        # Inject anomalies
        data = self.inject_anomalies(data, anomaly_prob)
        
        # Save if path provided
        if save_path:
            data.to_csv(save_path, index=False)
            print(f"Dataset saved to {save_path}")
        
        return data


if __name__ == "__main__":
    # Example usage
    simulator = PipelineDataSimulator()
    dataset = simulator.generate_dataset(
        n_samples=10000,
        anomaly_prob=0.05,
        save_path="data/simulated_pipeline_data.csv"
    )
    print(f"Generated dataset shape: {dataset.shape}")
    print(f"\nDataset info:")
    print(dataset.info())
    print(f"\nSample data:")
    print(dataset.head())
