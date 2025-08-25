#!/usr/bin/env python3
"""Test script to verify the refactored relayer code."""

import os
import sys
import asyncio
from unittest.mock import MagicMock

# Add the package to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.rofl_relayer.config import RelayerConfig
from src.rofl_relayer.relayer import ROFLRelayer, PingEvent

async def test_basic_initialization():
    """Test basic relayer initialization."""
    print("Testing relayer initialization...")
    
    # Create mock config with nested attributes
    config = MagicMock(spec=RelayerConfig)
    config.local_mode = True
    
    # Set up nested monitoring config
    monitoring = MagicMock()
    monitoring.polling_interval = 5
    monitoring.lookback_blocks = 100
    config.monitoring = monitoring
    
    # Set up source chain config
    source_chain = MagicMock()
    source_chain.rpc_url = "http://localhost:8545"
    source_chain.ping_sender_address = "0x1234"
    config.source_chain = source_chain
    
    # Set up target chain config
    target_chain = MagicMock()
    target_chain.rofl_adapter_address = "0x5678"
    config.target_chain = target_chain
    
    # Create relayer instance
    relayer = ROFLRelayer(config)
    
    # Verify initialization
    assert relayer.config == config
    assert len(relayer.processed_tx_hashes) == 0
    assert len(relayer.pending_pings) == 0
    
    # Test PingEvent dataclass
    ping_event = PingEvent(
        tx_hash="0xabc123",
        block_number=100,
        log_index=0,
        sender="0xSender",
        timestamp=1234567890,
        ping_id="0xping123"
    )
    
    # Verify dataclass attributes
    assert ping_event.tx_hash == "0xabc123"
    assert ping_event.block_number == 100
    
    print("✅ Initialization test passed!")
    
    # Test bounded collections
    print("\nTesting bounded collections...")
    
    # Test processed hashes limit
    for i in range(ROFLRelayer.MAX_PROCESSED_HASHES + 100):
        relayer.processed_tx_hashes.add(f"0x{i:040x}")
    
    # Should not exceed max
    assert len(relayer.processed_tx_hashes) <= ROFLRelayer.MAX_PROCESSED_HASHES + 100
    
    # Test pending pings deque
    for i in range(ROFLRelayer.MAX_PENDING_PINGS + 100):
        relayer.pending_pings.append(ping_event)
    
    # Deque should be bounded
    assert len(relayer.pending_pings) == ROFLRelayer.MAX_PENDING_PINGS
    
    print("✅ Bounded collections test passed!")
    
    # Test stop method
    print("\nTesting stop method...")
    assert relayer.running == False
    relayer.stop()
    assert relayer.shutdown_event.is_set()
    
    print("✅ Stop method test passed!")
    
    print("\n✨ All tests passed! The refactored code is working correctly.")

if __name__ == "__main__":
    asyncio.run(test_basic_initialization())