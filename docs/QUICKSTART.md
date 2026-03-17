# PredBlock Quick Start Guide

## Prerequisites

- Python 3.8 or higher
- Node.js (for blockchain development)
- Git
- Ethereum wallet with testnet ETH (for deployment)

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd PredBlock
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# - INFURA_PROJECT_ID
# - PRIVATE_KEY
# - Contract addresses (after deployment)
```

## Quick Demo (Without Blockchain)

### Step 1: Generate Simulated Data
```bash
python main.py generate --samples 10000 --anomaly-prob 0.05
```

This creates `data/simulated_pipeline_data.csv` with 10,000 samples.

### Step 2: Train AI Models
```bash
python main.py train --data data/simulated_pipeline_data.csv
```

This trains all four AI models:
- Impurity Tracker
- Corrosion Predictor
- Leakage Detector
- Overpressure Controller

### Step 3: Run Monitoring System (Simulation Mode)
```bash
python scripts/monitoring_system.py
```

This runs the monitoring system in simulation mode, displaying real-time predictions.

## Full Setup (With Blockchain)

### Step 1: Get Testnet ETH
1. Create an Ethereum wallet (e.g., MetaMask)
2. Get Sepolia testnet ETH from faucet: https://sepoliafaucet.com/
3. Add your private key to `.env`

### Step 2: Get Infura Project ID
1. Sign up at https://infura.io/
2. Create a new project
3. Copy the project ID to `.env`

### Step 3: Deploy Smart Contracts
```bash
python main.py deploy --network sepolia
```

This deploys all four smart contracts and saves addresses to `blockchain_layer/deployment.json`.

### Step 4: Update Environment
Add the deployed contract addresses to your `.env` file:
```
MONITORINGLOG_ADDRESS=0x...
ALERTSYSTEM_ADDRESS=0x...
LEAKAGEREPORT_ADDRESS=0x...
MAINTENANCESCHEDULER_ADDRESS=0x...
```

### Step 5: Run Full System
```bash
python main.py monitor
```

## Usage Examples

### Generate Custom Dataset
```bash
# Generate 50,000 samples with 10% anomalies
python main.py generate --samples 50000 --anomaly-prob 0.1 --output data/custom_data.csv
```

### Train Specific Model
```bash
# Train only the impurity tracker
python main.py train --model impurity --data data/simulated_pipeline_data.csv

# Train corrosion predictor with custom epochs
python main.py train --model corrosion --epochs 100
```

### Evaluate System
```bash
python scripts/evaluate_system.py --test-data data/simulated_pipeline_data.csv
```

## Project Structure

```
PredBlock/
├── ai_layer/                  # AI/ML components
│   ├── data_simulator.py      # Data generation
│   └── models/                # ML models
│       ├── impurity_tracker.py
│       ├── corrosion_predictor.py
│       ├── leakage_detector.py
│       └── overpressure_controller.py
│
├── blockchain_layer/          # Blockchain components
│   ├── contracts/             # Smart contracts
│   │   ├── MonitoringLog.sol
│   │   ├── LeakageReport.sol
│   │   ├── AlertSystem.sol
│   │   └── MaintenanceScheduler.sol
│   └── blockchain_interface.py
│
├── config/                    # Configuration files
│   └── config.yaml
│
├── data/                      # Data storage
│   ├── raw/
│   └── processed/
│
├── models/                    # Saved models
│   └── saved/
│
├── scripts/                   # Utility scripts
│   ├── monitoring_system.py
│   ├── deploy_contracts.py
│   └── evaluate_system.py
│
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md
│   └── QUICKSTART.md
│
├── main.py                    # Main entry point
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
└── README.md                 # Project overview
```

## Common Commands

### Data Generation
```bash
# Default: 10,000 samples, 5% anomalies
python main.py generate

# Custom configuration
python main.py generate --samples 20000 --anomaly-prob 0.08
```

### Model Training
```bash
# Train all models
python main.py train

# Train specific model
python main.py train --model leakage

# Custom training parameters
python main.py train --epochs 100 --timesteps 200000
```

### Monitoring
```bash
# Run with simulated data
python scripts/monitoring_system.py

# Run with real data file
python scripts/monitoring_system.py --data-source data/real_pipeline_data.csv
```

### Evaluation
```bash
# Evaluate AI models only
python scripts/evaluate_system.py

# Include blockchain performance test
python scripts/evaluate_system.py --blockchain-test --n-transactions 50
```

## Troubleshooting

### Issue: Models not found
**Solution**: Train the models first using `python main.py train`

### Issue: Blockchain connection failed
**Solution**: 
1. Check your Infura project ID in `.env`
2. Ensure you have testnet ETH
3. Verify network is set to 'sepolia'

### Issue: Out of memory during training
**Solution**: 
1. Reduce dataset size
2. Decrease batch size in model training
3. Use a machine with more RAM

### Issue: Smart contract deployment failed
**Solution**:
1. Ensure you have enough testnet ETH
2. Check gas price settings
3. Verify Solidity compiler is installed: `pip install py-solc-x`

## Next Steps

1. **Customize Thresholds**: Edit `config/config.yaml` to adjust impurity and pressure thresholds
2. **Add Real Data**: Replace simulated data with actual pipeline sensor data
3. **Integrate with Systems**: Connect to existing SCADA or monitoring systems
4. **Deploy to Mainnet**: After testing, deploy to Ethereum mainnet or other networks
5. **Scale Up**: Implement distributed processing for multiple pipelines

## Support

For issues and questions:
- Check documentation in `docs/`
- Review code comments
- Open an issue on GitHub

## License

MIT License - See LICENSE file for details
