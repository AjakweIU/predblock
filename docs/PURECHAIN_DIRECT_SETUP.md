# PureChain Direct Setup (Web3.py)

**NEW:** Direct Python connection to PureChain - **No Node.js bridge required!**

Based on the PureProt implementation approach.

## 🎯 What Changed?

### Before (Bridge Approach):
```
Python → HTTP → Node.js Bridge → PureChainLib → PureChain
```

### After (Direct Approach):
```
Python → Web3.py → PureChain
```

**Benefits:**
- ✅ **Simpler** - No Node.js dependency
- ✅ **Faster** - Direct connection
- ✅ **More Reliable** - Fewer moving parts
- ✅ **Easier Deployment** - Python only

## 📋 Prerequisites

### Python Dependencies (Already Installed)

```bash
pip install web3 py-solc-x
```

These are already in `requirements.txt`!

## 🚀 Quick Start

### 1. Basic Connection

```python
from blockchain_layer.purechain_connector import PureChainConnector

# Initialize
connector = PureChainConnector(network='testnet')

# Create account
account = connector.create_account()
print(f"Address: {account['address']}")
print(f"Private Key: {account['privateKey']}")

# Connect account
connector.connect_account(account['privateKey'])

# Check balance
balance = connector.get_balance()
print(f"Balance: {balance} PURE")
```

### 2. Deploy Smart Contract

```python
# Simple contract
contract_source = """
pragma solidity ^0.8.0;

contract SimpleStorage {
    uint256 public value;
    
    function setValue(uint256 _value) public {
        value = _value;
    }
}
"""

# Deploy
result = connector.deploy_contract(contract_source)
print(f"Contract deployed at: {result['address']}")
```

### 3. Interact with Contract

```python
# Read-only call
value = connector.call_contract(
    contract_address=result['address'],
    abi=result['abi'],
    method='getValue'
)

# State-changing transaction
receipt = connector.execute_contract(
    contract_address=result['address'],
    abi=result['abi'],
    method='setValue',
    args=[42]
)
```

### 4. Deploy PredBlock Contracts

```bash
python scripts/deploy_contracts_direct.py
```

Follow the prompts:
1. Create new account or use existing private key
2. Get testnet tokens (if needed)
3. Deploy all 4 contracts

## 🔐 Comprehensive Audit System

### Create Audit Record

```python
from blockchain_layer.purechain_connector import PredBlockAuditor

# Initialize
auditor = PredBlockAuditor(connector)

# Create audit
audit_record = auditor.create_audit_record(
    timestamp=int(time.time()),
    sensor_data={
        'pressure': 75.0,
        'temperature': 25.0,
        'flow_rate': 50.0,
        'H2O': 10.0,
        'H2S': 2.0,
        'SO2': 5.0,
        'O2': 1.0
    },
    predictions={
        'leakage_risk': 0.05,
        'corrosion_risk': 0.12,
        'overpressure_risk': 0.03
    },
    model_path='models/leakage_detector.pkl',
    alert_triggered=False
)

print(f"Master Hash: {audit_record['master_hash']}")
```

### Audit Record Structure

```json
{
  "timestamp": 1697800000,
  "sensor_data": {...},
  "predictions": {...},
  "alert_triggered": false,
  "software_version": "PredBlock-1.0.0",
  "hashes": {
    "ai_model": "sha256_hash_of_model_file",
    "sensor_data": "sha256_hash_of_sensor_data",
    "predictions": "sha256_hash_of_predictions",
    "parameters": "sha256_hash_of_parameters"
  },
  "master_hash": "sha256_hash_of_entire_record"
}
```

### Record to Blockchain

```python
# Record audit
tx_hash = auditor.record_to_blockchain(
    audit_record=audit_record,
    contract_address=monitoring_log_address,
    contract_abi=monitoring_log_abi
)

print(f"Recorded on blockchain: {tx_hash}")
```

### Verify Audit

```python
# Verify against blockchain
verified = auditor.verify_audit(
    local_audit=audit_record,
    blockchain_hash=blockchain_hash
)

if verified:
    print("✓ Audit verified!")
else:
    print("✗ Audit verification failed!")
```

## 📊 Complete CCS Monitoring Workflow

```python
import time
import json
from blockchain_layer.purechain_connector import PureChainConnector, PredBlockAuditor

# 1. Initialize
connector = PureChainConnector(network='testnet', private_key='your_key')
auditor = PredBlockAuditor(connector)

# 2. Load deployment info
with open('config/purechain_deployment.json', 'r') as f:
    deployment = json.load(f)

monitoring_log = deployment['MonitoringLog']

# 3. Monitor pipeline
while True:
    # Get sensor data
    sensor_data = get_sensor_readings()  # Your function
    
    # Run AI prediction
    predictions = run_ai_models(sensor_data)  # Your function
    
    # Check for alerts
    alert_triggered = predictions['overall_risk'] > 0.8
    
    # Create audit
    audit = auditor.create_audit_record(
        timestamp=int(time.time()),
        sensor_data=sensor_data,
        predictions=predictions,
        model_path='models/leakage_detector.pkl',
        alert_triggered=alert_triggered
    )
    
    # Record to blockchain
    tx_hash = auditor.record_to_blockchain(
        audit_record=audit,
        contract_address=monitoring_log['address'],
        contract_abi=monitoring_log['abi']
    )
    
    print(f"✓ Logged to blockchain: {tx_hash}")
    
    # If alert, create alert on blockchain
    if alert_triggered:
        alert_system = deployment['AlertSystem']
        connector.execute_contract(
            contract_address=alert_system['address'],
            abi=alert_system['abi'],
            method='createAlert',
            args=[
                "High Risk Detected",
                f"Overall risk: {predictions['overall_risk']:.2f}",
                3  # severity: critical
            ]
        )
    
    time.sleep(60)  # Wait 1 minute
```

