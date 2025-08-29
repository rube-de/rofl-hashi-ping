# Utility Classes Documentation

This document provides detailed documentation for the utility classes used in the ROFL Oracle.

## Table of Contents
- [ContractUtility](#contractutility)
- [RoflUtility](#roflutility)
- [PollingEventListener](#pollingeventlistener)
- [Integration Patterns](#integration-patterns)
- [Testing Utilities](#testing-utilities)

## ContractUtility

The `ContractUtility` class provides a flexible interface for interacting with Ethereum smart contracts, supporting both transaction signing and read-only operations.

### Class Overview

```python
class ContractUtility:
    def __init__(self, rpc_url: str, secret: str = "")
    def _add_signing_middleware(self, secret: str) -> None
    def get_contract_abi(self, contract_name: str) -> list
```

### Initialization Modes

#### Full Mode (with Transaction Signing)

When initialized with a private key, the utility can sign and send transactions:

```python
from src.rofl_oracle.utils.contract_utility import ContractUtility

# Full mode with signing capability
utility = ContractUtility(
    rpc_url="https://sapphire.oasis.io",
    secret="0xYourPrivateKey"
)

# The Web3 instance is configured with signing middleware
contract = utility.w3.eth.contract(address=address, abi=abi)

# Can send transactions
tx_hash = contract.functions.storeBlockHeader(
    block_number,
    block_hash
).transact()
```

#### Read-Only Mode

When initialized without a private key, the utility operates in read-only mode:

```python
# Read-only mode
utility = ContractUtility(rpc_url="https://ethereum.publicnode.com")

# Can only read contract state
contract = utility.w3.eth.contract(address=address, abi=abi)
block_hash = contract.functions.getBlockHash(block_number).call()
```

### ABI Management

The utility automatically loads contract ABIs from the `contracts/` directory:

```python
# Load ABI for a contract
abi = utility.get_contract_abi("ROFLAdapter")

# ABIs are loaded from: contracts/ROFLAdapter.json
# Path resolution is automatic and works from any directory
```

### Error Handling

```python
# Missing RPC URL
try:
    utility = ContractUtility("")
except ValueError as e:
    # "RPC URL is required"
    
# Missing contract file
try:
    abi = utility.get_contract_abi("NonExistent")
except FileNotFoundError:
    # Contract file not found
```

### Use Cases

1. **Oracle Operations**: Read-only mode for fetching block headers
2. **Local Testing**: Full mode with local private key
3. **Contract Deployment**: Full mode for deploying contracts
4. **State Monitoring**: Read-only mode for watching contract state

## RoflUtility

The `RoflUtility` class manages interactions with the ROFL runtime, handling key generation, transaction signing, and CBOR response decoding.

### Class Overview

```python
class RoflUtility:
    def __init__(self, url: str = '')
    async def _appd_post(self, path: str, payload: Any) -> Any
    async def fetch_key(self, id: str) -> str
    def _decode_cbor_response(self, response_hex: str) -> Dict[str, Any]
    async def submit_tx(self, tx: TxParams) -> bool
```

### Connection Modes

#### Unix Domain Socket (Default)

```python
# Uses /run/rofl-appd.sock by default
rofl = RoflUtility()

# Custom socket path
rofl = RoflUtility("/custom/path/to/socket.sock")
```

#### HTTP Endpoint

```python
# For testing or remote ROFL access
rofl = RoflUtility("http://localhost:8080")
```

### Key Management

Fetch ephemeral keys from ROFL runtime:

```python
# Generate/fetch a secp256k1 key
key = await rofl.fetch_key("oracle_key_id")

# Keys are managed by ROFL and never exposed
```

### Transaction Submission

Submit transactions through ROFL with automatic signing:

```python
# Prepare transaction
tx_params = {
    "gas": 150000,
    "to": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb7",
    "value": 0,
    "data": "0x" + encoded_function_call
}

# Submit through ROFL
try:
    success = await rofl.submit_tx(tx_params)
    if success:
        logger.info("Transaction submitted successfully")
except Exception as e:
    logger.error(f"Transaction failed: {e}")
```

### CBOR Response Handling

ROFL responses are CBOR-encoded. The utility handles decoding automatically:

```python
# Manual CBOR decoding (usually not needed)
hex_response = "a163026b01f4"  # CBOR for {"ok": true}
decoded = rofl._decode_cbor_response(hex_response)
# Returns: {"ok": True}

# Error responses
hex_error = "a165726f72f5"  # CBOR for {"error": "..."}
decoded = rofl._decode_cbor_response(hex_error)
# Returns: {"error": "error message"}
```

### Timeout Configuration

All ROFL operations use a 30-second timeout:

```python
# Timeout is automatic and configured internally
response = await rofl._appd_post(path, payload)  # 30s timeout
```

## PollingEventListener

The `PollingEventListener` provides reliable event monitoring through periodic polling.

### Key Features

- Configurable polling intervals
- Automatic reconnection on failures
- Initial sync with configurable lookback
- Graceful error handling

### Basic Usage

```python
from src.rofl_oracle.utils.polling_event_listener import PollingEventListener

# Initialize listener
listener = PollingEventListener(
    w3=web3_instance,
    contract=contract_instance,
    event_name="BlockHeaderRequested",
    polling_interval=30,  # seconds
    initial_lookback=100  # blocks
)

# Start listening
async for event in listener.listen():
    # Process each event
    await process_event(event)
```

### Configuration Options

```python
# Minimal configuration
listener = PollingEventListener(
    w3=w3,
    contract=contract,
    event_name="BlockHeaderRequested"
)

# Full configuration
listener = PollingEventListener(
    w3=w3,
    contract=contract,
    event_name="BlockHeaderRequested",
    polling_interval=15,      # Check every 15 seconds
    initial_lookback=500,     # Look back 500 blocks on start
    max_blocks_per_query=1000 # Query up to 1000 blocks at once
)
```

## Integration Patterns

### Oracle Pattern

Combining utilities for a complete oracle:

```python
class Oracle:
    def __init__(self, config):
        # Read-only for source chain
        self.source_utility = ContractUtility(
            rpc_url=config.source_rpc_url
        )
        
        # ROFL for target chain submissions
        self.rofl = RoflUtility()
        
        # Event listener for source chain
        source_contract = self.source_utility.w3.eth.contract(
            address=config.source_contract,
            abi=self.source_utility.get_contract_abi("BlockHeaderRequester")
        )
        
        self.listener = PollingEventListener(
            w3=self.source_utility.w3,
            contract=source_contract,
            event_name="BlockHeaderRequested"
        )
    
    async def run(self):
        async for event in self.listener.listen():
            await self.process_event(event)
```

### Testing Pattern

Using utilities in tests:

```python
@pytest.fixture
async def test_utilities():
    # Mock contract utility for testing
    contract_util = ContractUtility(
        rpc_url="http://localhost:8545",
        secret="0x" + "1" * 64  # Test key
    )
    
    # Mock ROFL utility
    rofl_util = RoflUtility("http://localhost:8080")
    
    return contract_util, rofl_util

async def test_oracle_flow(test_utilities):
    contract_util, rofl_util = test_utilities
    
    # Test contract interaction
    abi = contract_util.get_contract_abi("TestContract")
    assert abi is not None
    
    # Test ROFL submission
    with patch.object(rofl_util, '_appd_post') as mock_post:
        mock_post.return_value = {"data": "a163026b01f4"}
        success = await rofl_util.submit_tx(test_tx)
        assert success
```

## Testing Utilities

### Running Tests

```bash
# Run all utility tests
uv run pytest test/test_contract_utility.py test/test_rofl_utility.py -v

# Run with coverage
uv run pytest test/test_*utility.py --cov=src/rofl_oracle/utils --cov-report=term-missing

# Run specific test
uv run pytest test/test_contract_utility.py::TestContractUtility::test_init_read_only_mode
```

### Mocking Strategies

#### Mocking Web3

```python
@patch('src.rofl_oracle.utils.contract_utility.Web3')
def test_with_mock_web3(mock_web3):
    mock_instance = MagicMock()
    mock_web3.return_value = mock_instance
    
    utility = ContractUtility("http://test.rpc")
    # Assertions on mock_instance
```

#### Mocking ROFL Responses

```python
@patch.object(RoflUtility, '_appd_post')
async def test_with_mock_rofl(mock_post):
    mock_post.return_value = {
        "data": "a163026b01f4"  # CBOR: {"ok": true}
    }
    
    rofl = RoflUtility()
    success = await rofl.submit_tx(tx_params)
    assert success
```

#### Mocking File System

```python
from unittest.mock import mock_open

@patch('builtins.open', mock_open(read_data='{"abi": []}'))
def test_abi_loading():
    utility = ContractUtility("http://test.rpc")
    abi = utility.get_contract_abi("TestContract")
    assert abi == []
```

## Best Practices

### 1. Mode Selection

- Use **read-only mode** for:
  - Event monitoring
  - State queries
  - Source chain interactions

- Use **full mode** for:
  - Local testing only
  - Never in production (use ROFL instead)

### 2. Error Handling

Always wrap utility calls in try-except blocks:

```python
try:
    abi = utility.get_contract_abi("Contract")
except FileNotFoundError:
    logger.error("Contract ABI not found")
    # Handle missing ABI

try:
    success = await rofl.submit_tx(tx)
except Exception as e:
    logger.error(f"ROFL submission failed: {e}")
    # Handle submission failure
```

### 3. Resource Management

Use async context managers when available:

```python
async def process_events():
    listener = PollingEventListener(...)
    try:
        async for event in listener.listen():
            await process(event)
    finally:
        # Cleanup if needed
        pass
```

### 4. Testing

- Always mock external dependencies (Web3, ROFL)
- Test both success and failure paths
- Use fixtures for common test setups
- Verify timeout handling

## Troubleshooting

### Common Issues

#### ContractUtility Issues

**Problem**: "RPC URL is required"
- **Solution**: Ensure RPC URL is provided and not empty

**Problem**: Contract ABI not found
- **Solution**: Verify contract JSON file exists in `contracts/` directory

**Problem**: Transaction fails in read-only mode
- **Solution**: Initialize with private key for transaction signing

#### RoflUtility Issues

**Problem**: Socket connection fails
- **Solution**: Verify `/run/rofl-appd.sock` is mounted and accessible

**Problem**: CBOR decode error
- **Solution**: Check ROFL response format, ensure ROFL is running correctly

**Problem**: Transaction timeout
- **Solution**: Check network latency, ROFL may need more than 30 seconds

#### PollingEventListener Issues

**Problem**: No events received
- **Solution**: Verify contract address, event name, and that events are being emitted

**Problem**: High CPU usage
- **Solution**: Increase polling interval to reduce query frequency

**Problem**: Missing historical events
- **Solution**: Increase `initial_lookback` parameter

## Performance Considerations

### ContractUtility
- Reuse instances when possible
- Cache loaded ABIs in memory
- Use read-only mode when transactions aren't needed

### RoflUtility
- Keep connections alive for multiple transactions
- Batch transactions when possible
- Monitor 30-second timeout for slow operations

### PollingEventListener
- Adjust `polling_interval` based on chain block time
- Set appropriate `max_blocks_per_query` to avoid RPC limits
- Consider using WebSocket for real-time requirements

## Migration Guide

### From Direct Web3 Usage

Before:
```python
w3 = Web3(Web3.HTTPProvider(rpc_url))
account = Account.from_key(private_key)
# Manual middleware setup...
```

After:
```python
utility = ContractUtility(rpc_url, private_key)
# Middleware automatically configured
```

### From Manual ROFL Calls

Before:
```python
# Manual httpx client setup
# Manual CBOR encoding/decoding
# Manual error handling
```

After:
```python
rofl = RoflUtility()
success = await rofl.submit_tx(tx_params)
# Everything handled automatically
```

## Future Enhancements

Planned improvements for utility classes:

1. **ContractUtility**
   - Add connection pooling for multiple RPCs
   - Support for contract verification
   - Automatic gas estimation

2. **RoflUtility**
   - Retry logic with exponential backoff
   - Transaction receipt tracking
   - Batch transaction support

3. **PollingEventListener**
   - WebSocket fallback support
   - Event filtering and transformation
   - Persistent checkpoint storage

## Support

For issues or questions about utilities:
1. Check this documentation
2. Review test files for usage examples
3. Check README.md for quick start guides
4. Open an issue on GitHub for bugs or feature requests