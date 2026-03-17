# Migration Guide: Bridge → Direct Web3.py

## 🎯 What Changed?

We've simplified PureChain integration by eliminating the Node.js bridge and using **direct Web3.py connection** (inspired by PureProt's approach).

### Before (Bridge Approach):
```
Python → HTTP → Node.js Bridge → PureChainLib → PureChain
```

### After (Direct Approach):
```
Python → Web3.py → PureChain
```

## ✅ Benefits

| Aspect | Before | After |
|--------|--------|-------|
| **Setup** | Python + Node.js | Python only |
| **Processes** | 2 (Python + Node) | 1 (Python) |
| **Dependencies** | npm + pip | pip only |
| **Complexity** | High | Low |
| **Reliability** | Bridge can fail | Direct connection |
| **Performance** | HTTP overhead | Direct |

## 📋 Migration Steps

### Step 1: No New Dependencies Needed!

Web3.py and py-solc-x are already in `requirements.txt`:

```bash
# Already installed!
pip install web3 py-solc-x
```

### Step 2: Update Your Code

#### Old Approach (Bridge):

```python
from blockchain_layer.purechain_interface import PureChainInterface

# Required Node.js bridge running
purechain = PureChainInterface(
    bridge_url="http://localhost:3000",
    network="testnet"
)

# Deploy contract
result = purechain.deploy_contract(solidity_source)
```

#### New Approach (Direct):

```python
from blockchain_layer.purechain_connector import PureChainConnector

# No bridge needed!
connector = PureChainConnector(
    network='testnet',
    private_key='your_private_key'
)

# Deploy contract
result = connector.deploy_contract(solidity_source)
```

### Step 3: Update Deployment Scripts

#### Old:

```bash
# Terminal 1 - Start bridge
cd blockchain_layer
npm install
npm start

# Terminal 2 - Deploy
python scripts/deploy_to_purechain.py
```

#### New:

```bash
# Single command!
python scripts/deploy_contracts_direct.py
```

### Step 4: Update Monitoring Code

#### Old:

```python
# Required bridge running
purechain = PureChainInterface(bridge_url="http://localhost:3000")

# Execute contract
purechain.execute_contract(
    contract_address=address,
    abi=abi,
    method='logReading',
    args=[pressure, temp, flow]
)
```

#### New:

```python
# Direct connection
connector = PureChainConnector(network='testnet', private_key='your_key')

# Execute contract
connector.execute_contract(
    contract_address=address,
    abi=abi,
    method='logReading',
    args=[pressure, temp, flow]
)
```

## 🔧 Code Changes Summary

### 1. Import Statements

```python
# Old
from blockchain_layer.purechain_interface import PureChainInterface

# New
from blockchain_layer.purechain_connector import PureChainConnector
```

### 2. Initialization

```python
# Old
purechain = PureChainInterface(bridge_url="http://localhost:3000")

# New
connector = PureChainConnector(network='testnet', private_key='your_key')
```

### 3. Account Creation

```python
# Old
account = purechain.create_account()

# New
account = connector.create_account()
```

### 4. Contract Deployment

```python
# Old
result = purechain.deploy_contract(source)

# New
result = connector.deploy_contract(source)
```

### 5. Contract Interaction

```python
# Old
value = purechain.call_contract(address, abi, 'getValue')
receipt = purechain.execute_contract(address, abi, 'setValue', [42])

# New
value = connector.call_contract(address, abi, 'getValue')
receipt = connector.execute_contract(address, abi, 'setValue', [42])
```

## 🆕 New Features

### 1. Comprehensive Audit System

```python
from blockchain_layer.purechain_connector import PredBlockAuditor

auditor = PredBlockAuditor(connector)

# Create audit with cryptographic hashing
audit = auditor.create_audit_record(
    timestamp=int(time.time()),
    sensor_data=sensor_data,
    predictions=predictions,
    model_path='models/leakage_detector.pkl',
    alert_triggered=False
)

# Audit includes hashes of:
# - AI model file
# - Sensor data
# - Predictions
# - Parameters
# - Master hash of entire record
```

### 2. File Hashing for Reproducibility

