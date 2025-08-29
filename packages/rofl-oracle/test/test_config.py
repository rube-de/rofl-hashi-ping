#!/usr/bin/env python3
"""Tests for the configuration module."""

import logging
import os
import pytest
from unittest.mock import patch

from src.rofl_oracle.config import (
    SourceChainConfig,
    TargetChainConfig, 
    OracleConfig
)


class TestSourceChainConfig:
    """Tests for SourceChainConfig."""
    
    def test_valid_source_config(self):
        """Test creating a valid source chain configuration."""
        config = SourceChainConfig(
            rpc_url="https://ethereum.publicnode.com",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        
        assert config.rpc_url == "https://ethereum.publicnode.com"
        assert config.contract_address == "0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        assert config.chain_id is None  # Not set until connecting to RPC
    
    def test_checksum_address_conversion(self):
        """Test that addresses are converted to checksum format."""
        # Lowercase address should be converted
        config = SourceChainConfig(
            rpc_url="https://test.rpc",
            contract_address="0x85bfe05492afc3d04ff3b2ca6771acf6f853d90d"  # lowercase
        )
        
        # Should be converted to checksum format
        assert config.contract_address == "0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
    
    def test_invalid_rpc_url_scheme(self):
        """Test that invalid RPC URL schemes are rejected."""
        with pytest.raises(ValueError, match="Invalid RPC URL scheme"):
            SourceChainConfig(
                rpc_url="ftp://invalid.scheme",
                contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
            )
    
    def test_missing_rpc_url(self):
        """Test that missing RPC URL raises an error."""
        with pytest.raises(ValueError, match="Source RPC URL is required"):
            SourceChainConfig(
                rpc_url="",
                contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
            )
    
    def test_invalid_contract_address(self):
        """Test that invalid contract address raises an error."""
        with pytest.raises(ValueError, match="Invalid source contract address"):
            SourceChainConfig(
                rpc_url="https://test.rpc",
                contract_address="invalid-address"
            )
    
    def test_missing_contract_address(self):
        """Test that missing contract address raises an error."""
        with pytest.raises(ValueError, match="Source contract address is required"):
            SourceChainConfig(
                rpc_url="https://test.rpc",
                contract_address=""
            )
    
    def test_websocket_rpc_url(self):
        """Test that WebSocket URLs are accepted."""
        config = SourceChainConfig(
            rpc_url="wss://ethereum.publicnode.com",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        assert config.rpc_url == "wss://ethereum.publicnode.com"


class TestTargetChainConfig:
    """Tests for TargetChainConfig."""
    
    def test_valid_target_config(self):
        """Test creating a valid target chain configuration."""
        config = TargetChainConfig(
            network="sapphire-testnet",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        
        assert config.network == "sapphire-testnet"
        assert config.contract_address == "0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
    
    def test_supported_networks(self):
        """Test that all supported networks are accepted."""
        for network in ["sapphire-localnet", "sapphire-testnet", "sapphire-mainnet"]:
            config = TargetChainConfig(
                network=network,
                contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
            )
            assert config.network == network
    
    def test_unsupported_network(self):
        """Test that unsupported networks are rejected."""
        with pytest.raises(ValueError, match="Unsupported network"):
            TargetChainConfig(
                network="invalid-network",
                contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
            )
    
    def test_missing_contract_address(self):
        """Test that missing contract address raises an error."""
        with pytest.raises(ValueError, match="Target contract address is required"):
            TargetChainConfig(
                network="sapphire-testnet",
                contract_address=""
            )


class TestOracleConfig:
    """Tests for OracleConfig."""
    
    def test_valid_oracle_config(self):
        """Test creating a valid oracle configuration."""
        source = SourceChainConfig(
            rpc_url="https://test.rpc",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        target = TargetChainConfig(
            network="sapphire-testnet",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        
        config = OracleConfig(
            source_chain=source,
            target_chain=target,
            polling_interval=12
        )
        
        assert config.source_chain == source
        assert config.target_chain == target
        assert config.polling_interval == 12
        assert config.local_mode is False
        assert config.local_private_key is None
    
    def test_polling_interval_validation(self):
        """Test polling interval validation."""
        source = SourceChainConfig(
            rpc_url="https://test.rpc",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        target = TargetChainConfig(
            network="sapphire-testnet",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        
        # Test zero interval
        with pytest.raises(ValueError, match="Polling interval must be positive"):
            OracleConfig(source_chain=source, target_chain=target, polling_interval=0)
        
        # Test negative interval
        with pytest.raises(ValueError, match="Polling interval must be positive"):
            OracleConfig(source_chain=source, target_chain=target, polling_interval=-1)
        
        # Test too long interval
        with pytest.raises(ValueError, match="Polling interval too long"):
            OracleConfig(source_chain=source, target_chain=target, polling_interval=301)
    
    def test_local_mode_requires_private_key(self):
        """Test that local mode requires a private key."""
        source = SourceChainConfig(
            rpc_url="https://test.rpc",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        target = TargetChainConfig(
            network="sapphire-testnet",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        
        with pytest.raises(ValueError, match="Local mode requires LOCAL_PRIVATE_KEY"):
            OracleConfig(
                source_chain=source,
                target_chain=target,
                local_mode=True,
                local_private_key=None
            )
    
    def test_valid_private_key(self):
        """Test valid private key format."""
        source = SourceChainConfig(
            rpc_url="https://test.rpc",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        target = TargetChainConfig(
            network="sapphire-testnet",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        
        # Valid key with 0x prefix
        config = OracleConfig(
            source_chain=source,
            target_chain=target,
            local_mode=True,
            local_private_key="0x" + "a" * 64
        )
        assert config.local_private_key == "0x" + "a" * 64
        
        # Valid key without prefix
        config = OracleConfig(
            source_chain=source,
            target_chain=target,
            local_mode=True,
            local_private_key="b" * 64
        )
        assert config.local_private_key == "b" * 64
    
    def test_invalid_private_key_length(self):
        """Test invalid private key length."""
        source = SourceChainConfig(
            rpc_url="https://test.rpc",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        target = TargetChainConfig(
            network="sapphire-testnet",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        
        with pytest.raises(ValueError, match="Invalid private key length"):
            OracleConfig(
                source_chain=source,
                target_chain=target,
                local_mode=True,
                local_private_key="0x" + "a" * 63  # Too short
            )
    
    def test_invalid_private_key_format(self):
        """Test invalid private key format."""
        source = SourceChainConfig(
            rpc_url="https://test.rpc",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        target = TargetChainConfig(
            network="sapphire-testnet",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        
        with pytest.raises(ValueError, match="Invalid private key format"):
            OracleConfig(
                source_chain=source,
                target_chain=target,
                local_mode=True,
                local_private_key="0x" + "g" * 64  # Invalid hex
            )
    
    @patch.dict(os.environ, {
        "SOURCE_RPC_URL": "https://test.rpc",
        "SOURCE_CONTRACT_ADDRESS": "0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d",
        "CONTRACT_ADDRESS": "0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d",
        "NETWORK": "sapphire-testnet",
        "POLLING_INTERVAL": "20"
    })
    def test_from_env(self):
        """Test loading configuration from environment variables."""
        config = OracleConfig.from_env()
        
        assert config.source_chain.rpc_url == "https://test.rpc"
        assert config.source_chain.contract_address == "0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        assert config.target_chain.network == "sapphire-testnet"
        assert config.target_chain.contract_address == "0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        assert config.polling_interval == 20
        assert config.local_mode is False
    
    @patch.dict(os.environ, {
        "SOURCE_RPC_URL": "https://test.rpc",
        "SOURCE_CONTRACT_ADDRESS": "0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d",
        "CONTRACT_ADDRESS": "0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d",
        "LOCAL_PRIVATE_KEY": "0x" + "a" * 64
    })
    def test_from_env_local_mode(self):
        """Test loading configuration for local mode."""
        config = OracleConfig.from_env(local_mode=True)
        
        assert config.local_mode is True
        assert config.local_private_key == "0x" + "a" * 64
    
    @patch.dict(os.environ, {})
    def test_from_env_missing_required(self):
        """Test that missing required environment variables raise errors."""
        with pytest.raises(ValueError, match="SOURCE_CONTRACT_ADDRESS"):
            OracleConfig.from_env()
    
    @patch.dict(os.environ, {
        "SOURCE_CONTRACT_ADDRESS": "0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
    })
    def test_from_env_missing_target_contract(self):
        """Test that missing target contract raises an error."""
        with pytest.raises(ValueError, match="CONTRACT_ADDRESS"):
            OracleConfig.from_env()
    
    def test_with_chain_id(self):
        """Test updating configuration with chain ID."""
        source = SourceChainConfig(
            rpc_url="https://test.rpc",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        target = TargetChainConfig(
            network="sapphire-testnet",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        
        config = OracleConfig(
            source_chain=source,
            target_chain=target
        )
        
        # Initially no chain ID
        assert config.source_chain.chain_id is None
        
        # Update with chain ID
        new_config = config.with_chain_id(1)
        
        # New config has chain ID
        assert new_config.source_chain.chain_id == 1
        # Other fields unchanged
        assert new_config.source_chain.rpc_url == config.source_chain.rpc_url
        assert new_config.target_chain == config.target_chain
        assert new_config.polling_interval == config.polling_interval
    
    def test_log_config(self, caplog):
        """Test configuration logging."""
        source = SourceChainConfig(
            rpc_url="https://test.rpc",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d",
            chain_id=1
        )
        target = TargetChainConfig(
            network="sapphire-testnet",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        
        config = OracleConfig(
            source_chain=source,
            target_chain=target,
            polling_interval=15,
            local_mode=True,
            local_private_key="0x" + "a" * 64
        )
        
        with caplog.at_level(logging.INFO):
            config.log_config()
        
        log_text = caplog.text
        assert "ROFL Oracle Configuration" in log_text
        assert "https://test.rpc" in log_text
        assert "Chain ID: 1" in log_text
        assert "sapphire-testnet" in log_text
        assert "15 seconds" in log_text
        assert "Mode: LOCAL" in log_text
        assert "Local Key: [CONFIGURED]" in log_text
    
    def test_immutability(self):
        """Test that configuration is immutable."""
        source = SourceChainConfig(
            rpc_url="https://test.rpc",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        target = TargetChainConfig(
            network="sapphire-testnet",
            contract_address="0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d"
        )
        
        config = OracleConfig(
            source_chain=source,
            target_chain=target
        )
        
        # Cannot modify attributes
        with pytest.raises(AttributeError):
            config.polling_interval = 30
        
        with pytest.raises(AttributeError):
            config.source_chain.rpc_url = "https://new.rpc"