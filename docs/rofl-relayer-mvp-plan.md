# ROFL Cross-Chain Ping Demonstration MVP

## Overview

This document outlines the MVP (Minimum Viable Product) implementation plan for a simple cross-chain ping demonstration built on Oasis ROFL (Runtime OFf-chain Logic) technology. The system demonstrates the core concept of cross-chain event verification: proving that an event occurred on one chain and verifying that proof on another chain.

## MVP Goals

1. **Simple Event Verification**: Prove a ping event occurred on Ethereum Sepolia and verify it on Oasis Sapphire
2. **Educational Focus**: Demonstrate core cross-chain proof concepts without complexity
3. **Cryptographic Verification**: Use Merkle proofs to verify event occurrence
4. **ROFL Integration**: Leverage ROFL for off-chain proof generation
5. **Minimal Implementation**: Focus on the essential proof-of-concept
6. **Foundation for Learning**: Simple base for understanding cross-chain verification

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Ethereum Sepolia                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐         ┌──────────────────────┐                     │
│  │   PingSender    │────────▶│ BlockHeaderRequester │                     │
│  │   (simple)      │ trigger │   (existing)         │                     │
│  └─────────┬───────┘         └──────────────────────┘                     │
│            │                                                               │
│            │ Ping Event                                                    │
│            │ (just sender + timestamp)                                     │
│            ▼                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
             │
             │ Monitor
             │
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ROFL Environment (Oasis Network)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    ROFL Ping Relayer                                    ││
│  │  - Monitors simple Ping events                                          ││
│  │  - Triggers header requests automatically                               ││
│  │  - Generates Merkle proofs from transaction receipts                    ││
│  │  - Submits event proofs to Sapphire                                    ││
│  └─────────────────────────────┬───────────────────────────────────────────┘│
│                                │                                             │
│  ┌─────────────────────────────▼───────────────────────────────────────────┐│
│  │                  ROFL Header Oracle (existing)                          ││
│  │  - Provides block headers for verification                              ││
│  │  - Stores headers in ROFLAdapter                                        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────┬───────────────────────────┘
                                                  │
                                                  │ Submit Proofs
                                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Oasis Sapphire                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────┐                     │
│  │            PingReceiver Contract                  │                     │
│  │  - Verifies Merkle proofs against stored headers │                     │
│  │  - Confirms ping events occurred on source       │                     │
│  │  - Emits PingReceived confirmation events        │                     │
│  └─────────────────┬────────────────────────────────┘                     │
│                    │                                                      │
│  ┌─────────────────▼────────────────────────────────┐                     │
│  │         ROFLAdapter (existing)                    │                     │
│  │  - Stores block headers from oracle              │                     │
│  │  - Provides header access for verification       │                     │
│  └─────────────────┬────────────────────────────────┘                     │
│                    │                                                      │
│  ┌─────────────────▼────────────────────────────────┐                     │
│  │      Hashi Verification Infrastructure           │                     │
│  │  - HashiProver for Merkle proof verification    │                     │
│  │  - Event validation and processing              │                     │
│  └───────────────────────────────────────────────────┘                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Implementation Components

### 1. Source Chain Components (Ethereum Sepolia)

#### 1.1 PingSender Contract (NEW)
**Location**: `packages/ping/contracts/PingSender.sol`

**Purpose**: Emit simple ping events that can be proven on other chains

**Key Features (MVP)**:
- Emit simple `Ping` events with minimal data
- Automatically request block headers via `BlockHeaderRequester`
- Generate unique ping IDs for replay protection
- No complex message data - just proof of occurrence

**Contract Interface**:
```solidity
contract PingSender {
    event Ping(
        address indexed sender,
        uint256 indexed timestamp,
        uint256 blockNumber
    );

    event HeaderRequested(
        uint256 indexed sourceChainId,
        uint256 indexed blockNumber,
        bytes32 indexed context
    );

    function ping() external;
}
```

#### 1.2 BlockHeaderRequester Contract (EXISTING)
**Location**: `packages/ping/contracts/BlockHeaderRequester.sol`

**Status**: ✅ Already implemented
**Integration**: PingSender will interact with this contract to request headers

### 2. ROFL Components (Oasis Network)

#### 2.1 ROFL Ping Relayer Service (NEW)
**Location**: `packages/rofl-relayer/src/rofl-relayer/ping_relayer.py`

