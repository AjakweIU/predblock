"""
PureChain Interface for PredBlock
Python wrapper for PureChain blockchain via Node.js bridge
"""

import requests
import json
import time
from typing import Dict, List, Any, Optional
from loguru import logger


class PureChainInterface:
    """Interface to PureChain blockchain via Node.js bridge"""
    
    def __init__(self, 
                 bridge_url: str = "http://localhost:3000",
                 network: str = "testnet",
                 private_key: Optional[str] = None):
        """
        Initialize PureChain interface
        
        Args:
            bridge_url: URL of the Node.js bridge service
            network: 'testnet' or 'mainnet'
            private_key: Optional private key to connect wallet
        """
        self.bridge_url = bridge_url.rstrip('/')
        self.network = network
        self.private_key = private_key
        self.address = None
        
        # Initialize connection
        self._initialize()
    
    def _initialize(self):
        """Initialize PureChain connection"""
        try:
            response = requests.post(
                f"{self.bridge_url}/api/init",
                json={
                    "network": self.network,
                    "privateKey": self.private_key
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.address = data.get('address')
                    logger.info(f"Connected to PureChain {self.network}")
                    if self.address:
                        logger.info(f"Wallet address: {self.address}")
                else:
                    logger.error(f"Failed to initialize: {data.get('error')}")
            else:
                logger.error(f"Bridge connection failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to connect to PureChain bridge: {e}")
            logger.warning("Make sure the bridge is running: node blockchain_layer/purechain_bridge.js")
    
    def create_account(self) -> Dict[str, str]:
        """
        Create new PureChain account
        
        Returns:
            Dictionary with address, privateKey, and mnemonic
        """
        try:
            response = requests.post(
                f"{self.bridge_url}/api/account/create",
                timeout=30
            )
            
            data = response.json()
            if data.get('success'):
                return data['account']
            else:
                raise Exception(data.get('error', 'Unknown error'))
        except Exception as e:
            logger.error(f"Failed to create account: {e}")
            raise
    
    def connect_account(self, private_key: str) -> str:
        """
        Connect account with private key
        
        Args:
            private_key: Private key to connect
            
        Returns:
            Connected address
        """
        try:
            response = requests.post(
                f"{self.bridge_url}/api/account/connect",
                json={"privateKey": private_key},
                timeout=30
            )
            
            data = response.json()
            if data.get('success'):
                self.address = data['address']
                self.private_key = private_key
                return self.address
            else:
                raise Exception(data.get('error', 'Unknown error'))
        except Exception as e:
            logger.error(f"Failed to connect account: {e}")
            raise
    
    def get_balance(self, address: Optional[str] = None) -> float:
        """
        Get balance in PURE
        
        Args:
            address: Address to check (uses connected address if None)
            
        Returns:
            Balance in PURE
        """
        try:
            addr = address or self.address
            if not addr:
                raise Exception("No address specified and no wallet connected")
            
            response = requests.get(
                f"{self.bridge_url}/api/balance/{addr}",
                timeout=30
            )
            
            data = response.json()
            if data.get('success'):
                return float(data['balance'])
            else:
                raise Exception(data.get('error', 'Unknown error'))
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            raise
    
    def deploy_contract(self, 
                       solidity_source: str,
                       constructor_args: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Deploy smart contract to PureChain
        
        Args:
            solidity_source: Solidity source code
            constructor_args: Constructor arguments
            
        Returns:
            Dictionary with contractAddress and abi
        """
        try:
            response = requests.post(
                f"{self.bridge_url}/api/contract/deploy",
                json={
                    "source": solidity_source,
                    "constructorArgs": constructor_args or []
                },
                timeout=120
            )
            
            data = response.json()
            if data.get('success'):
                logger.info(f"Contract deployed at: {data['contractAddress']}")
                return {
                    'address': data['contractAddress'],
                    'abi': data['abi']
                }
            else:
                raise Exception(data.get('error', 'Unknown error'))
        except Exception as e:
            logger.error(f"Failed to deploy contract: {e}")
            raise
    
    def call_contract(self,
                     contract_address: str,
                     abi: List[Dict],
                     method: str,
                     args: Optional[List[Any]] = None) -> Any:
        """
        Call contract method (read-only)
        
        Args:
            contract_address: Contract address
            abi: Contract ABI
            method: Method name
            args: Method arguments
            
        Returns:
            Method return value
        """
        try:
            response = requests.post(
                f"{self.bridge_url}/api/contract/call",
                json={
                    "contractAddress": contract_address,
                    "abi": abi,
                    "method": method,
                    "args": args or []
                },
                timeout=30
            )
            
            data = response.json()
            if data.get('success'):
                return data['result']
            else:
                raise Exception(data.get('error', 'Unknown error'))
        except Exception as e:
            logger.error(f"Failed to call contract: {e}")
            raise
    
    def execute_contract(self,
                        contract_address: str,
                        abi: List[Dict],
                        method: str,
                        args: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Execute contract method (state-changing)
        
        Args:
            contract_address: Contract address
            abi: Contract ABI
            method: Method name
            args: Method arguments
            
        Returns:
            Transaction receipt
        """
        try:
            response = requests.post(
                f"{self.bridge_url}/api/contract/execute",
                json={
                    "contractAddress": contract_address,
                    "abi": abi,
                    "method": method,
                    "args": args or []
                },
                timeout=60
            )
            
            data = response.json()
            if data.get('success'):
                logger.info(f"Transaction: {data['transactionHash']}")
                return data['receipt']
            else:
                raise Exception(data.get('error', 'Unknown error'))
        except Exception as e:
            logger.error(f"Failed to execute contract: {e}")
            raise
    
    def send_transaction(self, to: str, value: str) -> Dict[str, Any]:
        """
        Send PURE to address
        
        Args:
            to: Recipient address
            value: Amount in PURE (e.g., "1.0")
            
        Returns:
            Transaction receipt
        """
        try:
            response = requests.post(
                f"{self.bridge_url}/api/transaction/send",
                json={
                    "to": to,
                    "value": value
                },
                timeout=60
            )
            
            data = response.json()
            if data.get('success'):
                logger.info(f"Transaction sent: {data['transactionHash']}")
                return data['receipt']
            else:
                raise Exception(data.get('error', 'Unknown error'))
        except Exception as e:
            logger.error(f"Failed to send transaction: {e}")
            raise
    
    def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """
        Get transaction details
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Transaction details
        """
        try:
            response = requests.get(
                f"{self.bridge_url}/api/transaction/{tx_hash}",
                timeout=30
            )
            
            data = response.json()
            if data.get('success'):
                return data['transaction']
            else:
                raise Exception(data.get('error', 'Unknown error'))
        except Exception as e:
            logger.error(f"Failed to get transaction: {e}")
            raise
    
    def get_block(self, block_number: Optional[int] = None) -> Dict[str, Any]:
        """
        Get block information
        
        Args:
            block_number: Block number (latest if None)
            
        Returns:
            Block details
        """
        try:
            endpoint = f"{self.bridge_url}/api/block"
            if block_number is not None:
                endpoint += f"/{block_number}"
            
            response = requests.get(endpoint, timeout=30)
            
            data = response.json()
            if data.get('success'):
                return data['block']
            else:
                raise Exception(data.get('error', 'Unknown error'))
        except Exception as e:
            logger.error(f"Failed to get block: {e}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get network status
        
        Returns:
            Network status information
        """
        try:
            response = requests.get(
                f"{self.bridge_url}/api/status",
                timeout=30
            )
            
            data = response.json()
            if data.get('success'):
                return data['status']
            else:
                raise Exception(data.get('error', 'Unknown error'))
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            raise
    
    def health_check(self) -> bool:
        """
        Check if bridge is running
        
        Returns:
            True if bridge is healthy
        """
        try:
            response = requests.get(
                f"{self.bridge_url}/health",
                timeout=5
            )
            
            data = response.json()
            return data.get('success', False)
        except:
            return False
