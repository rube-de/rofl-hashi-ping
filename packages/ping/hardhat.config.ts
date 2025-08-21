import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import "./tasks";
import * as dotenv from "dotenv";

dotenv.config();

// const accounts = process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : {
//   mnemonic: "test test test test test test test test test test test junk",
//   path: "m/44'/60'/0'/0",
//   initialIndex: 0,
//   count: 20,
//   passphrase: "",
// };

const TEST_HDWALLET = {
  mnemonic: "test test test test test test test test test test test junk",
  path: "m/44'/60'/0'/0",
  initialIndex: 0,
  count: 20,
  passphrase: ""
}

const accounts = process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : TEST_HDWALLET;

const config: HardhatUserConfig = {
  networks: {
    hardhat: {
      accounts: TEST_HDWALLET
    },
    "sapphire-localnet": { // Sapphire localnet docker
      url: "http://localhost:8545",
      chainId: 0x5afd,
      accounts: TEST_HDWALLET,
    },    
    "base-mainnet": {
      url: `https://base-mainnet.g.alchemy.com/v2/${process.env.ALCHEMY_API_KEY}`,
      accounts,
      chainId: 8453
    },
    "base-sepolia": {
      url: "https://sepolia.base.org",
      accounts,
      chainId: 84532
    },
    "eth-sepolia": {
      url: `https://eth-sepolia.g.alchemy.com/v2/${process.env.ALCHEMY_API_KEY}`,
      accounts,
      chainId: 11155111
    },
    "sapphire-testnet": {
      url: "https://testnet.sapphire.oasis.dev",
      accounts,
      chainId: 23295
    }
  },
  solidity: "0.8.28",
};

export default config;
