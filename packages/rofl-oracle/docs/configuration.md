# ROFL Oracle Configuration Guide

This document describes the configuration system for the ROFL Oracle, introduced as part of the refactoring effort (Task 1.1).

## Overview

The ROFL Oracle uses a type-safe configuration system built with Python dataclasses. Configuration is loaded from environment variables with comprehensive validation to ensure all settings are correct before the oracle starts.

## Configuration Structure

The configuration is organized into three main components:

```python
OracleConfig
├── SourceChainConfig    # Source blockchain settings
├── TargetChainConfig    # Target Sapphire network settings
└── Oracle Settings      # Polling interval, mode, etc.
```

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SOURCE_CONTRACT_ADDRESS` | Address of the BlockHeaderRequester contract on the source chain | `0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d` |
| `CONTRACT_ADDRESS` | Address of the ROFLAdapter contract on Sapphire | `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb` |

### Optional Variables

| Variable | Description | Default | Valid Values |
|----------|-------------|---------|--------------|
| `SOURCE_RPC_URL` | RPC endpoint for the source chain | `https://ethereum.publicnode.com` | Any HTTP(S) or WebSocket URL |
| `NETWORK` | Target Sapphire network | `sapphire-testnet` | `sapphire-localnet`, `sapphire-testnet`, `sapphire-mainnet` |
| `POLLING_INTERVAL` | Seconds between event checks | `12` | 1-300 |
| `LOCAL_PRIVATE_KEY` | Private key for local mode testing | None | 64 hex characters (with or without 0x prefix) |

## Usage Examples

### Basic Usage

```bash
# Set required environment variables
export SOURCE_CONTRACT_ADDRESS=0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d
export CONTRACT_ADDRESS=0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb

# Run the oracle
python main.py
```

### Custom Source Chain

```bash
export SOURCE_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY
export SOURCE_CONTRACT_ADDRESS=0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d
export CONTRACT_ADDRESS=0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb

python main.py
```

### Local Mode Testing

```bash
# Set local mode private key
export LOCAL_PRIVATE_KEY=0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef

# Run in local mode
python main.py --local
```

### Custom Polling Interval

```bash
export POLLING_INTERVAL=30  # Check every 30 seconds
python main.py
```

## Configuration Loading

The configuration is loaded using the `OracleConfig.from_env()` class method:

```python
from src.rofl_oracle.config import OracleConfig

# Load configuration from environment
config = OracleConfig.from_env(local_mode=False)

# Access configuration values
print(f"Source RPC: {config.source_chain.rpc_url}")
print(f"Target Network: {config.target_chain.network}")
print(f"Polling Interval: {config.polling_interval}")
```

## Validation

The configuration system performs comprehensive validation:

### Address Validation
- Validates Ethereum addresses using Web3
- Automatically converts addresses to checksum format
- Rejects invalid addresses with clear error messages

### URL Validation
- Accepts HTTP, HTTPS, WebSocket (ws/wss) schemes
- Rejects invalid URL schemes (e.g., FTP)
- Validates URL format

### Network Validation
- Only accepts supported Sapphire networks
- Provides list of valid networks in error messages

### Polling Interval Validation
- Must be positive integer
- Minimum: 1 second
- Maximum: 300 seconds (5 minutes)

### Private Key Validation (Local Mode)
- Required when using `--local` flag
- Must be 64 hexadecimal characters
- Can include or omit `0x` prefix

## Error Handling

The configuration system provides clear, actionable error messages:

```bash
# Missing required variable
❌ Configuration Error: CONTRACT_ADDRESS environment variable is required. 
This should be the ROFLAdapter contract address on Sapphire.

# Invalid address format
❌ Configuration Error: Invalid source contract address: invalid-address

# Unsupported network
❌ Configuration Error: Unsupported network: invalid-network. 
Supported networks: sapphire-localnet, sapphire-mainnet, sapphire-testnet
```

## Configuration Immutability

Configuration objects are immutable (frozen dataclasses) to prevent accidental modification during runtime:

```python
config = OracleConfig.from_env()
config.polling_interval = 30  # Raises AttributeError
```

To update configuration (e.g., adding chain ID after RPC connection):

```python
# Create new config with chain ID
config = config.with_chain_id(chain_id=1)
```

## Debugging Configuration

Use the `log_config()` method to display the current configuration:

```python
config = OracleConfig.from_env()
config.log_config()
```

Output:
```
============================================================
ROFL Oracle Configuration
============================================================

Source Chain:
  RPC URL: https://ethereum.publicnode.com
  Contract: 0x85BfE05492aFC3D04Ff3B2ca6771ACF6f853d90d
  Chain ID: 1

Target Chain (Sapphire):
  Network: sapphire-testnet
  Contract: 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb

Oracle Settings:
  Polling Interval: 12 seconds
  Mode: PRODUCTION
============================================================
```

## Testing

The configuration system includes comprehensive tests:

```bash
# Run configuration tests
cd packages/rofl-oracle
uv run pytest test/test_config.py -v
```

Test coverage includes:
- Valid configuration creation
- Environment variable loading
- Validation error cases
- Address checksumming
- Private key validation
- Configuration immutability
- Chain ID updates

## Migration from Old System

The new configuration system replaces the previous scattered environment variable loading:

### Before (Old System)
```python
# Variables loaded in multiple places
contract_address = os.environ.get("CONTRACT_ADDRESS", "")
self.network = os.environ.get("NETWORK", "sapphire-testnet")
self.polling_interval = int(os.environ.get("POLLING_INTERVAL", "12"))
```

### After (New System)
```python
# Centralized configuration with validation
config = OracleConfig.from_env()
# All settings validated and ready to use
```

## Benefits of the New System

1. **Type Safety**: Full type hints for all configuration values
2. **Validation**: Comprehensive validation with clear error messages
3. **Immutability**: Prevents accidental configuration changes
4. **Centralization**: Single source of truth for configuration
5. **Testability**: Easy to test with mock configurations
6. **Performance**: Uses `slots=True` for memory efficiency
7. **Documentation**: Self-documenting with dataclass attributes

## Future Enhancements

Potential improvements for future iterations:
- YAML/TOML configuration file support
- Configuration hot-reloading
- Environment-specific configuration profiles
- Configuration validation CLI command
- Default configuration templates