import os
import time
from typing import Any, Dict, Optional

from eth_typing import HexStr
from web3 import Web3
from web3.types import BlockData

from .utils.contract_utility import ContractUtility
from .utils.rofl_utility import RoflUtility


class HeaderOracle:
    """
    Header Oracle that fetches block headers from a source chain
    and submits them to the ROFLAdapter contract on Oasis Sapphire.
    """

    def __init__(self) -> None:
        """
        Initialize the HeaderOracle.
        All configuration is read from environment variables.
        """
        # Load configuration from environment
        self._load_config()

        # Initialize ROFL utility and fetch secret
        self.rofl_utility = RoflUtility()
        self.secret = self.rofl_utility.fetch_key("header-oracle")

        # Initialize contract utility
        self.contract_utility = ContractUtility(self.network, self.secret)

        # Connect to source chain
        self.source_w3 = Web3(Web3.HTTPProvider(self.source_rpc_url))
        if not self.source_w3.is_connected():
            raise Exception(
                f"Failed to connect to source chain at {self.source_rpc_url}"
            )

        # Load ROFLAdapter ABI
        self.rofl_adapter_abi = self._load_rofl_adapter_abi()

        # Create contract instance
        self.contract = self.contract_utility.w3.eth.contract(
            address=self.contract_address, abi=self.rofl_adapter_abi
        )

        # Track last processed block
        self.last_processed_block = 0

        print("HeaderOracle initialized:")
        print(f"  Source RPC: {self.source_rpc_url}")
        print(f"  Source Chain ID: {self.source_chain_id}")
        print(f"  Target Network: {self.network}")
        print(f"  Contract Address: {self.contract_address}")
        print(f"  Polling Interval: {self.polling_interval}s")

    def _load_config(self) -> None:
        """
        Load configuration from environment variables.
        """
        # Required configuration
        contract_address = os.environ.get("CONTRACT_ADDRESS", "")
        if not contract_address:
            raise Exception("CONTRACT_ADDRESS environment variable is not set")

        self.contract_address = Web3.to_checksum_address(contract_address)

        # Network configuration
        self.network = os.environ.get("NETWORK", "sapphire-testnet")

        # Source chain configuration
        self.source_rpc_url = os.environ.get(
            "SOURCE_RPC_URL", "https://ethereum.publicnode.com"
        )
        self.source_chain_id = int(os.environ.get("SOURCE_CHAIN_ID", "1"))

        # Oracle configuration
        self.polling_interval = int(os.environ.get("POLLING_INTERVAL", "12"))

    def _load_rofl_adapter_abi(self) -> list[Dict[str, Any]]:
        """
        Load the ROFLAdapter ABI.
        For now, we'll define it inline based on the contract interface.
        """
        # Minimal ABI for the storeBlockHeader function
        return [
            {
                "inputs": [
                    {"name": "chainId", "type": "uint256"},
                    {"name": "blockNumber", "type": "uint256"},
                    {"name": "blockHash", "type": "bytes32"},
                ],
                "name": "storeBlockHeader",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            }
        ]

    def fetch_latest_block(self) -> Optional[BlockData]:
        """
        Fetch the latest block from the source chain.

        :return: Block data or None if fetch fails
        """
        try:
            block = self.source_w3.eth.get_block("latest")
            return block
        except Exception as e:
            print(f"Error fetching latest block: {e}")
            return None

    def submit_block_header(self, block_number: int, block_hash: str) -> bool:
        """
        Submit a block header to the ROFLAdapter contract.

        :param block_number: The block number
        :param block_hash: The block hash
        :return: True if submission was successful, False otherwise
        """
        try:
            # Build and submit the transaction
            tx_params = self.contract.functions.storeBlockHeader(
                self.source_chain_id, block_number, block_hash
            ).build_transaction({'gasPrice': self.contract_utility.w3.eth.gas_price})
            
            print(f"Submitting block header for block {block_number}")
            tx_hash = self.rofl_utility.submit_tx(tx_params)
            
            # Wait for transaction receipt
            tx_receipt = self.contract_utility.w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"Transaction submitted. Hash: {tx_receipt.transactionHash.hex()}")
            return True

        except Exception as e:
            print(f"Error submitting block header: {e}")
            return False

    def run(self) -> None:
        """
        Main loop that continuously fetches and submits block headers.
        """
        print("Starting HeaderOracle main loop...")

        while True:
            try:
                # Fetch the latest block
                block = self.fetch_latest_block()

                if block:
                    block_number = block.get("number")
                    block_hash = block.get("hash")
                    
                    if block_number is not None and block_hash is not None and block_number > self.last_processed_block:
                        # Convert block_hash to hex string with 0x prefix
                        block_hash_hex = block_hash.hex() if isinstance(block_hash, bytes) else block_hash
                        if not block_hash_hex.startswith('0x'):
                            block_hash_hex = '0x' + block_hash_hex
                        
                        # Submit the block header
                        success = self.submit_block_header(
                            block_number, block_hash_hex
                        )

                        if success:
                            self.last_processed_block = block_number
                            print(f"Successfully processed block {block_number}")
                        else:
                            print(f"Failed to process block {block_number}, will retry")

                # Wait before next poll
                time.sleep(self.polling_interval)

            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(self.polling_interval)
