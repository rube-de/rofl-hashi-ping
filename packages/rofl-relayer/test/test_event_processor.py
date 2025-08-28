"""Unit tests for the EventProcessor class."""

import pytest
from unittest.mock import Mock
from rofl_relayer.event_processor import EventProcessor


class TestEventProcessor:
    """Test suite for EventProcessor class."""
    
    def test_processed_hash_tracking_with_lru(self):
        """Test that hash tracking maintains LRU behavior with O(1) lookups."""
        processor = EventProcessor()
        
        # Set a smaller max for testing - need to recreate deque with new maxlen
        processor.MAX_PROCESSED_HASHES = 5
        from collections import deque
        processor.processed_tx_hashes_deque = deque(maxlen=5)
        processor.processed_tx_hashes_set.clear()
        
        # Add hashes up to capacity
        hashes = [f"0xhash{i}" for i in range(5)]
        for hash_val in hashes:
            processor._track_processed_hash(hash_val)
        
        # Verify all hashes are tracked
        assert len(processor.processed_tx_hashes_deque) == 5
        assert len(processor.processed_tx_hashes_set) == 5
        for hash_val in hashes:
            assert hash_val in processor.processed_tx_hashes_set
        
        # Add one more hash - should evict the oldest (hash0)
        processor._track_processed_hash("0xhash5")
        
        # Verify LRU eviction worked correctly
        assert len(processor.processed_tx_hashes_deque) == 5
        assert len(processor.processed_tx_hashes_set) == 5
        assert "0xhash0" not in processor.processed_tx_hashes_set
        assert "0xhash5" in processor.processed_tx_hashes_set
        
        # Verify deque order (oldest to newest)
        expected_order = ["0xhash1", "0xhash2", "0xhash3", "0xhash4", "0xhash5"]
        assert list(processor.processed_tx_hashes_deque) == expected_order
    
    def test_duplicate_hash_not_added(self):
        """Test that duplicate hashes are not added to tracking structures."""
        processor = EventProcessor()
        
        # Track a hash
        processor._track_processed_hash("0xabc123")
        initial_deque_len = len(processor.processed_tx_hashes_deque)
        initial_set_len = len(processor.processed_tx_hashes_set)
        
        # Try to track the same hash again
        processor._track_processed_hash("0xabc123")
        
        # Verify no duplicate was added
        assert len(processor.processed_tx_hashes_deque) == initial_deque_len
        assert len(processor.processed_tx_hashes_set) == initial_set_len
    
    def test_o1_lookup_performance(self):
        """Test that hash lookup is O(1) by checking set membership."""
        processor = EventProcessor()
        
        # Add many hashes
        for i in range(1000):
            processor._track_processed_hash(f"0xhash{i}")
        
        # Verify we're using set for lookups (O(1))
        assert isinstance(processor.processed_tx_hashes_set, set)
        assert "0xhash500" in processor.processed_tx_hashes_set  # O(1) operation
        assert "0xnonexistent" not in processor.processed_tx_hashes_set  # O(1) operation