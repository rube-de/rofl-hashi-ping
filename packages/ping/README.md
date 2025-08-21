# Ping Package - BlockHeaderRequester Contract

## Overview

This package contains the `BlockHeaderRequester` - an MVP smart contract that enables event-driven block header synchronization between chains. It emits events monitored by the ROFL Header Oracle to fetch and store block headers on-demand.

## Features

- **Event-Driven**: Replaces polling with efficient event-based block requests
- **Public Access**: Anyone can request blocks (MVP - no restrictions)
- **Deduplication**: Prevents requesting the same block multiple times
- **Cross-Chain Support**: Can request blocks from any chain ID

## Contract Interface

```solidity
// Request a block header
function requestBlockHeader(
    uint256 chainId,      // Source chain ID (e.g., 11155111 for Sepolia)
    uint256 blockNumber,  // Block number to request
    bytes32 context      // Optional context (e.g., message ID)
) external

// Check if a block was already requested
function isBlockRequested(
    uint256 chainId,
    uint256 blockNumber
) external view returns (bool)

// Get the request ID for a chain/block combination
function getRequestId(
    uint256 chainId,
    uint256 blockNumber
) public pure returns (bytes32)
```

## Events

```solidity
event BlockHeaderRequested(
    uint256 indexed chainId,
    uint256 indexed blockNumber,
    address requester,
    bytes32 context
);
```

## Quick Start

```bash
# Install dependencies
bun install

# Compile contracts
bun hardhat compile

# Run tests
bun hardhat test

# Set your private key
export PRIVATE_KEY=your_private_key_here

# Deploy to Sepolia
bun hardhat deploy:block-header-requester --network eth-sepolia

# Deploy with verification
bun hardhat deploy:block-header-requester --network eth-sepolia --verify true
```

## Tasks

### Deploy Contract
```bash
bun hardhat deploy:block-header-requester --network eth-sepolia [--verify true]
```
Options:
- `--verify`: Verify on Etherscan (default: false)

### Request Block Header
```bash
# Request latest block from current network (uses defaults)
bun hardhat request:block-header --contract 0x... --network eth-sepolia

# Request specific block from specific chain
bun hardhat request:block-header \
  --contract 0x... \
  --chainid 1 \
  --blocknumber 5000000 \
  --network eth-sepolia
```
Options:
- `--contract`: Contract address (required)
- `--chainid`: Chain ID (optional, defaults to current network)
- `--blocknumber`: Block number (optional, defaults to latest)
- `--context`: Context data (optional)

### Check Request Status
```bash
bun hardhat check:block-requested \
  --contract 0x... \
  --chainid 1 \
  --blocknumber 5000000 \
  --network eth-sepolia
```

## Testing

```bash
# Run all tests
bun hardhat test

# Run with coverage
bun hardhat coverage

# Run specific test
bun hardhat test test/BlockHeaderRequester.test.ts
```

## How It Works

1. **Request**: Anyone calls `requestBlockHeader()` with a chain ID and block number
2. **Event**: Contract emits `BlockHeaderRequested` event
3. **Oracle**: ROFL Header Oracle monitors events and fetches the requested block
4. **Storage**: Oracle stores the block header in ROFLAdapter on Sapphire

## Example Usage

```typescript
// Request a block when sending a cross-chain message
const requester = await ethers.getContractAt("BlockHeaderRequester", address);

// Request the current block from current network
const chainId = (await ethers.provider.getNetwork()).chainId;
const blockNumber = await ethers.provider.getBlockNumber();
const messageId = ethers.encodeBytes32String("msg-001");

const tx = await requester.requestBlockHeader(chainId, blockNumber, messageId);
await tx.wait();

console.log("Block header requested for message:", messageId);
```

## Network Configuration

- `hardhat` - Local Hardhat network
- `sapphire-localnet` - Local Oasis Sapphire (port 8545)
- `eth-sepolia` - Ethereum Sepolia testnet
- `base-sepolia` - Base Sepolia testnet
- `sapphire-testnet` - Oasis Sapphire testnet

## Gas Costs

- Deploy contract: ~358,000 gas
- Request block header: ~47,500 gas

## Security Considerations

⚠️ **MVP Version**: This is a minimal implementation for testing:
- No access control (anyone can request)
- No rate limiting
- Basic deduplication only

For production, consider adding:
- Access control for authorized requesters
- Rate limiting to prevent spam
- Block range validation
- Emergency pause mechanism

## Future Enhancements

- [ ] Access control system
- [ ] Block range requests
- [ ] Rate limiting
- [ ] Request cancellation
- [ ] Request priority levels
- [ ] Integration with Hashi Reporter pattern
- [ ] CrossChainPingSender contract
- [ ] PingReceiver contract on Sapphire

## Project Structure

```
packages/ping/
├── contracts/
│   └── BlockHeaderRequester.sol
├── tasks/
│   └── deploy-block-header-requester.ts
├── test/
│   └── BlockHeaderRequester.test.ts
├── hardhat.config.ts
└── README.md
```

## Environment Variables

```bash
# Required for deployment
PRIVATE_KEY=your_private_key_here

# Optional - for Alchemy RPC
ALCHEMY_API_KEY=your_alchemy_api_key
```

## License

MIT