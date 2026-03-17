# PureChain Integration Guide

Complete guide for deploying PredBlock smart contracts to PureChain blockchain.

## 🔗 What is PureChain?

**PureChain** is an EVM-compatible blockchain with:
- ✅ **Zero gas fees** - All transactions cost 0 PURE
- ✅ **Full Ethereum compatibility** - Use Solidity contracts
- ✅ **Fast transactions** - Quick confirmation times
- ✅ **Testnet available** - Free testing environment

**Network Details:**
- **RPC Endpoint:** https://purechainnode.com
- **Chain ID:** 900520900520
- **Network:** PureChain Testnet
- **Gas Price:** 0 (Zero gas fees!)

## 📋 Prerequisites

### 1. Node.js & npm
```bash
# Check if installed
node --version  # Should be >= 16.0.0
npm --version   # Should be >= 8.0.0

# Install if needed (Windows)
# Download from: https://nodejs.org/
```

### 2. Python Environment
```bash
# Activate your virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

## 🚀 Quick Start

### Step 1: Install PureChain Bridge Dependencies

```bash
cd blockchain_layer
npm install
```

This installs:
- `purechainlib` - PureChain SDK
- `express` - Web server for Python bridge
- `body-parser` - JSON parsing

### Step 2: Start the PureChain Bridge

The bridge is a Node.js service that allows Python to interact with PureChain.

```bash
# From blockchain_layer directory
npm start

# Or with auto-reload during development
npm run dev
```

You should see:
```
PureChain Bridge running on port 3000
Network: testnet
Endpoint: http://localhost:3000
```

**Keep this terminal open!** The bridge must be running for Python to connect.

### Step 3: Deploy Smart Contracts

Open a **new terminal** and run:

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Run deployment script
python scripts/deploy_to_purechain.py
```

Follow the prompts:
1. **Create new account** or use existing private key
2. **Save your credentials** (address, private key, mnemonic)
3. **Get testnet tokens** from PureChain faucet (if needed)
4. **Deploy contracts** - All 4 contracts will be deployed

## 📝 Detailed Setup

### Configuration

Create `.env` file in `blockchain_layer/`:

```bash
# Copy example
cd blockchain_layer
cp .env.example .env

# Edit with your settings
nano .env  # or use any text editor
```

`.env` contents:
```env
# Network: testnet or mainnet
PURECHAIN_NETWORK=testnet

# Bridge server port
PURECHAIN_BRIDGE_PORT=3000

# Optional: Private key for default wallet
PURECHAIN_PRIVATE_KEY=your_private_key_here
```

### Getting Testnet Tokens

1. **Create account** using the deployment script
2. **Copy your address**
3. **Visit PureChain faucet** (check PureChain documentation)
4. **Request testnet PURE tokens**
5. **Wait for tokens** to arrive
6. **Run deployment** again

## 🔧 Using PureChain in Python

### Basic Usage

```python
from blockchain_layer.purechain_interface import PureChainInterface

# Initialize (bridge must be running)
purechain = PureChainInterface(
    bridge_url="http://localhost:3000",
    network="testnet",
    private_key="your_private_key"  # Optional
)

# Check balance
balance = purechain.get_balance()
print(f"Balance: {balance} PURE")

# Get network status
status = purechain.get_status()
print(f"Chain ID: {status['chainId']}")
```

### Deploy Contract

```python
# Solidity source code
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
result = purechain.deploy_contract(contract_source)
print(f"Contract deployed at: {result['address']}")

# Save ABI for later use
contract_address = result['address']
contract_abi = result['abi']
```

### Interact with Contract

```python
# Call read-only method
value = purechain.call_contract(
    contract_address=contract_address,
    abi=contract_abi,
    method="value",
    args=[]
)
print(f"Current value: {value}")

# Execute state-changing method
receipt = purechain.execute_contract(
    contract_address=contract_address,
    abi=contract_abi,
    method="setValue",
    args=[42]
)
print(f"Transaction: {receipt['hash']}")
```

### Send Transactions

```python
# Send PURE tokens
receipt = purechain.send_transaction(
    to="0x...",
    value="1.0"  # Amount in PURE
)
print(f"Transaction hash: {receipt['hash']}")
```

## 📦 Deployed Contracts

After successful deployment, you'll have:

### 1. MonitoringLog
Records all pipeline sensor readings on-chain.

**Functions:**
- `logReading()` - Store sensor data
- `getReading()` - Retrieve historical data
- `getLatestReading()` - Get most recent reading

