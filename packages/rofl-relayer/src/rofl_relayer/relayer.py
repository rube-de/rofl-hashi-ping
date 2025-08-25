"""
ROFL Relayer implementation.

This module contains the main relayer service that monitors Ping events
on Ethereum and relays them to Oasis Sapphire using cryptographic proofs.
"""

import asyncio
import sys
from typing import Any, Dict, Set

from web3 import Web3
from web3.types import EventData

from .config import RelayerConfig
from .utils.polling_event_listener import PollingEventListener
from .utils.contract_utility import ContractUtility


class ROFLRelayer:
    """Main relayer service class."""

    def __init__(self, local_mode: bool = False):
        """
        Initialize the ROFL Relayer.

        Args:
            local_mode: Run in local mode without ROFL utilities
        """
        self.local_mode = local_mode
        self.running = False
        
        # Load configuration
        try:
            print("\nLoading configuration...")
            self.config = RelayerConfig.from_env(local_mode=local_mode)
            self.config.log_config()
        except ValueError as e:
            print(f"\nConfiguration Error: {e}")
            print("\nRequired environment variables:")
            print("  - SOURCE_RPC_URL: Ethereum RPC endpoint")
            print("  - PING_SENDER_ADDRESS: PingSender contract address")
            print("  - PING_RECEIVER_ADDRESS: PingReceiver contract address")
            print("  - ROFL_ADAPTER_ADDRESS: ROFLAdapter contract address")
            if local_mode:
                print("  - PRIVATE_KEY: Private key for signing transactions")
            sys.exit(1)
        
        # Initialize polling listeners (will be set in init_event_monitoring)
        self.ping_listener: PollingEventListener | None = None
        self.hash_listener: PollingEventListener | None = None
        
        # State tracking
        self.processed_tx_hashes: Set[str] = set()
        self.pending_pings: list[Dict[str, Any]] = []
        self.stored_hashes: Dict[int, str] = {}  # block_number -> block_hash
    
    async def init_event_monitoring(self) -> None:
        """Initialize polling listeners for both chains."""
        print("\nInitializing event monitoring...")
        
        # Use ContractUtility in ABI-only mode (no network/secret needed)
        contract_util = ContractUtility()
        
        # Load PingSender ABI
        ping_sender_abi = contract_util.get_contract_abi("PingSender")
        
        # ROFLAdapter uses a simple ABI for HashStored event
        rofl_adapter_abi = [
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "id", "type": "uint256"},
                    {"indexed": True, "name": "hash", "type": "bytes32"}
                ],
                "name": "HashStored",
                "type": "event"
            }
        ]
        
        # Initialize PingSender event listener (source chain)
        self.ping_listener = PollingEventListener(
            rpc_url=self.config.source_chain.rpc_url,
            contract_address=self.config.source_chain.ping_sender_address,
            event_name="Ping",
            abi=ping_sender_abi,
            lookback_blocks=self.config.monitoring.lookback_blocks
        )
        
        # Initialize ROFLAdapter event listener (target chain)
        # For MVP, we'll use the same RPC for testing, but in production this would be Sapphire
        self.hash_listener = PollingEventListener(
            rpc_url=self.config.source_chain.rpc_url,  # TODO: Use target chain RPC
            contract_address=self.config.target_chain.rofl_adapter_address,
            event_name="HashStored", 
            abi=rofl_adapter_abi,
            lookback_blocks=self.config.monitoring.lookback_blocks
        )
        
        print(f"Initialized PingSender listener at {self.config.source_chain.ping_sender_address}")
        print(f"Initialized ROFLAdapter listener at {self.config.target_chain.rofl_adapter_address}")
    
    async def process_ping_event(self, event: EventData) -> None:
        """
        Process Ping events from the source chain.
        
        Args:
            event: The Ping event data
        """
        try:
            # Extract transaction hash
            tx_hash = event.get('transactionHash')
            if not tx_hash:
                print("Warning: Event missing transaction hash")
                return
            
            # Convert to hex string if needed
            if isinstance(tx_hash, bytes):
                tx_hash = tx_hash.hex()
            
            # Check if already processed
            if tx_hash in self.processed_tx_hashes:
                return  # Skip duplicate
            
            # Mark as processed
            self.processed_tx_hashes.add(tx_hash)
            
            # Extract event data
            block_number = event.get('blockNumber', 0)
            log_index = event.get('logIndex', 0)
            
            # Decode event arguments (for Ping event)
            # Event signature: Ping(address indexed sender, uint256 indexed timestamp, uint256 blockNumber)
            args = event.get('args', {})
            sender = args.get('sender', '0x0')
            timestamp = args.get('timestamp', 0)
            
            # Generate ping ID (matches contract logic)
            # For now, use a simple hash of the event data
            ping_id = Web3.keccak(text=f"{tx_hash}-{log_index}")
            
            # Create ping record
            ping_event = {
                'tx_hash': tx_hash,
                'block_number': block_number,
                'log_index': log_index,
                'sender': sender,
                'timestamp': timestamp,
                'ping_id': ping_id.hex(),
            }
            
            # Log event
            print(f"\n{'='*60}")
            print(f"Ping Event Detected!")
            print(f"  TX: {tx_hash[:10]}...")
            print(f"  Block: {block_number}")
            print(f"  Sender: {sender}")
            print(f"  Timestamp: {timestamp}")
            print(f"  Ping ID: {ping_id.hex()[:10]}...")
            print(f"{'='*60}\n")
            
            # Queue for processing
            self.pending_pings.append(ping_event)
            
            # TODO: Phase 3 - Generate Merkle proof
            # TODO: Phase 4 - Wait for header availability
            # TODO: Phase 5 - Submit proof to target chain
            
        except Exception as e:
            print(f"Error processing ping event: {e}")
            import traceback
            traceback.print_exc()
    
    async def process_hash_stored(self, event: EventData) -> None:
        """
        Process HashStored events from the ROFLAdapter on target chain.
        
        Args:
            event: The HashStored event data
        """
        try:
            # Extract event data
            args = event.get('args', {})
            block_id = args.get('id', 0)
            block_hash = args.get('hash', '0x0')
            
            if isinstance(block_hash, bytes):
                block_hash = block_hash.hex()
            
            # Store the hash
            self.stored_hashes[block_id] = block_hash
            
            print(f"Hash Stored: Block {block_id} -> {block_hash[:10]}...")
            
            # Check if any pending pings can now be processed
            for ping in self.pending_pings:
                if ping['block_number'] == block_id:
                    print(f"Header available for ping {ping['ping_id'][:10]}...")
                    # TODO: Phase 3 - Generate and submit proof
            
        except Exception as e:
            print(f"Error processing HashStored event: {e}")
    
    async def run(self) -> None:
        """Main event loop for the relayer service."""
        self.running = True
        print("\nROFL Relayer Started")
        print("="*60)

        try:
            # Initialize event monitoring
            await self.init_event_monitoring()
            
            # Start polling listeners in background tasks
            ping_task = asyncio.create_task(
                self.ping_listener.start_polling(
                    callback=self.process_ping_event,
                    interval=self.config.monitoring.polling_interval
                )
            )
            
            hash_task = asyncio.create_task(
                self.hash_listener.start_polling(
                    callback=self.process_hash_stored,
                    interval=self.config.monitoring.polling_interval
                )
            )
            
            print(f"Polling interval: {self.config.monitoring.polling_interval} seconds")
            print(f"Lookback blocks: {self.config.monitoring.lookback_blocks}")
            print("="*60)
            print("\nWaiting for events...\n")
            
            # Main processing loop
            while self.running:
                # Process pending pings
                if self.pending_pings:
                    print(f"Pending pings in queue: {len(self.pending_pings)}")
                
                # Log status periodically
                await asyncio.sleep(10)
                
                # Check if tasks are still running
                if ping_task.done() or hash_task.done():
                    print("Warning: A polling task has stopped unexpectedly")
                    break

        except Exception as e:
            print(f"\nError in main loop: {e}")
            raise
        finally:
            # Stop polling listeners
            if self.ping_listener:
                await self.ping_listener.stop()
            if self.hash_listener:
                await self.hash_listener.stop()
            
            print("\nROFL Relayer Stopped")

    def stop(self) -> None:
        """Stop the relayer service."""
        self.running = False