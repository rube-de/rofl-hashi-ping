"""
State management utilities for ROFL Relayer.

This module provides efficient bounded collections and state tracking
utilities for managing processed transactions and pending events.
"""

from collections import OrderedDict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Set


@dataclass
class PingEvent:
    """Represents a Ping event from the source chain."""
    tx_hash: str
    block_number: int
    sender: str
    timestamp: int
    ping_id: str


class RelayerStateManager:
    """
    Manages state for the ROFL relayer with bounded collections.
    
    Uses OrderedDict for efficient LRU-style bounded sets and
    deque for bounded queues.
    """
    
    def __init__(self, max_processed: int = 10000, max_pending: int = 1000):
        """
        Initialize the state manager.
        
        Args:
            max_processed: Maximum number of processed transaction hashes to track
            max_pending: Maximum number of pending ping events to queue
        """
        self.max_processed = max_processed
        self.max_pending = max_pending
        
        # Use OrderedDict for efficient bounded set with LRU eviction
        self._processed_tx_hashes: OrderedDict[str, None] = OrderedDict()
        
        # Use deque for efficient bounded queue
        self._pending_pings: deque[PingEvent] = deque(maxlen=max_pending)
        
        # Store block hashes by block number
        self._stored_hashes: Dict[int, str] = {}
    
    def track_processed(self, tx_hash: str) -> None:
        """
        Track a processed transaction hash with automatic eviction of oldest entries.
        
        Args:
            tx_hash: Transaction hash to track
        """
        # Remove if already exists to update position
        if tx_hash in self._processed_tx_hashes:
            del self._processed_tx_hashes[tx_hash]
        
        # Add to end (most recent)
        self._processed_tx_hashes[tx_hash] = None
        
        # Evict oldest if over limit
        while len(self._processed_tx_hashes) > self.max_processed:
            self._processed_tx_hashes.popitem(last=False)  # Remove oldest (first)
    
    def is_processed(self, tx_hash: str) -> bool:
        """
        Check if a transaction hash has been processed.
        
        Args:
            tx_hash: Transaction hash to check
            
        Returns:
            True if the transaction has been processed
        """
        return tx_hash in self._processed_tx_hashes
    
    def add_pending_ping(self, ping: PingEvent) -> None:
        """
        Add a ping event to the pending queue.
        
        Automatically evicts oldest events if queue is full.
        
        Args:
            ping: PingEvent to add to the queue
        """
        self._pending_pings.append(ping)
    
    def get_pending_pings(self, block_number: Optional[int] = None) -> List[PingEvent]:
        """
        Get pending ping events, optionally filtered by block number.
        
        Args:
            block_number: If provided, only return pings for this block number
            
        Returns:
            List of pending ping events
        """
        if block_number is None:
            return list(self._pending_pings)
        
        return [ping for ping in self._pending_pings if ping.block_number == block_number]
    
    def remove_pending_ping(self, ping: PingEvent) -> bool:
        """
        Remove a specific ping event from the pending queue.
        
        Args:
            ping: PingEvent to remove
            
        Returns:
            True if the ping was found and removed
        """
        try:
            self._pending_pings.remove(ping)
            return True
        except ValueError:
            return False
    
    def store_block_hash(self, block_number: int, block_hash: str) -> None:
        """
        Store a block hash for a given block number.
        
        Args:
            block_number: Block number
            block_hash: Block hash to store
        """
        self._stored_hashes[block_number] = block_hash
    
    def get_stored_hash(self, block_number: int) -> Optional[str]:
        """
        Get the stored hash for a block number.
        
        Args:
            block_number: Block number to look up
            
        Returns:
            Block hash if found, None otherwise
        """
        return self._stored_hashes.get(block_number)
    
    def get_all_pending_pings(self) -> deque[PingEvent]:
        """
        Get the underlying deque of all pending pings.
        
        Returns:
            Deque containing all pending ping events
        """
        return self._pending_pings
    
    def get_stats(self) -> dict:
        """
        Get current state manager statistics.
        
        Returns:
            Dictionary with state metrics
        """
        return {
            'processed_hashes': len(self._processed_tx_hashes),
            'pending_pings': len(self._pending_pings),
            'stored_hashes': len(self._stored_hashes),
            'max_processed': self.max_processed,
            'max_pending': self.max_pending
        }
    
    def clear_old_hashes(self, keep_recent: int = 100) -> int:
        """
        Clear old stored block hashes, keeping only the most recent ones.
        
        Args:
            keep_recent: Number of recent block hashes to keep
            
        Returns:
            Number of hashes removed
        """
        if len(self._stored_hashes) <= keep_recent:
            return 0
        
        # Get block numbers sorted in descending order
        sorted_blocks = sorted(self._stored_hashes.keys(), reverse=True)
        
        # Keep only the most recent
        blocks_to_keep = set(sorted_blocks[:keep_recent])
        blocks_to_remove = [b for b in self._stored_hashes.keys() if b not in blocks_to_keep]
        
        for block in blocks_to_remove:
            del self._stored_hashes[block]
        
        return len(blocks_to_remove)