"""
Deploy PredBlock Smart Contracts to PureChain
Direct Web3.py approach - No Node.js bridge needed!
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from blockchain_layer.purechain_connector import PureChainConnector
from loguru import logger
import json


def load_contract(filename: str) -> str:
    """Load Solidity contract from file"""
    contract_path = os.path.join('blockchain_layer', 'contracts', filename)
    with open(contract_path, 'r') as f:
        return f.read()


def deploy_monitoring_log(connector: PureChainConnector):
    """Deploy MonitoringLog contract"""
    logger.info("Deploying MonitoringLog contract...")
    
    source = load_contract('MonitoringLog.sol')
    result = connector.deploy_contract(source)
    
    logger.success(f"MonitoringLog deployed at: {result['address']}")
    return result


def deploy_alert_system(connector: PureChainConnector):
    """Deploy AlertSystem contract"""
    logger.info("Deploying AlertSystem contract...")
    
    source = load_contract('AlertSystem.sol')
    result = connector.deploy_contract(source)
    
    logger.success(f"AlertSystem deployed at: {result['address']}")
    return result


def deploy_leakage_report(connector: PureChainConnector):
    """Deploy LeakageReport contract"""
    logger.info("Deploying LeakageReport contract...")
    
    source = load_contract('LeakageReport.sol')
    result = connector.deploy_contract(source)
    
    logger.success(f"LeakageReport deployed at: {result['address']}")
    return result


def deploy_maintenance_scheduler(connector: PureChainConnector):
    """Deploy MaintenanceScheduler contract"""
    logger.info("Deploying MaintenanceScheduler contract...")
    
    source = load_contract('MaintenanceScheduler.sol')
    result = connector.deploy_contract(source)
    
    logger.success(f"MaintenanceScheduler deployed at: {result['address']}")
    return result


def save_deployment_info(contracts: dict, filename: str = 'purechain_deployment.json'):
    """Save deployment information to file"""
    output_path = os.path.join('config', filename)
    os.makedirs('config', exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(contracts, f, indent=2)
    
    logger.info(f"Deployment info saved to {output_path}")


def main():
    """Main deployment function"""
    
    print("="*70)
    print("PREDBLOCK - PURECHAIN DEPLOYMENT (Direct Web3.py)")
    print("="*70)
    
    # Account setup
    print("\n" + "="*70)
    print("ACCOUNT SETUP")
    print("="*70)
    
    choice = input("\n1. Create new account\n2. Use existing private key\nChoice (1/2): ").strip()
    
    connector = PureChainConnector(network='testnet')
    
    if choice == '1':
        logger.info("Creating new account...")
        account = connector.create_account()
        
        print("\n⚠️  SAVE THESE CREDENTIALS SECURELY!")
        print(f"Address: {account['address']}")
        print(f"Private Key: {account['privateKey']}")
        
        connector.connect_account(account['privateKey'])
        
        print("\n⚠️  You need testnet PURE tokens to deploy contracts.")
        print("Visit PureChain faucet to get testnet tokens.")
        input("Press Enter when you have tokens...")
    
    elif choice == '2':
        private_key = input("Enter your private key: ").strip()
        connector.connect_account(private_key)
    
    else:
        logger.error("Invalid choice")
        return
    
    # Check balance
    balance = connector.get_balance()
    logger.info(f"Account balance: {balance} PURE")
    
    if balance == 0:
        logger.warning("Zero balance detected.")
        logger.info("PureChain has ZERO gas fees - deployment should still work!")
        proceed = input("Continue with deployment? (y/n): ").strip().lower()
        if proceed != 'y':
            logger.info("Deployment cancelled.")
            return
    
    # Deploy contracts
    print("\n" + "="*70)
    print("DEPLOYING CONTRACTS")
    print("="*70)
    
    contracts = {}
    
    try:
        # Deploy MonitoringLog
        monitoring_log = deploy_monitoring_log(connector)
        contracts['MonitoringLog'] = monitoring_log
        
        # Deploy AlertSystem
        alert_system = deploy_alert_system(connector)
        contracts['AlertSystem'] = alert_system
        
        # Deploy LeakageReport
        leakage_report = deploy_leakage_report(connector)
        contracts['LeakageReport'] = leakage_report
        
        # Deploy MaintenanceScheduler
        maintenance_scheduler = deploy_maintenance_scheduler(connector)
        contracts['MaintenanceScheduler'] = maintenance_scheduler
        
        # Save deployment info
        save_deployment_info(contracts)
        
        print("\n" + "="*70)
        print("✓ DEPLOYMENT COMPLETE")
        print("="*70)
        
        print("\nDeployed Contracts:")
        for name, info in contracts.items():
            print(f"  {name}: {info['address']}")
        
        print(f"\nNetwork: PureChain Testnet")
        print(f"Chain ID: 900520900520")
        print(f"Gas Fees: 0 PURE (Zero gas!)")
        
        # Test connection
        print("\n" + "="*70)
        print("TESTING BLOCKCHAIN CONNECTION")
        print("="*70)
        
        status = connector.get_network_status()
        print(f"✓ Connected: {status['connected']}")
        print(f"✓ Chain ID: {status['chainId']}")
        print(f"✓ Latest Block: {status['latestBlock']}")
        print(f"✓ Gas Price: {status['gasPrice']} (Zero!)")
        
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        raise


if __name__ == "__main__":
    main()
