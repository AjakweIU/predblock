"""
Direct PureChain Connector using Web3.py
No Node.js bridge required - pure Python implementation
Based on PureProt's approach
"""

from web3 import Web3
try:
    from web3.middleware import ExtraDataToPOAMiddleware as poa_middleware
except ImportError:
    from web3.middleware import geth_poa_middleware as poa_middleware
import json
import hashlib
import time
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from loguru import logger
from solcx import compile_source, install_solc, set_solc_version


class PureChainConnector:
    """
    Direct Python connector to PureChain blockchain.
    Eliminates the need for Node.js bridge.
    """
    
    # Official PureChain Network Configuration
    PURECHAIN_TESTNET = {
        'rpc_url': 'https://purechainnode.com',
        'chain_id': 900520900520,
        'gas_price': 0,  # Zero gas fees!
        'gas_limit': 8000000
    }
    
    PURECHAIN_MAINNET = {
        'rpc_url': 'https://purechainnode.com',
        'chain_id': 900520900520,
        'gas_price': 0,  # Zero gas fees!
        'gas_limit': 8000000
    }
    
    def __init__(self, 
                 private_key: Optional[str] = None,
                 network: str = 'testnet',
                 rpc_url: Optional[str] = None,
                 chain_id: Optional[int] = None):
        """
        Initialize PureChain connector.
        
        Args:
            private_key: Private key for signing transactions
            network: 'testnet' or 'mainnet'
            rpc_url: Custom RPC URL (overrides network default)
            chain_id: Custom chain ID (overrides network default)
        """
        # Configure network
        if network == 'testnet':
            config = self.PURECHAIN_TESTNET
        elif network == 'mainnet':
            config = self.PURECHAIN_MAINNET
        else:
            raise ValueError(
                f"Unknown network '{network}'. Use 'testnet' or 'mainnet'."
            )
        
        self.rpc_url = rpc_url or config['rpc_url']
        self.chain_id = chain_id or config['chain_id']
        self.gas_price = config['gas_price']
        self.gas_limit = config['gas_limit']
        self.network = network
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Add PoA middleware for PureChain compatibility
        self.w3.middleware_onion.inject(poa_middleware, layer=0)
        
        # Check connection
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to PureChain at {self.rpc_url}")
        
        logger.info(f"Connected to PureChain {network}")
        logger.info(f"RPC: {self.rpc_url}")
        logger.info(f"Chain ID: {self.chain_id}")
        
        # Setup account if private key provided
        self.account = None
        self.address = None
        if private_key:
            self.connect_account(private_key)
    
    def connect_account(self, private_key: str):
        """
        Connect account with private key.
        
        Args:
            private_key: Private key (with or without 0x prefix)
        """
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
        
        self.account = self.w3.eth.account.from_key(private_key)
        self.address = self.account.address
        
        logger.info(f"Account connected: {self.address}")
        
        # Check balance
        balance = self.get_balance()
        logger.info(f"Account balance: {balance} PURE")
    
    def create_account(self) -> Dict[str, str]:
        """
        Create new PureChain account.
        
        Returns:
            Dictionary with address, privateKey, and mnemonic
        """
        account = self.w3.eth.account.create()
        
        return {
            'address': account.address,
            'privateKey': account.key.hex(),
            'mnemonic': None  # Web3.py doesn't generate mnemonics by default
        }
    
    def get_balance(self, address: Optional[str] = None) -> float:
        """
        Get balance in PURE.
        
        Args:
            address: Address to check (uses connected address if None)
            
        Returns:
            Balance in PURE
        """
        addr = address or self.address
        if not addr:
            raise ValueError("No address specified and no account connected")
        
        balance_wei = self.w3.eth.get_balance(addr)
        balance_eth = self.w3.from_wei(balance_wei, 'ether')
        
        return float(balance_eth)
    
    def compile_contract(self, solidity_source: str) -> Dict[str, Any]:
        """
        Compile Solidity contract.
        
        Args:
            solidity_source: Solidity source code
            
        Returns:
            Dictionary with abi and bytecode
        """
        try:
            # Install solc if needed
            try:
                set_solc_version('0.8.0')
            except:
                logger.info("Installing solc 0.8.0...")
                install_solc('0.8.0')
                set_solc_version('0.8.0')
            
            # Compile
            compiled = compile_source(solidity_source)
            
            # Get first contract
            contract_id, contract_interface = list(compiled.items())[0]
            
            return {
                'abi': contract_interface['abi'],
                'bytecode': contract_interface['bin']
            }
        
        except Exception as e:
            logger.error(f"Contract compilation failed: {e}")
            raise
    
    def deploy_contract(self, 
                       solidity_source: str,
                       constructor_args: Optional[list] = None) -> Dict[str, Any]:
        """
        Deploy smart contract to PureChain.
        
        Args:
            solidity_source: Solidity source code
            constructor_args: Constructor arguments
            
        Returns:
            Dictionary with address and abi
        """
        if not self.account:
            raise ValueError("No account connected. Call connect_account() first.")
        
        logger.info("Compiling contract...")
        compiled = self.compile_contract(solidity_source)
        
        # Create contract instance
        Contract = self.w3.eth.contract(
            abi=compiled['abi'],
            bytecode=compiled['bytecode']
        )
        
        # Build deployment transaction
        logger.info("Building deployment transaction...")
        constructor = Contract.constructor(*(constructor_args or []))
        
        tx = constructor.build_transaction({
            'from': self.address,
            'nonce': self.w3.eth.get_transaction_count(self.address),
            'gas': self.gas_limit,
            'gasPrice': self.gas_price,
            'chainId': self.chain_id
        })
        
        # Sign and send
        logger.info("Signing and sending transaction...")
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Wait for receipt
        logger.info(f"Waiting for transaction {tx_hash.hex()}...")
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status != 1:
            raise Exception("Contract deployment failed")
        
        contract_address = receipt.contractAddress
        
        logger.success(f"Contract deployed at: {contract_address}")
        logger.info(f"Gas used: {receipt.gasUsed}")
        
        return {
            'address': contract_address,
            'abi': compiled['abi'],
            'transactionHash': tx_hash.hex(),
            'gasUsed': receipt.gasUsed
        }
    
    def get_contract(self, address: str, abi: list):
        """
        Get contract instance.
        
        Args:
            address: Contract address
            abi: Contract ABI
            
        Returns:
            Contract instance
        """
        return self.w3.eth.contract(address=address, abi=abi)
    
    def call_contract(self,
                     contract_address: str,
                     abi: list,
                     method: str,
                     args: Optional[list] = None) -> Any:
        """
        Call contract method (read-only).
        
        Args:
            contract_address: Contract address
            abi: Contract ABI
            method: Method name
            args: Method arguments
            
        Returns:
            Method return value
        """
        contract = self.get_contract(contract_address, abi)
        func = getattr(contract.functions, method)
        
        return func(*(args or [])).call()
    
    def execute_contract(self,
                        contract_address: str,
                        abi: list,
                        method: str,
                        args: Optional[list] = None) -> Dict[str, Any]:
        """
        Execute contract method (state-changing).
        
        Args:
            contract_address: Contract address
            abi: Contract ABI
            method: Method name
            args: Method arguments
            
        Returns:
            Transaction receipt
        """
        if not self.account:
            raise ValueError("No account connected. Call connect_account() first.")
        
        contract = self.get_contract(contract_address, abi)
        func = getattr(contract.functions, method)
        
        # Build transaction
        tx = func(*(args or [])).build_transaction({
            'from': self.address,
            'nonce': self.w3.eth.get_transaction_count(self.address),
            'gas': 1000000,
            'gasPrice': self.gas_price,
            'chainId': self.chain_id
        })
        
        # Sign and send
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Wait for receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status != 1:
            raise Exception(f"Transaction failed: {method}")
        
        logger.info(f"Transaction successful: {tx_hash.hex()}")
        
        return {
            'transactionHash': tx_hash.hex(),
            'blockNumber': receipt.blockNumber,
            'gasUsed': receipt.gasUsed,
            'status': receipt.status
        }
    
    def send_transaction(self, to: str, value: str) -> Dict[str, Any]:
        """
        Send PURE to address.
        
        Args:
            to: Recipient address
            value: Amount in PURE (e.g., "1.0")
            
        Returns:
            Transaction receipt
        """
        if not self.account:
            raise ValueError("No account connected. Call connect_account() first.")
        
        value_wei = self.w3.to_wei(float(value), 'ether')
        
        tx = {
            'from': self.address,
            'to': to,
            'value': value_wei,
            'nonce': self.w3.eth.get_transaction_count(self.address),
            'gas': 21000,
            'gasPrice': self.gas_price,
            'chainId': self.chain_id
        }
        
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return {
            'transactionHash': tx_hash.hex(),
            'blockNumber': receipt.blockNumber,
            'gasUsed': receipt.gasUsed,
            'status': receipt.status
        }
    
    def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """
        Get transaction details.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Transaction details
        """
        tx = self.w3.eth.get_transaction(tx_hash)
        
        return {
            'hash': tx.hash.hex(),
            'from': tx['from'],
            'to': tx.to,
            'value': str(self.w3.from_wei(tx.value, 'ether')),
            'gas': tx.gas,
            'gasPrice': tx.gasPrice,
            'nonce': tx.nonce,
            'blockNumber': tx.blockNumber
        }
    
    def get_block(self, block_number: Optional[int] = None) -> Dict[str, Any]:
        """
        Get block information.
        
        Args:
            block_number: Block number (latest if None)
            
        Returns:
            Block details
        """
        block = self.w3.eth.get_block(block_number or 'latest')
        
        return {
            'number': block.number,
            'hash': block.hash.hex(),
            'timestamp': block.timestamp,
            'transactions': len(block.transactions),
            'gasUsed': block.gasUsed,
            'gasLimit': block.gasLimit
        }
    
    def get_network_status(self) -> Dict[str, Any]:
        """
        Get network status.
        
        Returns:
            Network information
        """
        latest_block = self.w3.eth.block_number
        
        return {
            'connected': self.w3.is_connected(),
            'chainId': self.chain_id,
            'latestBlock': latest_block,
            'gasPrice': self.gas_price,
            'peerCount': self.w3.net.peer_count if hasattr(self.w3.net, 'peer_count') else 0
        }
    
    def health_check(self) -> bool:
        """
        Check if connection is healthy.
        
        Returns:
            True if connected
        """
        return self.w3.is_connected()


