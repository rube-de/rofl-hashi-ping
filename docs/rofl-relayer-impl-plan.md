n# ROFL Relayer Implementation Plan

## Overview
Minimal implementation of an automated ROFL relayer that monitors Ping events on Ethereum Sepolia and relays them to Oasis Sapphire using cryptographic proofs.

### Event Flow
1. **PingSender** emits `Ping` event on source chain (Ethereum)
2. **Oracle** fetches block header via BlockHeaderRequester
3. **ROFLAdapter** emits `HashStored` event on target chain (Sapphire)
4. **Relayer** detects both events and generates proof
5. **Relayer** submits proof to PingReceiver on target chain

## Quick Start Development Path
Since environment and contracts are ready:
1. ✅ **Phase 1**: Configuration and project structure - COMPLETED
2. ✅ **Phase 2**: Event monitoring using polling - COMPLETED
3. **Phase 3**: Port proof generation from TypeScript - NEXT
4. **Phase 4**: Header coordination with ROFLAdapter
5. **Phase 5**: Submit proofs using ROFL utilities
6. **Phase 8.3**: End-to-end testing with deployed contracts

## Required Environment Variables (Simplified)
Core environment variables needed:
- `SOURCE_RPC_URL` - Ethereum RPC endpoint
- `PING_SENDER_ADDRESS` - PingSender contract to monitor for Ping events
- `PING_RECEIVER_ADDRESS` - PingReceiver contract for proof submission
- `ROFL_ADAPTER_ADDRESS` - ROFLAdapter contract to monitor for HashStored events
- `PRIVATE_KEY` - Only required in local mode

## Current State ✅
- ✅ Python environment already set up in `packages/rofl-relayer/`
- ✅ TypeScript tasks tested and working (send-ping, generate-proof, relay-message)
- ✅ Contracts deployed:
  - **Ethereum Sepolia**: PingSender (0xDCC23A03E6b6aA254cA5B0be942dD5CafC9A2299)
  - **Sapphire Testnet**: PingReceiver (0x1f54b7AF3A462aABed01D5910a3e5911e76D4B51)
  - **ROFLAdapter**: 0x9f983F759d511D0f404582b0bdc1994edb5db856
- ✅ Utility classes implemented and working:
  - PollingEventListener (Polling-based event monitoring) - **NEW**
  - EventListenerUtility (WebSocket monitoring - for future use)
  - ContractUtility (ABI loading and Sapphire interaction)
  - RoflUtility (ROFL transaction submission)
- ✅ Event monitoring successfully detecting real blockchain events

## Phase 1: Configuration Setup ✅ COMPLETED

### 1.0 Project Structure ✅ COMPLETED
- [x] Proper Python package structure following best practices
- [x] `main.py` - Minimal CLI entry point (30 lines)
- [x] `src/rofl_relayer/relayer.py` - Business logic (65 lines)
- [x] `src/rofl_relayer/config.py` - Configuration management (160 lines)
- [x] Docker Compose setup for both ROFL and local modes
- [x] Single README.md documentation

### 1.1 Prepare Contract Interfaces ✅ COMPLETED
- [x] Create `contracts/` directory in rofl-relayer package
- [x] Copy PingSender ABI and address to `contracts/PingSender.json`
- [x] Copy PingReceiver ABI and address to `contracts/PingReceiver.json`
- [x] Copy BlockHeaderRequester ABI and address to `contracts/BlockHeaderRequester.json`
- [x] Update ContractUtility.get_contract_abi() to load from simple `contracts/` structure
- [ ] In code: Use `contract_util.get_contract_abi('PingSender')` to load ABIs
- [ ] In code: Get contract addresses from environment variables

