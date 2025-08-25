"""
Configuration module for ROFL Relayer.

This module provides dataclasses for managing configuration of the ROFL relayer
that monitors Ping events on Ethereum and relays them to Oasis Sapphire.
"""

import os
from dataclasses import dataclass, field


@dataclass
class SourceChainConfig:
    """Configuration for the source chain (Ethereum Sepolia)."""
    rpc_url: str
    ping_sender_address: str


@dataclass
class TargetChainConfig:
    """Configuration for the target chain (Oasis Sapphire)."""
    ping_receiver_address: str
    rofl_adapter_address: str
    private_key: str
    network: str = "sapphire-testnet"  # Default to testnet


@dataclass
class MonitoringConfig:
    """Configuration for event monitoring and processing."""
    # Hard-coded sensible defaults for MVP
    polling_interval: int = 30  # seconds
    retry_count: int = 3
    lookback_blocks: int = 100
    websocket_timeout: int = 60  # seconds
    process_batch_size: int = 10  # max events to process in one batch


@dataclass
class RelayerConfig:
    """Main configuration class for the ROFL Relayer."""

    source_chain: SourceChainConfig
    target_chain: TargetChainConfig
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    local_mode: bool = False

    @classmethod
    def from_env(cls, local_mode: bool = False) -> "RelayerConfig":
        """
        Load configuration from environment variables.

        Returns:
            RelayerConfig: Configured relayer instance

        Raises:
            ValueError: If required environment variables are missing
        """
        # Source chain configuration
        source_rpc_url = os.environ.get("SOURCE_RPC_URL")
        if not source_rpc_url:
            raise ValueError(
                "SOURCE_RPC_URL environment variable is required. "
                "Example: https://ethereum-sepolia.publicnode.com"
            )

        ping_sender_address = os.environ.get("PING_SENDER_ADDRESS")
        if not ping_sender_address:
            raise ValueError(
                "PING_SENDER_ADDRESS environment variable is required. "
                "This is the address of the deployed PingSender contract on source chain"
            )

        # Target chain configuration
        target_network = os.environ.get("TARGET_NETWORK", "sapphire-testnet")

        ping_receiver_address = os.environ.get("PING_RECEIVER_ADDRESS")
        if not ping_receiver_address:
            raise ValueError(
                "PING_RECEIVER_ADDRESS environment variable is required. "
                "This is the address of the deployed PingReceiver contract on target chain"
            )

        rofl_adapter_address = os.environ.get("ROFL_ADAPTER_ADDRESS")
        if not rofl_adapter_address:
            raise ValueError(
                "ROFL_ADAPTER_ADDRESS environment variable is required. "
                "This is the address of the ROFLAdapter contract for monitoring HashStored events"
            )

        private_key = os.environ.get("PRIVATE_KEY")
        if not private_key:
            if not local_mode:
                # In ROFL mode, private key might be managed differently
                private_key = "0x" + "0" * 64  # Placeholder for ROFL mode
            else:
                raise ValueError(
                    "PRIVATE_KEY environment variable is required in local mode. "
                    "This is used to sign transactions on the target chain"
                )

        # Monitoring configuration with hard-coded defaults
        monitoring_config = MonitoringConfig()

        # Create configuration objects
        source_chain = SourceChainConfig(
            rpc_url=source_rpc_url,
            ping_sender_address=ping_sender_address,
        )

        target_chain = TargetChainConfig(
            ping_receiver_address=ping_receiver_address,
            rofl_adapter_address=rofl_adapter_address,
            private_key=private_key,
            network=target_network,
        )

        return cls(
            source_chain=source_chain,
            target_chain=target_chain,
            monitoring=monitoring_config,
            local_mode=local_mode,
        )

    def log_config(self) -> None:
        """Log configuration settings (hiding sensitive data)."""
        print("\n=== ROFL Relayer Configuration ===")
        print(f"Mode: {'LOCAL' if self.local_mode else 'ROFL'}")

        print("\n[Source Chain]")
        print(f"  RPC URL: {self.source_chain.rpc_url}")
        print(f"  PingSender: {self.source_chain.ping_sender_address}")

        print("\n[Target Chain]")
        print(f"  Network: {self.target_chain.network}")
        print(f"  PingReceiver: {self.target_chain.ping_receiver_address}")
        print(f"  ROFLAdapter: {self.target_chain.rofl_adapter_address}")
        print(f"  Private Key: {'[SET]' if self.target_chain.private_key else '[NOT SET]'}")

        print("\n[Monitoring Settings]")
        print(f"  Polling Interval: {self.monitoring.polling_interval}s")
        print(f"  Retry Count: {self.monitoring.retry_count}")
        print(f"  Lookback Blocks: {self.monitoring.lookback_blocks}")
        print(f"  WebSocket Timeout: {self.monitoring.websocket_timeout}s")
        print(f"  Batch Size: {self.monitoring.process_batch_size}")
        print("===================================\n")