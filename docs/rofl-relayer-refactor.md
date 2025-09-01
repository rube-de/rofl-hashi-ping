# ROFL Relayer Refactoring Plan

## Executive Summary

The ROFL Relayer cannot detect events from ROFL transactions on Oasis Sapphire through standard RPC queries. This document outlines a minimal refactoring plan to replace event-based detection with direct state polling.

## Problem Analysis

### Current State
- **Issue**: HashStored events from ROFLAdapter are not accessible via RPC
- **Root Cause**: ROFL transactions execute in a confidential context on Sapphire
- **Impact**: Relayer cannot detect when block hashes are stored, breaking the bridge flow

### Verification Results
| Component | Event Visibility | Direct State Access |
|-----------|-----------------|---------------------|
| ROFLAdapter (ROFL tx) | ❌ Not via RPC | ✅ Works |
| MockAdapter (Regular tx) | ✅ Works | ✅ Works |
| Block Explorer | ✅ Shows events | N/A |

## Solution Design: Unified Polling-Based Detection

### Core Concept
Replace ALL event listening with periodic state polling for both ROFLAdapter (production) and MockAdapter (local testing). This ensures consistent behavior across environments and simplifies the codebase. When a ping is detected, continuously check if the corresponding hash has been stored until it appears or times out.

### Architecture Comparison

#### Current Architecture (Event-Driven)
```
Source Chain          Sapphire              Relayer
     │                    │                    │
     ├─[Ping Event]──────>│                    │
     │                    ├─[Store Hash]       │
     │                    ├─[HashStored Event]─X─> (Never arrives)
     │                    │                    │
                         Breaks Here
```

#### New Architecture (Polling-Based)
```
Source Chain          Sapphire              Relayer
     │                    │                    │
     ├─[Ping Event]──────────────────────────>│
     │                    │                    ├─[Start Polling]
     │                    ├─[Store Hash]       │
     │                    │<───[getHash?]──────┤
     │                    │<───[getHash?]──────┤
     │                    ├───[Returns Hash]──>│
     │                    │                    ├─[Process Proof]
```

## MVP Implementation Strategy

### Design Principles
1. **Simplicity First**: One ping triggers one polling loop
2. **No Premature Optimization**: Fixed intervals, no fancy algorithms
3. **Clear Failure Modes**: Explicit timeouts and error handling
4. **Environment Parity**: Same detection mechanism for local and production
5. **Minimal Changes**: Modify only what's necessary

### Component Changes

#### 1. New Hash Polling Module
- **Purpose**: Check if a hash exists for a specific block
- **Interface**: Simple async function that polls until found or timeout
- **Configuration**: Poll interval and timeout duration

#### 2. Modified Event Processor
- **Change**: When ping detected, start polling instead of waiting for event
- **Maintains**: Existing proof generation logic unchanged
- **Queue Management**: Track pending pings awaiting hash detection

#### 3. Configuration Updates
- **New Parameters**:
  - Polling interval (default: 12 seconds)
  - Timeout duration (default: 5 minutes)
  - Max concurrent polls (default: 50)

#### 4. Unified Event Monitoring
- **Remove**: ALL HashStored event listeners (both ROFLAdapter and MockAdapter)
- **Keep**: Only Ping event listener (source chain)
- **Benefit**: Single code path for all environments

### Data Flow

1. **Ping Detection**
   - Relayer detects Ping event from source chain
   - Extracts block number that needs hash

2. **Polling Initiation**
   - Creates polling task for detected block number
   - Adds to pending pings tracking structure

3. **Hash Detection Loop**
   - Every N seconds, call getHash(chainId, blockNumber)
   - Check if returned value is non-zero
   - Continue until found or timeout

4. **Proof Processing**
   - Once hash detected, proceed with existing proof generation
   - Submit proof to target chain
   - Clean up pending ping from queue

### Error Handling

| Scenario | Response | Recovery |
|----------|----------|----------|
| Hash not found within timeout | Log warning, mark as failed | Manual intervention or retry |
| RPC connection failure | Exponential backoff | Automatic reconnection |
| Rate limiting | Slow down polling | Adjust interval dynamically |
| Contract call revert | Log error | Skip and continue |

## Performance Considerations

### MVP Performance Profile

#### Resource Usage
- **RPC Calls**: ~5 per minute per pending ping
- **Memory**: O(n) where n = pending pings
- **CPU**: Minimal (mostly waiting)
- **Network**: ~1KB per poll request/response

