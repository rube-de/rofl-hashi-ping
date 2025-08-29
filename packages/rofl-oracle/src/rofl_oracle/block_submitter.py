#!/usr/bin/env python3
"""Block submission handling for ROFL Oracle.

This module handles the submission of block headers to the ROFLAdapter contract
on Oasis Sapphire, supporting both local (testing) and production (ROFL) modes.
"""

import logging
from typing import Any, TYPE_CHECKING

from web3 import Web3
from web3.types import TxParams, Wei

if TYPE_CHECKING:
    from .utils.contract_utility import ContractUtility
    from .utils.rofl_utility import RoflUtility

logger = logging.getLogger(__name__)


class BlockSubmitter:
    """Handles block header submission to the ROFLAdapter contract."""
    
    def __init__(
        self,
        contract_util: "ContractUtility",
        rofl_util: "RoflUtility | None",
        source_chain_id: int,
        contract_address: str
    ) -> None:
        """
        Initialize the BlockSubmitter.
        
        Args:
            contract_util: Utility for contract interactions
            rofl_util: ROFL utility for transaction submission (None for local mode)
            source_chain_id: Chain ID of the source chain
            contract_address: Address of the ROFLAdapter contract
        """
        self.contract_util = contract_util
        self.rofl_util = rofl_util
        self.source_chain_id = source_chain_id
        self.contract_address = Web3.to_checksum_address(contract_address)
        
        # Load ABI and create contract instance
        self.rofl_adapter_abi = self._load_rofl_adapter_abi()
        self.contract = self.contract_util.w3.eth.contract(
            address=self.contract_address,
            abi=self.rofl_adapter_abi
        )
        
        # Log initialization mode
        mode = "ROFL production" if rofl_util else "local testing"
        logger.info(f"BlockSubmitter initialized in {mode} mode")
        logger.info(f"  Source Chain ID: {source_chain_id}")
        logger.info(f"  ROFLAdapter Address: {contract_address}")
    
    def _load_rofl_adapter_abi(self) -> list[dict[str, Any]]:
        """
        Load the ROFLAdapter ABI.
        
        Returns:
            Minimal ABI for the storeBlockHeader function
        """
        return [
            {
                "inputs": [
                    {"name": "chainId", "type": "uint256"},
                    {"name": "blockNumber", "type": "uint256"},
                    {"name": "blockHash", "type": "bytes32"},
                ],
                "name": "storeBlockHeader",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            }
        ]
    
    async def submit_block_header(self, block_number: int, block_hash: str) -> bool:
        """
        Submit a block header to the ROFLAdapter contract.
        
        This method handles both local mode (direct transaction) and production
        mode (ROFL submission) based on whether rofl_util was provided.
        
        Args:
            block_number: The block number to submit
            block_hash: The block hash (with 0x prefix)
            
        Returns:
            True if submission was successful, False otherwise
        """
        try:
            logger.info(f"Submitting block header for block {block_number}, hash: {block_hash}")
            
            if self.rofl_util:
                # Production mode: submit via ROFL
                # Build transaction for ROFL (ROFL handles nonce, from address, and signing)
                tx_params: TxParams = {
                    'from': '0x0000000000000000000000000000000000000000',  # ROFL will override
                    'gas': 300000,
                    'gasPrice': self.contract_util.w3.eth.gas_price,
                    'value': Wei(0)
                }
                
                tx_data = self.contract.functions.storeBlockHeader(
                    self.source_chain_id,
                    block_number,
                    block_hash
                ).build_transaction(tx_params)
                
                logger.debug(f"Submitting transaction to ROFL with gas={tx_params['gas']}")
                
                # Submit via ROFL utility
                success = await self.rofl_util.submit_tx(tx_data)
                
                if success:
                    logger.info("✓ Block header submitted successfully via ROFL")
                    return True
                else:
                    logger.error("✗ Failed to submit block header via ROFL")
                    return False
                    
            else:
                # Local mode: submit directly using transact()
                logger.info("🔧 LOCAL MODE: Submitting transaction directly")
                
                try:
                    # Use transact() for local mode - this sends a real transaction
                    tx_hash = self.contract.functions.storeBlockHeader(
                        self.source_chain_id,
                        block_number,
                        block_hash
                    ).transact({
                        'gas': 300000,
                        'gasPrice': self.contract_util.w3.eth.gas_price
                    })
                    
                    logger.info(f"✓ Transaction submitted successfully: {Web3.to_hex(tx_hash)}")
                    
                    # Wait for receipt to confirm success
                    receipt = self.contract_util.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
                    
                    if receipt['status'] == 1:
                        logger.info(f"✓ Transaction confirmed in block {receipt['blockNumber']}")
                        return True
                    else:
                        logger.error(f"✗ Transaction failed with status={receipt['status']}")
                        return False
                        
                except Exception as tx_error:
                    logger.error(f"Local transaction failed: {tx_error}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error submitting block header: {e}", exc_info=True)
            return False