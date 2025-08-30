#!/usr/bin/env python3
"""Block submission handling for ROFL Oracle.

This module handles the submission of block headers to the ROFLAdapter contract
on Oasis Sapphire, supporting both local (testing) and production (ROFL) modes.
"""

import logging
from typing import TYPE_CHECKING, Any

from web3 import Web3
from web3.contract import Contract
from web3.types import HexBytes, TxParams, TxReceipt, Wei

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
        self.contract_util: ContractUtility = contract_util
        self.rofl_util: RoflUtility | None = rofl_util
        self.source_chain_id: int = source_chain_id
        self.contract_address: str = Web3.to_checksum_address(contract_address)
        
        self.rofl_adapter_abi: list[dict[str, Any]] = self.contract_util.get_contract_abi("ROFLAdapter")
        self.contract: Contract = self.contract_util.w3.eth.contract(
            address=self.contract_address,
            abi=self.rofl_adapter_abi
        )
        
        # Log initialization mode using walrus operator
        if mode := ("ROFL production" if rofl_util else "local testing"):
            logger.info(f"BlockSubmitter initialized in {mode} mode")
            logger.info(f"  Source Chain ID: {source_chain_id}")
            logger.info(f"  ROFLAdapter Address: {contract_address}")
    
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
            
            # Use pattern matching for mode selection
            match self.rofl_util:
                case None:
                    # Local mode
                    logger.info("🔧 LOCAL MODE: Submitting transaction directly")
                    
                    try:
                        tx_hash: HexBytes = self.contract.functions.storeBlockHeader(
                            self.source_chain_id,
                            block_number,
                            block_hash
                        ).transact({
                            'gas': 300000,
                            'gasPrice': self.contract_util.w3.eth.gas_price
                        })
                        
                        logger.info(f"✓ Transaction submitted successfully: {Web3.to_hex(tx_hash)}")
                        
                        # Wait for receipt to confirm success
                        receipt: TxReceipt = self.contract_util.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
                        
                        # Use walrus operator for status check
                        if (status := receipt.get('status', 0)) == 1:
                            logger.info(f"✓ Transaction confirmed in block {receipt['blockNumber']}")
                            return True
                        else:
                            logger.error(f"✗ Transaction failed with status={status}")
                            return False
                            
                    except Exception as tx_error:
                        logger.error(f"Local transaction failed: {tx_error}")
                        return False
                
                case rofl_util:
                    # Production mode: submit via ROFL
                    tx_params: TxParams = {
                        'from': '0x0000000000000000000000000000000000000000',  # ROFL will override
                        'gas': 300000,
                        'gasPrice': self.contract_util.w3.eth.gas_price,
                        'value': Wei(0)
                    }
                    
                    tx_data: dict[str, Any] = self.contract.functions.storeBlockHeader(
                        self.source_chain_id,
                        block_number,
                        block_hash
                    ).build_transaction(tx_params)
                    
                    logger.debug(f"Submitting transaction to ROFL with gas={tx_params.get('gas')}")
                    
                    # Submit via ROFL utility
                    if await rofl_util.submit_tx(tx_data):
                        logger.info("✓ Block header submitted successfully via ROFL")
                        return True
                    else:
                        logger.error("✗ Failed to submit block header via ROFL")
                        return False
                    
        except Exception as e:
            logger.error(f"Error submitting block header: {e}", exc_info=True)
            return False