## 🔧 Configuration

### Network Configuration

```python
# Testnet (default)
connector = PureChainConnector(network='testnet')

# Mainnet
connector = PureChainConnector(network='mainnet')

# Custom network
connector = PureChainConnector(
    network='custom',
    rpc_url='https://custom-node.com:8545',
    chain_id=123456
)
```

### Environment Variables

Create `.env` file:

```env
PURECHAIN_NETWORK=testnet
PURECHAIN_PRIVATE_KEY=your_private_key_here
```

Load in Python:

```python
from dotenv import load_dotenv
import os

load_dotenv()

connector = PureChainConnector(
    network=os.getenv('PURECHAIN_NETWORK', 'testnet'),
    private_key=os.getenv('PURECHAIN_PRIVATE_KEY')
)
```

## 📝 Examples

Run the examples:

```bash
python examples/purechain_direct_example.py
```

Available examples:
1. Basic Connection
2. Deploy Smart Contract
3. Audit System
4. Complete CCS Monitoring Workflow

## 🆚 Comparison: Bridge vs Direct

| Feature | Bridge (Old) | Direct (New) |
|---------|--------------|--------------|
| **Setup** | Python + Node.js | Python only |
| **Dependencies** | npm + pip | pip only |
| **Processes** | 2 (Python + Node) | 1 (Python) |
| **Complexity** | High | Low |
| **Reliability** | Bridge can fail | Direct connection |
| **Performance** | HTTP overhead | Direct |
| **Deployment** | Complex | Simple |

## 🐛 Troubleshooting

### Solc Installation

If contract compilation fails:

```python
from solcx import install_solc, set_solc_version

# Install specific version
install_solc('0.8.0')
set_solc_version('0.8.0')
```

### Connection Issues

```python
# Test connection
if connector.health_check():
    print("✓ Connected to PureChain")
else:
    print("✗ Connection failed")
    
# Get network status
status = connector.get_network_status()
print(status)
```

### Gas Limit Issues

PureChain has an 8M gas limit. If deployment fails:

```python
# Reduce contract complexity
# Or deploy in multiple transactions
```

## 📚 API Reference

### PureChainConnector

```python
class PureChainConnector:
    def __init__(self, private_key=None, network='testnet', rpc_url=None, chain_id=None)
    def connect_account(self, private_key: str)
    def create_account(self) -> Dict[str, str]
    def get_balance(self, address: Optional[str] = None) -> float
    def deploy_contract(self, solidity_source: str, constructor_args: Optional[list] = None) -> Dict
    def call_contract(self, contract_address: str, abi: list, method: str, args: Optional[list] = None) -> Any
    def execute_contract(self, contract_address: str, abi: list, method: str, args: Optional[list] = None) -> Dict
    def send_transaction(self, to: str, value: str) -> Dict
    def get_transaction(self, tx_hash: str) -> Dict
    def get_block(self, block_number: Optional[int] = None) -> Dict
    def get_network_status(self) -> Dict
    def health_check(self) -> bool
```

### PredBlockAuditor

```python
class PredBlockAuditor:
    def __init__(self, connector: PureChainConnector)
    def calculate_file_hash(self, file_path: str) -> str
    def calculate_data_hash(self, data: Dict[str, Any]) -> str
    def create_audit_record(self, timestamp: int, sensor_data: Dict, predictions: Dict, ...) -> Dict
    def record_to_blockchain(self, audit_record: Dict, contract_address: str, contract_abi: list) -> str
    def verify_audit(self, local_audit: Dict, blockchain_hash: str) -> bool
```

## 🎯 Migration from Bridge

If you were using the old bridge approach:

### Before:
```python
from blockchain_layer.purechain_interface import PureChainInterface

purechain = PureChainInterface(bridge_url="http://localhost:3000")
```

### After:
```python
from blockchain_layer.purechain_connector import PureChainConnector

connector = PureChainConnector(network='testnet', private_key='your_key')
```

**No Node.js bridge needed!**

## 🚀 Next Steps

1. ✅ Run examples: `python examples/purechain_direct_example.py`
2. ✅ Deploy contracts: `python scripts/deploy_contracts_direct.py`
3. ✅ Integrate with AI models
4. ✅ Set up monitoring workflow
5. ✅ Deploy to production

---

**Zero gas fees + Direct Python connection = Simple & Powerful!** 🎉
