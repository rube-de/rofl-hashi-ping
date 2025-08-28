# Event-Driven Header Oracle MVP Implementation Plan

## Overview

This document outlines the MVP (Minimum Viable Product) implementation plan for transitioning from a polling-based header oracle to an event-driven system that efficiently synchronizes block headers between Ethereum Sepolia and Oasis Sapphire using ROFL (Runtime OFf-chain Logic).

## MVP Goals

1. **Simplicity**: Minimal viable functionality to prove the concept
2. **Event-Driven**: Replace polling with event-based block requests
3. **Public Access**: No restrictions for MVP testing
4. **Single Blocks**: Support individual block requests only
5. **Quick Deployment**: Get to testnet fast for validation

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Ethereum Sepolia                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐         ┌──────────────────────┐             │
│  │  PingSender     │────────▶│ BlockHeaderRequester │             │
│  │  (future)       │ request │ (event emitter)      │             │
│  └─────────────────┘         └──────────┬───────────┘             │
│                                          │                         │
│                              BlockHeaderRequested                  │
│                                   Event ▼                          │
└─────────────────────────────────────────┼─────────────────────────┘
                                          │
                                          │ Monitor
                                          │
┌─────────────────────────────────────────┼─────────────────────────┐
│                    ROFL Environment     ▼                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────┐             │
│  │            Header Oracle Service                  │             │
│  │  - Monitors BlockHeaderRequested events          │             │
│  │  - Fetches requested blocks from Ethereum        │             │
│  │  - Submits to ROFLAdapter with ROFL auth        │             │
│  └──────────────────────────────────┬───────────────┘             │
│                                      │                             │
└──────────────────────────────────────┼─────────────────────────────┘
                                      │
                                      │ Store
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Oasis Sapphire                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────┐             │
│  │              ROFLAdapter Contract                 │             │
│  │  - Verifies ROFL authorization                   │             │
│  │  - Stores block headers                          │             │
│  │  - Provides header access for message relayer    │             │
│  └──────────────────────────────────────────────────┘             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Event-Driven Header Oracle (Current Focus)

#### 1.1 BlockHeaderRequester Contract (Ethereum Sepolia) - Minimal Version

**Location**: `packages/ping/contracts/BlockHeaderRequester.sol`

**Key Features (MVP Implementation)**:
- Emit `BlockHeaderRequested` events when blocks are needed
- Support single block requests only
- Public access (no restrictions for MVP)
- Basic deduplication to prevent redundant requests

**Contract Interface (MVP)**:
```solidity
contract BlockHeaderRequester {
    event BlockHeaderRequested(
        uint256 indexed chainId,
        uint256 indexed blockNumber,
        address requester,
        bytes32 context
    );
    
    // MVP - anyone can request, single blocks only
    function requestBlockHeader(uint256 chainId, uint256 blockNumber, bytes32 context) external;
}
```

#### 1.2 Modified Header Oracle Service (Python)

**Location**: `packages/rofl-oracle/src/rofl_oracle/header_oracle.py`

**Changes Required (Minimal)**:
1. Replace polling loop with event monitoring
2. Add event filter for `BlockHeaderRequested` events
3. Implement basic request deduplication
4. Add context tracking for debugging

**Key Methods (Minimal)**:
- `monitor_events()`: Main event monitoring loop
- `process_block_request()`: Handle individual block requests
- `fetch_and_store_block()`: Existing functionality, adapted for events

#### 1.3 ROFLAdapter Contract (Already Exists)

**Location**: `packages/hashi/packages/evm/contracts/adapters/oasis/ROFLAdapter.sol`

**No Changes Required**: Current implementation already supports storing block headers with ROFL authorization.

### Phase 2: Message Relayer (Future Implementation)

#### 2.1 CrossChainPingSender Contract (Ethereum Sepolia)

**Purpose**: Initiate cross-chain ping messages

**Key Features**:
- Create ping messages with target chain and data
- Request required block headers automatically
- Emit events for message relayer monitoring

#### 2.2 ROFL Message Relayer Service

**Purpose**: Relay messages with merkle proofs

**Key Features**:
- Monitor message events from PingSender
- Generate merkle proofs using stored headers
- Submit messages to target chain
- Verify message execution

#### 2.3 PingReceiver Contract (Oasis Sapphire)

**Purpose**: Execute ping messages on target chain

**Key Features**:
- Verify merkle proofs against stored headers
- Execute ping logic
- Emit confirmation events

### Phase 3: Hashi Integration (Future Enhancement)

#### 3.1 ROFLReporter Contract

**Purpose**: Bridge to Hashi protocol

**Key Features**:
- Implement IReporter interface
- Integrate with Yaho for message dispatching
- Maintain compatibility with existing adapters

## MVP Implementation Steps

### Step 1: Deploy MVP Contract
1. Deploy BlockHeaderRequester.sol to Ethereum Sepolia
2. Verify on Etherscan
3. Test with a manual transaction

### Step 2: Update Header Oracle
1. Add event listener for BlockHeaderRequested
2. Process events and fetch blocks
3. Submit to ROFLAdapter

### Step 3: Test End-to-End
1. Request a block via contract
2. Verify oracle processes event
3. Check block stored on Sapphire

### Future Improvements (Post-MVP)
- Access control
- Block range requests
- Rate limiting
- Batch optimization

