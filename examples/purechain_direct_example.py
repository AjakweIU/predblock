"""
Example: Using PureChain Direct Connector
No Node.js bridge required!
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from blockchain_layer.purechain_connector import PureChainConnector, PredBlockAuditor
import json
import time


def example_1_basic_connection():
    """Example 1: Basic connection and account management"""
    
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Connection")
    print("="*70)
    
    # Initialize connector
    connector = PureChainConnector(network='testnet')
    
    # Create new account
    print("\n1. Creating new account...")
    account = connector.create_account()
    print(f"   Address: {account['address']}")
    print(f"   Private Key: {account['privateKey'][:20]}...")
    
    # Connect account
    print("\n2. Connecting account...")
    connector.connect_account(account['privateKey'])
    
    # Check balance
    print("\n3. Checking balance...")
    balance = connector.get_balance()
    print(f"   Balance: {balance} PURE")
    
    # Get network status
    print("\n4. Getting network status...")
    status = connector.get_network_status()
    print(f"   Connected: {status['connected']}")
    print(f"   Chain ID: {status['chainId']}")
    print(f"   Latest Block: {status['latestBlock']}")
    print(f"   Gas Price: {status['gasPrice']} (Zero!)")


def example_2_deploy_contract():
    """Example 2: Deploy a simple contract"""
    
    print("\n" + "="*70)
    print("EXAMPLE 2: Deploy Smart Contract")
    print("="*70)
    
    # Simple storage contract
    contract_source = """
    pragma solidity ^0.8.0;
    
    contract SimpleStorage {
        uint256 public value;
        
        event ValueChanged(uint256 newValue);
        
        function setValue(uint256 _value) public {
            value = _value;
            emit ValueChanged(_value);
        }
        
        function getValue() public view returns (uint256) {
            return value;
        }
    }
    """
    
    # Initialize connector with private key
    private_key = input("Enter your private key (or press Enter to skip): ").strip()
    if not private_key:
        print("Skipping deployment example (no private key provided)")
        return
    
    connector = PureChainConnector(network='testnet', private_key=private_key)
    
    # Deploy contract
    print("\n1. Deploying contract...")
    result = connector.deploy_contract(contract_source)
    print(f"   Contract Address: {result['address']}")
    print(f"   Transaction Hash: {result['transactionHash']}")
    print(f"   Gas Used: {result['gasUsed']}")
    
    # Interact with contract
    print("\n2. Calling getValue() (read-only)...")
    value = connector.call_contract(
        contract_address=result['address'],
        abi=result['abi'],
        method='getValue'
    )
    print(f"   Current value: {value}")
    
    # Execute transaction
    print("\n3. Calling setValue(42) (state-changing)...")
    tx_receipt = connector.execute_contract(
        contract_address=result['address'],
        abi=result['abi'],
        method='setValue',
        args=[42]
    )
    print(f"   Transaction Hash: {tx_receipt['transactionHash']}")
    print(f"   Gas Used: {tx_receipt['gasUsed']}")
    
    # Read new value
    print("\n4. Reading new value...")
    new_value = connector.call_contract(
        contract_address=result['address'],
        abi=result['abi'],
        method='getValue'
    )
    print(f"   New value: {new_value}")


def example_3_audit_system():
    """Example 3: Comprehensive audit system"""
    
    print("\n" + "="*70)
    print("EXAMPLE 3: Audit System")
    print("="*70)
    
    # Initialize
    connector = PureChainConnector(network='testnet')
    auditor = PredBlockAuditor(connector)
    
    # Create audit record
    print("\n1. Creating audit record...")
    
    sensor_data = {
        'pressure': 75.0,
        'temperature': 25.0,
        'flow_rate': 50.0,
        'H2O': 10.0,
        'H2S': 2.0,
        'SO2': 5.0,
        'O2': 1.0
    }
    
    predictions = {
        'leakage_risk': 0.05,
        'corrosion_risk': 0.12,
        'overpressure_risk': 0.03,
        'overall_risk': 'low'
    }
    
    audit_record = auditor.create_audit_record(
        timestamp=int(time.time()),
        sensor_data=sensor_data,
        predictions=predictions,
        alert_triggered=False,
        parameters={'model_version': '1.0', 'threshold': 0.8}
    )
    
    print(f"   Master Hash: {audit_record['master_hash']}")
    print(f"   Sensor Data Hash: {audit_record['hashes']['sensor_data']}")
    print(f"   Predictions Hash: {audit_record['hashes']['predictions']}")
    
    # Save audit record
    print("\n2. Saving audit record...")
    with open('audit_record_example.json', 'w') as f:
        json.dump(audit_record, f, indent=2)
    print("   Saved to: audit_record_example.json")
    
    print("\n3. Audit record structure:")
    print(json.dumps(audit_record, indent=2))


def example_4_complete_workflow():
    """Example 4: Complete CCS monitoring workflow"""
    
    print("\n" + "="*70)
    print("EXAMPLE 4: Complete CCS Monitoring Workflow")
    print("="*70)
    
    private_key = input("Enter your private key (or press Enter to skip): ").strip()
    if not private_key:
        print("Skipping workflow example (no private key provided)")
        return
    
    # Load deployment info
    try:
        with open('config/purechain_deployment.json', 'r') as f:
            deployment = json.load(f)
    except FileNotFoundError:
        print("Deployment info not found. Run deploy_contracts_direct.py first.")
        return
    
    # Initialize
    connector = PureChainConnector(network='testnet', private_key=private_key)
    auditor = PredBlockAuditor(connector)
    
    # Simulate sensor reading
    print("\n1. Simulating sensor reading...")
    sensor_data = {
        'pressure': 75.5,
        'temperature': 25.2,
        'flow_rate': 50.1,
        'H2O': 10.5,
        'H2S': 2.1,
        'SO2': 5.2,
        'O2': 1.1
    }
    print(f"   Sensor data: {sensor_data}")
    
    # AI prediction (simulated)
    print("\n2. Running AI prediction...")
    predictions = {
        'leakage_risk': 0.08,
        'corrosion_risk': 0.15,
        'overpressure_risk': 0.04,
        'overall_risk': 'low'
    }
    print(f"   Predictions: {predictions}")
    
    # Create audit record
    print("\n3. Creating audit record...")
    audit_record = auditor.create_audit_record(
        timestamp=int(time.time()),
        sensor_data=sensor_data,
        predictions=predictions,
        alert_triggered=False
    )
    print(f"   Master Hash: {audit_record['master_hash']}")
    
    # Record to blockchain
    print("\n4. Recording to blockchain...")
    monitoring_log = deployment['MonitoringLog']
    
    tx_hash = auditor.record_to_blockchain(
        audit_record=audit_record,
        contract_address=monitoring_log['address'],
        contract_abi=monitoring_log['abi']
    )
    print(f"   Transaction Hash: {tx_hash}")
    
    # Verify
    print("\n5. Verification complete!")
    print(f"   ✓ Sensor data logged")
    print(f"   ✓ Predictions recorded")
    print(f"   ✓ Audit trail created")
    print(f"   ✓ Blockchain transaction: {tx_hash}")


def main():
    """Run all examples"""
    
    print("="*70)
    print("PREDBLOCK - PURECHAIN DIRECT CONNECTOR EXAMPLES")
    print("="*70)
    
    print("\nAvailable examples:")
    print("1. Basic Connection")
    print("2. Deploy Smart Contract")
    print("3. Audit System")
    print("4. Complete CCS Monitoring Workflow")
    print("5. Run all examples")
    
    choice = input("\nSelect example (1-5): ").strip()
    
    if choice == '1':
        example_1_basic_connection()
    elif choice == '2':
        example_2_deploy_contract()
    elif choice == '3':
        example_3_audit_system()
    elif choice == '4':
        example_4_complete_workflow()
    elif choice == '5':
        example_1_basic_connection()
        example_2_deploy_contract()
        example_3_audit_system()
        example_4_complete_workflow()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
