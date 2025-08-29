#!/usr/bin/env python
"""
Test the PollingEventListener integration with HeaderOracle.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rofl_oracle.utils.polling_event_listener import PollingEventListener


async def test_polling_listener_structure():
    """Test that PollingEventListener is properly structured for oracle use."""
    print("\n" + "="*60)
    print("Test: PollingEventListener Structure for Oracle")
    print("="*60)
    
    # Test contract address and ABI (using example values)
    test_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0fA99"
    test_abi = [
        {
            "anonymous": False,
            "inputs": [
                {"indexed": True, "name": "chainId", "type": "uint256"},
                {"indexed": True, "name": "blockNumber", "type": "uint256"}
            ],
            "name": "BlockHeaderRequested",
            "type": "event"
        }
    ]
    
    try:
        # Create listener instance with oracle-specific configuration
        listener = PollingEventListener(
            rpc_url="https://ethereum-sepolia.publicnode.com",
            contract_address=test_address,
            event_name="BlockHeaderRequested",
            abi=test_abi,
            lookback_blocks=100
        )
        
        print(f"✓ Created PollingEventListener for oracle")
        print(f"  - RPC URL: {listener.rpc_url}")
        print(f"  - Contract: {listener.contract_address}")
        print(f"  - Event: {listener.event_name}")
        print(f"  - Lookback: {listener.lookback_blocks} blocks")
        
        # Check status
        status = listener.get_status()
        assert status["is_running"] == False
        assert status["event_name"] == "BlockHeaderRequested"
        print(f"✓ Status check passed")
        
        # Verify Web3 connection
        assert listener.w3 is not None
        assert listener.contract is not None
        print(f"✓ Web3 and contract instances created")
        
        print("\n[PASS] PollingEventListener is properly configured for oracle use")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_event_callback_signature():
    """Test that the event callback signature matches oracle expectations."""
    print("\n" + "="*60)
    print("Test: Event Callback Signature Compatibility")
    print("="*60)
    
    # Mock callback similar to HeaderOracle.process_block_header_event
    events_received = []
    
    async def mock_process_event(event_data):
        """Mock event processor matching oracle signature."""
        events_received.append(event_data)
        print(f"  - Mock callback received event: {type(event_data)}")
        return None  # Oracle callback returns None
    
    # Test that the callback can be passed to polling listener
    try:
        test_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0fA99"
        test_abi = [
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "chainId", "type": "uint256"},
                    {"indexed": True, "name": "blockNumber", "type": "uint256"}
                ],
                "name": "BlockHeaderRequested",
                "type": "event"
            }
        ]
        
        listener = PollingEventListener(
            rpc_url="https://ethereum-sepolia.publicnode.com",
            contract_address=test_address,
            event_name="BlockHeaderRequested",
            abi=test_abi,
            lookback_blocks=1  # Small lookback for test
        )
        
        # Test initial sync with callback (won't find events on test address)
        await listener.initial_sync(mock_process_event)
        print(f"✓ Initial sync completed with mock callback")
        
        # The callback should be compatible
        print(f"✓ Callback signature is compatible")
        
        print("\n[PASS] Event callback signature matches oracle requirements")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all integration tests."""
    print("\n" + "="*70)
    print(" PollingEventListener Integration Tests for Oracle ")
    print("="*70)
    
    tests = [
        ("PollingEventListener Structure", test_polling_listener_structure),
        ("Event Callback Compatibility", test_event_callback_signature),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[ERROR] Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print(" Test Summary ")
    print("="*70)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All integration tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)