# MockAdapter Testing Guide

The MockAdapter is a testing utility for the Hashi cross-chain messaging protocol that allows developers to simulate oracle behavior without requiring actual oracle infrastructure.

## Overview

The `MockAdapter` contract (`packages/hashi/packages/evm/contracts/adapters/Mock/MockAdapter.sol`) is a simplified oracle adapter designed specifically for testing and development purposes. It provides a way to manually set and retrieve block hashes for any domain, making it ideal for testing cross-chain logic without the complexity and delays of real oracle systems.

## Key Features

- **Manual Hash Setting**: Direct control over block hashes via the `setHashes()` function
- **No External Dependencies**: Works standalone without requiring oracle infrastructure
- **Immediate Availability**: Hashes are available instantly after setting (no consensus delays)
- **Full Adapter Compatibility**: Inherits from both `Adapter` and `BlockHashAdapter` interfaces
- **Multi-Domain Support**: Can simulate hashes from multiple chains simultaneously

## Contract Interface

```solidity
contract MockAdapter is Adapter, BlockHashAdapter {
    // Set multiple hashes for a specific domain
    function setHashes(
        uint256 domain,           // Chain ID of the source chain
        uint256[] memory ids,     // Block numbers or message IDs
        bytes32[] memory hashes   // Corresponding hashes
    ) external
    
    // Inherited from Adapter
    function getHash(uint256 domain, uint256 id) public view returns (bytes32)
}
```

## Deployment

### Using Hardhat Console

```bash
npx hardhat console --network sapphire-testnet

# In the console:
> const MockAdapter = await ethers.getContractFactory("MockAdapter")
> const mockAdapter = await MockAdapter.deploy()
> await mockAdapter.deployed()
> console.log("MockAdapter deployed to:", mockAdapter.address)
```

### Using a Deployment Script

Create a deployment script `scripts/deploy-mock-adapter.js`:

```javascript
const { ethers } = require("hardhat");

async function main() {
  console.log("Deploying MockAdapter...");
  
  const MockAdapter = await ethers.getContractFactory("MockAdapter");
  const mockAdapter = await MockAdapter.deploy();
  await mockAdapter.deployed();
  
  console.log("MockAdapter deployed to:", mockAdapter.address);
  return mockAdapter.address;
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
```

Run the script:
```bash
npx hardhat run scripts/deploy-mock-adapter.js --network sapphire-testnet
```

## Integration with Hashi

### 1. Configure with ShoyuBashi

```javascript
const { ethers } = require("hardhat");

async function configureMockAdapter() {
  const SHOYUBASHI_ADDRESS = "0x..."; // Your deployed ShoyuBashi
  const MOCK_ADAPTER_ADDRESS = "0x..."; // Your deployed MockAdapter
  
  const shoyuBashi = await ethers.getContractAt("ShoyuBashi", SHOYUBASHI_ADDRESS);
  
  // Enable MockAdapter for Ethereum mainnet (domain = 1)
  await shoyuBashi.enableAdapter(1, [MOCK_ADAPTER_ADDRESS]);
  
  // Set threshold (e.g., 1 for testing)
  await shoyuBashi.setThreshold(1, 1);
  
  console.log("MockAdapter configured with ShoyuBashi");
}
```

### 2. Configure with Plain Hashi

If using Hashi directly without ShoyuBashi, simply pass the MockAdapter address when querying:

```javascript
const hash = await hashi.getHash(domain, blockNumber, [mockAdapterAddress]);
```

## Usage Examples

### Basic Hash Setting

```javascript
const mockAdapter = await ethers.getContractAt("MockAdapter", MOCK_ADAPTER_ADDRESS);

// Set a single block hash
const domain = 1; // Ethereum mainnet
const blockNumber = [18000000];
const blockHash = ["0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"];

await mockAdapter.setHashes(domain, blockNumber, blockHash);
```

### Batch Hash Setting

```javascript
// Set multiple block hashes at once
const domain = 1;
const blockNumbers = [18000000, 18000001, 18000002];
const blockHashes = [
  "0x1111111111111111111111111111111111111111111111111111111111111111",
  "0x2222222222222222222222222222222222222222222222222222222222222222",
  "0x3333333333333333333333333333333333333333333333333333333333333333"
];

await mockAdapter.setHashes(domain, blockNumbers, blockHashes);
```

### Simulating Cross-Chain Messages

```javascript
// Simulate a message hash from another chain
const sourceChainId = 1;
const messageId = 12345;
const messageHash = ethers.utils.keccak256(
  ethers.utils.defaultAbiCoder.encode(
    ["address", "uint256", "bytes"],
    [targetAddress, value, data]
  )
);

await mockAdapter.setHashes(sourceChainId, [messageId], [messageHash]);
```

## Testing Patterns

### Unit Test Example

