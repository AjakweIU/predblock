"""
Deploy PredBlock Smart Contracts to PureChain
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from blockchain_layer.purechain_interface import PureChainInterface
from loguru import logger
import json


def load_contract(filename: str) -> str:
    """Load Solidity contract from file"""
    contract_path = os.path.join('blockchain_layer', 'contracts', filename)
    with open(contract_path, 'r') as f:
        return f.read()


def deploy_monitoring_log(purechain: PureChainInterface):
    """Deploy MonitoringLog contract"""
    logger.info("Deploying MonitoringLog contract...")
    
    source = load_contract('MonitoringLog.sol')
    result = purechain.deploy_contract(source)
    
    logger.success(f"MonitoringLog deployed at: {result['address']}")
    return result


def deploy_alert_system(purechain: PureChainInterface):
    """Deploy AlertSystem contract"""
    logger.info("Deploying AlertSystem contract...")
    
    source = load_contract('AlertSystem.sol')
    result = purechain.deploy_contract(source)
    
    logger.success(f"AlertSystem deployed at: {result['address']}")
    return result


def deploy_leakage_report(purechain: PureChainInterface):
    """Deploy LeakageReport contract"""
    logger.info("Deploying LeakageReport contract...")
    
    source = load_contract('LeakageReport.sol')
    result = purechain.deploy_contract(source)
    
    logger.success(f"LeakageReport deployed at: {result['address']}")
    return result


def deploy_maintenance_scheduler(purechain: PureChainInterface):
    """Deploy MaintenanceScheduler contract"""
    logger.info("Deploying MaintenanceScheduler contract...")
    
    source = load_contract('MaintenanceScheduler.sol')
    result = purechain.deploy_contract(source)
    
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
    print("PREDBLOCK - PURECHAIN DEPLOYMENT")
    print("="*70)
    
    # Check if bridge is running
    purechain = PureChainInterface()
    
    if not purechain.health_check():
        logger.error("PureChain bridge is not running!")
        logger.info("Start the bridge first:")
        logger.info("  cd blockchain_layer")
        logger.info("  npm install")
        logger.info("  npm start")
        return
    
    # Create or connect account
    print("\n" + "="*70)
    print("ACCOUNT SETUP")
    print("="*70)
    
    choice = input("\n1. Create new account\n2. Use existing private key\nChoice (1/2): ").strip()
    
    if choice == '1':
        logger.info("Creating new account...")
        account = purechain.create_account()
        
        print("\n⚠️  SAVE THESE CREDENTIALS SECURELY!")
        print(f"Address: {account['address']}")
        print(f"Private Key: {account['privateKey']}")
        print(f"Mnemonic: {account['mnemonic']}")
        
        purechain.connect_account(account['privateKey'])
        
        print("\n⚠️  You need testnet PURE tokens to deploy contracts.")
        print("Visit PureChain faucet to get testnet tokens.")
        input("Press Enter when you have tokens...")
    
    elif choice == '2':
        private_key = input("Enter your private key: ").strip()
        purechain.connect_account(private_key)
    
    else:
        logger.error("Invalid choice")
        return
    
    # Check balance
    balance = purechain.get_balance()
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
        monitoring_log = deploy_monitoring_log(purechain)
        contracts['MonitoringLog'] = monitoring_log
        
        # Deploy AlertSystem
        alert_system = deploy_alert_system(purechain)
        contracts['AlertSystem'] = alert_system
        
        # Deploy LeakageReport
        leakage_report = deploy_leakage_report(purechain)
        contracts['LeakageReport'] = leakage_report
        
        # Deploy MaintenanceScheduler
        maintenance_scheduler = deploy_maintenance_scheduler(purechain)
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
        
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        raise


if __name__ == "__main__":
    main()
