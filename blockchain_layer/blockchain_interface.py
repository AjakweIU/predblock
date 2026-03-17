"""
Blockchain Interface for PredBlock
Handles interaction with smart contracts
"""

from web3 import Web3
from eth_account import Account
import json
import os
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
import yaml


class BlockchainInterface:
    """Interface for interacting with blockchain smart contracts"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize blockchain connection"""
        load_dotenv()
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        blockchain_config = self.config['blockchain']
        
        # Connect to blockchain network
        infura_url = f"https://{blockchain_config['testnet']}.infura.io/v3/{os.getenv('INFURA_PROJECT_ID')}"
        self.w3 = Web3(Web3.HTTPProvider(infura_url))
        
        # Load account
        private_key = os.getenv('PRIVATE_KEY')
        if private_key:
            self.account = Account.from_key(private_key)
        else:
            self.account = None
        
        # Contract instances
        self.contracts = {}
        
        print(f"Connected to blockchain: {self.w3.is_connected()}")
    
    def load_contract(self, contract_name: str, contract_address: str = None) -> object:
        """Load a smart contract"""
        
        # Load ABI
        abi_path = f"blockchain_layer/contracts/abi/{contract_name}.json"
        
        if not os.path.exists(abi_path):
            print(f"Warning: ABI file not found at {abi_path}")
            return None
        
        with open(abi_path, 'r') as f:
            contract_abi = json.load(f)
        
        # Get contract address
        if contract_address is None:
            contract_address = os.getenv(f'{contract_name.upper()}_ADDRESS')
        
        if contract_address is None:
            print(f"Warning: Contract address not found for {contract_name}")
            return None
        
        # Create contract instance
        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=contract_abi
        )
        
        self.contracts[contract_name] = contract
        print(f"Loaded contract: {contract_name} at {contract_address}")
        
        return contract
    
    def add_monitoring_record(self, 
                             pressure: float,
                             temperature: float,
                             flow_rate: float,
                             h2o: float,
                             h2s: float,
                             so2: float,
                             o2: float,
                             nox: float,
                             sensor_id: str) -> Optional[str]:
        """Add a monitoring record to blockchain"""
        
        if 'MonitoringLog' not in self.contracts:
            print("MonitoringLog contract not loaded")
            return None
        
        contract = self.contracts['MonitoringLog']
        
        # Convert to contract format (multiply by 100 for precision)
        pressure_val = int(pressure * 100)
        temperature_val = int(temperature * 100)
        flow_rate_val = int(flow_rate * 100)
        h2o_val = int(h2o)
        h2s_val = int(h2s)
        so2_val = int(so2)
        o2_val = int(o2)
        nox_val = int(nox)
        
        # Build transaction
        transaction = contract.functions.addRecord(
            pressure_val,
            temperature_val,
            flow_rate_val,
            h2o_val,
            h2s_val,
            so2_val,
            o2_val,
            nox_val,
            sensor_id
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 300000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        # Sign and send transaction
        signed_txn = self.w3.eth.account.sign_transaction(transaction, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        # Wait for receipt
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return tx_hash.hex()
    
    def report_leakage(self,
                      detection_timestamp: int,
                      location: str,
                      severity: int,
                      pressure_drop: float,
                      o2_level: float,
                      acoustic_signal: float,
                      description: str,
                      evidence_hash: bytes) -> Optional[str]:
        """Report a leakage incident"""
        
        if 'LeakageReport' not in self.contracts:
            print("LeakageReport contract not loaded")
            return None
        
        contract = self.contracts['LeakageReport']
        
        # Convert values
        pressure_drop_val = int(pressure_drop * 100)
        o2_level_val = int(o2_level)
        acoustic_signal_val = int(acoustic_signal)
        
        # Build transaction
        transaction = contract.functions.reportIncident(
            detection_timestamp,
            location,
            severity,
            pressure_drop_val,
            o2_level_val,
            acoustic_signal_val,
            description,
            evidence_hash
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 500000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        # Sign and send
        signed_txn = self.w3.eth.account.sign_transaction(transaction, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return tx_hash.hex()
    
    def trigger_alert(self,
                     alert_type: int,
                     sensor_id: str,
                     description: str,
                     value: float) -> Optional[str]:
        """Trigger an alert on blockchain"""
        
        if 'AlertSystem' not in self.contracts:
            print("AlertSystem contract not loaded")
            return None
        
        contract = self.contracts['AlertSystem']
        
        # Convert value
        value_val = int(value * 100)
        
        # Build transaction
        transaction = contract.functions.triggerAlert(
            alert_type,
            sensor_id,
            description,
            value_val
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 300000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        # Sign and send
        signed_txn = self.w3.eth.account.sign_transaction(transaction, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return tx_hash.hex()
    
    def schedule_maintenance(self,
                           scheduled_time: int,
                           maintenance_type: int,
                           priority: int,
                           location: str,
                           description: str,
                           required_actions: List[str],
                           estimated_duration: int,
                           ai_prediction_hash: bytes) -> Optional[str]:
        """Schedule a maintenance task"""
        
        if 'MaintenanceScheduler' not in self.contracts:
            print("MaintenanceScheduler contract not loaded")
            return None
        
        contract = self.contracts['MaintenanceScheduler']
        
        # Build transaction
        transaction = contract.functions.scheduleTask(
            scheduled_time,
            maintenance_type,
            priority,
            location,
            description,
            required_actions,
            estimated_duration,
            ai_prediction_hash
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 500000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        # Sign and send
        signed_txn = self.w3.eth.account.sign_transaction(transaction, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return tx_hash.hex()
    
    def get_record_count(self, contract_name: str) -> int:
        """Get total record count from a contract"""
        
        if contract_name not in self.contracts:
            return 0
        
        contract = self.contracts[contract_name]
        
        if contract_name == 'MonitoringLog':
            return contract.functions.getRecordCount().call()
        elif contract_name == 'AlertSystem':
            return contract.functions.getAlertCount().call()
        elif contract_name == 'LeakageReport':
            return contract.functions.getIncidentCount().call()
        elif contract_name == 'MaintenanceScheduler':
            return contract.functions.getTaskCount().call()
        
        return 0
    
    def get_active_alerts(self) -> List[int]:
        """Get list of active alert IDs"""
        
        if 'AlertSystem' not in self.contracts:
            return []
        
        contract = self.contracts['AlertSystem']
        return contract.functions.getActiveAlerts().call()
    
    def get_gas_used(self, tx_hash: str) -> int:
        """Get gas used for a transaction"""
        receipt = self.w3.eth.get_transaction_receipt(tx_hash)
        return receipt['gasUsed']
    
    def estimate_transaction_cost(self, tx_hash: str) -> float:
        """Estimate transaction cost in ETH"""
        receipt = self.w3.eth.get_transaction_receipt(tx_hash)
        gas_used = receipt['gasUsed']
        gas_price = self.w3.eth.get_transaction(tx_hash)['gasPrice']
        cost_wei = gas_used * gas_price
        cost_eth = self.w3.from_wei(cost_wei, 'ether')
        return float(cost_eth)


if __name__ == "__main__":
    # Example usage
    interface = BlockchainInterface()
    
    # Load contracts (requires deployed addresses)
    # interface.load_contract('MonitoringLog', '0x...')
    # interface.load_contract('AlertSystem', '0x...')
