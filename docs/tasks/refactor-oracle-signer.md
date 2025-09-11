# Oracle Signer Refactor - ROFL Mode Enhancement

## Overview

This document outlines the refactoring of the ROFL Oracle to implement a dedicated oracle key management system in ROFL mode. Instead of relying solely on ROFL's internal transaction submission mechanism, the oracle will generate and manage its own signing key, register it with the ROFLAdapter contract, and use it for block header submissions.

## Current Implementation

### Local Mode
- Uses a private key from environment variable (`LOCAL_PRIVATE_KEY`)
- ContractUtility initializes with the secret for signing
- Direct transaction submission to MockAdapter contract using Web3 signing middleware
- Transactions are signed with the provided private key

### ROFL Mode
- No dedicated oracle key management
- ContractUtility initialized without a secret (read-only mode)
- Transactions built unsigned and submitted via `RoflUtility.submit_tx()`
- ROFL runtime handles all signing internally
- No explicit oracle address registration

## Proposed Architecture

### Key Components

1. **Oracle Key Generation**
   - Use `RoflUtility.fetch_key()` to generate/retrieve a dedicated oracle key
   - Key is deterministically derived based on a key identifier
   - Ensures consistent oracle address across restarts

2. **Oracle Registration**
   - Call `ROFLAdapter.setOracle()` to register the oracle address
   - This transaction is submitted via ROFL (using `submit_tx`)
   - Establishes the oracle as an authorized submitter

3. **Block Header Submission**
   - Sign transactions with the oracle key (similar to local mode)
   - Submit signed transactions directly to the network
   - Maintains consistency between local and ROFL modes

## Implementation Steps

### Phase 1: Oracle Key Management

#### 1.1 Generate Oracle Key on Startup
```python
# In HeaderOracle.__init__()
if not config.local_mode:
    # Generate/fetch oracle key from ROFL
    oracle_key = await rofl_utility.fetch_key("rofl-oracle-signer")
    self.secret = oracle_key
else:
    # Existing local mode logic
    self.secret = config.local_private_key
```

#### 1.2 Initialize ContractUtility with Key
```python
# Always initialize with secret when available
self.contract_utility = ContractUtility(
    config.target_chain.rpc_url, 
    self.secret  # Now available in both modes
)
```

### Phase 2: Oracle Registration

#### 2.1 Add Registration Method to BlockSubmitter
```python
async def register_oracle(self) -> bool:
    """
    Register the oracle address with the ROFLAdapter contract.
    Only needed in ROFL mode on first initialization.
    """
    if not self.rofl_util:
        return True  # Not needed in local mode
    
    # Get oracle address from the key
    oracle_address = self.contract_util.w3.eth.default_account
    
    # Build setOracle transaction
    tx_params = {
        "from": "0x0000000000000000000000000000000000000000",
        "gas": 100000,
        "gasPrice": self.contract_util.w3.eth.gas_price,
        "value": Wei(0),
    }
    
    tx_data = self.contract.functions.setOracle(
        oracle_address
    ).build_transaction(tx_params)
    
    # Submit via ROFL (this uses ROFL's authority)
    return await self.rofl_util.submit_tx(tx_data)
```

#### 2.2 Check and Register on Startup
```python
# In HeaderOracle.__init__() after BlockSubmitter creation
if not config.local_mode:
    # Check if oracle is already registered
    current_oracle = await block_submitter.get_registered_oracle()
    expected_oracle = contract_utility.w3.eth.default_account
    
    if current_oracle != expected_oracle:
        logger.info(f"Registering oracle address: {expected_oracle}")
        success = await block_submitter.register_oracle()
        if not success:
            raise Exception("Failed to register oracle address")
```

### Phase 3: Unified Block Submission

#### 3.1 Modify BlockSubmitter.submit_block_header()
```python
async def submit_block_header(self, block_number: int, block_hash: str) -> bool:
    """
    Submit block header using oracle key in both modes.
    """
    try:
        # Both modes now use the same submission logic
        if self.rofl_util:
            # ROFL mode: use storeBlockHeader
            tx = self.contract.functions.storeBlockHeader(
                self.source_chain_id, block_number, block_hash
            )
        else:
            # Local mode: use setHashes
            tx = self.contract.functions.setHashes(
                self.source_chain_id,
                [int(block_number)],
                [block_hash],
            )
        
        # Send transaction (signed with oracle key)
        tx_hash = tx.transact({
            "gas": 300000,
            "gasPrice": self.contract_util.w3.eth.gas_price,
        })
        
        # Wait for confirmation
        receipt = self.contract_util.w3.eth.wait_for_transaction_receipt(
            tx_hash, timeout=self.request_timeout
        )
        
        return receipt.get("status", 0) == 1
        
    except Exception as e:
        logger.error(f"Error submitting block header: {e}")
        return False
```

## Configuration Changes

### Environment Variables
No new environment variables needed - the oracle key is generated deterministically by ROFL.

### Key Identifier
The oracle key uses identifier `"rofl-oracle-signer"` to ensure consistency across restarts.

## Benefits of This Approach

1. **Consistency**: Both local and ROFL modes use similar signing patterns
2. **Transparency**: Clear oracle address visible on-chain
3. **Security**: Oracle registration prevents unauthorized submissions
4. **Debugging**: Easier to trace transactions from a known oracle address
5. **Testing**: Local mode better simulates production behavior

## Migration Strategy

### Deployment Steps
1. Deploy updated ROFL oracle application
2. On first run, oracle automatically:
   - Generates its signing key
   - Registers with ROFLAdapter contract
   - Begins submitting with new key
3. Monitor initial submissions for success
4. Verify oracle address in contract state

### Rollback Plan
If issues occur:
1. Revert to previous ROFL application version
2. Oracle continues using ROFL internal signing
3. No contract changes needed (setOracle is optional)

## Testing Checklist

- [ ] Oracle key generation in ROFL mode
- [ ] Oracle registration transaction succeeds
- [ ] Block headers submit with oracle signature
- [ ] Contract accepts submissions from registered oracle
- [ ] Local mode continues to work unchanged
- [ ] Oracle address persists across restarts
- [ ] Error handling for registration failures
