# Phase 3: ROFL Relayer Proof Generation - Simplified MVP

## Overview

This document outlines a **simplified, minimal** implementation for adding proof generation to the ROFL relayer. Focus is on getting a working MVP with the least complexity possible.

## Core Requirement

The relayer must generate cryptographic proofs in Python that are byte-for-byte identical to the TypeScript implementation. These proofs allow the target chain to verify events from the source chain without trusting a single oracle.

## Proof Structure (Hashi Format)

The proof is an 8-element array:
1. `chainId` - Source chain ID
2. `blockNumber` - Block containing the event
3. `encodedBlockHeader` - Serialized block header
4. `ancestralBlockNumber` - Set to 0 (MVP doesn't use ancestral proofs)
5. `ancestralBlockHeaders` - Empty array []
6. `merkleProof` - Array of proof nodes
7. `transactionIndex` - RLP-encoded transaction index
8. `logIndex` - Event position in logs

## Simplified MVP Implementation

### 1. Minimal Dependencies

Add to `pyproject.toml`:
```toml
dependencies = [
    "web3",          # Already present
    "rlp>=3.0.0",    # For RLP encoding
    "trie>=2.0.0",   # For Merkle Patricia Trie
]
```

Skip eth-utils and eth-hash if web3 provides what we need.

### 2. Single ProofManager Class

Create **`src/rofl_relayer/proof_manager.py`** (~200 lines total)

```python
class ProofManager:
    """Handles proof generation and submission for cross-chain messages"""
    
    def __init__(self, web3_source, contract_util, rofl_util=None):
        """Initialize with Web3 and utility instances"""
        self.web3 = web3_source
        self.contract_util = contract_util
        self.rofl_util = rofl_util
        
    async def generate_proof(self, tx_hash: str, log_index: int = 0) -> list:
        """
        Generate Hashi-format proof for a transaction.
        Returns 8-element array matching TypeScript format.
        """
        # 1. Fetch receipt and block
        # 2. Get all receipts in block
        # 3. RLP encode all receipts
        # 4. Build Merkle trie
        # 5. Generate proof for target receipt
        # 6. Encode block header
        # 7. Return formatted proof array
        
    async def submit_proof(self, proof: list, receiver_address: str) -> str:
        """
        Submit proof to PingReceiver contract.
        Returns transaction hash.
        """
        # Format proof for contract call
        # Prepare transaction data
        
        if self.rofl_util:
            # ROFL mode: prepare tx and use rofl_util.submit_tx()
            tx_data = self._prepare_tx_data(proof, receiver_address)
            return await self.rofl_util.submit_tx(tx_data)
        else:
            # Local mode: use contract_util
            return await self.contract_util.call_contract_method(
                receiver_address, "receivePing", proof
            )
    
    async def process_ping_event(self, ping_event, receiver_address: str):
        """
        Complete flow: generate and submit proof for a ping event.
        """
        proof = await self.generate_proof(
            ping_event.tx_hash, 
            ping_event.log_index
        )
        return await self.submit_proof(proof, receiver_address)
        
    # Private helper methods
    def _encode_receipt(self, receipt): 
        """RLP encode a single receipt with transaction type handling"""
        
    def _build_trie(self, receipts): 
        """Build Merkle Patricia Trie from receipts"""
        
    def _encode_block_header(self, block): 
        """Serialize block header"""
        
    def _prepare_tx_data(self, proof, receiver_address): 
        """Format transaction data for submission"""
```

### 3. Simple Integration

Update `event_processor.py` (add ~10 lines):

```python
# In __init__:
self.proof_manager = ProofManager(web3, contract_util, rofl_util)

# When we have matching Ping and HashStored events:
async def process_matched_events(self, ping_event, hash_stored):
    try:
        tx_hash = await self.proof_manager.process_ping_event(
            ping_event, 
            self.config.target_chain.ping_receiver_address
        )
        logger.info(f"Proof submitted: {tx_hash}")
    except Exception as e:
        logger.error(f"Proof processing failed: {e}")
```

### 4. Key Implementation Details

#### RLP Encoding
- Handle Type 0 (legacy) and Type 2 (EIP-1559) transactions
- Type prefix: None for Type 0, 0x02 for Type 2
- Encode receipt: [status, cumulative_gas, logs_bloom, logs]

#### Merkle Trie
- Key: RLP-encoded transaction index
- Value: RLP-encoded receipt (with type prefix if needed)
- Verify trie root matches block's receiptsRoot

#### Block Header
- Use web3's block data
- Serialize in correct field order
- Verify hash matches block hash

### 5. Testing Strategy

The **only** test that matters for MVP:

```python
# Generate our proof
our_proof = proof_manager.generate_proof(web3, "0x3794cbba...")

# Compare with TypeScript proof
typescript_proof = json.load(open("proof.json"))

# Must be identical
assert our_proof == typescript_proof
```

If this passes, ship it.

### 6. Implementation Steps

1. **Add dependencies** (5 minutes)
   ```bash
   # Update pyproject.toml
   uv sync
   ```

2. **Create ProofManager class** (3-4 hours)
   - Start with generate_proof method
   - Port TypeScript logic to Python
   - Test each component against known values

3. **Add submission logic** (30 minutes)
   - Implement submit_proof method
   - Prepare transaction data
   - Use existing utilities

4. **Integrate with event processor** (15 minutes)
   - Initialize ProofManager
   - Call process_ping_event when ready

5. **Test end-to-end** (1 hour)
   - Verify proof matches TypeScript output
   - Test submission to contract

**Total time: ~5 hours**

## Design Rationale

### Why ProofManager Class?

- **Cohesion**: All proof logic in one place
- **Clean Architecture**: Utils remain generic, business logic separated
- **Testability**: Can test generation and submission independently
- **Simplicity**: Event processor just calls one method

### Why Not Multiple Modules?

- **KISS Principle**: One class, one file, one responsibility
- **MVP Focus**: Add structure later if needed
- **Easier Debugging**: All proof code in one place
- **Faster Development**: Less boilerplate, less coordination

## Success Criteria

✅ Proof generation matches TypeScript byte-for-byte
✅ Proof submission succeeds on target chain
✅ Total code addition < 250 lines
✅ Implementation complete in < 1 day

## What We're NOT Doing (MVP Scope)

❌ Complex error handling (just try/catch and log)
❌ Retry logic (fail fast for MVP)
❌ Queue management (process synchronously)
❌ State persistence (stateless for MVP)
❌ Performance optimization (make it work first)
❌ Multiple proof types (just Ping events)
❌ Extensive validation (trust RPC data)

## Next Steps After MVP

Once the MVP works, consider:
1. Add retry logic for transient failures
2. Implement proof caching
3. Add more comprehensive error handling
4. Support other event types
5. Optimize for performance

But first: **Ship a working proof generator**.