**Purpose**: Monitor ping events and generate proofs for verification on target chain

**Key Features (MVP)**:
- **Real-time WebSocket event monitoring** using existing EventListenerUtility
- Automatic WebSocket reconnection and fallback to polling
- Simple header request coordination with existing oracle
- Basic Merkle proof generation from transaction receipts
- Proof submission to target chain for verification
- Simple error handling and retry logic
- Basic state tracking for processed pings

**Core Methods**:
```python
class PingRelayer:
    def monitor_ping_events()           # Main event monitoring loop
    def process_ping_event()            # Handle individual ping events
    def ensure_header_availability()    # Coordinate header requests
    def generate_merkle_proof()         # Create cryptographic proof
    def submit_proof_to_target()        # Send proof to Sapphire
    def verify_ping_confirmation()      # Confirm ping was verified
```

#### 2.2 ROFL Header Oracle (EXISTING)
**Location**: `packages/rofl-oracle/src/rofl_oracle/header_oracle.py`

**Status**: ✅ Already implemented
**Integration**: Message relayer will coordinate with oracle for header availability

### 3. Target Chain Components (Oasis Sapphire)

#### 3.1 PingReceiver Contract (NEW)
**Location**: `packages/ping/contracts/PingReceiver.sol`

**Purpose**: Verify that ping events occurred on source chain

**Key Features (MVP)**:
- **🔒 CRITICAL**: Complete Merkle proof verification using Hashi infrastructure
- **🔒 CRITICAL**: Full cryptographic validation of proofs before acceptance
- Simple ping confirmation after successful verification
- Event emission for confirmation
- Simple replay protection with ping IDs
- Minimal access controls (proof verification provides security)

**Contract Interface**:
```solidity
contract PingReceiver {
    event PingReceived(
        uint256 indexed sourceChainId,
        bytes32 indexed pingId,
        address indexed originalSender,
        uint256 originalTimestamp,
        uint256 originalBlockNumber,
        uint256 verifiedAt
    );

    event PingVerified(
        bytes32 indexed pingId,
        bool success,
        string reason
    );

    mapping(bytes32 => bool) public pingsReceived;

    function receivePing(
        ReceiptProof calldata proof
    ) external;
}
```

#### 3.2 ROFLAdapter Contract (EXISTING)
**Location**: `packages/hashi/packages/evm/contracts/adapters/oasis/ROFLAdapter.sol`

**Status**: ✅ Already implemented
**Integration**: PingReceiver will read block headers from this contract

#### 3.3 Hashi Verification Infrastructure (EXISTING)
**Location**: `packages/hashi/packages/evm/contracts/prover/`

**Status**: ✅ Already implemented
**Integration**: PingReceiver will use HashiProver for Merkle proof verification

## Implementation Phases

### Phase 1: Core Message Infrastructure (MVP)

#### Week 1: Contract Development
1. **PingSender Contract Implementation**
   - Basic ping message structure
   - Event emission for message tracking
   - Integration with BlockHeaderRequester
   - Unit tests and deployment scripts

2. **PingReceiver Contract Implementation**
   - Message verification using Hashi infrastructure
   - Basic message processing
   - Event emission for confirmations
   - Simple validation (no advanced access controls for MVP)

#### Week 2: ROFL Relayer Service
1. **Event Monitoring Setup**
   - Initialize EventListenerUtility with WebSocket support
   - Real-time PingMessage event monitoring (<1 second latency)
   - Automatic WebSocket reconnection and error handling

2. **Message Processing Pipeline**
   - Real-time WebSocket event processing using EventListenerUtility
   - Header availability coordination with existing oracle
   - Merkle proof generation from receipts
   - Message submission to Sapphire with full verification
   - Error handling and retry logic

### Phase 2: Integration and Testing

#### Week 3: End-to-End Integration
1. **Component Integration**
   - Connect PingSender → ROFL Relayer → PingReceiver
   - Verify header oracle coordination
   - Test message flow with real transactions

2. **Verification Testing**
   - Merkle proof generation and verification
   - Block header dependency resolution
   - Edge case handling (failed txs, reorgs)

#### Week 4: MVP Completion
1. **Basic Security Implementation**
   - Simple ping replay protection
   - Basic input validation

