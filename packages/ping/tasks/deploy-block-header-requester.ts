import { task, types } from "hardhat/config";
import { HardhatRuntimeEnvironment } from "hardhat/types";

task("deploy:block-header-requester", "Deploy the BlockHeaderRequester contract")
  .addOptionalParam("verify", "Verify contract on Etherscan", false, types.boolean)
  .setAction(async (taskArgs, hre: HardhatRuntimeEnvironment) => {
    const { ethers } = hre;
    
    console.log("Deploying BlockHeaderRequester contract...");
    console.log("Network:", hre.network.name);
    
    // Get the deployer account
    const [deployer] = await ethers.getSigners();
    console.log("Deploying with account:", deployer.address);
    
    // Check account balance
    const balance = await ethers.provider.getBalance(deployer.address);
    console.log("Account balance:", ethers.formatEther(balance), "ETH");
    
    // Deploy the contract
    const BlockHeaderRequester = await ethers.getContractFactory("BlockHeaderRequester");
    const blockHeaderRequester = await BlockHeaderRequester.deploy();
    
    // Wait for deployment
    await blockHeaderRequester.waitForDeployment();
    const contractAddress = await blockHeaderRequester.getAddress();
    
    console.log("BlockHeaderRequester deployed to:", contractAddress);
    console.log("Transaction hash:", blockHeaderRequester.deploymentTransaction()?.hash);
    
    // Wait for a few block confirmations
    console.log("Waiting for block confirmations...");
    await blockHeaderRequester.deploymentTransaction()?.wait(2);
    
    // Verify the contract on Etherscan if requested
    if (taskArgs.verify && hre.network.name !== "localhost" && hre.network.name !== "hardhat") {
      console.log("\nVerifying contract on Etherscan...");
      try {
        await hre.run("verify:verify", {
          address: contractAddress,
          constructorArguments: [],
        });
        console.log("Contract verified successfully!");
      } catch (error: any) {
        if (error.message.includes("Already Verified")) {
          console.log("Contract is already verified!");
        } else {
          console.error("Error verifying contract:", error);
        }
      }
    } else if (taskArgs.verify) {
      console.log("Skipping verification on local network");
    }
    
    // Log deployment info for documentation
    console.log("\n=== Deployment Summary ===");
    console.log("Network:", hre.network.name);
    console.log("Contract Address:", contractAddress);
    console.log("Deployer:", deployer.address);
    console.log("Block Number:", await ethers.provider.getBlockNumber());
    console.log("==========================\n");
    
    // Save deployment info to a file
    const fs = require("fs");
    const path = require("path");
    const deploymentInfo = {
      network: hre.network.name,
      contractAddress: contractAddress,
      deployer: deployer.address,
      blockNumber: await ethers.provider.getBlockNumber(),
      timestamp: new Date().toISOString(),
      transactionHash: blockHeaderRequester.deploymentTransaction()?.hash,
    };
    
    const deploymentsDir = path.join(__dirname, "../deployments");
    if (!fs.existsSync(deploymentsDir)) {
      fs.mkdirSync(deploymentsDir, { recursive: true });
    }
    
    const deploymentFile = path.join(
      deploymentsDir,
      `BlockHeaderRequester-${hre.network.name}.json`
    );
    fs.writeFileSync(deploymentFile, JSON.stringify(deploymentInfo, null, 2));
    console.log(`Deployment info saved to: ${deploymentFile}`);
    
    return contractAddress;
  });

// Task to test requesting a block header
task("request:block-header", "Request a block header using the deployed contract")
  .addParam("contract", "The BlockHeaderRequester contract address")
  .addOptionalParam("chainid", "The chain ID to request from (defaults to current network)", undefined, types.int)
  .addOptionalParam("blocknumber", "The block number to request (defaults to latest)", undefined, types.int)
  .addOptionalParam("context", "Optional context data (32 bytes)", "0x0000000000000000000000000000000000000000000000000000000000000000")
  .setAction(async (taskArgs, hre: HardhatRuntimeEnvironment) => {
    const { ethers } = hre;
    
    // Get chain ID from network if not provided
    const chainId = taskArgs.chainid || (await ethers.provider.getNetwork()).chainId;
    
    // Get latest block number if not provided
    const blockNumber = taskArgs.blocknumber || await ethers.provider.getBlockNumber();
    
    console.log("Requesting block header...");
    console.log("Contract:", taskArgs.contract);
    console.log("Chain ID:", chainId.toString());
    console.log("Block Number:", blockNumber.toString());
    console.log("Context:", taskArgs.context);
    
    // Get the contract instance
    const blockHeaderRequester = await ethers.getContractAt(
      "BlockHeaderRequester",
      taskArgs.contract
    );
    
    // Check if block was already requested
    const isRequested = await blockHeaderRequester.isBlockRequested(
      chainId,
      blockNumber
    );
    
    if (isRequested) {
      console.log("⚠️  Block has already been requested!");
      return;
    }
    
    // Request the block header
    const tx = await blockHeaderRequester.requestBlockHeader(
      chainId,
      blockNumber,
      taskArgs.context
    );
    
    console.log("Transaction sent:", tx.hash);
    console.log("Waiting for confirmation...");
    
    const receipt = await tx.wait();
    console.log("Transaction confirmed in block:", receipt?.blockNumber);
    
    // Parse the event
    const event = receipt?.logs
      .map((log: any) => {
        try {
          return blockHeaderRequester.interface.parseLog(log);
        } catch {
          return null;
        }
      })
      .find((parsedLog: any) => parsedLog?.name === "BlockHeaderRequested");
    
    if (event) {
      console.log("\n✅ Block header requested successfully!");
      console.log("Event details:");
      console.log("  Chain ID:", event.args.chainId.toString());
      console.log("  Block Number:", event.args.blockNumber.toString());
      console.log("  Requester:", event.args.requester);
      console.log("  Context:", event.args.context);
    }
  });

// Task to check if a block was requested
task("check:block-requested", "Check if a block header was already requested")
  .addParam("contract", "The BlockHeaderRequester contract address")
  .addParam("chainid", "The chain ID")
  .addParam("blocknumber", "The block number")
  .setAction(async (taskArgs, hre: HardhatRuntimeEnvironment) => {
    const { ethers } = hre;
    
    const blockHeaderRequester = await ethers.getContractAt(
      "BlockHeaderRequester",
      taskArgs.contract
    );
    
    const isRequested = await blockHeaderRequester.isBlockRequested(
      taskArgs.chainid,
      taskArgs.blocknumber
    );
    
    const requestId = await blockHeaderRequester.getRequestId(
      taskArgs.chainid,
      taskArgs.blocknumber
    );
    
    console.log("\n=== Block Request Status ===");
    console.log("Chain ID:", taskArgs.chainid);
    console.log("Block Number:", taskArgs.blocknumber);
    console.log("Request ID:", requestId);
    console.log("Status:", isRequested ? "✅ Already Requested" : "❌ Not Requested");
    console.log("===========================\n");
  });