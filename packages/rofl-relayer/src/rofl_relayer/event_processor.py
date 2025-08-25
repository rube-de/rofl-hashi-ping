"""
Event processor for handling blockchain events.

This module contains the logic for processing Ping and HashStored events,
keeping the processing logic separate from the relay orchestration.
"""

import logging
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional, Set

from web3 import Web3
from web3.types import EventData

logger = logging.getLogger(__name__)


@dataclass
class PingEvent:
    """Represents a Ping event from the source chain."""
    tx_hash: str
    block_number: int
    log_index: int
    sender: str
    timestamp: int
    ping_id: str


class EventProcessor:
    """Processes blockchain events for the ROFL relayer."""
    
    # Maximum items to track (prevent unbounded growth)
    MAX_PROCESSED_HASHES = 10000
    MAX_PENDING_PINGS = 1000
    
    def __init__(self):
        """Initialize the event processor."""
        # State tracking with bounded collections
        self.processed_tx_hashes: Set[str] = set()
        self.pending_pings: Deque[PingEvent] = deque(maxlen=self.MAX_PENDING_PINGS)
        self.stored_hashes: Dict[int, str] = {}  # block_number -> block_hash
    
    async def process_ping_event(self, event: EventData) -> Optional[PingEvent]:
        """
        Process a Ping event from the source chain.
        
        Args:
            event: The Ping event data
            
        Returns:
            PingEvent if successfully processed, None if skipped or error
        """
        try:
            # Extract and validate transaction hash
            tx_hash = event.get('transactionHash')
            if not tx_hash:
                logger.warning("Event missing transaction hash")
                return None
            
            # Convert to hex string if needed
            if isinstance(tx_hash, bytes):
                tx_hash = tx_hash.hex()
            
            # Skip if already processed
            if tx_hash in self.processed_tx_hashes:
                return None
            
            # Track processed transaction (with size limit)
            self._track_processed_hash(tx_hash)
            
            # Extract event data
            block_number = event.get('blockNumber', 0)
            log_index = event.get('logIndex', 0)
            args = event.get('args', {})
            sender = args.get('sender', '0x0')
            timestamp = args.get('timestamp', 0)
            
            # Generate ping ID (hash of transaction + log index for uniqueness)
            ping_id = Web3.keccak(text=f"{tx_hash}-{log_index}").hex()
            
            # Create typed ping event
            ping_event = PingEvent(
                tx_hash=tx_hash,
                block_number=block_number,
                log_index=log_index,
                sender=sender,
                timestamp=timestamp,
                ping_id=ping_id
            )
            
            logger.info(
                f"Ping event detected - TX: {tx_hash[:10]}... Block: {block_number} "
                f"Sender: {sender} ID: {ping_id[:10]}..."
            )
            
            # Queue for processing
            self.pending_pings.append(ping_event)
            return ping_event
            
        except Exception as e:
            logger.error(f"Error processing ping event: {e}", exc_info=True)
            return None
    
    async def process_hash_stored(self, event: EventData) -> Optional[tuple[int, str]]:
        """
        Process a HashStored event from the ROFLAdapter.
        
        Args:
            event: The HashStored event data
            
        Returns:
            Tuple of (block_id, block_hash) if successful, None if error
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
            
            logger.info(f"Hash stored - Block {block_id}: {block_hash[:10]}...")
            
            # Check if any pending pings can now be processed
            matching_pings = self._find_pings_for_block(block_id)
            if matching_pings:
                logger.info(f"Found {len(matching_pings)} pings ready for block {block_id}")
                # MVP: Additional proof generation would go here
            
            return (block_id, block_hash)
            
        except Exception as e:
            logger.error(f"Error processing HashStored event: {e}", exc_info=True)
            return None
    
    def _track_processed_hash(self, tx_hash: str) -> None:
        """
        Track a processed transaction hash with size limits.
        
        Args:
            tx_hash: Transaction hash to track
        """
        self.processed_tx_hashes.add(tx_hash)
        if len(self.processed_tx_hashes) > self.MAX_PROCESSED_HASHES:
            # Remove oldest entries (convert to list, slice, convert back)
            self.processed_tx_hashes = set(
                list(self.processed_tx_hashes)[-self.MAX_PROCESSED_HASHES:]
            )
    
    def _find_pings_for_block(self, block_number: int) -> list[PingEvent]:
        """
        Find pending pings that match a specific block number.
        
        Args:
            block_number: Block number to match
            
        Returns:
            List of matching PingEvent objects
        """
        return [ping for ping in self.pending_pings if ping.block_number == block_number]
    
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