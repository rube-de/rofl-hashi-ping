import { expect } from "chai";
import { ethers } from "hardhat";
import { PingSender, PingReceiver, BlockHeaderRequester } from "../typechain-types";
import { SignerWithAddress } from "@nomicfoundation/hardhat-ethers/signers";

describe("Simple Ping Cross-Chain Integration", function () {
  let pingSender: PingSender;
  let pingReceiver: PingReceiver;
  let blockHeaderRequester: BlockHeaderRequester;
  let owner: SignerWithAddress;
  let addr1: SignerWithAddress;
  let relayer: SignerWithAddress;
  
  const SOURCE_CHAIN_ID = 11155111; // Sepolia
  const SHOYU_BASHI_ADDRESS = "0x1234567890123456789012345678901234567890";

  beforeEach(async function () {
    [owner, addr1, relayer] = await ethers.getSigners();
    
    // Deploy BlockHeaderRequester
    const BlockHeaderRequester = await ethers.getContractFactory("BlockHeaderRequester");
    blockHeaderRequester = await BlockHeaderRequester.deploy();
    await blockHeaderRequester.waitForDeployment();
    
    // Deploy PingSender (source chain)
    const PingSender = await ethers.getContractFactory("PingSender");
    pingSender = await PingSender.deploy(
      await blockHeaderRequester.getAddress(),
      SOURCE_CHAIN_ID
    );
    await pingSender.waitForDeployment();
    
    // Deploy PingReceiver (target chain)
    const PingReceiver = await ethers.getContractFactory("PingReceiver");
    pingReceiver = await PingReceiver.deploy(SHOYU_BASHI_ADDRESS);
    await pingReceiver.waitForDeployment();
  });

  describe("Ping Flow Simulation", function () {
    it("Should create consistent ping IDs across sender and receiver", async function () {
      const sender = owner.address;
      const blockNumber = 12345;
      
      // Generate ping ID using PingSender logic
      const senderPingId = await pingSender.generatePingId(
        SOURCE_CHAIN_ID,
        sender,
        blockNumber
      );
      
      // Generate the same ping ID manually using identical logic
      const manualPingId = ethers.keccak256(
        ethers.AbiCoder.defaultAbiCoder().encode(
          ["uint256", "address", "uint256"],
          [SOURCE_CHAIN_ID, sender, blockNumber]
        )
      );
      
      expect(senderPingId).to.equal(manualPingId);
      
      // Verify the ping hasn't been received on receiver side
      const [received, originalSender, originalBlockNumber] = await pingReceiver.getPingStatus(senderPingId);
      expect(received).to.be.false;
      expect(originalSender).to.equal(ethers.ZeroAddress);
      expect(originalBlockNumber).to.equal(0);
    });

    it("Should emit events in correct sequence for ping sending", async function () {
      const tx = await pingSender.ping();
      const receipt = await tx.wait();
      const blockNumber = receipt!.blockNumber;
      
      const expectedPingId = await pingSender.generatePingId(
        SOURCE_CHAIN_ID,
        owner.address,
        blockNumber
      );
      
      // Verify Ping event
      await expect(tx)
        .to.emit(pingSender, "Ping")
        .withArgs(owner.address, blockNumber);
      
      // Verify HeaderRequested event
      await expect(tx)
        .to.emit(pingSender, "HeaderRequested")
        .withArgs(SOURCE_CHAIN_ID, blockNumber, expectedPingId);
      
      // Verify BlockHeaderRequested event on BlockHeaderRequester
      await expect(tx)
        .to.emit(blockHeaderRequester, "BlockHeaderRequested")
        .withArgs(
          SOURCE_CHAIN_ID,
          blockNumber,
          await pingSender.getAddress(),
          expectedPingId
        );
    });

    it("Should handle multiple pings from same sender", async function () {
      // Send three pings
      const tx1 = await pingSender.ping();
      const tx2 = await pingSender.ping();
      const tx3 = await pingSender.ping();
      
      const receipt1 = await tx1.wait();
      const receipt2 = await tx2.wait();
      const receipt3 = await tx3.wait();
      
      // Generate expected ping IDs
      const pingId1 = await pingSender.generatePingId(
        SOURCE_CHAIN_ID,
        owner.address,
        receipt1!.blockNumber
      );
      
      const pingId2 = await pingSender.generatePingId(
        SOURCE_CHAIN_ID,
        owner.address,
        receipt2!.blockNumber
      );
      
      const pingId3 = await pingSender.generatePingId(
        SOURCE_CHAIN_ID,
        owner.address,
        receipt3!.blockNumber
      );
      
      // All ping IDs should be different (different block numbers)
      expect(pingId1).to.not.equal(pingId2);
      expect(pingId2).to.not.equal(pingId3);
      expect(pingId1).to.not.equal(pingId3);
      
      // All pings should be unprocessed on receiver side
      const [received1] = await pingReceiver.getPingStatus(pingId1);
      const [received2] = await pingReceiver.getPingStatus(pingId2);
      const [received3] = await pingReceiver.getPingStatus(pingId3);
      
      expect(received1).to.be.false;
      expect(received2).to.be.false;
      expect(received3).to.be.false;
    });

    it("Should handle pings from different senders", async function () {
      // Send from owner
      const tx1 = await pingSender.connect(owner).ping();
      const receipt1 = await tx1.wait();
      
      // Send from addr1  
      const tx2 = await pingSender.connect(addr1).ping();
      const receipt2 = await tx2.wait();
      
      // Generate expected ping IDs
      const pingIdFromOwner = await pingSender.generatePingId(
        SOURCE_CHAIN_ID,
        owner.address,
        receipt1!.blockNumber
      );
      
      const pingIdFromAddr1 = await pingSender.generatePingId(
        SOURCE_CHAIN_ID,
        addr1.address,
        receipt2!.blockNumber
      );
      
      // Ping IDs should be different (different senders)
      expect(pingIdFromOwner).to.not.equal(pingIdFromAddr1);
    });
  });

  describe("Event Data Verification", function () {
    it("Should create verifiable event data for ROFL processing", async function () {
      const tx = await pingSender.ping();
      const receipt = await tx.wait();
      
      // Find the Ping event
      const event = receipt!.logs.find((log: any) => {
        try {
          return pingSender.interface.parseLog(log)?.name === "Ping";
        } catch {
          return false;
        }
      });
      
      expect(event).to.not.be.undefined;
      
      if (event) {
        const parsedEvent = pingSender.interface.parseLog(event);
        
        // Verify event has all required fields for ROFL processing
        expect(parsedEvent!.args.sender).to.equal(owner.address);
        expect(parsedEvent!.args.blockNumber).to.equal(receipt!.blockNumber);
        
        // Verify ping ID can be reconstructed
        const reconstructedId = ethers.keccak256(
          ethers.AbiCoder.defaultAbiCoder().encode(
            ["uint256", "address", "uint256"],
            [SOURCE_CHAIN_ID, owner.address, receipt!.blockNumber]
          )
        );
        
        const expectedId = await pingSender.generatePingId(
          SOURCE_CHAIN_ID,
          owner.address,
          receipt!.blockNumber
        );
        
        expect(reconstructedId).to.equal(expectedId);
      }
    });

    it("Should create events compatible with Merkle proof generation", async function () {
      const tx = await pingSender.ping();
      const receipt = await tx.wait();
      
      // Verify transaction receipt contains the log
      expect(receipt!.logs.length).to.be.greaterThan(0);
      
      // Verify log has proper structure for Merkle proof generation
      const pingLog = receipt!.logs.find((log: any) => {
        try {
          const parsed = pingSender.interface.parseLog(log);
          return parsed?.name === "Ping";
        } catch {
          return false;
        }
      });
      
      expect(pingLog).to.not.be.undefined;
      
      if (pingLog) {
        // Verify log has address (contract that emitted it)
        expect(pingLog.address).to.equal(await pingSender.getAddress());
        
        // Verify log has topics (indexed parameters)
        expect(pingLog.topics.length).to.equal(3); // event sig + 2 indexed params
        
        // Verify minimal data structure (everything is indexed for simplicity)
        expect(pingLog.data).to.equal("0x"); // No non-indexed data
      }
    });
  });

  describe("Header Request Integration", function () {
    it("Should properly coordinate header requests with ping sending", async function () {
      const tx = await pingSender.ping();
      const receipt = await tx.wait();
      const blockNumber = receipt!.blockNumber;
      
      // Verify the block was marked as requested in BlockHeaderRequester
      const isRequested = await blockHeaderRequester.isBlockRequested(SOURCE_CHAIN_ID, blockNumber);
      expect(isRequested).to.be.true;
      
      // Verify request ID can be generated consistently
      const requestId = await blockHeaderRequester.getRequestId(SOURCE_CHAIN_ID, blockNumber);
      const manualRequestId = ethers.keccak256(
        ethers.AbiCoder.defaultAbiCoder().encode(
          ["uint256", "uint256"],
          [SOURCE_CHAIN_ID, blockNumber]
        )
      );
      
      expect(requestId).to.equal(manualRequestId);
    });

    it("Should handle multiple pings in same block gracefully", async function () {
      // In Hardhat, transactions will be in different blocks
      // But this tests the duplicate header request handling
      const tx1 = await pingSender.ping();
      const tx2 = await pingSender.ping();
      
      const receipt1 = await tx1.wait();
      const receipt2 = await tx2.wait();
      
      // Both should succeed despite potential duplicate header requests
      expect(receipt1!.status).to.equal(1); // success
      expect(receipt2!.status).to.equal(1); // success
      
      // Verify both pings have different IDs
      const pingId1 = await pingSender.generatePingId(
        SOURCE_CHAIN_ID,
        owner.address,
        receipt1!.blockNumber
      );
      
      const pingId2 = await pingSender.generatePingId(
        SOURCE_CHAIN_ID,
        owner.address,
        receipt2!.blockNumber
      );
      
      expect(pingId1).to.not.equal(pingId2);
    });
  });

  describe("Cross-Chain Ping Lifecycle", function () {
    it("Should simulate complete ping lifecycle", async function () {
      // Step 1: Send ping on source chain
      const sendTx = await pingSender.ping();
      const sendReceipt = await sendTx.wait();
      
      // Step 2: Extract ping details
      const pingEvent = sendReceipt!.logs.find((log: any) => {
        try {
          return pingSender.interface.parseLog(log)?.name === "Ping";
        } catch {
          return false;
        }
      });
      
      expect(pingEvent).to.not.be.undefined;
      
      const parsedEvent = pingSender.interface.parseLog(pingEvent!);
      const pingId = await pingSender.generatePingId(
        SOURCE_CHAIN_ID,
        parsedEvent!.args.sender,
        parsedEvent!.args.blockNumber
      );
      
      // Step 3: Verify header was requested
      const headerEvent = sendReceipt!.logs.find((log: any) => {
        try {
          return pingSender.interface.parseLog(log)?.name === "HeaderRequested";
        } catch {
          return false;
        }
      });
      
      expect(headerEvent).to.not.be.undefined;
      
      // Step 4: Verify ping not yet received on receiver
      const [initialReceived] = await pingReceiver.getPingStatus(pingId);
      expect(initialReceived).to.be.false;
      
      // Step 5: Simulate ROFL processing (would happen off-chain)
      // In real scenario, ROFL would:
      // - Detect the Ping event
      // - Wait for block header to be available
      // - Generate Merkle proof
      // - Call receivePing with proof
      
      // This completes the testable portion of the lifecycle
      // The actual proof verification would require Hashi infrastructure
      
      console.log(`    ✓ Ping ${pingId} ready for ROFL processing`);
      console.log(`    ✓ Block ${sendReceipt!.blockNumber} header requested`);
      console.log(`    ✓ Event data prepared for Merkle proof generation`);
    });
  });
});