## Configuration

### Environment Variables

**Header Oracle Service**:
```bash
# Existing variables
CONTRACT_ADDRESS=0x...  # ROFLAdapter on Sapphire
NETWORK=sapphire-testnet
SOURCE_RPC_URL=https://ethereum-sepolia.publicnode.com

# New variables
REQUESTER_CONTRACT_ADDRESS=0x...  # BlockHeaderRequester on Ethereum
EVENT_LOOKBACK_BLOCKS=1000  # How many blocks to look back for events
EVENT_POLLING_INTERVAL=12  # Seconds between event checks
```

### Gas Considerations

**Ethereum Sepolia**:
- BlockHeaderRequested event: ~25,000 gas
- Future: Batch request (10 blocks): ~50,000 gas

**Oasis Sapphire**:
- Store single header: ~45,000 gas
- Future: Store batch (10 headers): ~350,000 gas

## Security Considerations

1. **MVP**: Public access (add restrictions in production)
2. **ROFL Authorization**: All header storage requires valid ROFL auth
3. **Event Replay Protection**: Track processed requests to prevent duplicates
4. **Chain ID Validation**: Verify requests match monitored chain
5. **Future**: Access control and rate limiting (production version)

## Testing Strategy

### Unit Tests
- BlockHeaderRequester contract tests (Hardhat)
- Header Oracle event processing (Python pytest)
- Mock event generation for testing

### Integration Tests
- End-to-end block request and storage
- Multi-block range requests
- Error handling and recovery
- Performance under load

### Testnet Deployment
1. Deploy to Ethereum Sepolia first
2. Test with small number of requests
3. Monitor gas usage and performance
4. Scale up gradually

## Monitoring and Maintenance

### Metrics to Track
- Number of block requests per hour
- Average response time from request to storage
- Gas costs on both chains
- Failed requests and error rates
- RPC endpoint health

### Alerting
- Set up alerts for:
  - Oracle service downtime
  - High error rates
  - Unusual request patterns
  - Low ROFL app balance

## Future Enhancements (v2 and beyond)

1. **Block Range Requests**: Add support for requesting multiple blocks
2. **Access Control**: Fine-grained requester authorization
3. **Batch Optimization**: Process multiple requests in single transaction
4. **Caching Layer**: Cache frequently requested blocks
5. **Multi-Chain Support**: Extend to other source chains
6. **WebSocket Support**: Use WebSocket for real-time event monitoring
7. **Merkle Proof Generation**: Add proof generation to oracle service

## Dependencies

### Smart Contracts
- OpenZeppelin Contracts: v5.0.0
- Oasis Sapphire Contracts: latest
- Hardhat: v2.19.0

### Python Services
- web3.py: v6.0.0
- oasis-sdk: latest
- cbor2: v5.4.0

## MVP Timeline

- **Day 1**: Deploy MVP contract to Sepolia
- **Day 2**: Update Header Oracle with event monitoring
- **Day 3**: End-to-end testing
- **Future**: Production hardening and features

## MVP Success Criteria

1. ✅ Can request a block header via contract
2. ✅ Oracle detects and processes the event
3. ✅ Block header stored on Sapphire
4. ✅ Deduplication works (same block not fetched twice)

## Future Success Criteria

1. ✅ Support for block range requests
2. ✅ 50% reduction in unnecessary RPC calls
3. ✅ System handles 100+ requests per hour
4. ✅ Complete test coverage (>80%)
5. ✅ Fine-grained access control

## Appendix

### A. MVP Contract Implementation

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract BlockHeaderRequester {
    
    event BlockHeaderRequested(
        uint256 indexed chainId,
        uint256 indexed blockNumber,
        address requester,
        bytes32 context
    );
    
    mapping(bytes32 => bool) public requestedBlocks;
    
    function requestBlockHeader(
        uint256 chainId,
        uint256 blockNumber,
        bytes32 context
    ) external {
        bytes32 requestId = keccak256(abi.encode(chainId, blockNumber));
        
        // Simple deduplication
        require(!requestedBlocks[requestId], "Already requested");
        
        requestedBlocks[requestId] = true;
        emit BlockHeaderRequested(chainId, blockNumber, msg.sender, context);
    }
    
    // Check if a block was already requested
    function isBlockRequested(uint256 chainId, uint256 blockNumber) 
        external 
        view 
        returns (bool) 
    {
        bytes32 requestId = keccak256(abi.encode(chainId, blockNumber));
        return requestedBlocks[requestId];
    }
}
```

### B. Event Structure

```solidity
event BlockHeaderRequested(
    uint256 indexed chainId,    // Source chain ID
    uint256 indexed blockNumber, // Block number needed
    address requester,           // Who requested it
    bytes32 context             // Additional context (e.g., message ID)
);
```

### C. Error Codes

- `E001`: Unauthorized requester
- `E002`: Invalid block range
- `E003`: Chain ID mismatch
- `E004`: Duplicate request
- `E005`: ROFL authorization failed

### D. Related Documents

- [Hashi Protocol Documentation](../packages/hashi/README.md)
- [ROFL Oracle Setup Guide](../packages/rofl-oracle/README.md)
- [Oasis ROFL Documentation](https://docs.oasis.io/rofl/)