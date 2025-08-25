import { task } from "hardhat/config";
import { HardhatRuntimeEnvironment } from "hardhat/types";

task("post-blockhash", "Post block hash to mock oracle contract (MockAdapter or MockShoyuBashi)")
  .addParam("chainId", "Source chain ID")
  .addParam("blockNumber", "Block number")
  .addParam("blockHash", "Block hash (from generate-proof output)")
  .addOptionalParam("contract", "Mock contract address (MockAdapter or MockShoyuBashi)", "0x9f983F759d511D0f404582b0bdc1994edb5db856")
  .addOptionalParam("type", "Contract type: 'adapter' or 'shoyubashi' (default: 'adapter')", "adapter")
  .setAction(async (taskArgs, hre: HardhatRuntimeEnvironment) => {
    const { ethers } = hre;
    
    console.log("🔗 Posting block hash to mock oracle contract");
    console.log("Contract:", taskArgs.contract);
    console.log("Chain ID:", taskArgs.chainId);
    console.log("Block Number:", taskArgs.blockNumber);
    console.log("Block Hash:", taskArgs.blockHash);
    
    const contractType = taskArgs.type;
    console.log(`📝 Using contract type: ${contractType}`);
    
    if (contractType === "adapter") {
      // Handle MockAdapter
      console.log("🔧 Posting to MockAdapter using setHashes()...");
      
      // Define minimal ABI for MockAdapter functions
      const mockAdapterABI = [
        "function setHashes(uint256 domain, uint256[] memory ids, bytes32[] memory hashes) external",
        "function getHash(uint256 domain, uint256 id) external view returns (bytes32)"
      ];
      
      const [signer] = await ethers.getSigners();
      const mockAdapter = new ethers.Contract(taskArgs.contract, mockAdapterABI, signer);
      
      // Prepare arrays for MockAdapter
      const blockNumbers = [taskArgs.blockNumber];
      const blockHashes = [taskArgs.blockHash];
      
      // Post the hash
      const tx = await mockAdapter.setHashes(
        taskArgs.chainId,
        blockNumbers, 
        blockHashes
      );
      
      console.log("📤 Transaction sent:", tx.hash);
      await tx.wait();
      console.log("✅ Block hash posted successfully to MockAdapter!");
      
      // Verify it was stored
      const storedHash = await mockAdapter.getHash(taskArgs.chainId, taskArgs.blockNumber);
      console.log("🔍 Verification - stored hash:", storedHash);
      console.log("✅ Match:", storedHash === taskArgs.blockHash ? "YES" : "NO");
      
    } else if (contractType === "shoyubashi") {
      // Handle MockShoyuBashi
      console.log("🔧 Posting to MockShoyuBashi using setThresholdHash()...");
      
      const MockShoyuBashi = await ethers.getContractFactory("MockShoyuBashi");
      const mockShoyuBashi = MockShoyuBashi.attach(taskArgs.contract);
      
      // Post the hash (MockShoyuBashi takes single values, not arrays)
      const tx = await mockShoyuBashi.setThresholdHash(
        taskArgs.chainId,
        taskArgs.blockNumber,
        taskArgs.blockHash
      );
      
      console.log("📤 Transaction sent:", tx.hash);
      await tx.wait();
      console.log("✅ Block hash posted successfully to MockShoyuBashi!");
      
      // Verify it was stored
      const storedHash = await mockShoyuBashi.getThresholdHash(taskArgs.chainId, taskArgs.blockNumber);
      console.log("🔍 Verification - stored hash:", storedHash);
      console.log("✅ Match:", storedHash === taskArgs.blockHash ? "YES" : "NO");
      
    } else {
      throw new Error(`Unknown contract type: ${contractType}. Use 'adapter' or 'shoyubashi'.`);
    }
    
    console.log("\n💡 Usage Notes:");
    if (contractType === "adapter") {
      console.log("  MockAdapter is typically used with custom HashiProver implementations");
      console.log("  that directly query specific adapter contracts for block hashes.");
    } else {
      console.log("  MockShoyuBashi implements the IShoyuBashi interface used by HashiProver");
      console.log("  and is the recommended mock for testing PingReceiver contracts.");
    }
  });