```python
# Hash trained models
model_hash = auditor.calculate_file_hash('models/leakage_detector.pkl')

# Hash any data
data_hash = auditor.calculate_data_hash({'key': 'value'})
```

### 3. Blockchain Verification

```python
# Record to blockchain
tx_hash = auditor.record_to_blockchain(
    audit_record=audit,
    contract_address=monitoring_log_address,
    contract_abi=monitoring_log_abi
)

# Verify later
verified = auditor.verify_audit(
    local_audit=audit,
    blockchain_hash=blockchain_hash
)
```

## 🗑️ What to Remove

### 1. Node.js Bridge Files (Optional)

You can keep these for reference, but they're no longer needed:

```
blockchain_layer/purechain_bridge.js
blockchain_layer/package.json
blockchain_layer/.env.example
```

### 2. Old Deployment Script (Optional)

```
scripts/deploy_to_purechain.py  # Old bridge-based script
```

Use the new one:
```
scripts/deploy_contracts_direct.py  # New direct script
```

## 📝 Updated Workflow

### Complete CCS Monitoring Example

```python
import time
import json
from blockchain_layer.purechain_connector import PureChainConnector, PredBlockAuditor

# Initialize (no bridge needed!)
connector = PureChainConnector(
    network='testnet',
    private_key=os.getenv('PURECHAIN_PRIVATE_KEY')
)

auditor = PredBlockAuditor(connector)

# Load deployment info
with open('config/purechain_deployment.json', 'r') as f:
    deployment = json.load(f)

# Monitor loop
while True:
    # 1. Get sensor data
    sensor_data = {
        'pressure': 75.0,
        'temperature': 25.0,
        'flow_rate': 50.0,
        'H2O': 10.0,
        'H2S': 2.0,
        'SO2': 5.0,
        'O2': 1.0
    }
    
    # 2. Run AI prediction
    predictions = {
        'leakage_risk': 0.05,
        'corrosion_risk': 0.12,
        'overpressure_risk': 0.03
    }
    
    # 3. Create comprehensive audit
    audit = auditor.create_audit_record(
        timestamp=int(time.time()),
        sensor_data=sensor_data,
        predictions=predictions,
        model_path='models/leakage_detector.pkl',
        alert_triggered=False
    )
    
    # 4. Record to blockchain
    tx_hash = auditor.record_to_blockchain(
        audit_record=audit,
        contract_address=deployment['MonitoringLog']['address'],
        contract_abi=deployment['MonitoringLog']['abi']
    )
    
    print(f"✓ Logged to blockchain: {tx_hash}")
    
    time.sleep(60)
```

## 🐛 Troubleshooting

### Issue: Solc Not Found

```python
from solcx import install_solc, set_solc_version

install_solc('0.8.0')
set_solc_version('0.8.0')
```

### Issue: Connection Failed

```python
# Test connection
if connector.health_check():
    print("✓ Connected")
else:
    print("✗ Connection failed")
    
# Check status
status = connector.get_network_status()
print(status)
```

### Issue: Transaction Failed

```python
# Check balance
balance = connector.get_balance()
print(f"Balance: {balance} PURE")

# Check gas limit (PureChain has 8M limit)
# Reduce contract complexity if needed
```

## 📚 Resources

- **New Documentation:** `docs/PURECHAIN_DIRECT_SETUP.md`
- **Examples:** `examples/purechain_direct_example.py`
- **Deployment:** `scripts/deploy_contracts_direct.py`
- **API Reference:** See `PURECHAIN_DIRECT_SETUP.md`

## ✅ Migration Checklist

- [ ] Update imports to use `PureChainConnector`
- [ ] Remove bridge initialization code
- [ ] Update deployment scripts
- [ ] Add comprehensive audit system
- [ ] Test contract deployment
- [ ] Test contract interaction
- [ ] Update monitoring workflow
- [ ] Remove Node.js dependencies (optional)
- [ ] Update documentation references

## 🎉 You're Done!

Your PredBlock system now uses **direct Web3.py connection** with:
- ✅ Simpler setup
- ✅ Better reliability
- ✅ Comprehensive audit trail
- ✅ Cryptographic hashing
- ✅ Zero gas fees on PureChain

**No Node.js bridge required!** 🚀