2. **Testing and Documentation**
   - End-to-end testing
   - Basic monitoring setup
   - Documentation for test deployment

### Phase 3: Advanced Features (Future)

#### Message Types and Routing
- Support for different message types
- Dynamic routing to multiple target contracts
- Message acknowledgment system

#### Cross-Chain State Synchronization
- State proofs for complex data structures
- Multi-step transaction coordination
- Atomic cross-chain operations

## Technical Implementation Details

### Ping ID Generation
```solidity
function generatePingId(
    uint256 sourceChainId,
    uint256 blockNumber,
    address sender,
    uint256 timestamp
) pure returns (bytes32) {
    return keccak256(abi.encode(sourceChainId, blockNumber, sender, timestamp));
}
```

### Merkle Proof Structure
```json
{
    "pingEventHash": "0x...",
    "merkleProof": ["0x...", "0x..."],
    "blockNumber": 12345,
    "sourceChainId": 11155111,
    "receiptRlp": "0x...",
    "logIndex": 1,
    "transactionHash": "0x..."
}
```

### Event Monitoring Architecture
```python
# Use existing EventListenerUtility for WebSocket-based event listening
from rofl_oracle.utils.event_listener_utility import EventListenerUtility

class PingRelayer:
    def __init__(self, source_rpc_url: str):
        # Initialize event listener with automatic WebSocket URL conversion
        self.event_listener = EventListenerUtility(rpc_url=source_rpc_url)
        
    async def start_event_monitoring(self):
        """Start real-time WebSocket event monitoring."""
        event_obj = self.source_contract.events.Ping()
        
        # WebSocket listener with automatic reconnection
        await self.event_listener.listen_for_contract_events(
            contract_address=self.ping_sender_address,
            event_obj=event_obj,
            callback=self.process_ping_event
        )
```

## MVP Security Considerations (Test Environment)

### 1. **CRITICAL: Full Merkle Proof Security (Non-Negotiable)**
- **Complete Merkle Proof Verification**: Full cryptographic verification using Hashi infrastructure
- **Proof Generation Integrity**: Ensure accurate proof generation from transaction receipts
- **Block Header Validation**: Verify block headers against trusted sources
- **Receipt RLP Validation**: Proper RLP decoding and validation
- **Log Index Verification**: Correct event log identification and extraction

⚠️ **Note**: Merkle proof verification MUST be production-grade secure even in MVP - this is the core trust mechanism

### 2. **MVP-Level Security (Simplified for Testing)**
- **Ping Replay Protection**: Simple tracking of processed ping events
- **ROFL Authorization**: Verify ROFL app authorization for critical operations
- **Input Sanitization**: Basic validation of proof data
- **Chain ID Verification**: Ensure pings are from expected source chain

### 3. **Test Environment Relaxations (Future Production Requirements)**
- **Access Control**: Permissive access for testing (production: fine-grained permissions)
- **Rate Limiting**: No rate limiting for MVP (production: DDoS protection)
- **Economic Security**: No fee/MEV protection (production: economic attack resistance)
- **Key Management**: Simple key handling (production: secure key rotation)

## Gas Cost Analysis (MVP Estimates)

### Source Chain (Ethereum Sepolia)
- **PingSender.ping()**: ~30,000 gas (simple implementation)
- **BlockHeaderRequester.requestBlockHeader()**: ~25,000 gas (existing)
- **Total per ping**: ~55,000 gas

### Target Chain (Oasis Sapphire)
- **PingReceiver.receivePing()**: ~100,000 gas (full verification required)
- **Complete Merkle proof verification**: ~80,000 gas (no shortcuts allowed)
- **Total per ping**: ~180,000 gas

### MVP Considerations
- **🔒 Security**: Full Merkle proof verification cost (non-negotiable)
- **Simplicity**: No gas optimization beyond security requirements
- **Single ping processing**: No batching optimization
- **Basic error handling**: Minimal retry logic for non-security operations

## Testing Strategy

### Unit Testing
- **Smart Contracts**: Hardhat test suite for all contracts
- **ROFL Service**: Python pytest for service components
- **Mock Infrastructure**: Mock contracts and RPC responses

### Integration Testing
- **🔒 CRITICAL**: Comprehensive Merkle proof verification testing
  - Valid proofs from real transaction receipts
  - Invalid proof rejection (tampered proofs, wrong block headers)
  - Edge cases (empty receipts, malformed RLP, incorrect log indices)