#### Timing Characteristics
- **Detection Latency**: Average 6 seconds (half of poll interval)
- **Worst Case**: Full timeout period (5 minutes)
- **Best Case**: First poll after storage

#### Scalability Limits
- **Concurrent Pings**: Up to 50 (configurable)
- **RPC Rate**: ~250 calls/minute maximum
- **Timeout Queue**: Automatic cleanup after 5 minutes

## Testing Strategy

### Test Scenarios

1. **Happy Path**
   - Send ping → Oracle stores hash → Relayer detects → Proof generated

2. **Timeout Scenario**
   - Send ping → No hash stored → Timeout after 5 minutes → Logged as failed

3. **Multiple Concurrent Pings**
   - Send 10 pings → Poll all simultaneously → Verify independent detection

4. **Recovery Testing**
   - Disconnect RPC → Verify reconnection → Resume polling

### Validation Criteria
- Hash detection works for both ROFL and Mock transactions
- Identical behavior in local and production environments
- Memory usage stable over 24 hours
- RPC usage within acceptable limits

## Deployment Plan

### Phases

**Phase 1: Development**
- Implement polling mechanism
- Update event processor
- Add configuration parameters

**Phase 2: Testing**
- Unit test polling logic
- Integration test on testnet
- Load test with multiple pings

**Phase 3: Staged Rollout**
- Deploy to testnet environment
- Monitor for 48 hours
- Deploy to production with feature flag

**Phase 4: Monitoring**
- Track detection success rate
- Monitor RPC usage
- Collect performance metrics

## Future Enhancements

### 1. Batch Polling
- **Concept**: Check multiple block hashes in single RPC call
- **Benefit**: Reduce RPC calls by factor of N
- **Technology**: Multicall smart contract pattern

### 2. Intelligent Polling Strategy
- **Adaptive Intervals**: Poll new blocks frequently, old blocks rarely
- **Predictive Timing**: Learn typical oracle response times
- **Priority Queue**: Service recent pings first
- **Exponential Backoff**: Reduce frequency over time

### 3. Metrics and Observability
- **Metrics to Track**:
  - Polls per minute
  - Average detection latency
  - Success/timeout ratio
  - RPC error rates
- **Dashboards**: Grafana for visualization
- **Alerts**: PagerDuty for timeout spikes

### 4. Optimization Techniques
- **Caching**: Remember checked blocks to avoid re-polling
- **Connection Pooling**: Reuse RPC connections
- **Fallback RPCs**: Multiple endpoints for reliability
- **State Compression**: Efficient pending ping storage

### 5. Advanced Adapter Support
- **Multi-Adapter Support**: Handle different adapter contracts
- **Dynamic Configuration**: Per-adapter polling strategies
- **Adapter Registry**: Automatic discovery of new adapters

## Risk Assessment

### Technical Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|---------|------------|
| RPC rate limiting | Medium | High | Use dedicated RPC endpoint |
| Memory leak from pending queue | Low | Medium | Implement queue size limits |
| Extended oracle downtime | Low | High | Add alerting and manual tools |
| Network congestion | Medium | Medium | Implement retry logic |

### Operational Risks
- **Cost Increase**: More RPC calls increase infrastructure costs
- **Monitoring Overhead**: Need to track new metrics
- **Debugging Complexity**: Polling loops harder to debug than events

## Success Metrics

### MVP Success Criteria
- ✓ Relayer detects ROFL transaction hashes
- ✓ End-to-end message relay functional
- ✓ Average detection under 30 seconds
- ✓ Stable operation for 24 hours

### Long-term Goals
- 99% hash detection success rate
- Average latency under 15 seconds
- RPC costs under $100/month
- Zero manual interventions per week

## Benefits of Unified Approach

### Advantages
1. **Consistency**: Same behavior in all environments
2. **Simplicity**: Single code path to maintain and debug
3. **Testing**: Local tests accurately reflect production behavior
4. **Reliability**: No environment-specific bugs
5. **Maintainability**: Reduced code complexity

### Trade-offs
- **Performance**: Polling less efficient than events for MockAdapter
- **RPC Usage**: Increased calls in local testing
- **Latency**: Uniform detection delay across environments

However, these trade-offs are acceptable given the critical importance of environment parity and code simplicity.

## Conclusion

This refactoring addresses a fundamental limitation of ROFL on Sapphire while establishing a unified approach for all environments. By using polling universally, we ensure that local testing accurately reflects production behavior. While polling is less efficient than event-driven architecture, it's the only reliable method that works consistently across all adapter types. The MVP focuses on simplicity, correctness, and environment parity, with optimizations deferred to future iterations based on production experience.