class PredBlockAuditor:
    """
    Comprehensive blockchain auditor for PredBlock.
    Based on PureProt's audit system.
    """
    
    def __init__(self, connector: PureChainConnector):
        """
        Initialize auditor.
        
        Args:
            connector: PureChain connector instance
        """
        self.connector = connector
    
    def calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA-256 hash of a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            SHA-256 hash as hex string
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    def calculate_data_hash(self, data: Dict[str, Any]) -> str:
        """
        Calculate hash of data dictionary.
        
        Args:
            data: Data dictionary
            
        Returns:
            SHA-256 hash
        """
        data_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(data_json.encode()).hexdigest()
    
    def create_audit_record(self,
                           timestamp: int,
                           sensor_data: Dict[str, float],
                           predictions: Dict[str, Any],
                           model_path: Optional[str] = None,
                           alert_triggered: bool = False,
                           parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create comprehensive audit record.
        
        Args:
            timestamp: Unix timestamp
            sensor_data: Sensor readings
            predictions: AI predictions
            model_path: Path to trained model file
            alert_triggered: Whether alert was triggered
            parameters: Additional parameters
            
        Returns:
            Complete audit record
        """
        audit_record = {
            'timestamp': timestamp,
            'sensor_data': sensor_data,
            'predictions': predictions,
            'alert_triggered': alert_triggered,
            'software_version': 'PredBlock-1.0.0',
            'hashes': {}
        }
        
        # Hash AI model file if provided
        if model_path and os.path.exists(model_path):
            audit_record['hashes']['ai_model'] = self.calculate_file_hash(model_path)
            audit_record['model_path'] = os.path.basename(model_path)
        
        # Hash sensor data
        audit_record['hashes']['sensor_data'] = self.calculate_data_hash(sensor_data)
        
        # Hash predictions
        audit_record['hashes']['predictions'] = self.calculate_data_hash(predictions)
        
        # Hash parameters if provided
        if parameters:
            audit_record['hashes']['parameters'] = self.calculate_data_hash(parameters)
            audit_record['parameters'] = parameters
        
        # Calculate master hash of entire audit record
        audit_json = json.dumps(audit_record, sort_keys=True, separators=(',', ':'))
        audit_record['master_hash'] = hashlib.sha256(audit_json.encode()).hexdigest()
        
        return audit_record
    
    def record_to_blockchain(self,
                            audit_record: Dict[str, Any],
                            contract_address: str,
                            contract_abi: list) -> str:
        """
        Record audit to blockchain.
        
        Args:
            audit_record: Audit record
            contract_address: MonitoringLog contract address
            contract_abi: Contract ABI
            
        Returns:
            Transaction hash
        """
        # Record on blockchain
        receipt = self.connector.execute_contract(
            contract_address=contract_address,
            abi=contract_abi,
            method='logReading',
            args=[
                audit_record['timestamp'],
                audit_record['master_hash'],
                json.dumps(audit_record['hashes'])
            ]
        )
        
        logger.success(f"Audit recorded on blockchain: {receipt['transactionHash']}")
        
        return receipt['transactionHash']
    
    def verify_audit(self,
                    local_audit: Dict[str, Any],
                    blockchain_hash: str) -> bool:
        """
        Verify audit against blockchain record.
        
        Args:
            local_audit: Local audit record
            blockchain_hash: Hash from blockchain
            
        Returns:
            True if verified
        """
        local_hash = local_audit['master_hash']
        verified = local_hash == blockchain_hash
        
        if verified:
            logger.success("✓ Audit verification successful")
        else:
            logger.error("✗ Audit verification failed")
            logger.error(f"  Local hash: {local_hash}")
            logger.error(f"  Blockchain hash: {blockchain_hash}")
        
        return verified
