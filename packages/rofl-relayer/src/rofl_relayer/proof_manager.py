"""
Proof generation manager for ROFL Relayer.

This module handles the generation and submission of cryptographic proofs
for cross-chain message verification using the Hashi protocol format.
"""

import logging
from typing import Any

import rlp
from trie import HexaryTrie
from hexbytes import HexBytes
from web3 import Web3
from web3.types import BlockData, TxReceipt

logger = logging.getLogger(__name__)


class ProofManager:
    """Handles proof generation and submission for cross-chain messages."""
    
    def __init__(self, web3_source: Web3, contract_util: Any, rofl_util: Any | None = None):
        """
        Initialize the ProofManager.
        
        Args:
            web3_source: Web3 instance for the source chain
            contract_util: Utility for contract interactions
            rofl_util: ROFL utility for transaction submission (optional)
        """
        self.web3 = web3_source
        self.contract_util = contract_util
        self.rofl_util = rofl_util
        
    async def generate_proof(self, tx_hash: str, log_index: int = 0) -> list[Any]:
        """
        Generate Hashi-format proof for a transaction.
        
        Args:
            tx_hash: Transaction hash containing the event
            log_index: Index of the log in the transaction receipt
            
        Returns:
            8-element array matching TypeScript format for Hashi proof
            
        Raises:
            ValueError: If receipt or block not found, or proof generation fails
        """
        logger.info(f"Generating proof for tx {tx_hash}, log index {log_index}")
        
        # 1. Fetch receipt and block
        receipt = self.web3.eth.get_transaction_receipt(tx_hash)
        if not receipt:
            raise ValueError(f"Transaction receipt not found for {tx_hash}")
            
        block_number = receipt['blockNumber']
        block = self.web3.eth.get_block(block_number, full_transactions=True)
        if not block:
            raise ValueError(f"Block not found for block number {block_number}")
            
        logger.info(f"Processing block {block_number}, tx index {receipt['transactionIndex']}")
        
        # 2. Get all receipts in block
        receipts = []
        for tx in block['transactions']:
            tx_hash_str = tx['hash'].hex() if hasattr(tx['hash'], 'hex') else tx['hash']
            tx_receipt = self.web3.eth.get_transaction_receipt(tx_hash_str)
            receipts.append(tx_receipt)
            
        logger.info(f"Fetched {len(receipts)} receipts from block")
        
        # 3. RLP encode all receipts and build trie
        trie = HexaryTrie({})
        
        for _idx, rec in enumerate(receipts):
            # RLP encode transaction index as trie key (index 0 encodes to empty bytes per Ethereum spec)
            tx_index = rec['transactionIndex']
            key = rlp.encode(b'') if tx_index == 0 else rlp.encode(tx_index)
            
            # Encode the receipt
            encoded_receipt = self._encode_receipt(rec)
            
            # Put in trie
            trie[key] = encoded_receipt
            
        # 4. Verify trie root matches block's receiptsRoot
        calculated_root = Web3.to_hex(trie.root_hash)
        block_receipts_root = Web3.to_hex(block['receiptsRoot'])
        
        if calculated_root != block_receipts_root:
            raise ValueError(f"Trie root mismatch! Calculated: {calculated_root}, Block: {block_receipts_root}")
            
        # 5. Generate proof for target receipt
        # RLP encode transaction index (index 0 encodes to empty bytes per Ethereum spec)
        tx_index = receipt['transactionIndex']
        receipt_key = rlp.encode(b'') if tx_index == 0 else rlp.encode(tx_index)
        proof_nodes = trie.get_proof(receipt_key)
        
        # Convert proof nodes to hex strings
        merkle_proof = [Web3.to_hex(rlp.encode(node)) for node in proof_nodes]
        
        # 6. Encode block header
        encoded_block_header = self._encode_block_header(block)
        
        # 7. Get chain ID
        chain_id = int(self.web3.eth.chain_id)
        
        # 8. Create proof structure for Hashi
        proof = [
            chain_id,                                    # chainId
            block_number,                                # blockNumber  
            encoded_block_header,                        # encodedBlockHeader
            0,                                           # ancestralBlockNumber (not used in MVP)
            [],                                          # ancestralBlockHeaders (not used in MVP)
            merkle_proof,                                # merkleProof
            Web3.to_hex(receipt_key),                   # transactionIndex (RLP encoded)
            log_index                                    # logIndex
        ]
        
        logger.info(f"Proof generated successfully with {len(merkle_proof)} merkle nodes")
        return proof
        
    async def submit_proof(self, proof: list[Any], receiver_address: str) -> str:
        """
        Submit proof to PingReceiver contract.
        
        Args:
            proof: The generated proof array
            receiver_address: Address of the PingReceiver contract
            
        Returns:
            Transaction hash of the submission
        """
        logger.info(f"Submitting proof to PingReceiver at {receiver_address}")
        
        # Get the contract instance
        abi = self.contract_util.get_contract_abi("PingReceiver")
        contract = self.contract_util.w3.eth.contract(
            address=Web3.to_checksum_address(receiver_address),
            abi=abi
        )
        
        if self.rofl_util:
            # ROFL mode: build transaction for rofl_util
            tx_data = contract.functions.receivePing(proof).build_transaction({
                'from': '0x0000000000000000000000000000000000000000',  # ROFL will override
                'gas': 3000000,
                'gasPrice': self.contract_util.w3.eth.gas_price,
                'value': 0
            })
            tx_hash = await self.rofl_util.submit_tx(tx_data)
            logger.info(f"Proof submitted via ROFL: {tx_hash}")
            return tx_hash
        else:
            # Local mode: use transact() directly 
            tx_hash = contract.functions.receivePing(proof).transact({
                'gas': 3000000,
                'gasPrice': self.contract_util.w3.eth.gas_price
            })
            logger.info(f"Proof submitted locally: {Web3.to_hex(tx_hash)}")
            return Web3.to_hex(tx_hash)
            
    async def process_ping_event(self, ping_event: Any, receiver_address: str) -> str:
        """
        Complete flow: generate and submit proof for a ping event.
        
        Args:
            ping_event: The PingEvent object containing tx_hash and log_index
            receiver_address: Address of the PingReceiver contract
            
        Returns:
            Transaction hash of the proof submission
        """
        proof = await self.generate_proof(ping_event.tx_hash, ping_event.log_index)
        return await self.submit_proof(proof, receiver_address)
        
    # Private helper methods
        
    def _to_bytes_safe(self, value) -> bytes:
        """
        Safely convert value to bytes, handling HexBytes, bytes, and hex strings.
        
        Args:
            value: Value to convert (HexBytes, bytes, or hex string)
            
        Returns:
            Bytes representation
        """
        if isinstance(value, HexBytes):
            return bytes(value)
        elif isinstance(value, bytes):
            return value
        else:
            return Web3.to_bytes(hexstr=value)
    
    def _encode_receipt(self, receipt: TxReceipt) -> bytes:
        """
        RLP encode a single receipt with transaction type handling.
        
        Args:
            receipt: Transaction receipt to encode
            
        Returns:
            RLP encoded receipt with type prefix if needed
        """
        # Get transaction type (0 for legacy, 2 for EIP-1559)
        tx_type = int(receipt.get('type', 0))
        
        # Encode receipt fields
        status = b'\x01' if receipt['status'] == 1 else b''
        cumulative_gas = receipt['cumulativeGasUsed']
        logs_bloom = receipt['logsBloom']
        
        # Encode logs (handling both HexBytes and hex strings)
        encoded_logs = []
        for log in receipt['logs']:
            encoded_log = [
                self._to_bytes_safe(log['address']),
                [self._to_bytes_safe(topic) for topic in log['topics']],
                self._to_bytes_safe(log['data'])
            ]
            encoded_logs.append(encoded_log)
            
        # Create receipt tuple
        receipt_data = [status, cumulative_gas, logs_bloom, encoded_logs]
        encoded = rlp.encode(receipt_data)
        
        # Add transaction type prefix if not legacy (type 0)
        if tx_type == 0:
            return encoded
        else:
            # For typed transactions, prepend the type byte
            return bytes([tx_type]) + encoded
            
    def _encode_block_header(self, block: BlockData) -> str:
        """
        Serialize block header to match Ethereum block encoding.
        Note: web3.py doesn't provide a built-in method for this.
        
        Args:
            block: Block data from Web3
            
        Returns:
            Hex string of serialized block header
        """
        # Convert block fields to bytes for RLP encoding (handling HexBytes)
        header_fields = [
            self._to_bytes_safe(block['parentHash']),
            self._to_bytes_safe(block['sha3Uncles']),
            self._to_bytes_safe(block['miner']),
            self._to_bytes_safe(block['stateRoot']),
            self._to_bytes_safe(block['transactionsRoot']),
            self._to_bytes_safe(block['receiptsRoot']),
            self._to_bytes_safe(block['logsBloom']),
            block['difficulty'],
            block['number'],
            block['gasLimit'],
            block['gasUsed'],
            block['timestamp'],
            self._to_bytes_safe(block['extraData']),
            self._to_bytes_safe(block['mixHash']),
            self._to_bytes_safe(block['nonce']),
        ]
        
        # Add baseFeePerGas if present (post-London)
        if 'baseFeePerGas' in block and block['baseFeePerGas'] is not None:
            header_fields.append(block['baseFeePerGas'])
            
        # Add withdrawalsRoot if present (post-Shanghai)  
        if 'withdrawalsRoot' in block and block['withdrawalsRoot'] is not None:
            header_fields.append(self._to_bytes_safe(block['withdrawalsRoot']))
            
        # Add additional post-Shanghai fields if present
        if 'blobGasUsed' in block and block['blobGasUsed'] is not None:
            header_fields.append(block['blobGasUsed'])
            
        if 'excessBlobGas' in block and block['excessBlobGas'] is not None:
            header_fields.append(block['excessBlobGas'])
            
        if 'parentBeaconBlockRoot' in block and block['parentBeaconBlockRoot'] is not None:
            header_fields.append(self._to_bytes_safe(block['parentBeaconBlockRoot']))
            
        # RLP encode the header
        encoded = rlp.encode(header_fields)
        
        # Verify hash matches
        calculated_hash = Web3.keccak(encoded)
        block_hash_bytes = self._to_bytes_safe(block['hash'])
        
        if calculated_hash != block_hash_bytes:
            logger.warning("Header hash mismatch. This may be due to network-specific encoding.")
            
        return Web3.to_hex(encoded)