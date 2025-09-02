# ROFL Oracle Refactoring Plan

## Executive Summary

This document outlines a comprehensive refactoring plan to port improvements from the ROFL Relayer to the ROFL Oracle. The relayer demonstrates superior architecture, reliability, and maintainability that should be adopted by the oracle for production readiness.

## Current State Analysis

### Oracle Issues
- **Monolithic Design**: Single 395-line `HeaderOracle` class violating SOLID principles
- **Complex Event System**: WebSocket with polling fallback adds unnecessary complexity
- **Poor Observability**: Print statements instead of structured logging
- **Scattered Configuration**: Environment variables handled ad-hoc
- **Limited Testing**: Single test file with minimal coverage
- **Legacy Patterns**: Missing modern Python 3.12+ features

### Relayer Strengths
- **Modular Architecture**: Separated concerns across multiple focused modules
- **Simple Polling**: Reliable HTTP-based event polling without WebSocket complexity  
- **Structured Config**: Type-safe dataclass configuration with validation
- **Professional Logging**: Proper logging with levels and formatters
- **Modern Python**: Leverages Python 3.12+ features for performance
- **Comprehensive Testing**: Multiple focused test files

## Refactoring Priorities

### Phase 1: Foundation (High Impact, Required First)

#### 1.1 Configuration System
**Current**: Scattered environment variable handling in `_load_config()`  
**Target**: Structured dataclass-based configuration

```python
# New: src/rofl_oracle/config.py
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SourceChainConfig:
    """Configuration for the source chain."""
    rpc_url: str
    contract_address: str
    chain_id: Optional[int] = None  # Auto-detect if not provided

@dataclass
class TargetChainConfig:
    """Configuration for Oasis Sapphire."""
    network: str  # sapphire-testnet, sapphire, etc.
    contract_address: str
    
@dataclass
class OracleConfig:
    """Main configuration for HeaderOracle."""
    source_chain: SourceChainConfig
    target_chain: TargetChainConfig
    polling_interval: int = 12
    lookback_blocks: int = 100
    local_mode: bool = False
    
    @classmethod
    def from_env(cls) -> "OracleConfig":
        """Load from environment with validation."""
        # Implementation with clear error messages
```

**Benefits**:
- Type safety and IDE autocomplete
- Centralized validation with helpful error messages
- Easy testing with config objects
- Clear documentation of required settings

#### 1.2 Replace Print Statements with Logging
**Current**: 40+ print statements throughout the code  
**Target**: Structured logging with appropriate levels

```python
import logging

logger = logging.getLogger(__name__)

# Replace:
print(f"HeaderOracle: Starting initialization...")
# With:
logger.info("Starting HeaderOracle initialization")

# Replace:
print(f"Error fetching block {block_number}: {e}")
# With:
logger.error("Error fetching block %s", block_number, exc_info=True)
```

**Benefits**:
- Production-ready log aggregation
- Configurable log levels
- Structured output with timestamps
- Better debugging with stack traces

### Phase 2: Architecture (Breaking Monolith)

#### 2.1 Extract Event Processing
**Current**: Event processing mixed into `HeaderOracle` class  
**Target**: Separate `EventProcessor` class

```python
# New: src/rofl_oracle/event_processor.py
class EventProcessor:
    """Processes BlockHeaderRequested events."""
    
    def __init__(self, source_w3: Web3, source_chain_id: int):
        self.source_w3 = source_w3
        self.source_chain_id = source_chain_id
        self.processed_events: set[str] = set()
    
    async def process_block_header_event(self, event: EventData) -> BlockHeader | None:
        """Process event and return block header if needed."""
        # Moved from HeaderOracle.process_block_header_event
```

#### 2.2 Extract Block Submission Logic
**Current**: Submission logic embedded in `HeaderOracle`  
**Target**: Separate `BlockSubmitter` class

```python
# New: src/rofl_oracle/block_submitter.py
class BlockSubmitter:
    """Handles block header submission to Sapphire."""
    
    def __init__(self, contract_util: ContractUtility, rofl_util: RoflUtility | None):
        self.contract_util = contract_util
        self.rofl_util = rofl_util
    
    async def submit_block_header(self, chain_id: int, block_number: int, block_hash: str) -> bool:
        """Submit block header to ROFLAdapter."""
        # Moved from HeaderOracle.submit_block_header
```

#### 2.3 Create Models Module
**Current**: No data models, passing raw dicts  
**Target**: Type-safe data models

```python
# New: src/rofl_oracle/models.py
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class BlockHeaderEvent:
    """BlockHeaderRequested event data."""
    chain_id: int
    block_number: int
    requester: str
    context: str
    event_block: int

@dataclass(frozen=True, slots=True)
class BlockHeader:
    """Block header data."""
    number: int
    hash: str
    timestamp: int
```

### Phase 3: Event System Simplification

#### 3.1 Replace Complex Event Listener
**Current**: `EventListenerUtility` with WebSocket + polling fallback  
**Target**: Simple `PollingEventListener` from relayer

```python
# Copy from relayer with oracle-specific modifications
class PollingEventListener:
    """Simple, reliable HTTP-based event polling."""
    
    async def start_polling(self, callback, interval: int = 12):
        """Poll for events at regular intervals."""
        # No WebSocket complexity
        # Clear error handling
        # Built-in retry logic
```

