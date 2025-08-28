import asyncio
import codecs
import os
from typing import Any

import cbor2
from web3 import Web3
from web3.types import BlockData, TxParams, Wei

from .utils.contract_utility import ContractUtility
from .utils.event_listener_utility import EventListenerUtility, parse_event_topic_as_int
from .utils.rofl_utility import RoflUtility


class HeaderOracle:
    """
    Header Oracle that fetches block headers from a source chain
    and submits them to the ROFLAdapter contract on Oasis Sapphire.
    """

    def __init__(self, local_mode: bool = False) -> None:
        """
        Initialize the HeaderOracle.
        All configuration is read from environment variables.
        
        :param local_mode: If True, skip ROFL utilities and use local private key
        """
        self.local_mode = local_mode
        print(f"HeaderOracle: Starting initialization{'(LOCAL MODE)' if local_mode else ''}...")
        
        try:
            # Load configuration from environment
            print("HeaderOracle: Loading configuration from environment...")
            self._load_config()
            print("HeaderOracle: Configuration loaded successfully")

            if not local_mode:
                # Initialize ROFL utility and fetch secret
                print("HeaderOracle: Initializing ROFL utility...")
                self.rofl_utility = RoflUtility()
                
                print("HeaderOracle: Fetching oracle key from ROFL...")
                self.secret = self.rofl_utility.fetch_key("header-oracle")
                print("HeaderOracle: Oracle key fetched successfully")
            else:
                # Use local private key for testing
                print("HeaderOracle: Using local private key (LOCAL MODE)...")
                local_key = os.environ.get("LOCAL_PRIVATE_KEY")
                if not local_key:
                    raise Exception(
                        "LOCAL_PRIVATE_KEY environment variable is required in local mode. "
                        "Set it to a private key for testing."
                    )
                self.secret = local_key
                self.rofl_utility = None
                print("HeaderOracle: Local private key loaded successfully")

            # Initialize contract utility
            print("HeaderOracle: Initializing contract utility...")
            self.contract_utility = ContractUtility(self.network, self.secret)
            print("HeaderOracle: Contract utility initialized")

            # Connect to source chain for block fetching
            print(f"HeaderOracle: Connecting to source chain at {self.source_rpc_url}...")
            self.source_w3 = Web3(Web3.HTTPProvider(self.source_rpc_url, request_kwargs={'timeout': 10}))
            if not self.source_w3.is_connected():
                raise Exception(
                    f"Failed to connect to source chain at {self.source_rpc_url}"
                )
            print("HeaderOracle: Connected to source chain")
            
            # Fetch chain ID from the connected RPC endpoint
            print("HeaderOracle: Fetching chain ID...")
            self.source_chain_id = self.source_w3.eth.chain_id
            print(f"HeaderOracle: Chain ID is {self.source_chain_id}")

            # Load ABIs
            print("HeaderOracle: Loading contract ABIs...")
            self.rofl_adapter_abi = self._load_rofl_adapter_abi()
            self.block_requester_abi = self._load_block_requester_abi()
            print("HeaderOracle: ABIs loaded")

            # Create ROFL adapter contract instance (for Sapphire)
            print("HeaderOracle: Creating ROFL adapter contract instance...")
            self.contract = self.contract_utility.w3.eth.contract(
                address=self.contract_address, abi=self.rofl_adapter_abi
            )
            print("HeaderOracle: Contract instance created")
            
            # Create source chain contract instance (for event listening)
            print("HeaderOracle: Creating source chain contract instance...")
            self.source_contract = self.source_w3.eth.contract(
                address=self.source_contract_address, abi=self.block_requester_abi
            )
            print("HeaderOracle: Source chain contract instance created")

            # Initialize event listener utility
            print("HeaderOracle: Initializing event listener...")
            self.event_listener = EventListenerUtility(
                rpc_url=self.source_rpc_url
            )
            print("HeaderOracle: Event listener initialized")

            print("\n" + "="*50)
            print("HeaderOracle initialized successfully!")
            print("="*50)
            print(f"  Source RPC: {self.source_rpc_url}")
            print(f"  Source Chain ID: {self.source_chain_id}")
            print(f"  Source Contract: {self.source_contract_address}")
            print(f"  Target Network: {self.network}")
            print(f"  ROFLAdapter Address: {self.contract_address}")
            print("  Event Listener: WebSocket + Polling fallback")
            print("="*50 + "\n")
            
        except Exception as e:
            print(f"\n!!! HeaderOracle initialization failed: {e}")
            print(f"Exception type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            raise

    def _load_config(self) -> None:
        """
        Load configuration from environment variables.
        """
        print("  Checking environment variables...")
        
        # Required configuration
        contract_address = os.environ.get("CONTRACT_ADDRESS", "")
        print(f"  CONTRACT_ADDRESS: {'[SET]' if contract_address else '[NOT SET]'}")
        if not contract_address:
            raise Exception("CONTRACT_ADDRESS environment variable is not set. This should be the ROFLAdapter contract address on Sapphire.")

        self.contract_address = Web3.to_checksum_address(contract_address)
        
        # Source contract address (BlockHeaderRequester)
        source_contract = os.environ.get("SOURCE_CONTRACT_ADDRESS", "")
        print(f"  SOURCE_CONTRACT_ADDRESS: {'[SET]' if source_contract else '[NOT SET]'}")
        if not source_contract:
            raise Exception("SOURCE_CONTRACT_ADDRESS environment variable is not set. This should be the BlockHeaderRequester contract address.")
        
        self.source_contract_address = Web3.to_checksum_address(source_contract)

        # Network configuration
        self.network = os.environ.get("NETWORK", "sapphire-testnet")

        # Source chain configuration
        self.source_rpc_url = os.environ.get(
            "SOURCE_RPC_URL", "https://ethereum.publicnode.com"
        )

        # Oracle configuration
        self.polling_interval = int(os.environ.get("POLLING_INTERVAL", "12"))

    def _load_rofl_adapter_abi(self) -> list[dict[str, Any]]:
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
    
    def _load_block_requester_abi(self) -> list[dict[str, Any]]:
        """
        Load the BlockHeaderRequester ABI.
        Only includes the event we need to listen for.
        """
        return [
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "internalType": "uint256", "name": "chainId", "type": "uint256"},
                    {"indexed": True, "internalType": "uint256", "name": "blockNumber", "type": "uint256"},
                    {"indexed": False, "internalType": "address", "name": "requester", "type": "address"},
                    {"indexed": False, "internalType": "bytes32", "name": "context", "type": "bytes32"}
                ],
                "name": "BlockHeaderRequested",
                "type": "event"
            }
        ]

    def _decode_rofl_response(self, response_hex: str) -> dict[str, Any]:
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

    def fetch_block_by_number(self, block_number: int) -> BlockData | None:
        """
        Fetch a specific block by number from the source chain.

        :param block_number: The block number to fetch
        :return: Block data or None if fetch fails
        """
        try:
            block = self.source_w3.eth.get_block(block_number)
            return block
        except Exception as e:
            print(f"Error fetching block {block_number}: {e}")
            return None
    
    async def process_block_header_event(self, event_data: Any) -> None:
        """
        Process a BlockHeaderRequested event.
        
        :param event_data: Event data from the event listener
        """
        try:
            # Handle both dict and EventData formats
            if hasattr(event_data, 'get'):
                # Dict format from WebSocket
                topics = event_data.get('topics', [])
                block_number = event_data.get('blockNumber', 0)
            else:
                # EventData format from polling
                topics = getattr(event_data, 'topics', [])
                block_number = getattr(event_data, 'blockNumber', 0)
            
            if len(topics) < 3:  # Need at least event signature + 2 indexed topics
                print(f"Warning: Insufficient topics in event: {topics}")
                return
            
            # Decode indexed parameters (chainId, blockNumber from topics)
            chain_id = parse_event_topic_as_int(topics[1]) if len(topics) > 1 else 0
            requested_block = parse_event_topic_as_int(topics[2]) if len(topics) > 2 else 0
            
            print("Processing BlockHeaderRequested event:")
            print(f"  Chain ID: {chain_id}")
            print(f"  Requested Block: {requested_block}")
            print(f"  Event Block: {block_number}")
            
            # Only process events for our source chain
            if chain_id != self.source_chain_id:
                print(f"Skipping event for different chainId {chain_id} (our chainId is {self.source_chain_id})")
                return
            
            # Fetch the requested block
            block = self.fetch_block_by_number(requested_block)
            
            if block:
                block_hash = block.get("hash")
                
                if block_hash is not None:
                    # Convert block_hash to hex string with 0x prefix
                    block_hash_hex = block_hash.hex() if isinstance(block_hash, bytes) else block_hash
                    if not block_hash_hex.startswith('0x'):
                        block_hash_hex = '0x' + block_hash_hex
                    
                    # Submit the block header
                    success = self.submit_block_header(requested_block, block_hash_hex)
                    
                    if success:
                        print(f"✓ Successfully submitted block {requested_block} header to Sapphire")
                    else:
                        print(f"✗ Failed to submit block {requested_block} header")
            else:
                print(f"Could not fetch block {requested_block}")
                
        except Exception as e:
            print(f"Error processing BlockHeaderRequested event: {e}")
            import traceback
            traceback.print_exc()

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
            
            if self.local_mode:
                # Local mode: just log the transaction without submitting
                print("  🔧 LOCAL MODE: Simulating transaction submission")
                print(f"  📋 Transaction details:")
                print(f"     To: {tx_params.get('to')}")
                print(f"     Gas: {tx_params.get('gas')}")
                print(f"     Gas Price: {tx_params.get('gasPrice')}")
                print(f"     Data: {tx_params.get('data', '')[:100]}...")
                print("  ✓ Transaction simulation completed (LOCAL MODE)")
                return True
            else:
                # Production mode: submit via ROFL
                try:
                    assert self.rofl_utility is not None, "ROFL utility should be initialized in production mode"
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

    async def run(self) -> None:
        """
        Main entry point for the HeaderOracle.
        Starts event listening using the EventListenerUtility.
        """
        print("Starting HeaderOracle...")
        print(f"Listening for BlockHeaderRequested events from {self.source_contract_address}")
        
        try:
            # Use the contract event object directly for cleaner topic generation
            event_obj = self.source_contract.events.BlockHeaderRequested()
            
            print("Event configuration created, starting event listener...")
            
            # Start event listening (this will run indefinitely)
            await self.event_listener.listen_for_contract_events(
                contract_address=self.source_contract_address,
                event_obj=event_obj,
                callback=self.process_block_header_event
            )
            
        except Exception as e:
            print(f"Error in main loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("Cleaning up...")
            await self.event_listener.stop()
            print("HeaderOracle stopped")


# Async main function for running the HeaderOracle
async def main():
    """Run the HeaderOracle."""
    import logging
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    oracle = HeaderOracle()
    await oracle.run()


if __name__ == "__main__":
    asyncio.run(main())
