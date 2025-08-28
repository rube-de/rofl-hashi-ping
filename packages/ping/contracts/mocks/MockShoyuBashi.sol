// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/**
 * @title MockShoyuBashi  
 * @notice Minimal mock for testing PingReceiver with HashiProverLib
 * @dev Only implements getThresholdHash which is what HashiProverLib needs
 */
contract MockShoyuBashi {
    
    // Mapping: chainId => blockNumber => blockHeaderHash
    mapping(uint256 => mapping(uint256 => bytes32)) private thresholdHashes;
    
    /**
     * @notice Set a threshold hash for testing
     * @param chainId Chain ID  
     * @param blockNumber Block number
     * @param blockHeaderHash Block header hash
     */
    function setThresholdHash(uint256 chainId, uint256 blockNumber, bytes32 blockHeaderHash) external {
        thresholdHashes[chainId][blockNumber] = blockHeaderHash;
    }
    
    /**
     * @notice Get threshold hash (matches IShoyuBashi interface)
     * @param domain Chain ID
     * @param id Block number
     * @return Block header hash
     */
    function getThresholdHash(uint256 domain, uint256 id) external view returns (bytes32) {
        bytes32 hash = thresholdHashes[domain][id];
        require(hash != bytes32(0), "MockShoyuBashi: hash not set");
        return hash;
    }
}