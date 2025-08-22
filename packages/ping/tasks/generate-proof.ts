import { task } from "hardhat/config";
import { HardhatRuntimeEnvironment } from "hardhat/types";

task("generate-proof", "Generate Merkle proof for cross-chain ping verification")
  .addParam("txHash", "Transaction hash containing the Ping event")
  .addParam("sourceChain", "Source chain RPC URL or network name")
  .addOptionalParam("logIndex", "Log index of Ping event (auto-detect if not provided)")
  .setAction(async (taskArgs, hre: HardhatRuntimeEnvironment) => {
    const { ethers } = hre;
    
    console.log("🛠️  Generating Merkle Proof");
    console.log("Transaction hash:", taskArgs.txHash);
    console.log("Source chain:", taskArgs.sourceChain);
    
    // This is a helper task for developers/testing
    // In production, the ROFL relayer handles proof generation automatically
    
    let sourceProvider: any;
    
    // Determine if sourceChain is a network name or RPC URL
    if (taskArgs.sourceChain.startsWith("http")) {
      sourceProvider = new ethers.JsonRpcProvider(taskArgs.sourceChain);
    } else {
      // Try to use configured network
      const networks = hre.config.networks;
      if (networks[taskArgs.sourceChain]) {
        const networkConfig = networks[taskArgs.sourceChain] as any;
        sourceProvider = new ethers.JsonRpcProvider(networkConfig.url);
      } else {
        throw new Error(`Unknown network: ${taskArgs.sourceChain}`);
      }
    }
    
    try {
      // Get transaction receipt
      console.log("📥 Fetching transaction receipt...");
      const receipt = await sourceProvider.getTransactionReceipt(taskArgs.txHash);
      
      if (!receipt) {
        throw new Error("Transaction receipt not found");
      }
      
      console.log("  Block number:", receipt.blockNumber);
      console.log("  Transaction index:", receipt.index);
      console.log("  Status:", receipt.status === 1 ? "Success" : "Failed");
      console.log("  Logs count:", receipt.logs.length);
      
      // Get block header
      console.log("\n📦 Fetching block header...");
      const block = await sourceProvider.getBlock(receipt.blockNumber);
      
      if (!block) {
        throw new Error("Block not found");
      }
      
      console.log("  Block hash:", block.hash);
      console.log("  Block timestamp:", new Date(block.timestamp * 1000).toISOString());
      console.log("  Transactions count:", block.transactions.length);
      
      // Find Ping log
      let pingLogIndex = taskArgs.logIndex;
      
      if (pingLogIndex === undefined) {
        console.log("\n🔍 Auto-detecting Ping log...");
        
        // Try to decode logs to find Ping event
        const pingSenderInterface = new ethers.Interface([
          "event Ping(address indexed sender, uint256 indexed blockNumber)"
        ]);
        
        for (let i = 0; i < receipt.logs.length; i++) {
          try {
            const parsed = pingSenderInterface.parseLog(receipt.logs[i]);
            if (parsed && parsed.name === "Ping") {
              pingLogIndex = i;
              console.log(`  Found Ping at log index ${i}`);
              console.log(`  Sender: ${parsed.args.sender}`);
              console.log(`  Block Number: ${parsed.args.blockNumber}`);
              break;
            }
          } catch {
            // Not a Ping log, continue
          }
        }
        
        if (pingLogIndex === undefined) {
          throw new Error("Ping log not found in transaction");
        }
      }
      
      // Prepare proof structure
      console.log("\n🧮 Generating proof structure...");
      
      const proof = {
        chainId: Number((await sourceProvider.getNetwork()).chainId),
        blockNumber: receipt.blockNumber,
        blockHeader: "0x", // Would need to RLP encode the block header
        ancestralBlockNumber: 0, // For MVP, using direct block
        ancestralBlockHeaders: [],
        receiptProof: [], // Would need to generate Merkle proof from receipt trie
        transactionIndex: ethers.toBeHex(receipt.index),
        logIndex: pingLogIndex
      };
      
      console.log("📋 Proof Structure (for reference):");
      console.log(JSON.stringify(proof, null, 2));
      
      console.log("\n⚠️  Note: This is a simplified proof structure for reference.");
      console.log("Complete proof generation requires:");
      console.log("1. RLP encoding of block headers");
      console.log("2. Merkle proof generation from receipt trie");
      console.log("3. Proper transaction index encoding");
      console.log("");
      console.log("🤖 In production, the ROFL relayer handles this automatically using:");
      console.log("- Web3.py for RLP encoding/decoding");
      console.log("- Eth-hash for Merkle proof generation"); 
      console.log("- Proper transaction receipt processing");
      
      // For developers: show what the ROFL relayer would do
      console.log("\n🔗 ROFL Relayer Workflow:");
      console.log("1. Monitor Ping events in real-time");
      console.log("2. Wait for block header availability in Hashi");
      console.log("3. Generate complete Merkle proof:");
      console.log(`   - Block header: ${block.hash}`);
      console.log(`   - Transaction receipt at index: ${receipt.index}`);
      console.log(`   - Event log at index: ${pingLogIndex}`);
      console.log("4. Submit proof to PingReceiver.receivePing()");
      
      return {
        chainId: proof.chainId,
        blockNumber: proof.blockNumber,
        transactionHash: taskArgs.txHash,
        transactionIndex: receipt.index,
        logIndex: pingLogIndex,
        blockHash: block.hash
      };
      
    } catch (error) {
      console.error("❌ Error generating proof:", error);
      throw error;
    }
  });