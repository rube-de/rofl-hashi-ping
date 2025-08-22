# Ping Package - Cross-Chain Event Verification

Cross-chain ping system using Oasis ROFL and Hashi protocol. Proves events occurred on one chain and verifies them on another using cryptographic proofs.

## Components

- **PingSender**: Emits ping events on source chain
- **PingReceiver**: Verifies ping events on target chain using Merkle proofs
- **BlockHeaderRequester**: Requests block headers for proof generation
- **ROFL Header Oracle**: Trustlessly provides block headers on target chain
- **Relayer**: Off-chain service that generates and submits proofs (can be run by anyone)

## Security

- **Cryptographic Proofs**: Tamper-proof verification using Merkle Patricia Trie
- **Multi-Oracle Consensus**: Hashi aggregates multiple oracles for block header validation
- **Replay Protection**: Block number ensures each ping is unique
- **Permissionless**: Anyone with valid proof can trigger verification

## Flow

1. User calls `PingSender.ping()` on source chain
2. `Ping(sender, blockNumber)` event is emitted
3. Block header is automatically requested for proof generation
4. ROFL Header Oracle trustlessly provides block headers on target chain
5. Relayer detects event and generates Merkle proof
6. Anyone calls `PingReceiver.receivePing()` with proof
7. Event is verified using trustless block headers from ROFL oracle

## Contract API

### PingSender
```solidity
function ping() external returns (bytes32 pingId)
function generatePingId(uint256 sourceChainId, address sender, uint256 blockNumber) external pure returns (bytes32)
```

### PingReceiver  
```solidity
function receivePing(ReceiptProof calldata proof) external
function getPingStatus(bytes32 pingId) external view returns (bool received, address originalSender, uint256 originalBlockNumber)
```

## Key Events

```solidity
// PingSender
event Ping(address indexed sender, uint256 indexed blockNumber);

// PingReceiver  
event PingReceived(uint256 indexed sourceChainId, bytes32 indexed pingId, address indexed originalSender, uint256 originalBlockNumber);
```

## Quick Start

```bash
bun install
bun hardhat compile
bun hardhat test

export PRIVATE_KEY=your_private_key_here
```

## Deploy

```bash
# Deploy across eth-sepolia -> sapphire-testnet
bun hardhat deploy-ping-cross-chain --shoyu-bashi 0x...

# Custom networks
bun hardhat deploy-ping-cross-chain \
  --source-network eth-sepolia \
  --target-network base-sepolia \
  --shoyu-bashi 0x...
```

## Usage

```bash
# Send ping
bun hardhat send-ping --network eth-sepolia --sender 0x...

# Check status
bun hardhat check-ping --network sapphire-testnet --receiver 0x... --ping-id 0x...
```

## Networks

- `eth-sepolia` - Ethereum Sepolia testnet
- `base-sepolia` - Base Sepolia testnet  
- `sapphire-testnet` - Oasis Sapphire testnet
- `hardhat` - Local development

## Environment Variables

```bash
PRIVATE_KEY=your_private_key_here
ALCHEMY_API_KEY=your_alchemy_api_key  # Optional
```

## License

MIT