- **Cross-Chain Flow**: End-to-end message passing tests
- **Security Scenarios**: Attempt malicious proof submissions
- **Error Handling**: Network issues, RPC failures (non-security errors only)

### Testnet Deployment
1. **Ethereum Sepolia**: Deploy PingSender and BlockHeaderRequester
2. **Oasis Sapphire Testnet**: Deploy PingReceiver and verify Hashi integration
3. **ROFL Testnet**: Deploy relayer service with comprehensive monitoring

## Configuration and Environment

### Environment Variables (MVP)
```bash
# Source chain configuration
SOURCE_RPC_URL=https://ethereum-sepolia.publicnode.com
SOURCE_CHAIN_ID=11155111
PING_SENDER_ADDRESS=0x...

# Target chain configuration  
TARGET_NETWORK=sapphire-testnet
TARGET_CHAIN_ID=23295
PING_RECEIVER_ADDRESS=0x...

# ROFL configuration
ROFL_APP_ID=0x...
PRIVATE_KEY=0x...  # Simple key management for testing

# MVP service configuration
EVENT_POLLING_FALLBACK_INTERVAL=30  # Fallback polling if WebSocket fails
MAX_RETRY_ATTEMPTS=2      # Simple retry logic
WEBSOCKET_HEARTBEAT_INTERVAL=30  # WebSocket health check interval
ENABLE_DEBUG_LOGGING=true  # Verbose logging for debugging
```

### Service Configuration
```yaml
# rofl-relayer-config.yaml
message_relayer:
  source_chain:
    rpc_url: "https://ethereum-sepolia.publicnode.com"
    chain_id: 11155111
    contracts:
      ping_sender: "0x..."
      block_header_requester: "0x..."
  
  target_chain:
    network: "sapphire-testnet"
    chain_id: 23295
    contracts:
      ping_receiver: "0x..."
      rofl_adapter: "0x..."
  
  monitoring:
    polling_interval: 12
    confirmations_required: 3
    event_lookback_blocks: 1000
  
  processing:
    batch_size: 10
    max_retries: 3
    retry_delay: 30
```

## Monitoring and Observability

### Key Metrics
- **Messages Per Hour**: Track relayer throughput
- **Success Rate**: Message delivery success percentage
- **Latency**: Time from source event to target execution
- **Gas Costs**: Monitor cross-chain operation costs
- **Error Rates**: Track failed messages and root causes

### Alerting Rules
- **Service Health**: Alert on relayer service downtime
- **High Error Rate**: Alert on >5% failure rate
- **Stuck Messages**: Alert on messages pending >1 hour
- **Gas Price Spikes**: Alert on unexpectedly high costs