```javascript
const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Cross-Chain Message Verification", function () {
  let mockAdapter;
  let hashi;
  
  beforeEach(async function () {
    // Deploy contracts
    const MockAdapter = await ethers.getContractFactory("MockAdapter");
    mockAdapter = await MockAdapter.deploy();
    
    const Hashi = await ethers.getContractFactory("Hashi");
    hashi = await Hashi.deploy();
  });
  
  it("Should verify message with mock oracle", async function () {
    // Set test hash
    const domain = 1;
    const blockNumber = 12345;
    const testHash = ethers.utils.keccak256("0x1234");
    
    await mockAdapter.setHashes(domain, [blockNumber], [testHash]);
    
    // Verify through Hashi
    const retrievedHash = await hashi.getHash(
      domain, 
      blockNumber, 
      [mockAdapter.address]
    );
    
    expect(retrievedHash).to.equal(testHash);
  });
  
  it("Should handle multiple adapters with same hash", async function () {
    // Deploy second mock adapter
    const MockAdapter = await ethers.getContractFactory("MockAdapter");
    const mockAdapter2 = await MockAdapter.deploy();
    
    // Set same hash in both adapters
    const hash = ethers.utils.keccak256("0x5678");
    await mockAdapter.setHashes(1, [100], [hash]);
    await mockAdapter2.setHashes(1, [100], [hash]);
    
    // Get unanimous hash from both adapters
    const unanimousHash = await hashi.getHash(
      1, 
      100, 
      [mockAdapter.address, mockAdapter2.address]
    );
    
    expect(unanimousHash).to.equal(hash);
  });
});
```

### Integration Test Example

```javascript
describe("End-to-End Message Flow", function () {
  it("Should execute cross-chain message", async function () {
    // 1. Deploy infrastructure
    const mockAdapter = await deployMockAdapter();
    const hashi = await deployHashi();
    const yaru = await deployYaru(hashi.address, YAHO_ADDRESS, SOURCE_CHAIN_ID);
    
    // 2. Simulate message from source chain
    const message = {
      id: 1,
      data: "0x...",
      hash: ethers.utils.keccak256("0xmessage")
    };
    
    // 3. Set message hash in mock adapter
    await mockAdapter.setHashes(
      SOURCE_CHAIN_ID, 
      [message.id], 
      [message.hash]
    );
    
    // 4. Execute message through Yaru
    const tx = await yaru.executeMessage(
      message.id,
      message.data,
      [mockAdapter.address]
    );
    
    // 5. Verify execution
    expect(tx).to.emit(yaru, "MessageExecuted").withArgs(message.id);
  });
});
```

## Development Workflow

1. **Initial Setup**: Deploy MockAdapter alongside Hashi contracts
2. **Configure Adapters**: Enable MockAdapter in ShoyuBashi or use directly with Hashi
3. **Set Test Data**: Use `setHashes()` to simulate oracle responses
4. **Test Logic**: Execute cross-chain logic with predictable oracle data
5. **Iterate Quickly**: Update hashes instantly without waiting for real oracles

## Common Use Cases

### 1. Testing Message Verification
- Set known message hashes
- Verify message execution logic
- Test error handling for invalid hashes

### 2. Simulating Multiple Oracles
- Deploy multiple MockAdapters
- Set different or conflicting hashes
- Test consensus mechanisms

### 3. Development Environment
- Quick iteration without oracle delays
- Predictable test conditions
- Cost-effective testing (no oracle fees)

### 4. Debugging Production Issues
- Reproduce specific hash scenarios
- Test edge cases with controlled data
- Isolate issues from oracle behavior

## Security Considerations

⚠️ **WARNING: Testing Only**

The MockAdapter should **NEVER** be used in production environments because:

1. **No Authentication**: Anyone can call `setHashes()` to set arbitrary values
2. **No Verification**: Hashes are not verified against actual blockchain data
3. **Centralized Control**: Completely bypasses the security of decentralized oracles
4. **No Consensus**: Single point of failure with no multi-oracle validation

## Comparison with Real Adapters

| Feature | MockAdapter | Production Adapters |
|---------|------------|-------------------|
| Setup Complexity | Simple | Complex |
| External Dependencies | None | Oracle infrastructure |
| Hash Availability | Immediate | Consensus delays |
| Cost | Gas only | Gas + oracle fees |
| Security | None | Cryptographic proofs |
| Use Case | Testing | Production |

## Troubleshooting

### Issue: Hashes not being retrieved
- Verify the correct domain ID is being used
- Check that the MockAdapter address is correct
- Ensure `setHashes()` transaction was successful

### Issue: Array length mismatch error
- The `ids` and `hashes` arrays must have the same length
- Check your input arrays before calling `setHashes()`

### Issue: Hash conflicts with multiple MockAdapters
- Ensure all MockAdapters have the same hash for consensus
- Or adjust threshold in ShoyuBashi if testing partial consensus

## Best Practices

1. **Clear Test Data**: Reset hashes between test cases to avoid interference
2. **Document Test Scenarios**: Comment what each hash represents in tests
3. **Use Realistic Data**: Test with hash formats that match production
4. **Test Edge Cases**: Include tests for missing hashes, conflicts, etc.
5. **Separate Test Contracts**: Deploy fresh MockAdapters for each test suite

## Next Steps

After testing with MockAdapter:

1. Graduate to testnet with real oracle adapters
2. Test with actual cross-chain delays and consensus
3. Verify gas costs with production adapters
4. Implement monitoring for production oracle health
5. Plan fallback strategies for oracle failures

## Additional Resources

- [Hashi Architecture Documentation](https://crosschain-alliance.gitbook.io/hashi)
- [Writing Tests with Hardhat](https://hardhat.org/tutorial/testing-contracts)
- [Ethers.js Documentation](https://docs.ethers.io/v5/)
- [Oasis Sapphire Testing Guide](https://docs.oasis.io/build/sapphire/)