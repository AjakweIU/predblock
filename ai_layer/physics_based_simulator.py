"""
Physics-Based CCS Pipeline Data Simulator
Generates realistic pipeline data based on thermodynamic principles and engineering models

References:
- NIST CO2 thermodynamic properties
- IEAGHG Technical Report on CO2 Pipeline Transport
- DNV GL Recommended Practice for CO2 Pipelines
- Corrosion kinetics from NACE standards
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from scipy.interpolate import interp1d, RectBivariateSpline
from scipy.integrate import odeint
import yaml


class CO2Properties:
    """CO2 thermodynamic properties based on NIST data"""
    
    # Pre-computed lookup table from CoolProp (Span-Wagner EOS)
    # Grid: T in [5, 80] °C  x  P in [50, 250] bar
    _spline = None
    _T_min, _T_max = 5.0, 80.0    # °C
    _P_min, _P_max = 50.0, 250.0  # bar
    
    @classmethod
    def _load_spline(cls):
        """Lazy-load the bicubic spline from the pre-computed lookup table."""
        if cls._spline is not None:
            return
        import os
        lookup_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'co2_density_lookup.npz'
        )
        if os.path.exists(lookup_path):
            npz = np.load(lookup_path)
            cls._spline = RectBivariateSpline(
                npz['T_celsius'], npz['P_bar'], npz['rho'], kx=3, ky=3
            )
        else:
            cls._spline = None  # will use fallback
    
    @staticmethod
    def _density_fallback(pressure_bar: float, temperature_celsius: float) -> float:
        """
        Legacy simplified correlation (kept as fallback for out-of-range inputs).
        """
        P = pressure_bar * 1e5  # Pa
        T = temperature_celsius + 273.15  # K
        Tc = 304.13  # K
        Pc = 7.3773e6  # Pa
        Tr = T / Tc
        Pr = P / Pc
        if Tr < 1.0:  # Subcritical
            rho_base = 1000 * (1.5 - 0.5 * Tr)
        else:  # Supercritical
            rho_base = 500 * Pr / Tr
        rho = rho_base * (1 + 0.1 * (Pr - 1))
        return np.clip(rho, 100, 1200)
    
    @classmethod
    def density(cls, pressure_bar: float, temperature_celsius: float) -> float:
        """
        Calculate CO2 density using bicubic-spline interpolation of Span-Wagner
        EOS reference data (pre-computed via CoolProp).
        
        Valid range: P ∈ [50, 250] bar, T ∈ [5, 80] °C.
        Falls back to a simplified correlation outside this range.
        
        Args:
            pressure_bar: Pressure in bar
            temperature_celsius: Temperature in Celsius
            
        Returns:
            Density in kg/m³
        """
        cls._load_spline()
        
        p = float(pressure_bar)
        t = float(temperature_celsius)
        
        if (cls._spline is not None
                and cls._P_min <= p <= cls._P_max
                and cls._T_min <= t <= cls._T_max):
            rho = float(cls._spline(t, p, grid=False))
            return np.clip(rho, 50, 1200)
        
        # Out of range — use legacy fallback
        return cls._density_fallback(p, t)
    
    @staticmethod
    def viscosity(temperature_celsius: float) -> float:
        """
        Calculate CO2 dynamic viscosity
        
        Args:
            temperature_celsius: Temperature in Celsius
            
        Returns:
            Dynamic viscosity in Pa·s
        """
        T = temperature_celsius + 273.15
        
        # Empirical correlation for CO2 viscosity
        mu = 1.48e-6 * np.exp(507.0 / T)
        
        return mu
    
    @staticmethod
    def speed_of_sound(pressure_bar: float, temperature_celsius: float) -> float:
        """
        Calculate speed of sound in CO2
        
        Args:
            pressure_bar: Pressure in bar
            temperature_celsius: Temperature in Celsius
            
        Returns:
            Speed of sound in m/s
        """
        T = temperature_celsius + 273.15
        
        # Simplified correlation
        c = 200 + 2 * temperature_celsius + 0.5 * pressure_bar
        
        return np.clip(c, 200, 400)


class PipelinePhysics:
    """Physical models for pipeline flow and transport"""
    
    def __init__(self, 
                 diameter: float = 0.5,  # m
                 length: float = 100000,  # m (100 km)
                 roughness: float = 4.6e-5):  # m (steel pipe)
        """
        Initialize pipeline physical parameters
        
        Args:
            diameter: Internal diameter in meters
            length: Pipeline length in meters
            roughness: Absolute roughness in meters
        """
        self.diameter = diameter
        self.length = length
        self.roughness = roughness
        self.area = np.pi * (diameter / 2) ** 2
    
    def pressure_drop(self, 
                     flow_rate: float,
                     density: float,
                     viscosity: float,
                     length: float = None) -> float:
        """
        Calculate pressure drop using Darcy-Weisbach equation
        
        Args:
            flow_rate: Mass flow rate in kg/s
            density: Fluid density in kg/m³
            viscosity: Dynamic viscosity in Pa·s
            length: Pipe length in m (uses self.length if None)
            
        Returns:
            Pressure drop in bar
        """
        if length is None:
            length = self.length
        
        # Velocity
        velocity = flow_rate / (density * self.area)
        
        # Reynolds number
        Re = density * velocity * self.diameter / viscosity
        
        # Friction factor (Colebrook-White approximation)
        if Re < 2300:  # Laminar
            f = 64 / Re
        else:  # Turbulent
            # Swamee-Jain approximation
            f = 0.25 / (np.log10(self.roughness / (3.7 * self.diameter) + 5.74 / Re**0.9))**2
        
        # Pressure drop (Darcy-Weisbach)
        dP = f * (length / self.diameter) * (density * velocity**2 / 2)
        
        return dP / 1e5  # Convert Pa to bar
    
    def acoustic_emission_normal(self, flow_rate: float, pressure: float) -> float:
        """
        Calculate normal acoustic emission level
        
        Args:
            flow_rate: Mass flow rate in kg/s
            pressure: Pressure in bar
            
        Returns:
            Acoustic emission in arbitrary units
        """
        # Base level from turbulent flow
        base = 30 + 0.5 * flow_rate + 0.1 * pressure
        
        # Add random fluctuations
        noise = np.random.normal(0, 3)
        
        return base + noise
    
    def acoustic_emission_leak(self, 
                               leak_size: float,
                               pressure: float,
                               distance: float = 10) -> float:
        """
        Calculate acoustic emission from leak
        
        Args:
            leak_size: Leak orifice diameter in mm
            pressure: Pressure in bar
            distance: Distance from sensor in m
            
        Returns:
            Acoustic emission amplitude
        """
        # Leak flow rate (simplified orifice equation)
        leak_velocity = 0.61 * np.sqrt(2 * pressure * 1e5 / 800)  # m/s
        leak_area = np.pi * (leak_size / 2000) ** 2  # m²
        
        # Acoustic power proportional to leak rate
        power = leak_velocity * leak_area * pressure
        
        # Attenuation with distance
        amplitude = 100 * power / (distance ** 1.5)
        
        return amplitude


class CorrosionKinetics:
    """Corrosion rate models based on impurity concentrations"""
    
    @staticmethod
    def corrosion_rate(h2o: float, 
                       h2s: float, 
                       so2: float,
                       temperature: float,
                       time_hours: float = 1.0) -> float:
        """
        Calculate corrosion rate using electrochemical kinetics
        
        Based on NACE standards and literature:
        - Water enables electrochemical corrosion
        - H2S and SO2 accelerate corrosion
        - Temperature increases reaction rates
        
        Args:
            h2o: Water content in ppmv
            h2s: H2S content in ppmv
            so2: SO2 content in ppmv
            temperature: Temperature in Celsius
            time_hours: Exposure time in hours
            
        Returns:
            Cumulative corrosion depth in micrometers
        """
        # Base corrosion rate (μm/year)
        if h2o < 50:
            base_rate = 0.1  # Negligible
        elif h2o < 100:
            base_rate = 1.0  # Low
        elif h2o < 500:
            base_rate = 10.0  # Moderate
        else:
            base_rate = 50.0  # High
        
        # H2S acceleration factor
        h2s_factor = 1.0 + (h2s / 10) ** 1.5
        
        # SO2 acceleration factor
        so2_factor = 1.0 + (so2 / 50) ** 1.2
        
        # Temperature factor (Arrhenius-type)
        temp_factor = np.exp(0.05 * (temperature - 25))
        
        # Total corrosion rate
        rate = base_rate * h2s_factor * so2_factor * temp_factor
        
        # Cumulative corrosion over time
        corrosion_depth = rate * (time_hours / 8760)  # Convert to hours
        
        return corrosion_depth


class PhysicsBasedSimulator:
    """
    Enhanced physics-based simulator for CCS pipeline monitoring
    Generates realistic data grounded in thermodynamic and engineering principles
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize simulator with physical models"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.pipeline_config = self.config['pipeline']
        self.impurity_config = self.config['impurities']
        self.sim_config = self.config['simulation']
        
        # Initialize physical models
        self.co2_props = CO2Properties()
        self.pipeline = PipelinePhysics(diameter=0.5, length=100000)
        self.corrosion = CorrosionKinetics()
        
        # Operating point
        self.base_pressure = self.pipeline_config['normal_pressure']
        self.base_temperature = self.pipeline_config['normal_temperature']
        self.base_flow_rate = 50.0  # kg/s
        
        # Cumulative corrosion tracker
        self.cumulative_corrosion = 0.0
    
    def generate_normal_operation(self, n_samples: int) -> pd.DataFrame:
        """
        Generate data for normal operating conditions with realistic physics
        
        Args:
            n_samples: Number of time samples
            
        Returns:
            DataFrame with realistic pipeline data
        """
        # Time series
        start_time = datetime.now()
        dt = self.sim_config['sampling_interval_seconds']
        timestamps = [start_time + timedelta(seconds=i*dt) for i in range(n_samples)]
        
        # Initialize arrays
        data = {
            'timestamp': timestamps,
            'pressure': np.zeros(n_samples),
            'temperature': np.zeros(n_samples),
            'flow_rate': np.zeros(n_samples),
            'H2O': np.zeros(n_samples),
            'H2S': np.zeros(n_samples),
            'SO2': np.zeros(n_samples),
            'O2': np.zeros(n_samples),
            'NOx': np.zeros(n_samples),
            'N2': np.zeros(n_samples),
            'CH4': np.zeros(n_samples),
            'acoustic_emission': np.zeros(n_samples),
            'vibration': np.zeros(n_samples),
            'density': np.zeros(n_samples),
            'corrosion_depth': np.zeros(n_samples),
            'leakage_risk': np.zeros(n_samples, dtype=int),
            'corrosion_risk': np.zeros(n_samples, dtype=int),
            'overpressure_risk': np.zeros(n_samples, dtype=int)
        }
        
        # Generate with temporal correlations
        for i in range(n_samples):
            # Flow rate with slow variations (operational changes)
            if i == 0:
                flow = self.base_flow_rate
            else:
                # Autoregressive process
                flow = 0.95 * data['flow_rate'][i-1] + 0.05 * self.base_flow_rate
                flow += np.random.normal(0, 1)
            
            data['flow_rate'][i] = np.clip(flow, 30, 80)
            
            # Temperature with diurnal variation
            hour_of_day = (i * dt / 3600) % 24
            diurnal = 3 * np.sin(2 * np.pi * hour_of_day / 24)
            temp = self.base_temperature + diurnal + np.random.normal(0, 0.5)
            data['temperature'][i] = temp
            
            # Pressure based on flow (physics-based)
            density = self.co2_props.density(self.base_pressure, temp)
            viscosity = self.co2_props.viscosity(temp)
            
            # Pressure drop along pipeline
            dp = self.pipeline.pressure_drop(data['flow_rate'][i], density, viscosity)
            
            # Inlet pressure to maintain flow
            pressure = self.base_pressure + 0.1 * (data['flow_rate'][i] - self.base_flow_rate)
            pressure += np.random.normal(0, 0.3)  # Sensor noise
            
            data['pressure'][i] = pressure
            data['density'][i] = self.co2_props.density(pressure, temp)
            
            # Impurities - realistic levels with slow drift
            if i == 0:
                data['H2O'][i] = np.random.uniform(10, 40)
                data['H2S'][i] = np.random.uniform(1, 8)
                data['SO2'][i] = np.random.uniform(5, 30)
                data['O2'][i] = np.random.uniform(1, 8)
                data['NOx'][i] = np.random.uniform(10, 40)
            else:
                # Slow drift with measurement noise
                data['H2O'][i] = 0.98 * data['H2O'][i-1] + np.random.normal(0, 2)
                data['H2S'][i] = 0.98 * data['H2S'][i-1] + np.random.normal(0, 0.5)
                data['SO2'][i] = 0.98 * data['SO2'][i-1] + np.random.normal(0, 1)
                data['O2'][i] = 0.98 * data['O2'][i-1] + np.random.normal(0, 0.5)
                data['NOx'][i] = 0.98 * data['NOx'][i-1] + np.random.normal(0, 1)
            
            # Clip to realistic ranges
            data['H2O'][i] = np.clip(data['H2O'][i], 5, 50)
            data['H2S'][i] = np.clip(data['H2S'][i], 0.5, 10)
            data['SO2'][i] = np.clip(data['SO2'][i], 2, 50)
            data['O2'][i] = np.clip(data['O2'][i], 0.5, 10)
            data['NOx'][i] = np.clip(data['NOx'][i], 5, 50)
            
            # Inert gases
            data['N2'][i] = np.random.uniform(1, 3)
            data['CH4'][i] = np.random.uniform(0.5, 1.5)
            
            # Acoustic emission (physics-based)
            data['acoustic_emission'][i] = self.pipeline.acoustic_emission_normal(
                data['flow_rate'][i], 
                pressure
            )
            
            # Vibration (correlated with flow)
            data['vibration'][i] = 8 + 0.1 * data['flow_rate'][i] + np.random.normal(0, 1)
            
            # Cumulative corrosion
            corr_rate = self.corrosion.corrosion_rate(
                data['H2O'][i],
                data['H2S'][i],
                data['SO2'][i],
                temp,
                time_hours=dt/3600
            )
            self.cumulative_corrosion += corr_rate
            data['corrosion_depth'][i] = self.cumulative_corrosion
        
        return pd.DataFrame(data)
    
    def inject_leakage_event(self, 
                            data: pd.DataFrame,
                            start_idx: int,
                            duration: int = 50,
                            leak_size_mm: float = 5.0) -> pd.DataFrame:
        """
        Inject realistic leakage event with physics-based signatures
        
        Args:
            data: DataFrame to modify
            start_idx: Starting index for leak
            duration: Duration in samples
            leak_size_mm: Leak orifice diameter in mm
            
        Returns:
            Modified DataFrame
        """
        data = data.copy()
        
        for i in range(start_idx, min(start_idx + duration, len(data))):
            # Pressure drop (proportional to leak size)
            leak_flow_loss = 0.1 * leak_size_mm  # kg/s
            pressure_drop = 2 * leak_size_mm  # bar
            
            data.loc[i, 'pressure'] -= pressure_drop * (1 - 0.5 * (i - start_idx) / duration)
            data.loc[i, 'flow_rate'] -= leak_flow_loss
            
            # O2 ingress (air leaking in)
            o2_increase = 5 + 2 * leak_size_mm
            data.loc[i, 'O2'] += o2_increase
            
            # Acoustic signature
            leak_acoustic = self.pipeline.acoustic_emission_leak(
                leak_size_mm,
                data.loc[i, 'pressure'],
                distance=10
            )
            data.loc[i, 'acoustic_emission'] += leak_acoustic
            
            # Vibration increase
            data.loc[i, 'vibration'] += 5 + np.random.normal(0, 2)
            
            # Mark as leakage risk
            data.loc[i, 'leakage_risk'] = 1
        
        return data
    
    def inject_corrosion_event(self,
                               data: pd.DataFrame,
                               start_idx: int,
                               duration: int = 250) -> pd.DataFrame:
        """
        Inject gradual corrosion event with realistic chemistry
        
        Args:
            data: DataFrame to modify
            start_idx: Starting index
            duration: Duration in samples (increased to 250 for longer events)
            
        Returns:
            Modified DataFrame
        """
        data = data.copy()
        
        for i in range(start_idx, min(start_idx + duration, len(data))):
            progress = (i - start_idx) / duration
            
            # Gradual increase in corrosive impurities (MORE SEVERE)
            # Using exponential growth to simulate accelerating corrosion
            exponential_factor = np.exp(2 * progress) - 1  # 0 to ~6.4
            
            data.loc[i, 'H2O'] += 150 * exponential_factor / 6.4  # Up to 150 ppm
            data.loc[i, 'H2S'] += 35 * exponential_factor / 6.4   # Up to 35 ppm
            data.loc[i, 'SO2'] += 180 * exponential_factor / 6.4  # Up to 180 ppm
            
            # Temperature increase (exothermic corrosion reactions)
            data.loc[i, 'temperature'] += 5 * progress
            
            # Slight pressure fluctuation due to gas generation
            data.loc[i, 'pressure'] += 0.5 * np.sin(progress * np.pi)
            
            # Mark as corrosion risk when thresholds exceeded (LOWER THRESHOLDS)
            if (data.loc[i, 'H2O'] > 80 or   # Lowered from 100
                data.loc[i, 'H2S'] > 15 or   # Lowered from 20
                data.loc[i, 'SO2'] > 80):    # Lowered from 100
                data.loc[i, 'corrosion_risk'] = 1
        
        return data
    
    def inject_overpressure_event(self,
                                  data: pd.DataFrame,
                                  start_idx: int,
                                  duration: int = 30) -> pd.DataFrame:
        """
        Inject overpressure event (e.g., valve closure, flow surge)
        
        Args:
            data: DataFrame to modify
            start_idx: Starting index
            duration: Duration in samples
            
        Returns:
            Modified DataFrame
        """
        data = data.copy()
        
        for i in range(start_idx, min(start_idx + duration, len(data))):
            progress = (i - start_idx) / duration
            
            # Pressure surge
            if progress < 0.3:  # Rapid increase
                data.loc[i, 'pressure'] += 20 * (progress / 0.3)
            else:  # Gradual relief
                data.loc[i, 'pressure'] += 20 * (1 - (progress - 0.3) / 0.7)
            
            # Temperature increase (compression heating)
            data.loc[i, 'temperature'] += 10 * np.sin(np.pi * progress)
            
            # Flow rate disturbance
            data.loc[i, 'flow_rate'] *= (1 + 0.3 * np.sin(2 * np.pi * progress))
            
            # Mark as overpressure risk
            if data.loc[i, 'pressure'] > 90:
                data.loc[i, 'overpressure_risk'] = 1
        
        return data
    
    def generate_realistic_dataset(self,
                                   n_samples: int = 10000,
                                   n_leakage_events: int = 3,
                                   n_corrosion_events: int = 2,
                                   n_overpressure_events: int = 2,
                                   save_path: str = None) -> pd.DataFrame:
        """
        Generate complete realistic dataset with physics-based anomalies
        
        Args:
            n_samples: Total number of samples
            n_leakage_events: Number of leakage events to inject
            n_corrosion_events: Number of corrosion events
            n_overpressure_events: Number of overpressure events
            save_path: Optional path to save CSV
            
        Returns:
            Complete DataFrame with realistic data
        """
        print(f"Generating {n_samples} samples with physics-based models...")
        
        # Generate base normal operation
        data = self.generate_normal_operation(n_samples)
        
        # Inject leakage events
        print(f"Injecting {n_leakage_events} leakage events...")
        for _ in range(n_leakage_events):
            start = np.random.randint(100, n_samples - 200)
            leak_size = np.random.uniform(2, 10)  # mm
            data = self.inject_leakage_event(data, start, duration=50, leak_size_mm=leak_size)
        
        # Inject corrosion events
        print(f"Injecting {n_corrosion_events} corrosion events...")
        for _ in range(n_corrosion_events):
            start = np.random.randint(100, n_samples - 300)
            data = self.inject_corrosion_event(data, start, duration=200)
        
        # Inject overpressure events
        print(f"Injecting {n_overpressure_events} overpressure events...")
        for _ in range(n_overpressure_events):
            start = np.random.randint(100, n_samples - 100)
            data = self.inject_overpressure_event(data, start, duration=30)
        
        # Calculate statistics
        total_anomalies = (
            data['leakage_risk'].sum() +
            data['corrosion_risk'].sum() +
            data['overpressure_risk'].sum()
        )
        anomaly_rate = total_anomalies / len(data)
        
        print(f"\nDataset Statistics:")
        print(f"  Total samples: {len(data)}")
        print(f"  Leakage events: {data['leakage_risk'].sum()}")
        print(f"  Corrosion events: {data['corrosion_risk'].sum()}")
        print(f"  Overpressure events: {data['overpressure_risk'].sum()}")
        print(f"  Overall anomaly rate: {anomaly_rate*100:.2f}%")
        
        # Save if path provided
        if save_path:
            data.to_csv(save_path, index=False)
            print(f"\n✓ Dataset saved to {save_path}")
        
        return data


if __name__ == "__main__":
    # Example usage
    simulator = PhysicsBasedSimulator()
    
    # Generate realistic dataset
    dataset = simulator.generate_realistic_dataset(
        n_samples=20000,
        n_leakage_events=5,
        n_corrosion_events=3,
        n_overpressure_events=3,
        save_path="data/physics_based_data.csv"
    )
    
    print("\nSample data:")
    print(dataset.head(10))
    
    print("\nData summary:")
    print(dataset.describe())