### 2. AlertSystem
Manages alerts and notifications for anomalies.

**Functions:**
- `createAlert()` - Create new alert
- `acknowledgeAlert()` - Mark alert as seen
- `resolveAlert()` - Close resolved alert
- `getActiveAlerts()` - List active alerts

### 3. LeakageReport
Tracks leakage events and reports.

**Functions:**
- `reportLeakage()` - Report leakage event
- `updateLeakageStatus()` - Update status
- `getLeakageReport()` - Get report details
- `getAllLeakages()` - List all leakages

### 4. MaintenanceScheduler
Schedules and tracks maintenance activities.

**Functions:**
- `scheduleTask()` - Create maintenance task
- `completeTask()` - Mark task complete
- `getTask()` - Get task details
- `getPendingTasks()` - List pending tasks

## 🔍 Monitoring & Debugging

### Check Bridge Health

```python
from blockchain_layer.purechain_interface import PureChainInterface

purechain = PureChainInterface()

if purechain.health_check():
    print("✓ Bridge is running")
else:
    print("✗ Bridge is not running")
    print("Start with: cd blockchain_layer && npm start")
```

### View Bridge Logs

The bridge outputs logs to console:
```
PureChain Bridge running on port 3000
Network: testnet
Endpoint: http://localhost:3000
```

### Test Bridge Endpoints

```bash
# Health check
curl http://localhost:3000/health

# Get status
curl http://localhost:3000/api/status

# Get balance
curl http://localhost:3000/api/balance/0x...
```

## 🐛 Troubleshooting

### Bridge Won't Start

**Error:** `Cannot find module 'purechainlib'`

**Solution:**
```bash
cd blockchain_layer
npm install
```

### Connection Refused

**Error:** `Connection refused to http://localhost:3000`

**Solution:**
1. Make sure bridge is running: `npm start`
2. Check port 3000 is not in use
3. Try different port in `.env`: `PURECHAIN_BRIDGE_PORT=3001`

### Deployment Fails

**Error:** `Insufficient funds`

**Solution:**
1. Check balance: `purechain.get_balance()`
2. Get testnet tokens from faucet
3. Wait for tokens to arrive

**Error:** `Contract compilation failed`

**Solution:**
1. Check Solidity syntax
2. Ensure pragma version is compatible
3. Check OpenZeppelin imports are correct

### Zero Balance

**Problem:** Account has 0 PURE tokens

**Solution:**
1. Visit PureChain faucet
2. Request testnet tokens
3. Wait 1-2 minutes
4. Check balance again

## 📚 Additional Resources

- **PureChainLib Documentation:** https://www.npmjs.com/package/purechainlib
- **PureChain Network:** https://purechainnode.com
- **Chain ID:** 900520900520

## 🔐 Security Best Practices

1. **Never commit private keys** to Git
2. **Use `.env` files** for sensitive data
3. **Add `.env` to `.gitignore`**
4. **Use testnet first** before mainnet
5. **Backup your mnemonic** phrase securely

## 🎯 Next Steps

After deployment:

1. ✅ **Test contracts** with sample data
2. ✅ **Integrate with AI models** for predictions
3. ✅ **Set up monitoring** dashboard
4. ✅ **Configure alerts** for anomalies
5. ✅ **Deploy to mainnet** when ready

## 💡 Example: Full Integration

```python
from blockchain_layer.purechain_interface import PureChainInterface
import json

# Load deployment info
with open('config/purechain_deployment.json', 'r') as f:
    contracts = json.load(f)

# Initialize
purechain = PureChainInterface(private_key="your_key")

# Log sensor reading
monitoring_log = contracts['MonitoringLog']
receipt = purechain.execute_contract(
    contract_address=monitoring_log['address'],
    abi=monitoring_log['abi'],
    method='logReading',
    args=[
        75.0,   # pressure
        25.0,   # temperature
        50.0,   # flow_rate
        10.0,   # H2O
        2.0,    # H2S
        5.0,    # SO2
        1.0     # O2
    ]
)

print(f"Reading logged: {receipt['hash']}")

# Create alert if anomaly detected
if anomaly_detected:
    alert_system = contracts['AlertSystem']
    receipt = purechain.execute_contract(
        contract_address=alert_system['address'],
        abi=alert_system['abi'],
        method='createAlert',
        args=[
            "Leakage Detected",
            "High O2 levels indicate potential leakage",
            3  # severity: critical
        ]
    )
    print(f"Alert created: {receipt['hash']}")
```

---

**Need help?** Check the troubleshooting section or open an issue on GitHub.
