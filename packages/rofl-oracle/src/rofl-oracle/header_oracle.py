import os
import time

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

    def __init__(self):
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

    def _load_config(self):
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

    def _load_rofl_adapter_abi(self) -> list:
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

    def fetch_latest_block(self) -> BlockData | None:
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

    def submit_block_header(self, block_number: int, block_hash: HexStr) -> bool:
        """
        Submit a block header to the ROFLAdapter contract.

        :param block_number: The block number
        :param block_hash: The block hash
        :return: True if submission was successful, False otherwise
        """
        try:
            # Build the transaction
            function = self.contract.functions.storeBlockHeader(
                self.source_chain_id, block_number, block_hash
            )

            # Get the transaction data
            tx_data = function.build_transaction(
                {
                    "from": self.contract_utility.w3.eth.default_account,
                    "nonce": self.contract_utility.w3.eth.get_transaction_count(
                        self.contract_utility.w3.eth.default_account
                    ),
                    "gas": 200000,
                    "gasPrice": self.contract_utility.w3.eth.gas_price,
                }
            )

            # Submit the transaction using ROFL utility
            print(f"Submitting block header for block {block_number}")
            result = self.rofl_utility.submit_tx(tx_data)

            print(f"Transaction submitted: {result}")
            return True

        except Exception as e:
            print(f"Error submitting block header: {e}")
            return False

    def run(self):
        """
        Main loop that continuously fetches and submits block headers.
        """
        print("Starting HeaderOracle main loop...")

        while True:
            try:
                # Fetch the latest block
                block = self.fetch_latest_block()

                if block and block["number"] > self.last_processed_block:
                    # Submit the block header
                    success = self.submit_block_header(
                        block["number"], block["hash"].hex()
                    )

                    if success:
                        self.last_processed_block = block["number"]
                        print(f"Successfully processed block {block['number']}")
                    else:
                        print(f"Failed to process block {block['number']}, will retry")

                # Wait before next poll
                time.sleep(self.polling_interval)

            except KeyboardInterrupt:
                print("Shutting down HeaderOracle...")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(self.polling_interval)
