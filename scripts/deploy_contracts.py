"""
Smart Contract Deployment Script
Deploys all PredBlock contracts to blockchain
"""

import json
import os
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
from solcx import compile_standard, install_solc
import yaml


def compile_contract(contract_path: str, contract_name: str) -> dict:
    """Compile a Solidity contract"""
    
    print(f"Compiling {contract_name}...")
    
    with open(contract_path, 'r') as f:
        contract_source = f.read()
    
    # Install solc if needed
    try:
        install_solc('0.8.0')
    except:
        pass
    
    # Compile
    compiled_sol = compile_standard(
        {
            "language": "Solidity",
            "sources": {f"{contract_name}.sol": {"content": contract_source}},
            "settings": {
                "outputSelection": {
                    "*": {
                        "*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]
                    }
                }
            },
        },
        solc_version="0.8.0",
    )
    
    # Extract ABI and bytecode
    contract_interface = compiled_sol['contracts'][f'{contract_name}.sol'][contract_name]
    abi = contract_interface['abi']
    bytecode = contract_interface['evm']['bytecode']['object']
    
    return {'abi': abi, 'bytecode': bytecode}


def deploy_contract(w3: Web3, account: Account, contract_data: dict, contract_name: str) -> str:
    """Deploy a contract to blockchain"""
    
    print(f"\nDeploying {contract_name}...")
    
    # Create contract
    contract = w3.eth.contract(abi=contract_data['abi'], bytecode=contract_data['bytecode'])
    
    # Build transaction
    transaction = contract.constructor().build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 5000000,
        'gasPrice': w3.eth.gas_price
    })
    
    # Sign transaction
    signed_txn = w3.eth.account.sign_transaction(transaction, account.key)
    
    # Send transaction
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    print(f"Transaction hash: {tx_hash.hex()}")
    
    # Wait for receipt
    print("Waiting for confirmation...")
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    contract_address = tx_receipt.contractAddress
    print(f"✓ {contract_name} deployed at: {contract_address}")
    
    return contract_address


def save_abi(abi: list, contract_name: str):
    """Save contract ABI to file"""
    
    os.makedirs('blockchain_layer/contracts/abi', exist_ok=True)
    
    abi_path = f'blockchain_layer/contracts/abi/{contract_name}.json'
    with open(abi_path, 'w') as f:
        json.dump(abi, f, indent=2)
    
    print(f"ABI saved to {abi_path}")


def deploy_all_contracts(network: str = 'sepolia'):
    """Deploy all PredBlock contracts"""
    
    load_dotenv()
    
    print("="*60)
    print("PredBlock Smart Contract Deployment")
    print("="*60)
    
    # Connect to network
    infura_url = f"https://{network}.infura.io/v3/{os.getenv('INFURA_PROJECT_ID')}"
    w3 = Web3(Web3.HTTPProvider(infura_url))
    
    if not w3.is_connected():
        print("❌ Failed to connect to blockchain network")
        return
    
    print(f"✓ Connected to {network}")
    
    # Load account
    private_key = os.getenv('PRIVATE_KEY')
    account = Account.from_key(private_key)
    print(f"Deploying from account: {account.address}")
    
    balance = w3.eth.get_balance(account.address)
    print(f"Account balance: {w3.from_wei(balance, 'ether')} ETH")
    
    # Contracts to deploy
    contracts = [
        ('MonitoringLog', 'blockchain_layer/contracts/MonitoringLog.sol'),
        ('LeakageReport', 'blockchain_layer/contracts/LeakageReport.sol'),
        ('AlertSystem', 'blockchain_layer/contracts/AlertSystem.sol'),
        ('MaintenanceScheduler', 'blockchain_layer/contracts/MaintenanceScheduler.sol')
    ]
    
    deployed_addresses = {}
    
    for contract_name, contract_path in contracts:
        try:
            # Compile contract
            contract_data = compile_contract(contract_path, contract_name)
            
            # Save ABI
            save_abi(contract_data['abi'], contract_name)
            
            # Deploy contract
            address = deploy_contract(w3, account, contract_data, contract_name)
            deployed_addresses[contract_name] = address
            
        except Exception as e:
            print(f"❌ Error deploying {contract_name}: {e}")
    
    # Save deployment info
    print("\n" + "="*60)
    print("Deployment Summary")
    print("="*60)
    
    deployment_info = {
        'network': network,
        'deployer': account.address,
        'contracts': deployed_addresses
    }
    
    with open('blockchain_layer/deployment.json', 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    print("\nDeployed Contracts:")
    for name, address in deployed_addresses.items():
        print(f"  • {name}: {address}")
    
    print("\n✓ Deployment info saved to blockchain_layer/deployment.json")
    
    # Update .env template
    print("\nAdd these to your .env file:")
    for name, address in deployed_addresses.items():
        print(f"{name.upper()}_ADDRESS={address}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy PredBlock smart contracts')
    parser.add_argument('--network', type=str, default='sepolia', help='Blockchain network')
    
    args = parser.parse_args()
    
    deploy_all_contracts(network=args.network)
