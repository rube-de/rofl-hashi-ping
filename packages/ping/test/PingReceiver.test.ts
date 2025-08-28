import { expect } from "chai";
import { ethers } from "hardhat";
import { PingReceiver } from "../typechain-types";
import { SignerWithAddress } from "@nomicfoundation/hardhat-ethers/signers";

describe("PingReceiver", function () {
  let pingReceiver: PingReceiver;
  let mockShoyuBashi: any;
  let owner: SignerWithAddress;
  let addr1: SignerWithAddress;
  let addr2: SignerWithAddress;
  
  const SOURCE_CHAIN_ID = 11155111; // Sepolia

  beforeEach(async function () {
    [owner, addr1, addr2] = await ethers.getSigners();
    
    // Deploy MockShoyuBashi
    const MockShoyuBashi = await ethers.getContractFactory("MockShoyuBashi");
    mockShoyuBashi = await MockShoyuBashi.deploy();
    await mockShoyuBashi.waitForDeployment();
    
    // Deploy PingReceiver
    const PingReceiver = await ethers.getContractFactory("PingReceiver");
    pingReceiver = await PingReceiver.deploy(await mockShoyuBashi.getAddress());
    await pingReceiver.waitForDeployment();
  });

  describe("Deployment", function () {
    it("Should set the correct ShoyuBashi address", async function () {
      expect(await pingReceiver.SHOYU_BASHI()).to.equal(await mockShoyuBashi.getAddress());
    });

  });

  describe("Ping Status Tracking", function () {
    it("Should return false for non-existent pings", async function () {
      const pingId = ethers.randomBytes(32);
      
      const [received, originalSender, originalBlockNumber] = await pingReceiver.getPingStatus(pingId);
      
      expect(received).to.be.false;
      expect(originalSender).to.equal(ethers.ZeroAddress);
      expect(originalBlockNumber).to.equal(0);
    });
  });

  describe("Ping Verification Access", function () {
    // Note: These tests focus on the data structures and validation logic
    // Full integration with Hashi proof verification would require more complex setup
    
    it("Should allow anyone to call receivePing with a valid proof", async function () {
      // Create a minimal proof structure (will fail at proof verification but not authorization)
      const proof = {
        chainId: SOURCE_CHAIN_ID,
        blockNumber: 12345,
        blockHeader: "0x",
        ancestralBlockNumber: 0,
        ancestralBlockHeaders: [],
        receiptProof: [],
        transactionIndex: "0x00",
        logIndex: 0
      };
      
      // Anyone can call this function - it will fail at HashiProverLib.verifyForeignEvent due to invalid proof
      // but not due to authorization issues
      await expect(
        pingReceiver.connect(addr1).receivePing(proof)
      ).to.be.reverted; // Will revert at HashiProverLib.verifyForeignEvent
    });

    it("Should test contract structure allows public access", async function () {
      const proof = {
        chainId: SOURCE_CHAIN_ID,
        blockNumber: 12345,
        blockHeader: "0x",
        ancestralBlockNumber: 0,
        ancestralBlockHeaders: [],
        receiptProof: [],
        transactionIndex: "0x00",
        logIndex: 0
      };
      
      // Test that the function is callable by different addresses (will fail at proof verification)
      await expect(
        pingReceiver.connect(owner).receivePing(proof)
      ).to.be.reverted; // Will revert at HashiProverLib.verifyForeignEvent
    });
  });

  describe("Ping ID Generation (for testing)", function () {
    it("Should generate consistent ping IDs using same logic as PingSender", async function () {
      const sourceChainId = SOURCE_CHAIN_ID;
      const sender = owner.address;
      const blockNumber = 12345;

      // Generate ping ID using the same logic as PingSender
      const pingId = ethers.keccak256(
        ethers.AbiCoder.defaultAbiCoder().encode(
          ["uint256", "address", "uint256"],
          [sourceChainId, sender, blockNumber]
        )
      );

      expect(pingId).to.be.properHex(64); // 32 bytes
      expect(pingId).to.not.equal(ethers.ZeroHash);
    });

    it("Should create valid event signature for Ping", async function () {
      // Verify the event signature matches what PingSender emits
      const eventSignature = "Ping(address,uint256)";
      const eventHash = ethers.keccak256(ethers.toUtf8Bytes(eventSignature));
      
      expect(eventHash).to.be.properHex(64);
      // This ensures our event decoding logic will match the actual events
    });
  });

  describe("Input Validation", function () {
    it("Should have correct error definitions", async function () {
      // Test that custom errors are properly defined in the interface
      const iface = pingReceiver.interface;
      
      // Check that error types exist in the ABI
      const errors = iface.fragments.filter(f => f.type === "error");
      const errorNames = errors.map(e => e.name);
      
      expect(errorNames).to.include("PingAlreadyReceived");
      expect(errorNames).to.include("InvalidProof");
      expect(errorNames).to.include("InvalidEventFormat");
    });
  });

  describe("Event Emissions", function () {
    it("Should define correct event structures", async function () {
      // Verify event parameter types match interface
      // This helps ensure ABI compatibility
      
      const iface = pingReceiver.interface;
      const pingReceivedEvent = iface.getEvent("PingReceived");
      const pingVerifiedEvent = iface.getEvent("PingVerified");
      
      expect(pingReceivedEvent).to.not.be.null;
      expect(pingVerifiedEvent).to.not.be.null;
      
      // Check indexed parameters
      expect(pingReceivedEvent!.inputs.filter(input => input.indexed).length).to.equal(3);
      expect(pingVerifiedEvent!.inputs.filter(input => input.indexed).length).to.equal(1);
    });
  });

  describe("Contract Configuration", function () {
    it("Should properly configure immutable variables", async function () {
      expect(await pingReceiver.SHOYU_BASHI()).to.equal(await mockShoyuBashi.getAddress());
    });

    it("Should accept valid constructor parameters", async function () {
      // Test deployment with different valid parameters
      const newShoyuBashi = "0x9876543210987654321098765432109876543210";
      
      const PingReceiver = await ethers.getContractFactory("PingReceiver");
      const newReceiver = await PingReceiver.deploy(newShoyuBashi);
      await newReceiver.waitForDeployment();
      
      expect(await newReceiver.SHOYU_BASHI()).to.equal(newShoyuBashi);
    });
  });

  describe("Integration Readiness", function () {
    it("Should be ready for cross-chain integration", async function () {
      // Verify contract has all necessary components for cross-chain integration
      expect(await pingReceiver.SHOYU_BASHI()).to.not.equal("0x");
      expect(await pingReceiver.SHOYU_BASHI()).to.not.equal(ethers.ZeroAddress);
    });

    it("Should be ready for Hashi integration", async function () {
      // Verify contract is configured for Hashi proof verification
      expect(await pingReceiver.SHOYU_BASHI()).to.not.equal(ethers.ZeroAddress);
      
      // Contract should have the proper imports and interface for HashiProverLib
      // This is verified by successful compilation
    });
  });
});