### 1.2 Configuration Structure ✅ COMPLETED
- [x] Created minimal dataclasses for configuration in `src/rofl_relayer/config.py`
- [x] SourceChainConfig: Only RPC URL and PingSender address (no chain ID - fetched at runtime)
- [x] TargetChainConfig: Only PingReceiver address and private key (with default network)
- [x] MonitoringConfig: Hard-coded sensible defaults (no env vars for MVP)
- [x] Main RelayerConfig class combines all configuration sections
- [x] Load from environment with only 3-4 required variables
- [x] Minimal validation - only address checksumming
- [x] Removed BlockHeaderRequester - not needed by relayer (oracle's responsibility)

## Phase 2: Event Monitoring ✅ COMPLETED

### 2.1 Polling-Based Event Listener ✅ COMPLETED
- [x] Created PollingEventListener utility class in `rofl_relayer.utils.polling_event_listener`
- [x] Initialize with Ethereum Sepolia RPC URL
- [x] Load PingSender ABI using `contract_util.get_contract_abi('PingSender')`
- [x] Create contract instance using Web3 with address from env vars
- [x] Implement async callback for Ping event processing
- [x] Add connection state tracking and logging
- [x] Successfully tested with real blockchain events (Block 9061255, TX 0x3794cbba...)

### 2.2 Polling Mechanism ✅ COMPLETED
- [x] Implement eth_getLogs based polling (primary approach, not fallback)
- [x] Track last processed block number
- [x] Add configurable polling interval (default 30 seconds)
- [x] Initial sync with 100 block lookback

### 2.3 Event Processing Pipeline ✅ COMPLETED
- [x] Create event queue for processing (pending_pings list)
- [x] Extract ping details (sender, block number) from event data
- [x] Generate ping ID using Web3.keccak
- [x] Track processed transaction hashes to prevent duplicates

## Phase 3: Merkle Proof Generation

### 3.1 Receipt Fetching
- [ ] Fetch transaction receipt using event transaction hash
- [ ] Get block data including all transaction receipts
- [ ] Validate receipt exists and matches event

### 3.2 RLP Encoding
- [ ] Port receipt RLP encoding logic from TypeScript
- [ ] Handle different transaction types (legacy, EIP-1559)
- [ ] Encode receipt status, gas used, logs bloom, and logs

### 3.3 Merkle Trie Construction
- [ ] Build receipt trie using py-trie or eth-hash
- [ ] Insert all block receipts with proper indexing
- [ ] Verify trie root matches block receipts root
- [ ] Generate Merkle proof for specific receipt

### 3.4 Proof Formatting
- [ ] Create proof structure matching Hashi format
- [ ] Include chain ID, block number, block header
- [ ] Add receipt proof array and log index
- [ ] Validate proof structure before submission

## Phase 4: Header Coordination

### 4.1 Monitor HashStored Events
- [ ] Listen to `HashStored(id, hash)` events from ROFLAdapter on target chain
- [ ] Match the block number from the Ping event with stored hashes
- [ ] Only proceed with proof submission after header is confirmed stored

### 4.2 Header Availability Check
- [ ] When a Ping event is detected, check if header for that block is already stored
- [ ] If not stored, wait for HashStored event from ROFLAdapter
- [ ] The oracle will fetch and store the header via BlockHeaderRequester
- [ ] Implement timeout and retry logic for waiting

## Phase 5: Proof Submission

### 5.1 Target Chain Integration
- [ ] Import ContractUtility from `rofl_relayer.utils.contract_utility`
- [ ] Initialize for Sapphire Testnet connection
- [ ] Load PingReceiver ABI using `contract_util.get_contract_abi('PingReceiver')`
- [ ] Create contract instance with address from env vars
- [ ] Format proof for receivePing function call

### 5.2 ROFL Transaction Submission
- [ ] Import RoflUtility from `rofl_relayer.utils.rofl_utility`
- [ ] Initialize with ROFL socket path
- [ ] Format transaction for PingReceiver.receivePing()
- [ ] Submit via RoflUtility.submit_tx()
- [ ] Parse transaction receipt for success/failure
- [ ] Extract and log emitted events

### 5.3 Error Handling
- [ ] Catch and handle proof verification failures
- [ ] Implement retry logic for transient failures
- [ ] Log detailed error messages for debugging
- [ ] Skip already processed pings gracefully

## Phase 6: State Management

### 6.1 In-Memory State
- [ ] Track processed transaction hashes (set)
- [ ] Store last processed block number
- [ ] Maintain ping ID to status mapping
- [ ] Implement state reset on restart

### 6.2 Persistence (Optional for MVP)
- [ ] Add simple JSON file persistence for processed pings
- [ ] Load state on startup
- [ ] Periodic state snapshots
- [ ] Clean up old entries after confirmation

## Phase 7: Main Loop Implementation (`main.py`)

### 7.1 Service Initialization
- [ ] Load configuration from environment variables
- [ ] Initialize ContractUtility for loading ABIs
- [ ] Load ABIs using `contract_util.get_contract_abi()`
- [ ] Initialize EventListenerUtility, RoflUtility
- [ ] Set up signal handlers for graceful shutdown
- [ ] Verify connectivity to both chains

### 7.2 Event Processing Loop
- [ ] Start WebSocket listener in async task
- [ ] Implement main event processing loop
- [ ] Handle events from queue sequentially
- [ ] Add health check and monitoring logs

### 7.3 Graceful Shutdown
- [ ] Handle SIGTERM/SIGINT signals
- [ ] Clean up WebSocket connections
- [ ] Save final state if using persistence
- [ ] Log shutdown reason and statistics

## Phase 8: Testing

### 8.1 Unit Tests
- [ ] Test proof generation with known data from TypeScript tasks
- [ ] Verify RLP encoding matches TypeScript implementation
- [ ] Test event parsing and ID generation
- [ ] Validate configuration loading

### 8.2 Integration Tests  
- [ ] Test with existing deployed contracts
- [ ] Test WebSocket connection to Ethereum Sepolia
- [ ] Verify fallback to polling works
- [ ] Test proof submission to Sapphire testnet
- [ ] Validate error handling paths

### 8.3 End-to-End Testing
- [ ] Send test ping using `bunx hardhat send-ping --network eth-sepolia`
- [ ] Run ROFL relayer and verify it detects the event
- [ ] Confirm automatic proof generation
- [ ] Verify ping received on Sapphire testnet
- [ ] Test multiple pings in sequence

## Phase 9: Deployment

### 9.1 ROFL Application Setup
- [ ] Register ROFL application if not exists
- [ ] Configure ROFL app permissions
- [ ] Set up key management
- [ ] Fund ROFL app for gas costs

### 9.2 Service Deployment
- [ ] Package application for ROFL deployment
- [ ] Deploy to ROFL runtime
- [ ] Verify service starts successfully
- [ ] Monitor initial event processing

### 9.3 Monitoring Setup
- [ ] Add structured logging with levels
- [ ] Implement metrics collection (events processed, success rate)
- [ ] Set up alerts for failures
- [ ] Create dashboard for monitoring

## Phase 10: Documentation

### 10.1 Code Documentation
- [ ] Add docstrings to all classes and methods
- [ ] Include type hints throughout
- [ ] Document configuration options
- [ ] Add inline comments for complex logic

### 10.2 Deployment Guide
- [ ] Write deployment instructions
- [ ] Document environment variables
- [ ] Create troubleshooting guide
- [ ] Add example configuration

### 10.3 Testing Guide
- [ ] Document test setup
- [ ] Provide test data examples
- [ ] Include verification steps
- [ ] Add common issues and solutions

## Success Criteria

- [ ] Relayer detects Ping events within 5 seconds
- [ ] Proofs are generated correctly and match TypeScript implementation
- [ ] Messages are successfully relayed to Sapphire
- [ ] Service handles disconnections gracefully
- [ ] Processing continues after restarts
- [ ] Error rate is below 5% in normal operation

## Implementation Notes

### Code Organization
- Minimal `main.py` entry point (30 lines)
- Business logic in `src/rofl_relayer/relayer.py` (65 lines)
- Configuration in `src/rofl_relayer/config.py` (160 lines)
- Import utilities from `rofl_relayer.utils.*`
- Follow KISS principle - maximum simplification achieved
- Proper Python package structure

### Performance Targets
- Event detection latency: < 5 seconds
- Proof generation time: < 2 seconds  
- End-to-end relay time: < 30 seconds
- Memory usage: < 100MB

### Security Considerations
- No private keys in code or logs
- Validate all inputs before processing
- Use checksummed addresses
- Handle RPC errors gracefully
- Implement rate limiting if needed

## Next Steps After Implementation

1. Performance optimization (batching, parallel processing)
2. Multi-chain support
3. Advanced monitoring and alerting
4. Database persistence for production
5. Web dashboard for status monitoring