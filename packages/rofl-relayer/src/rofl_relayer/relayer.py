"""
ROFL Relayer implementation.

This module contains the main relayer service that monitors Ping events
on Ethereum and relays them to Oasis Sapphire using cryptographic proofs.
"""

import asyncio
import sys

from .config import RelayerConfig


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
        
    async def run(self) -> None:
        """Main event loop for the relayer service."""
        self.running = True
        print("\nROFL Relayer Started")
        print("Monitoring for Ping events...")

        try:
            # TODO: Phase 2 - Initialize EventListenerUtility
            # TODO: Phase 2 - Start WebSocket monitoring
            # TODO: Phase 2 - Process events from queue

            # For now, just keep the service running
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            print(f"\nError in main loop: {e}")
            raise
        finally:
            print("\nROFL Relayer Stopped")

    def stop(self) -> None:
        """Stop the relayer service."""
        self.running = False