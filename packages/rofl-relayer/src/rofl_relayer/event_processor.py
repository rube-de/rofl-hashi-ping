"""
Event processor for handling blockchain events.

This module contains the logic for processing Ping and HashStored events,
keeping the processing logic separate from the relay orchestration.
"""

import logging
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, Optional, Set

from web3 import Web3
from web3.types import EventData

from .proof_manager import ProofManager

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
    
    def __init__(self, proof_manager: Optional[ProofManager] = None, config: Optional[Any] = None, web3_source: Optional[Web3] = None):
        """Initialize the event processor.
        
        Args:
            proof_manager: ProofManager instance for generating and submitting proofs
            config: RelayerConfig instance for accessing target addresses
            web3_source: Web3 instance for the source chain (for fetching receipts)
        """
        # State tracking with bounded collections
        self.processed_tx_hashes: Set[str] = set()
        self.pending_pings: Deque[PingEvent] = deque(maxlen=self.MAX_PENDING_PINGS)
        self.stored_hashes: Dict[int, str] = {}  # block_number -> block_hash
        
        # Proof generation
        self.proof_manager = proof_manager
        self.config = config
        self.web3_source = web3_source
    
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
            args = event.get('args', {})
            sender = args.get('sender', '0x0')
            timestamp = args.get('timestamp', 0)
            
            # Calculate transaction-local log index (position within the transaction's logs)
            # The proof verification needs the index within the transaction, not the global block index
            log_index = 0  # Default to first log in transaction
            if self.web3_source:
                try:
                    event_global_index = event.get('logIndex', 0)
                    receipt = self.web3_source.eth.get_transaction_receipt(tx_hash)
                    if receipt and 'logs' in receipt:
                        # Find this event's position within the transaction's logs
                        for i, log in enumerate(receipt['logs']):
                            if log.get('logIndex') == event_global_index:
                                log_index = i
                                break
                        logger.debug(f"Transaction has {len(receipt['logs'])} logs, Ping event at index {log_index}")
                except Exception as e:
                    logger.warning(f"Failed to calculate transaction-local log index: {e}, defaulting to 0")
            else:
                logger.warning("No web3_source available, defaulting to log index 0")
            
            # Debug logging
            logger.debug(f"Event data - blockNumber: {block_number}, txLogIndex: {log_index}, tx_hash: {tx_hash}")
            
            # Generate ping ID (hash of transaction + log index for uniqueness)
            ping_id = Web3.keccak(text=f"{tx_hash}-{log_index}").hex()
            
            # Create typed ping event
            ping_event = PingEvent(
                tx_hash=tx_hash,
                block_number=block_number,
                log_index=log_index,  # This is now the transaction-local index
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
            matching_pings = [ping for ping in self.pending_pings if ping.block_number == block_id]
            if matching_pings:
                logger.info(f"Found {len(matching_pings)} pings ready for block {block_id}")
                # Process matched events with proof generation
                if self.proof_manager and self.config:
                    for ping in matching_pings:
                        await self.process_matched_events(ping, block_hash)
            
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
    
    async def process_matched_events(self, ping_event: PingEvent, block_hash: str) -> None:
        """
        Process matched Ping and HashStored events by generating and submitting proof.
        
        Args:
            ping_event: The Ping event to process
            block_hash: The stored block hash for verification
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