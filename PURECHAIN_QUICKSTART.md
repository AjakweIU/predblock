# PureChain Quick Start - 5 Minutes

## 🚀 Setup in 3 Steps

### 1. Install Bridge Dependencies
```bash
cd blockchain_layer
npm install
```

### 2. Start Bridge (Keep Running)
```bash
npm start
```

Output:
```
PureChain Bridge running on port 3000
Network: testnet
Endpoint: http://localhost:3000
```

### 3. Deploy Contracts (New Terminal)
```bash
# Activate Python venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Deploy
python scripts/deploy_to_purechain.py
```

## 📝 Quick Commands

### Check Bridge Status
```bash
curl http://localhost:3000/health
```

### Python Usage
```python
from blockchain_layer.purechain_interface import PureChainInterface

# Connect
purechain = PureChainInterface(
    bridge_url="http://localhost:3000",
    network="testnet"
)

# Check balance
balance = purechain.get_balance()
print(f"Balance: {balance} PURE")
```

### Deploy Contract
```python
contract_source = """
pragma solidity ^0.8.0;
contract MyContract {
    uint256 public value;
    function setValue(uint256 _value) public {
        value = _value;
    }
}
"""

result = purechain.deploy_contract(contract_source)
print(f"Deployed at: {result['address']}")
```

## 🔗 Network Info

- **Chain ID:** 900520900520
- **RPC:** https://purechainnode.com
- **Gas Fees:** 0 PURE (FREE!)
- **Network:** Testnet

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| Bridge won't start | Run `npm install` in blockchain_layer |
| Connection refused | Make sure bridge is running (`npm start`) |
| Zero balance | Get testnet tokens from PureChain faucet |

## 📚 Full Documentation

See [docs/PURECHAIN_SETUP.md](docs/PURECHAIN_SETUP.md) for complete guide.

---

**Zero gas fees = Zero cost to deploy and run smart contracts!** 🎉
