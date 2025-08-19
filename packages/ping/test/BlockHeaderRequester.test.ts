import { expect } from "chai";
import { ethers } from "hardhat";
import { BlockHeaderRequester } from "../typechain-types";
import { SignerWithAddress } from "@nomicfoundation/hardhat-ethers/signers";

describe("BlockHeaderRequester", function () {
  let blockHeaderRequester: BlockHeaderRequester;
  let owner: SignerWithAddress;
  let addr1: SignerWithAddress;
  let addr2: SignerWithAddress;

  beforeEach(async function () {
    [owner, addr1, addr2] = await ethers.getSigners();
    
    const BlockHeaderRequester = await ethers.getContractFactory("BlockHeaderRequester");
    blockHeaderRequester = await BlockHeaderRequester.deploy();
    await blockHeaderRequester.waitForDeployment();
  });

  describe("Requesting Block Headers", function () {
    it("Should emit BlockHeaderRequested event", async function () {
      const chainId = 11155111; // Sepolia chain ID
      const blockNumber = 12345;
      const context = ethers.encodeBytes32String("test-context");

      await expect(blockHeaderRequester.requestBlockHeader(chainId, blockNumber, context))
        .to.emit(blockHeaderRequester, "BlockHeaderRequested")
        .withArgs(chainId, blockNumber, owner.address, context);
    });

    it("Should allow any address to request blocks (MVP - no restrictions)", async function () {
      const chainId = 11155111;
      const blockNumber = 12345;
      const context = ethers.encodeBytes32String("test");

      // Request from addr1
      await expect(
        blockHeaderRequester.connect(addr1).requestBlockHeader(chainId, blockNumber, context)
      ).to.emit(blockHeaderRequester, "BlockHeaderRequested");
    });

    it("Should prevent duplicate block requests", async function () {
      const chainId = 11155111;
      const blockNumber = 12345;
      const context = ethers.encodeBytes32String("test");

      // First request should succeed
      await blockHeaderRequester.requestBlockHeader(chainId, blockNumber, context);

      // Second request for same block should fail
      await expect(
        blockHeaderRequester.requestBlockHeader(chainId, blockNumber, context)
      ).to.be.revertedWith("Block already requested");
    });

    it("Should allow same block number on different chains", async function () {
      const blockNumber = 12345;
      const context = ethers.encodeBytes32String("test");

      // Request block 12345 on chain 1
      await expect(
        blockHeaderRequester.requestBlockHeader(1, blockNumber, context)
      ).to.emit(blockHeaderRequester, "BlockHeaderRequested");

      // Request same block number on chain 11155111 should succeed
      await expect(
        blockHeaderRequester.requestBlockHeader(11155111, blockNumber, context)
      ).to.emit(blockHeaderRequester, "BlockHeaderRequested");
    });
  });

  describe("Checking Request Status", function () {
    it("Should correctly report if block was requested", async function () {
      const chainId = 11155111;
      const blockNumber = 12345;
      const context = ethers.encodeBytes32String("test");

      // Initially should be false
      expect(await blockHeaderRequester.isBlockRequested(chainId, blockNumber)).to.be.false;

      // Request the block
      await blockHeaderRequester.requestBlockHeader(chainId, blockNumber, context);

      // Now should be true
      expect(await blockHeaderRequester.isBlockRequested(chainId, blockNumber)).to.be.true;
    });

    it("Should track different blocks independently", async function () {
      const chainId = 11155111;
      const context = ethers.encodeBytes32String("test");

      // Request block 100
      await blockHeaderRequester.requestBlockHeader(chainId, 100, context);

      // Check status
      expect(await blockHeaderRequester.isBlockRequested(chainId, 100)).to.be.true;
      expect(await blockHeaderRequester.isBlockRequested(chainId, 101)).to.be.false;
      expect(await blockHeaderRequester.isBlockRequested(chainId, 99)).to.be.false;
    });
  });

  describe("Request ID Generation", function () {
    it("Should generate consistent request IDs", async function () {
      const chainId = 11155111;
      const blockNumber = 12345;

      const requestId1 = await blockHeaderRequester.getRequestId(chainId, blockNumber);
      const requestId2 = await blockHeaderRequester.getRequestId(chainId, blockNumber);

      expect(requestId1).to.equal(requestId2);
    });

    it("Should generate different IDs for different parameters", async function () {
      const requestId1 = await blockHeaderRequester.getRequestId(1, 100);
      const requestId2 = await blockHeaderRequester.getRequestId(1, 101);
      const requestId3 = await blockHeaderRequester.getRequestId(2, 100);

      expect(requestId1).to.not.equal(requestId2);
      expect(requestId1).to.not.equal(requestId3);
      expect(requestId2).to.not.equal(requestId3);
    });
  });
});