### Logging Structure
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "component": "message_relayer",
  "event": "ping_message_processed",
  "data": {
    "messageId": "0x...",
    "sourceChain": 11155111,
    "targetChain": 23295,
    "blockNumber": 12345,
    "gasUsed": 85000,
    "processingTimeMs": 5000
  }
}
```

## MVP Success Criteria

### Core Functionality
1. ✅ Send ping event from Ethereum Sepolia
2. ✅ ROFL relayer detects and processes ping event  
3. ✅ Block header automatically requested and stored
4. ✅ Merkle proof generated and verified
5. ✅ Ping confirmed and verified on Sapphire

### Basic Performance Requirements
- **Basic Throughput**: Process 10+ pings per hour
- **Reasonable Latency**: <10 minutes from source event to target verification
- **Functional Reliability**: >80% ping verification success rate for testing

### Security Requirements
- **🔒 CRITICAL**: Full Merkle proof verification with complete cryptographic integrity
- **🔒 CRITICAL**: Accurate proof generation from transaction receipts and block headers
- **🔒 CRITICAL**: Proper RLP decoding and event log verification
- **✅ Basic**: Simple duplicate ping prevention
- **✅ Basic**: ROFL app authorization verification
- **✅ Basic**: Input validation and chain ID checks

## Future Enhancements (v2+)

### Advanced Security Features
- **Access Control**: Fine-grained permissions and role-based access
- **Rate Limiting**: Protection against spam and DoS attacks
- **Economic Security**: Fee structures and MEV protection
- **Advanced Monitoring**: Comprehensive security monitoring and alerting
- **Key Management**: Secure private key storage and rotation
- **Audit Trails**: Detailed logging and forensic capabilities

### Advanced Message Types
- **Token Transfers**: Cross-chain asset movement
- **State Synchronization**: Complex data structure updates
- **Multi-Step Transactions**: Atomic cross-chain operations
- **Conditional Messages**: Execute based on chain state

### Production Features
- **Message Batching**: Process multiple messages in single transaction
- **Parallel Processing**: Concurrent message handling
- **Dynamic Fee Optimization**: Adjust fees based on network conditions
- **Multi-Chain Support**: Expand to additional source/target chains
- **Enterprise Security**: Advanced threat protection and compliance

### Developer Experience
- **SDK Development**: JavaScript/TypeScript SDK for easy integration
- **Message Templates**: Pre-built message types for common use cases
- **Dashboard**: Web interface for monitoring and debugging
- **Documentation**: Comprehensive guides and examples

## Dependencies and Requirements

### Smart Contract Dependencies
```json
{
  "@openzeppelin/contracts": "^5.0.0",
  "@oasisprotocol/sapphire-contracts": "^0.2.9",
  "hardhat": "^2.19.0"
}
```

### Python Service Dependencies
```toml
[dependencies]
web3 = "^6.12.0"
sapphirepy = "^0.2.1"
eth-account = "^0.9.0"
cbor2 = "^5.4.0"
aiohttp = "^3.8.0"
pydantic = "^2.4.0"
```

### Infrastructure Requirements
- **Ethereum Sepolia**: RPC access for event monitoring
- **Oasis Sapphire Testnet**: Deployment and execution environment
- **ROFL Application**: Registered and funded ROFL app
- **Monitoring Stack**: Prometheus, Grafana for observability

## Development Timeline

### Sprint 1 (Week 1-2): Foundation
- **Day 1-3**: PingSender contract development and testing
- **Day 4-6**: PingReceiver contract development and testing  
- **Day 7-10**: Basic ROFL relayer service implementation
- **Day 11-14**: Integration testing and bug fixes

### Sprint 2 (Week 3-4): Integration
- **Day 15-17**: End-to-end flow testing
- **Day 18-20**: Performance optimization
- **Day 21-24**: Security hardening
- **Day 25-28**: Documentation and deployment

### Sprint 3 (Week 5-6): Production Ready
- **Day 29-31**: Comprehensive testing suite
- **Day 32-34**: Monitoring and alerting setup
- **Day 35-38**: Load testing and optimization
- **Day 39-42**: Final security review and deployment

## Risk Mitigation

### MVP Technical Risks (Test Environment)
- **RPC Failures**: Basic retry logic for RPC connectivity
- **Block Reorganizations**: Simple handling of chain reorgs
- **Service Failures**: Basic error handling and logging
- **Message Failures**: Simple retry mechanisms

### MVP Risk Mitigation
- **Basic Monitoring**: Simple logging and error tracking
- **Test Environment Controls**: Controlled test environment reduces risks
- **Manual Intervention**: Accept manual recovery for MVP testing
- **Simple Backup**: Basic RPC endpoint fallback

### Production Risks (Future Consideration)
- **Economic Attacks**: Advanced economic security measures
- **Key Management**: Secure private key storage and rotation
- **Service Downtime**: Redundancy and automated failover
- **Upgrade Coordination**: Seamless contract and service upgrades
- **Regulatory Compliance**: Legal and compliance considerations

## Conclusion

This MVP implementation plan provides a comprehensive roadmap for building a production-ready cross-chain message relayer using Oasis ROFL technology. The system leverages the existing Hashi verification infrastructure while adding powerful cross-chain messaging capabilities through confidential compute.

The phased approach ensures rapid delivery of core functionality while maintaining security and reliability standards. The modular architecture allows for future enhancements and scaling to support additional use cases and chains.

Key success factors include:
- **Robust event monitoring** with proper error handling
- **Cryptographic verification** using battle-tested Hashi infrastructure  
- **Comprehensive testing** across all integration points
- **Production-grade monitoring** for operational excellence
- **Clear upgrade paths** for future enhancements

The implementation provides a solid foundation for secure, efficient cross-chain communication that can be extended to support advanced use cases like cross-chain DeFi, governance, and state synchronization.