import os
import time
import codecs
from typing import Any, Dict, Optional

import cbor2
from web3 import Web3
from web3.types import BlockData, TxParams, Wei

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
        
        # Fetch chain ID from the connected RPC endpoint
        self.source_chain_id = self.source_w3.eth.chain_id

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

    def _decode_rofl_response(self, response_hex: str) -> Dict[str, Any]:
        """
        Decode CBOR response from ROFL service.
        
        :param response_hex: Hex-encoded CBOR response
        :return: Decoded CBOR data as dictionary
        """
        try:
            data_bytes = codecs.decode(response_hex, "hex")
            cbor_result = cbor2.loads(data_bytes)
            print(f"  Decoded CBOR: {cbor_result}")
            return cbor_result if isinstance(cbor_result, dict) else {"data": cbor_result}
        except Exception as decode_error:
            print(f"  CBOR decode error: {decode_error}")
            return {"error": "decode_failed", "raw": response_hex}

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
            # Build the transaction with required fields for ROFL
            # ROFL will handle nonce, from address, and signing
            tx_dict: TxParams = {
                'gas': 300000,  # Set explicit gas limit
                'gasPrice': self.contract_utility.w3.eth.gas_price,
                'value': Wei(0)  # No ETH value for this transaction
            }
            tx_params = self.contract.functions.storeBlockHeader(
                self.source_chain_id, block_number, block_hash
            ).build_transaction(tx_dict)
            
            print(f"Submitting block header for block {block_number}, hash: {block_hash}")
            
            try:
                rofl_response = self.rofl_utility.submit_tx(tx_params)
                print(f"ROFL response received: {rofl_response}")
                
                # Decode CBOR response to check for success
                decoded_response = self._decode_rofl_response(rofl_response)
                
                # Check for success indicator as done in the demo
                if 'ok' in decoded_response:
                    print("  ✓ Transaction submitted successfully to ROFL")
                    return True
                elif 'error' in decoded_response:
                    print(f"  ✗ ROFL transaction failed: {decoded_response}")
                    return False
                else:
                    print(f"  ⚠ Unknown ROFL response format: {decoded_response}")
                    # If no clear error, assume success (ROFL accepted the transaction)
                    return True
            except Exception as submit_error:
                print(f"Transaction submission failed: {submit_error}")
                return False

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
