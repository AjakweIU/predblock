# PureChain Quick Reference

## 🚀 One-Liners

### Initialize
```python
from blockchain_layer.purechain_connector import PureChainConnector
connector = PureChainConnector(network='testnet', private_key='your_key')
```

### Create Account
```python
account = connector.create_account()
# Save: account['address'], account['privateKey']
```

### Check Balance
```python
balance = connector.get_balance()  # Returns float (PURE)
```

### Deploy Contract
```python
result = connector.deploy_contract(solidity_source)
# Returns: {'address': '0x...', 'abi': [...], 'transactionHash': '0x...'}
```

### Call Contract (Read)
```python
value = connector.call_contract(address, abi, 'getValue')
```

### Execute Contract (Write)
```python
receipt = connector.execute_contract(address, abi, 'setValue', [42])
```

### Create Audit
```python
from blockchain_layer.purechain_connector import PredBlockAuditor
auditor = PredBlockAuditor(connector)
audit = auditor.create_audit_record(timestamp, sensor_data, predictions)
```

### Record to Blockchain
```python
tx_hash = auditor.record_to_blockchain(audit, contract_address, abi)
```

## 📋 Common Tasks

### Deploy All PredBlock Contracts
```bash
python scripts/deploy_contracts_direct.py
```

### Load Deployment Info
```python
import json
with open('config/purechain_deployment.json', 'r') as f:
    deployment = json.load(f)

monitoring_log = deployment['MonitoringLog']
alert_system = deployment['AlertSystem']
```

### Log Sensor Reading
```python
connector.execute_contract(
    contract_address=monitoring_log['address'],
    abi=monitoring_log['abi'],
    method='logReading',
    args=[timestamp, data_hash, json.dumps(hashes)]
)
```

### Create Alert
```python
connector.execute_contract(
    contract_address=alert_system['address'],
    abi=alert_system['abi'],
    method='createAlert',
    args=["Leakage Detected", "High O2 levels", 3]
)
```

## 🔧 Configuration

### Network Options
```python
# Testnet (default)
connector = PureChainConnector(network='testnet')

# Mainnet
connector = PureChainConnector(network='mainnet')

# Custom
connector = PureChainConnector(
    network='custom',
    rpc_url='https://custom-node.com:8545',
    chain_id=123456
)
```

### Environment Variables
```python
import os
from dotenv import load_dotenv

load_dotenv()
connector = PureChainConnector(
    network=os.getenv('PURECHAIN_NETWORK', 'testnet'),
    private_key=os.getenv('PURECHAIN_PRIVATE_KEY')
)
```

## 📊 Network Info

### PureChain Testnet
- **RPC:** https://purechainnode.com
- **Chain ID:** 900520900520
- **Gas Price:** 0 (Zero fees!)
- **Gas Limit:** 8,000,000

### Check Status
```python
status = connector.get_network_status()
# Returns: {'connected': True, 'chainId': 900520900520, 'latestBlock': 12345, ...}
```

### Health Check
```python
if connector.health_check():
    print("✓ Connected")
```

## 🔐 Audit System

### Complete Audit Workflow
```python
# 1. Create audit
audit = auditor.create_audit_record(
    timestamp=int(time.time()),
    sensor_data={'pressure': 75.0, 'temperature': 25.0, ...},
    predictions={'leakage_risk': 0.05, ...},
    model_path='models/leakage_detector.pkl',
    alert_triggered=False
)

# 2. Record to blockchain
tx_hash = auditor.record_to_blockchain(
    audit_record=audit,
    contract_address=monitoring_log['address'],
    contract_abi=monitoring_log['abi']
)

# 3. Verify
verified = auditor.verify_audit(audit, blockchain_hash)
```

### Hash Functions
```python
# Hash file
file_hash = auditor.calculate_file_hash('path/to/file.pkl')

# Hash data
data_hash = auditor.calculate_data_hash({'key': 'value'})
```

## 🐛 Troubleshooting

### Solc Not Found
```python
from solcx import install_solc, set_solc_version
install_solc('0.8.0')
set_solc_version('0.8.0')
```

### Connection Failed
```python
# Check connection
if not connector.health_check():
    print("Connection failed")
    status = connector.get_network_status()
    print(status)
```

### Transaction Failed
```python
# Check balance
balance = connector.get_balance()
if balance == 0:
    print("Zero balance - get testnet tokens")
```

## 📚 Resources

- **Setup Guide:** `docs/PURECHAIN_DIRECT_SETUP.md`
- **Examples:** `examples/purechain_direct_example.py`
- **Migration:** `MIGRATION_GUIDE.md`
- **Summary:** `REFACTORING_SUMMARY.md`

## 🎯 Quick Start

```bash
# 1. Deploy contracts
python scripts/deploy_contracts_direct.py

# 2. Run examples
python examples/purechain_direct_example.py

# 3. Integrate with your code
from blockchain_layer.purechain_connector import PureChainConnector
connector = PureChainConnector(network='testnet', private_key='your_key')
```

---

**Zero gas fees + Direct Python = Simple & Powerful!** 🚀