**Benefits**:
- Removes WebSocket complexity and failure modes
- Works reliably with any RPC endpoint
- Simpler to debug and maintain
- Already proven in relayer

### Phase 4: Utility Improvements

#### 4.1 Update ContractUtility
**Current**: Network name-based initialization  
**Target**: Direct RPC URL initialization

```python
class ContractUtility:
    def __init__(self, rpc_url: str, secret: str = ""):
        """Initialize with RPC URL directly."""
        self.rpc_url = rpc_url
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if secret:
            self._add_signing_middleware(secret)
    
    def get_contract_abi(self, contract_name: str) -> list:
        """Load ABI from standardized location."""
        # Improved path resolution
```

#### 4.2 Improve RoflUtility
- Add better error messages
- Add retry logic for ROFL operations
- Improve CBOR response handling

### Phase 5: Code Modernization

#### 5.1 Add Type Hints Throughout
```python
# Before
def fetch_block_by_number(self, block_number):
    
# After
def fetch_block_by_number(self, block_number: int) -> BlockData | None:
```

#### 5.2 Use Pattern Matching
```python
# Replace if/elif chains with match/case
match event.get('transactionHash'):
    case None:
        logger.warning("Missing transaction hash")
    case bytes() as tx_hash:
        tx_hash_hex = tx_hash.hex()
    case str() as tx_hash:
        tx_hash_hex = tx_hash
```

#### 5.3 Use Modern Python Features
- Walrus operator for assignments in conditions
- Union types instead of Optional
- f-strings consistently
- Dataclasses with frozen and slots

### Phase 6: Testing Infrastructure

#### 6.1 Split Test Files
```
test/
├── test_config.py        # Configuration tests
├── test_event_processor.py  # Event processing tests
├── test_block_submitter.py  # Submission tests
└── test_oracle.py        # Integration tests
```

#### 6.2 Add Unit Tests
- Mock Web3 interactions
- Test error conditions
- Validate configuration
- Test event processing logic

## Implementation Roadmap

### Week 1: Foundation
1. **Day 1-2**: Implement configuration system
2. **Day 3**: Replace print statements with logging
3. **Day 4-5**: Add comprehensive tests for new config

### Week 2: Architecture
1. **Day 1-2**: Extract EventProcessor class
2. **Day 3-4**: Extract BlockSubmitter class
3. **Day 5**: Create models module and refactor

### Week 3: Event System
1. **Day 1-3**: Port PollingEventListener from relayer
2. **Day 4-5**: Integrate and test new polling system

### Week 4: Polish
1. **Day 1-2**: Update utility classes
2. **Day 3-4**: Add type hints and modern Python features
3. **Day 5**: Final testing and documentation

## Migration Strategy

### Backward Compatibility
- Keep environment variable support during transition
- Maintain existing public interfaces
- Add deprecation warnings for old patterns
- Document migration path for users

### Testing Approach
1. Add tests for current functionality
2. Refactor with tests ensuring no regression
3. Add new tests for improved functionality
4. Performance benchmarking before/after

### Rollout Plan
1. Create feature branch `feature/oracle-refactor`
2. Implement changes incrementally with tests
3. Test in local environment thoroughly
4. Deploy to testnet for validation
5. Monitor for issues before mainnet deployment

## Expected Outcomes

### Immediate Benefits
- **Reliability**: Simpler polling without WebSocket failures
- **Maintainability**: Modular code easier to modify
- **Observability**: Proper logging for production debugging
- **Type Safety**: Catch errors at development time
- **Performance**: Modern Python features improve efficiency

### Long-term Benefits
- **Scalability**: Modular design supports new features
- **Testing**: Comprehensive test coverage reduces bugs
- **Onboarding**: Clear structure helps new developers
- **Reusability**: Shared utilities between oracle and relayer

## Risk Mitigation

### Potential Risks
1. **Breaking Changes**: Mitigated by backward compatibility
2. **Regression**: Mitigated by comprehensive testing
3. **Performance**: Mitigated by benchmarking
4. **Complexity**: Mitigated by incremental approach

### Rollback Plan
- Git tags at each phase completion
- Feature flags for new implementations
- Parallel deployment option
- Clear rollback procedures documented

## Success Metrics

### Code Quality
- File size under 300 lines (from 395)
- Test coverage >80% (from ~20%)
- Zero print statements (from 40+)
- Full type hint coverage

### Operational
- Event processing latency <1s
- Zero WebSocket failures
- 99.9% uptime target
- Clear error messages in logs

### Development
- Onboarding time reduced 50%
- Bug fix time reduced 40%
- Feature development velocity increased 30%

## Conclusion

This refactoring plan transforms the ROFL Oracle from a monolithic, complex system to a modular, reliable service following the successful patterns proven in the ROFL Relayer. The phased approach ensures safe migration while delivering immediate benefits at each stage.

Priority should be given to Phase 1 (Configuration and Logging) as it provides the foundation for all other improvements. The PollingEventListener replacement in Phase 3 will deliver the most immediate reliability improvements for production deployment.