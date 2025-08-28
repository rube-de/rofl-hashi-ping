"""
Event processor for handling blockchain events.

This module contains the logic for processing Ping and HashStored events,
keeping the processing logic separate from the relay orchestration.
"""

import logging
from collections import deque
from dataclasses import dataclass
from typing import Any, Optional
from collections.abc import Mapping

from web3.types import EventData
from web3 import Web3

from .proof_manager import ProofManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PingEvent:
    """Represents a Ping event from the source chain.
    
    Using frozen=True for immutability and slots=True for memory efficiency.
    """
    tx_hash: str
    block_number: int
    sender: str
    timestamp: int
    ping_id: str


class EventProcessor:
    """Processes blockchain events for the ROFL relayer."""
    
    # Class-level constants using Python 3.12 type annotations
    MAX_PROCESSED_HASHES: int = 10_000  # Using underscores for readability
    MAX_PENDING_PINGS: int = 1_000
    
    def __init__(self, proof_manager: Optional[ProofManager] = None, config: Optional[Any] = None) -> None:
        """Initialize the event processor.
        
        Args:
            proof_manager: ProofManager instance for generating and submitting proofs
            config: RelayerConfig instance for accessing target addresses
        """
        # State tracking with bounded collections
        # Using deque for O(1) append and automatic LRU eviction
        self.processed_tx_hashes: deque[str] = deque(maxlen=self.MAX_PROCESSED_HASHES)
        self.pending_pings: deque[PingEvent] = deque(maxlen=self.MAX_PENDING_PINGS)
        self.stored_hashes: dict[int, str] = {}  # block_number -> block_hash
        
        # Proof generation
        self.proof_manager = proof_manager
        self.config = config
    
    async def process_ping_event(self, event: EventData) -> Optional[PingEvent]:
        """
        Process a Ping event from the source chain.
        
        Args:
            event: The Ping event data
            
        Returns:
            PingEvent if successfully processed, None if skipped or error
        """
        try:
            # Extract and validate transaction hash using match/case (Python 3.10+)
            match event.get('transactionHash'):
                case None:
                    logger.warning("Event missing transaction hash")
                    return None
                case bytes() as tx_hash_bytes:
                    tx_hash = tx_hash_bytes.hex()
                case str() as tx_hash:
                    pass  # Already a string
                case _:
                    logger.warning(f"Unexpected transaction hash type: {type(event.get('transactionHash'))}")
                    return None
            
            # Skip if already processed
            if tx_hash in self.processed_tx_hashes:
                return None
            
            # Track processed transaction (with size limit)
            self._track_processed_hash(tx_hash)
            
            # Extract event data with type safety
            block_number: int = event.get('blockNumber', 0)
            args: Mapping[str, Any] = event.get('args', {})
            sender: str = args.get('sender', '0x0')
            timestamp: int = args.get('timestamp', 0)
            
            # Store event data for later proof generation
            # ProofManager will calculate the correct transaction-local index
            # Generate ping ID using transaction hash and event args for uniqueness
            ping_id: str = Web3.keccak(text=f"{tx_hash}-{sender}-{block_number}").hex()
            
            # Create typed ping event
            ping_event = PingEvent(
                tx_hash=tx_hash,
                block_number=block_number,
                sender=sender,
                timestamp=timestamp,
                ping_id=ping_id
            )
            
            # Using f-string with = for debug output (Python 3.8+)
            logger.info(
                f"Ping event detected - TX: {tx_hash[:10]}... {block_number=} "
                f"{sender=} ID: {ping_id[:10]}..."
            )
            
            # Queue for processing
            self.pending_pings.append(ping_event)
            return ping_event
            
        except Exception as e:
            logger.error(f"Error processing ping event: {e}", exc_info=True)
            return None
    
    async def process_hash_stored(self, event: EventData) -> tuple[int, str] | None:
        """
        Process a HashStored event from the ROFLAdapter.
        
        Args:
            event: The HashStored event data
            
        Returns:
            Tuple of (block_id, block_hash) if successful, None if error
        """
        try:
            # Extract event data with pattern matching
            args: Mapping[str, Any] = event.get('args', {})
            block_id: int = args.get('id', 0)
            
            # Handle block hash with pattern matching
            match args.get('hash', '0x0'):
                case bytes() as hash_bytes:
                    block_hash = hash_bytes.hex()
                case str() as hash_str:
                    block_hash = hash_str
                case _:
                    block_hash = '0x0'
            
            # Store the hash
            self.stored_hashes[block_id] = block_hash
            
            logger.info(f"Hash stored - Block {block_id}: {block_hash[:10]}...")
            
            # Check if any pending pings can now be processed
            # Using list comprehension with walrus operator for efficiency
            matching_pings: list[PingEvent] = [ping for ping in self.pending_pings if ping.block_number == block_id]
            if matching_pings:
                logger.info(f"Found {len(matching_pings)} pings ready for block {block_id}")
                # Process matched events with proof generation
                if self.proof_manager and self.config:
                    for ping in matching_pings:
                        await self.process_matched_events(ping)
            
            return (block_id, block_hash)
            
        except Exception as e:
            logger.error(f"Error processing HashStored event: {e}", exc_info=True)
            return None
    
    def _track_processed_hash(self, tx_hash: str) -> None:
        """
        Track a processed transaction hash with automatic LRU eviction.
        
        The deque automatically removes the oldest entry when maxlen is reached,
        providing proper Least Recently Used (LRU) behavior with O(1) operations.
        
        Args:
            tx_hash: Transaction hash to track
        """
        # Check if already exists to avoid duplicates
        if tx_hash not in self.processed_tx_hashes:
            self.processed_tx_hashes.append(tx_hash)
    
    async def process_matched_events(self, ping_event: PingEvent) -> None:
        """
        Process matched Ping and HashStored events by generating and submitting proof.
        
        Args:
            ping_event: The Ping event to process
        """
        try:
            if not self.proof_manager or not self.config:
                logger.warning("ProofManager or config not initialized, skipping proof generation")
                return
                
            receiver_address = self.config.target_chain.ping_receiver_address
            logger.info(f"Processing proof for Ping {ping_event.ping_id[:10]}... to receiver {receiver_address}")
            
            # Generate and submit proof
            tx_hash = await self.proof_manager.process_ping_event(
                ping_event,
                receiver_address
            )
            
            logger.info(f"Proof submitted successfully: {tx_hash}")
            
            # Remove from pending queue after successful processing
            if ping_event in self.pending_pings:
                self.pending_pings.remove(ping_event)
                
        except Exception as e:
            logger.error(f"Failed to process proof for Ping {ping_event.ping_id[:10]}...: {e}", exc_info=True)
    
    def get_stats(self) -> dict:
        """
        Get current processor statistics.
        
        Returns:
            Dictionary with current state metrics
        """
        return {
            'processed_hashes': len(self.processed_tx_hashes),
            'pending_pings': len(self.pending_pings),
            'stored_hashes': len(self.stored_hashes)
        }