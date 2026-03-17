# PredBlock: AI-Blockchain Framework for CCS Pipeline Monitoring

## Project Overview
A hybrid AI-Blockchain framework for predictive maintenance and monitoring of Carbon Capture and Storage (CCS) pipelines during CO₂ transportation.

## Research Problem
During CCS transportation via pipeline from capture site to utilization/storage site, critical safety concerns include:
- Pipeline failures (cracks, leakage)
- Over-pressurization
- Impurities in CO₂ causing corrosion

## Project Objectives
Develop a predictive maintenance system for CCS pipelines using AI, where operational data (pressure, temperature, impurity levels) is continuously monitored, and blockchain ensures transparency and auditability.

## System Architecture

### (A) AI Layer – Predictive Monitoring
**Inputs:**
- Pressure (bar/MPa)
- Temperature (°C)
- Flow rate (kg/s)
- Impurity concentrations (H₂O, SO₂, H₂S, O₂, NOₓ, N₂, CH₄)
- Vibration and acoustic emissions

**ML Tasks:**
1. **Impurity Tracking**: Classification/forecasting for abnormal impurity levels
2. **Corrosion/Leakage Risk**: Predictive models using anomaly detection
3. **Over-pressurization Control**: Reinforcement learning for valve operation

### (B) Blockchain Layer – Secure Data Sharing (PureChain)
**Platform:** PureChain - EVM-compatible blockchain with zero gas fees  
**Integration:** Direct Web3.py connection (No Node.js bridge required!)

**Functions:**
- Immutable storage of monitoring logs
- Transparent leakage reports (tamper-proof)
- Decentralized access for regulators, operators, and auditors
- Smart contracts for automated alerts and maintenance scheduling
- Comprehensive audit trail with cryptographic hashing

**Network Details:**
- Chain ID: 900520900520
- RPC: https://purechainnode.com
- Gas Fees: 0 PURE (Zero cost transactions!)
- **NEW:** Direct Python integration via Web3.py

## Key Thresholds

### Pressure
- Normal: 75 bar (7.5 MPa, ~1,088 psi)
- Alert: 90-100 bar (over-pressurization risk)

### Impurity Limits (ppmv)
| Impurity | Normal Range | Alert Threshold | Critical Impact |
|----------|--------------|-----------------|-----------------|
| H₂O | 0-50 ppm | >100 ppm | Corrosion risk |
| H₂S | 0-10 ppm | >20 ppm | Corrosion + toxicity |
| SO₂ | 0-50 ppm | >100 ppm | Rapid corrosion |
| O₂ | 0-10 ppm | >15 ppm | Oxidation/leakage |
| NOₓ | 0-50 ppm | >80 ppm | Acid formation |

## Project Structure
```
PredBlock/
├── ai_layer/              # AI/ML components
├── blockchain_layer/      # Blockchain and smart contracts
├── data/                  # Datasets and simulations
├── config/                # Configuration files
├── tests/                 # Unit and integration tests
├── docs/                  # Documentation
└── scripts/               # Utility scripts
```

## Expected Outcomes
- Higher pipeline efficiency
- Early leakage detection
- Trusted reporting for regulators
- Focus on pipeline integrity and MRV (Monitoring, Reporting, Verification)

## Installation

### Prerequisites
- Python 3.8+
- pip package manager
- (Optional) Ethereum wallet with testnet ETH for blockchain deployment

### Setup
```bash
# 1. Clone repository
git clone <repository-url>
cd PredBlock

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your credentials (Infura, private key, etc.)
```

## Quick Start

### Generate Physics-Based Data (Recommended for Publication)
```bash
# Generate complete train/val/test datasets with physics-based models
python scripts/generate_publication_data.py

# This creates:
# - data/train_physics.csv (50,000 samples, ~35 days)
# - data/val_physics.csv (15,000 samples, ~10 days)
# - data/test_physics.csv (10,000 samples, ~7 days)
# - Visualization plots in data/plots/
```

### Validate Data Quality
```bash
# Validate against literature standards
python scripts/validate_data_quality.py --data data/test_physics.csv
```

### Train AI Models
```bash
# Train all models on physics-based data
python main.py train --data data/train_physics.csv

# Or train specific model
python main.py train --model impurity --data data/train_physics.csv
```

### Run Monitoring System
```bash
# Simulation mode (generates data on-the-fly)
python scripts/monitoring_system.py

# Or use existing data
python main.py monitor --config config/config.yaml
```

### Evaluate System Performance
```bash
# Comprehensive evaluation with metrics
python scripts/evaluate_system.py --test-data data/test_physics.csv
```

## Usage

### Command-Line Interface

**Generate Data:**
```bash
# Physics-based (recommended)
python scripts/generate_publication_data.py --output-dir data

# Simple simulation (for testing)
python main.py generate --samples 10000 --anomaly-prob 0.05
```

**Train Models:**
```bash
# All models
python main.py train --data data/train_physics.csv

# Specific model with custom parameters
python main.py train --model corrosion --epochs 100
```

**Deploy Smart Contracts (PureChain):**
```bash
# Direct deployment - No Node.js bridge needed!
python scripts/deploy_contracts_direct.py
```

**Monitor Pipeline:**
```bash
python main.py monitor
```

### Python API

```python
from ai_layer.physics_based_simulator import PhysicsBasedSimulator
from ai_layer.models.impurity_tracker import ImpurityTracker

# Generate realistic data
simulator = PhysicsBasedSimulator()
data = simulator.generate_realistic_dataset(
    n_samples=10000,
    n_leakage_events=3,
    n_corrosion_events=2,
    n_overpressure_events=2
)

# Train model
tracker = ImpurityTracker()
metrics = tracker.train(data)
tracker.save_model()

# Make predictions
predictions = tracker.predict(data)
```

## Documentation

- **[Quick Start Guide](docs/QUICKSTART.md)** - Get started in 5 minutes
- **[Architecture](docs/ARCHITECTURE.md)** - System design and components
- **[Data Generation Methodology](docs/DATA_GENERATION_METHODOLOGY.md)** - Physics-based simulation details for publication
- **[PureChain Direct Setup](docs/PURECHAIN_DIRECT_SETUP.md)** - Deploy smart contracts with direct Web3.py (No Node.js!)

## For Publication

This project uses **physics-based simulation** grounded in:
- CO₂ thermodynamic properties (Span-Wagner EOS)
- Pipeline flow dynamics (Darcy-Weisbach equation)
- Corrosion kinetics (NACE standards)
- Acoustic emission models (ISO 15138)

All models are validated against literature values from:
- IEAGHG (2010) - CO₂ Pipeline Infrastructure
- DNV GL RP-F104 - Design and operation of CO₂ pipelines
- Dynamis (2008) - CO₂ quality recommendations
- NIST - CO₂ thermodynamic data

See [DATA_GENERATION_METHODOLOGY.md](docs/DATA_GENERATION_METHODOLOGY.md) for complete details.

## License
MIT License
