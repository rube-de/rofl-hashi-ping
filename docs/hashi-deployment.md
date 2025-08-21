# Hashi Deployment Guide for Sapphire Testnet

This guide walks through deploying Hashi cross-chain messaging contracts on the Oasis Sapphire testnet.

## Prerequisites

- Node.js v22 (use `nvm` to manage versions)
- Yarn package manager
- Sapphire testnet tokens (TEST Rose)
- Private key for deployment wallet

## Environment Setup

1. **Navigate to the EVM package directory:**
   ```bash
   cd packages/hashi/packages/evm
   ```

2. **Install dependencies:**
   ```bash
   yarn install
   ```

3. **Configure environment variables:**
   
   Edit the `.env` file with your deployment configuration:
   ```env
   PRIVATE_KEY="0x<your_private_key_here>"
   INFURA_API_KEY="<your_infura_key_if_needed>"
   
   # Optional: Override default Sapphire testnet RPC
   SAPPHIRE_TESTNET_JSON_RPC_URL="https://testnet.sapphire.oasis.dev"
   ```

   ⚠️ **Security Note:** Never commit your private key to version control. Use a dedicated deployment wallet.

## Getting Test Tokens

Before deploying, ensure your wallet has Sapphire TEST tokens for gas fees:

- Visit the [Oasis Testnet Faucet](https://faucet.testnet.oasis.dev/)
- Enter your wallet address
- Request TEST tokens for Sapphire testnet

## Contract Deployment

### 1. Deploy Core Hashi Contract

The Hashi contract is the main oracle aggregator:

```bash
npx hardhat deploy:Hashi --network sapphire-testnet
```

Save the deployed contract address for the next steps.

### 2. Deploy ShoyuBashi (Owner-Managed Hashi)

ShoyuBashi allows owner-controlled oracle configuration:

```bash
npx hardhat deploy:ShoyuBashi \
  --owner <YOUR_OWNER_ADDRESS> \
  --hashi <DEPLOYED_HASHI_ADDRESS> \
  --network sapphire-testnet
```

Parameters:
- `--owner`: Address that will control the ShoyuBashi instance
- `--hashi`: Address of the deployed Hashi contract from step 1

### 3. Deploy Message Passing Components (Optional)

#### Deploy Yaho (Message Dispatcher)

Yaho emits and stores message hashes for cross-chain communication:

```bash
npx hardhat deploy:Yaho --network sapphire-testnet
```

#### Deploy Yaru (Message Executor)

Yaru executes messages received from a source chain's Yaho instance:

```bash
npx hardhat deploy:Yaru \
  --hashi <HASHI_ADDRESS> \
  --yaho <YAHO_ADDRESS_ON_SOURCE_CHAIN> \
  --source-chain-id <SOURCE_CHAIN_ID> \
  --network sapphire-testnet
```

Parameters:
- `--hashi`: Address of the Hashi contract on Sapphire testnet
- `--yaho`: Address of the Yaho contract on the source chain
- `--source-chain-id`: Chain ID of the source chain (e.g., 1 for Ethereum mainnet)

### 4. Deploy Additional Components (As Needed)

#### Header Storage

For storing block headers:

```bash
npx hardhat deploy:HeaderStorage --network sapphire-testnet
```

#### Oracle Adapters

Deploy specific oracle adapters based on your bridging requirements. Available adapters include:
- AMB
- Axelar
- Chainlink CCIP
- Connext
- LayerZero
- And more...

Example for deploying a mock adapter (for testing):

```bash
npx hardhat deploy:adapter:Mock --network sapphire-testnet
```

## Post-Deployment Configuration

After deploying the contracts:

1. **Configure ShoyuBashi:**
   - Set oracle adapters for each supported domain
   - Define threshold requirements for consensus
   - Enable/disable specific adapters as needed

2. **Initialize Oracle Adapters:**
   - Configure each adapter with appropriate parameters
   - Set up reporter contracts on source chains
   - Establish connections between chains

3. **Test the Setup:**
   - Send test messages through Yaho
   - Verify oracle consensus through Hashi
   - Execute messages with Yaru

## Network Information

- **Network Name:** Sapphire Testnet
- **Chain ID:** 23295
- **RPC URL:** https://testnet.sapphire.oasis.dev
- **Currency:** TEST (Sapphire Test Rose)
- **Block Explorer:** https://explorer.oasis.io/testnet/sapphire

## Important Notes

- Contract verification on block explorers is not configured for Sapphire testnet
- Sapphire's confidential compute features are automatically available to deployed contracts
- Gas costs may vary from standard EVM chains due to confidential execution
- Always test thoroughly on testnet before mainnet deployment

## Troubleshooting

### Common Issues

1. **Insufficient gas:**
   - Ensure wallet has enough TEST tokens
   - Request more from the faucet if needed

2. **RPC connection errors:**
   - Verify the RPC URL is correct
   - Check network connectivity
   - Try alternative RPC endpoints if available

3. **Transaction failures:**
   - Check gas price settings
   - Verify contract parameters
   - Review transaction logs for specific errors

## Next Steps

After successful deployment:

1. Document all deployed contract addresses
2. Set up monitoring for oracle operations
3. Implement message relaying infrastructure
4. Configure cross-chain message routing
5. Test end-to-end message flow

## Additional Resources

- [Hashi Documentation](https://crosschain-alliance.gitbook.io/hashi)
- [Oasis Sapphire Documentation](https://docs.oasis.io/build/sapphire/)
- [Hashi Explorer](https://hashi-explorer.xyz)
- [Oasis Network Discord](https://discord.gg/oasisprotocol)