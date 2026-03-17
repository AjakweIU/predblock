# PredBlock System Architecture

## Overview
PredBlock is a hybrid AI-Blockchain framework for predictive maintenance and monitoring of Carbon Capture and Storage (CCS) pipelines during CO₂ transportation.

## System Components

### 1. AI Layer (Predictive Monitoring)

#### 1.1 Data Simulator
- **Purpose**: Generate realistic pipeline sensor data for training and testing
- **Outputs**: Time-series data with normal and anomalous conditions
- **Features**:
  - Pressure, temperature, flow rate
  - Impurity levels (H₂O, H₂S, SO₂, O₂, NOₓ, N₂, CH₄)
  - Acoustic emissions and vibration signals

#### 1.2 Machine Learning Models

##### Impurity Tracker
- **Algorithm**: Random Forest Classifier
- **Purpose**: Detect abnormal impurity levels
- **Input Features**: Pressure, temperature, flow rate, impurity concentrations
- **Output**: Binary classification (normal/alert) + probability score

##### Corrosion Predictor
- **Algorithm**: LSTM (Long Short-Term Memory)
- **Purpose**: Predict corrosion risk based on time-series patterns
- **Input**: Sequence of H₂O, H₂S, SO₂, temperature, acoustic emissions
- **Output**: Corrosion risk probability

##### Leakage Detector
- **Algorithm**: Isolation Forest (Anomaly Detection)
- **Purpose**: Detect pipeline leakage through anomaly patterns
- **Input Features**: Pressure, flow rate, O₂, acoustic emissions, vibration
- **Output**: Anomaly score and binary classification

##### Overpressure Controller
- **Algorithm**: PPO (Proximal Policy Optimization) - Reinforcement Learning
- **Purpose**: Optimize valve operations to prevent overpressure
- **State Space**: Pressure, flow rate, temperature
- **Action Space**: Valve position (0-1)
- **Reward**: Based on maintaining target pressure

### 2. Blockchain Layer (Secure Data Sharing)

#### 2.1 Smart Contracts

##### MonitoringLog.sol
- **Purpose**: Immutable storage of pipeline monitoring data
- **Functions**:
  - `addRecord()`: Store sensor readings
  - `getRecord()`: Retrieve historical data
  - `verifyRecord()`: Verify data integrity via hash

##### LeakageReport.sol
- **Purpose**: Tamper-proof leakage incident reporting
- **Features**:
  - Incident severity levels (LOW, MEDIUM, HIGH, CRITICAL)
  - Status tracking (REPORTED, INVESTIGATING, CONFIRMED, RESOLVED)
  - Investigator assignment
  - Evidence hash storage

##### AlertSystem.sol
- **Purpose**: Automated alert generation and management
- **Alert Types**: Impurity, Overpressure, Leakage, Corrosion
- **Functions**:
  - Threshold-based alert triggering
  - Alert acknowledgment and resolution
  - Active/critical alert queries

##### MaintenanceScheduler.sol
- **Purpose**: AI-driven maintenance task scheduling
- **Maintenance Types**: Preventive, Corrective, Predictive, Emergency
- **Features**:
  - Task assignment to personnel
  - Progress tracking
  - Overdue task identification
  - AI prediction hash linking

#### 2.2 Blockchain Interface
- **Technology**: Web3.py
- **Network**: Ethereum (Sepolia testnet)
- **Functions**:
  - Contract deployment and interaction
  - Transaction management
  - Gas cost tracking
  - Event monitoring

## Data Flow

```
Sensor Data → AI Models → Predictions → Blockchain Logging
     ↓            ↓            ↓              ↓
  Storage    Analysis    Alerts/Actions   Immutable Record
```

### Detailed Flow:

1. **Data Collection**
   - Sensors collect: pressure, temperature, flow rate, impurities, acoustic signals
   - Data sampled at configured intervals (default: 60 seconds)

