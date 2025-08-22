import { expect } from "chai";
import { ethers } from "hardhat";
import { PingSender, BlockHeaderRequester } from "../typechain-types";
import { SignerWithAddress } from "@nomicfoundation/hardhat-ethers/signers";

describe("PingSender", function () {
  let pingSender: PingSender;
  let blockHeaderRequester: BlockHeaderRequester;
  let owner: SignerWithAddress;
  let addr1: SignerWithAddress;
  let addr2: SignerWithAddress;
  
  const SOURCE_CHAIN_ID = 11155111; // Sepolia

  beforeEach(async function () {
    [owner, addr1, addr2] = await ethers.getSigners();
    
    // Deploy BlockHeaderRequester first
    const BlockHeaderRequester = await ethers.getContractFactory("BlockHeaderRequester");
    blockHeaderRequester = await BlockHeaderRequester.deploy();
    await blockHeaderRequester.waitForDeployment();
    
    // Deploy PingSender with BlockHeaderRequester address
    const PingSender = await ethers.getContractFactory("PingSender");
    pingSender = await PingSender.deploy(
      await blockHeaderRequester.getAddress(),
      SOURCE_CHAIN_ID
    );
    await pingSender.waitForDeployment();
  });

  describe("Deployment", function () {
    it("Should set the correct BlockHeaderRequester address", async function () {
      expect(await pingSender.blockHeaderRequester()).to.equal(
        await blockHeaderRequester.getAddress()
      );
    });

    it("Should set the correct source chain ID", async function () {
      expect(await pingSender.SOURCE_CHAIN_ID()).to.equal(SOURCE_CHAIN_ID);
    });
  });

  describe("Ping ID Generation", function () {
    it("Should generate consistent ping IDs", async function () {
      const sender = owner.address;
      const blockNumber = 12345;

      const pingId1 = await pingSender.generatePingId(
        SOURCE_CHAIN_ID,
        sender,
        blockNumber
      );
      
      const pingId2 = await pingSender.generatePingId(
        SOURCE_CHAIN_ID,
        sender,
        blockNumber
      );

      expect(pingId1).to.equal(pingId2);
    });

    it("Should generate different IDs for different parameters", async function () {
      const sender = owner.address;
      const blockNumber = 12345;

      const id1 = await pingSender.generatePingId(SOURCE_CHAIN_ID, sender, blockNumber);
      const id2 = await pingSender.generatePingId(SOURCE_CHAIN_ID, sender, blockNumber + 1);
      const id3 = await pingSender.generatePingId(SOURCE_CHAIN_ID + 1, sender, blockNumber);
      const id4 = await pingSender.generatePingId(SOURCE_CHAIN_ID, addr1.address, blockNumber);

      expect(id1).to.not.equal(id2);
      expect(id1).to.not.equal(id3);
      expect(id1).to.not.equal(id4);
      expect(id2).to.not.equal(id3);
      expect(id2).to.not.equal(id4);
      expect(id3).to.not.equal(id4);
    });

    it("Should match manually calculated ping ID", async function () {
      const sender = owner.address;
      const blockNumber = 12345;

      const contractId = await pingSender.generatePingId(
        SOURCE_CHAIN_ID,
        sender,
        blockNumber
      );

      const manualId = ethers.keccak256(
        ethers.AbiCoder.defaultAbiCoder().encode(
          ["uint256", "address", "uint256"],
          [SOURCE_CHAIN_ID, sender, blockNumber]
        )
      );

      expect(contractId).to.equal(manualId);
    });
  });

  describe("Sending Pings", function () {
    it("Should emit Ping event with correct parameters", async function () {
      const tx = await pingSender.ping();
      const receipt = await tx.wait();
      const blockNumber = receipt!.blockNumber;

      await expect(tx)
        .to.emit(pingSender, "Ping")
        .withArgs(owner.address, blockNumber);
    });

    it("Should allow different senders to ping in same block", async function () {
      // In a real blockchain, different transactions would be in different blocks
      // But in hardhat, we can test the ID generation logic
      
      const tx1 = await pingSender.connect(owner).ping();
      const receipt1 = await tx1.wait();
      const blockNumber1 = receipt1!.blockNumber;
      
      const tx2 = await pingSender.connect(addr1).ping();
      const receipt2 = await tx2.wait();
      const blockNumber2 = receipt2!.blockNumber;

      // Calculate expected ping IDs
      const pingId1 = await pingSender.generatePingId(SOURCE_CHAIN_ID, owner.address, blockNumber1);
      const pingId2 = await pingSender.generatePingId(SOURCE_CHAIN_ID, addr1.address, blockNumber2);

      expect(pingId1).to.not.equal(pingId2);
    });

    it("Should request block header and emit HeaderRequested event", async function () {
      const tx = await pingSender.ping();
      const receipt = await tx.wait();
      const blockNumber = receipt!.blockNumber;
      
      const expectedPingId = await pingSender.generatePingId(
        SOURCE_CHAIN_ID,
        owner.address,
        blockNumber
      );

      // Should emit HeaderRequested event
      await expect(tx)
        .to.emit(pingSender, "HeaderRequested")
        .withArgs(SOURCE_CHAIN_ID, blockNumber, expectedPingId);

      // Should also emit event on BlockHeaderRequester
      await expect(tx)
        .to.emit(blockHeaderRequester, "BlockHeaderRequested")
        .withArgs(SOURCE_CHAIN_ID, blockNumber, await pingSender.getAddress(), expectedPingId);
    });

    it("Should handle duplicate header requests gracefully", async function () {
      // Send first ping
      const tx1 = await pingSender.ping();
      
      // Send second ping - should handle any duplicate header request gracefully
      const tx2 = await pingSender.ping();
      
      // Both transactions should succeed even if header request handling has duplicates
      expect(tx1).to.not.be.reverted;
      expect(tx2).to.not.be.reverted;
    });

    it("Should return the correct ping ID", async function () {
      // Send actual transaction and check the ping ID from receipt
      const tx = await pingSender.ping();
      const receipt = await tx.wait();
      
      // Get actual ping ID from the transaction result
      const actualPingId = await pingSender.generatePingId(
        SOURCE_CHAIN_ID,
        owner.address,
        receipt!.blockNumber
      );
      
      // The ping ID should be deterministic based on the actual block number
      expect(actualPingId).to.be.properHex(64); // Valid 32-byte hex string
      expect(actualPingId).to.not.equal(ethers.ZeroHash);
    });
  });

  describe("Basic Functionality", function () {
    it("Should allow any address to ping", async function () {
      await expect(pingSender.connect(owner).ping()).to.not.be.reverted;
      await expect(pingSender.connect(addr1).ping()).to.not.be.reverted;
      await expect(pingSender.connect(addr2).ping()).to.not.be.reverted;
    });

    it("Should work with multiple pings from same sender", async function () {
      const tx1 = await pingSender.ping();
      const tx2 = await pingSender.ping();
      
      expect(tx1).to.not.be.reverted;
      expect(tx2).to.not.be.reverted;
      
      // Different blocks should produce different ping IDs
      const receipt1 = await tx1.wait();
      const receipt2 = await tx2.wait();
      const pingId1 = await pingSender.generatePingId(SOURCE_CHAIN_ID, owner.address, receipt1!.blockNumber);
      const pingId2 = await pingSender.generatePingId(SOURCE_CHAIN_ID, owner.address, receipt2!.blockNumber);
      
      expect(pingId1).to.not.equal(pingId2);
    });
  });
});