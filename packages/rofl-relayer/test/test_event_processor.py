"""Unit tests for the EventProcessor class."""

import pytest
from collections import OrderedDict
from unittest.mock import Mock
from rofl_relayer.event_processor import EventProcessor


class TestEventProcessor:
    """Test suite for EventProcessor class."""
    
    def test_processed_hash_tracking_with_lru(self):
        """Test that hash tracking maintains LRU behavior with O(1) lookups."""
        processor = EventProcessor()
        
        # Set a smaller max for testing
        processor.MAX_PROCESSED_HASHES = 5
        processor.processed_tx_hashes = OrderedDict()
        
        # Add hashes up to capacity
        hashes = [f"0xhash{i}" for i in range(5)]
        for hash_val in hashes:
            processor._track_processed_hash(hash_val)
        
        # Verify all hashes are tracked
        assert len(processor.processed_tx_hashes) == 5
        for hash_val in hashes:
            assert hash_val in processor.processed_tx_hashes
        
        # Add one more hash - should evict the oldest (hash0)
        processor._track_processed_hash("0xhash5")
        
        # Verify LRU eviction worked correctly
        assert len(processor.processed_tx_hashes) == 5
        assert "0xhash0" not in processor.processed_tx_hashes
        assert "0xhash5" in processor.processed_tx_hashes
        
        # Verify OrderedDict order (oldest to newest)
        expected_order = ["0xhash1", "0xhash2", "0xhash3", "0xhash4", "0xhash5"]
        assert list(processor.processed_tx_hashes.keys()) == expected_order
    
    def test_duplicate_hash_moves_to_end(self):
        """Test that duplicate hashes are moved to end (most recent) in LRU."""
        processor = EventProcessor()
        
        # Track multiple hashes
        processor._track_processed_hash("0xabc123")
        processor._track_processed_hash("0xdef456")
        processor._track_processed_hash("0xghi789")
        
        # Re-track the first hash (should move to end)
        processor._track_processed_hash("0xabc123")
        
        # Verify hash was moved to end and no duplicate was added
        assert len(processor.processed_tx_hashes) == 3
        assert list(processor.processed_tx_hashes.keys()) == ["0xdef456", "0xghi789", "0xabc123"]
    
    def test_o1_lookup_performance(self):
        """Test that hash lookup is O(1) using OrderedDict."""
        processor = EventProcessor()
        
        # Add many hashes
        for i in range(1000):
            processor._track_processed_hash(f"0xhash{i}")
        
        # Verify we're using OrderedDict for O(1) lookups
        assert isinstance(processor.processed_tx_hashes, OrderedDict)
        assert "0xhash500" in processor.processed_tx_hashes  # O(1) operation
        assert "0xnonexistent" not in processor.processed_tx_hashes  # O(1) operation
        
        # OrderedDict maintains both O(1) lookup and insertion order
        assert len(processor.processed_tx_hashes) == 1000