2. **AI Processing**
   - Impurity Tracker: Analyzes impurity levels
   - Leakage Detector: Identifies anomalous patterns
   - Corrosion Predictor: Forecasts corrosion risk
   - Overpressure Controller: Recommends valve adjustments

3. **Alert Generation**
   - Threshold violations trigger alerts
   - AI predictions generate risk scores
   - Alerts classified by severity (INFO, WARNING, CRITICAL)

4. **Blockchain Logging**
   - Monitoring data stored in MonitoringLog contract
   - Critical alerts trigger AlertSystem contract
   - Leakage incidents logged in LeakageReport contract
   - Maintenance tasks scheduled via MaintenanceScheduler

5. **Response Actions**
   - Operators notified of critical alerts
   - Automated valve adjustments (if enabled)
   - Maintenance personnel assigned to tasks
   - Regulators access transparent logs

## Key Thresholds

### Pressure
- Normal: 75 bar (7.5 MPa)
- Warning: 90 bar
- Critical: 100 bar

### Impurities (ppmv)
| Impurity | Normal | Warning | Critical |
|----------|--------|---------|----------|
| H₂O      | ≤50    | >100    | >150     |
| H₂S      | ≤10    | >20     | >50      |
| SO₂      | ≤50    | >100    | >200     |
| O₂       | ≤10    | >15     | >25      |
| NOₓ      | ≤50    | >80     | >120     |

## Security Features

1. **Data Integrity**
   - Cryptographic hashing of all records
   - Immutable blockchain storage
   - Verification functions for data authenticity

2. **Access Control**
   - Role-based permissions (Admin, Operator, Investigator)
   - Authorized reporter/scheduler lists
   - Smart contract modifiers for access restriction

3. **Transparency**
   - All actions logged on blockchain
   - Public verification of data integrity
   - Audit trail for regulators

## Performance Metrics

### AI Metrics
- Accuracy, Precision, Recall, F1-Score
- ROC-AUC for classification models
- Mean Absolute Error for predictions

### Blockchain Metrics
- Transaction latency (seconds)
- Throughput (transactions/second)
- Gas cost (wei/transaction)
- Storage efficiency

## Deployment Architecture

```
┌─────────────────────────────────────────────┐
│           PredBlock System                   │
├─────────────────────────────────────────────┤
│                                              │
│  ┌──────────────┐      ┌─────────────────┐ │
│  │  AI Layer    │      │ Blockchain Layer│ │
│  │              │      │                 │ │
│  │ • Models     │◄────►│ • Smart         │ │
│  │ • Simulator  │      │   Contracts     │ │
│  │ • Monitoring │      │ • Interface     │ │
│  └──────────────┘      └─────────────────┘ │
│         ▲                      ▲            │
│         │                      │            │
│         ▼                      ▼            │
│  ┌──────────────────────────────────────┐  │
│  │     Pipeline Sensors / Data Source   │  │
│  └──────────────────────────────────────┘  │
│                                              │
│  ┌──────────────────────────────────────┐  │
│  │  Stakeholders:                        │  │
│  │  • Operators                          │  │
│  │  • Regulators                         │  │
│  │  • Maintenance Personnel              │  │
│  │  • Carbon Credit Auditors             │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## Technology Stack

### AI/ML
- Python 3.8+
- TensorFlow/Keras (LSTM)
- scikit-learn (Random Forest, Isolation Forest)
- Stable-Baselines3 (PPO)
- pandas, numpy (Data processing)

### Blockchain
- Solidity 0.8.0
- Web3.py
- Ethereum (Sepolia testnet)
- Infura (Node provider)

### Utilities
- PyYAML (Configuration)
- python-dotenv (Environment management)
- matplotlib/seaborn (Visualization)

## Scalability Considerations

1. **AI Layer**
   - Model versioning and updates
   - Distributed training for large datasets
   - Real-time inference optimization

2. **Blockchain Layer**
   - Layer 2 solutions for higher throughput
   - Off-chain storage for large data
   - Batch transaction processing

3. **Integration**
   - Asynchronous processing
   - Message queues for high-volume data
   - Caching for frequent queries