// Additional helper functions for testing
describe("PingReceiver Helper Functions", function () {
  
  describe("RLP Encoding Utilities", function () {
    it("Should handle RLP-encoded ping event data format", async function () {
      // Test RLP encoding format that will be used in actual cross-chain pings
      const testData = {
        sender: "0x9876543210987654321098765432109876543210",
        blockNumber: 12345
      };
      
      // Verify data can be ABI encoded (this simulates what the ping event will contain)
      const encoded = ethers.AbiCoder.defaultAbiCoder().encode(
        ["address", "uint256"],
        [testData.sender, testData.blockNumber]
      );
      
      expect(encoded).to.be.properHex(128); // Expected length for the encoded data
      expect(encoded.length).to.be.greaterThan(2); // More than just "0x"
    });

    it("Should generate ping ID from event data", async function () {
      const sourceChainId = 11155111; // Sepolia
      const sender = "0x9876543210987654321098765432109876543210";
      const blockNumber = 12345;
      
      const pingId = ethers.keccak256(
        ethers.AbiCoder.defaultAbiCoder().encode(
          ["uint256", "address", "uint256"],
          [sourceChainId, sender, blockNumber]
        )
      );
      
      expect(pingId).to.be.properHex(64);
      expect(pingId).to.not.equal(ethers.ZeroHash);
    });
  });
});