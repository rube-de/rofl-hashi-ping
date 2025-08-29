#!/usr/bin/env python3
"""Unit tests for BlockSubmitter module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from web3 import Web3
from web3.types import TxParams, Wei

from src.rofl_oracle.block_submitter import BlockSubmitter


@pytest.fixture
def mock_contract_util():
    """Create a mock ContractUtility instance."""
    mock = MagicMock()
    mock.w3 = MagicMock()
    mock.w3.eth.gas_price = Wei(1000000000)  # 1 gwei
    mock.w3.eth.wait_for_transaction_receipt = MagicMock()
    return mock


@pytest.fixture
def mock_rofl_util():
    """Create a mock RoflUtility instance."""
    mock = AsyncMock()
    mock.submit_tx = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_contract():
    """Create a mock contract instance."""
    mock = MagicMock()
    mock.functions.storeBlockHeader = MagicMock()
    return mock


class TestBlockSubmitter:
    """Test suite for BlockSubmitter class."""
    
    def test_init_with_rofl_util(self, mock_contract_util, mock_rofl_util):
        """Test initialization with ROFL utility (production mode)."""
        source_chain_id = 1
        contract_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb7"
        
        with patch.object(BlockSubmitter, '_load_rofl_adapter_abi', return_value=[]):
            submitter = BlockSubmitter(
                contract_util=mock_contract_util,
                rofl_util=mock_rofl_util,
                source_chain_id=source_chain_id,
                contract_address=contract_address
            )
            
            assert submitter.contract_util == mock_contract_util
            assert submitter.rofl_util == mock_rofl_util
            assert submitter.source_chain_id == source_chain_id
            assert submitter.contract_address == Web3.to_checksum_address(contract_address)
    
    def test_init_without_rofl_util(self, mock_contract_util):
        """Test initialization without ROFL utility (local mode)."""
        source_chain_id = 1
        contract_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb7"
        
        with patch.object(BlockSubmitter, '_load_rofl_adapter_abi', return_value=[]):
            submitter = BlockSubmitter(
                contract_util=mock_contract_util,
                rofl_util=None,
                source_chain_id=source_chain_id,
                contract_address=contract_address
            )
            
            assert submitter.contract_util == mock_contract_util
            assert submitter.rofl_util is None
            assert submitter.source_chain_id == source_chain_id
            assert submitter.contract_address == Web3.to_checksum_address(contract_address)
    
    def test_load_rofl_adapter_abi(self, mock_contract_util):
        """Test ABI loading."""
        submitter = BlockSubmitter(
            contract_util=mock_contract_util,
            rofl_util=None,
            source_chain_id=1,
            contract_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb7"
        )
        
        abi = submitter._load_rofl_adapter_abi()
        
        assert isinstance(abi, list)
        assert len(abi) == 1
        assert abi[0]["name"] == "storeBlockHeader"
        assert abi[0]["type"] == "function"
        assert len(abi[0]["inputs"]) == 3
    
    @pytest.mark.asyncio
    async def test_submit_block_header_rofl_success(self, mock_contract_util, mock_rofl_util, mock_contract):
        """Test successful block header submission via ROFL."""
        source_chain_id = 1
        block_number = 12345
        block_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        # Setup mocks
        mock_build_tx = MagicMock()
        mock_build_tx.build_transaction = MagicMock(return_value={
            'to': '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb7',
            'data': '0xabcdef',
            'gas': 300000,
            'gasPrice': Wei(1000000000),
            'value': Wei(0)
        })
        mock_contract.functions.storeBlockHeader.return_value = mock_build_tx
        
        with patch.object(BlockSubmitter, '_load_rofl_adapter_abi', return_value=[]):
            submitter = BlockSubmitter(
                contract_util=mock_contract_util,
                rofl_util=mock_rofl_util,
                source_chain_id=source_chain_id,
                contract_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb7"
            )
            submitter.contract = mock_contract
            
            result = await submitter.submit_block_header(block_number, block_hash)
            
            assert result is True
            mock_contract.functions.storeBlockHeader.assert_called_once_with(
                source_chain_id, block_number, block_hash
            )
            mock_rofl_util.submit_tx.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_submit_block_header_rofl_failure(self, mock_contract_util, mock_rofl_util, mock_contract):
        """Test failed block header submission via ROFL."""
        mock_rofl_util.submit_tx = AsyncMock(return_value=False)
        
        source_chain_id = 1
        block_number = 12345
        block_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        # Setup mocks
        mock_build_tx = MagicMock()
        mock_build_tx.build_transaction = MagicMock(return_value={
            'to': '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb7',
            'data': '0xabcdef',
            'gas': 300000,
            'gasPrice': Wei(1000000000),
            'value': Wei(0)
        })
        mock_contract.functions.storeBlockHeader.return_value = mock_build_tx
        
        with patch.object(BlockSubmitter, '_load_rofl_adapter_abi', return_value=[]):
            submitter = BlockSubmitter(
                contract_util=mock_contract_util,
                rofl_util=mock_rofl_util,
                source_chain_id=source_chain_id,
                contract_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb7"
            )
            submitter.contract = mock_contract
            
            result = await submitter.submit_block_header(block_number, block_hash)
            
            assert result is False
            mock_rofl_util.submit_tx.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_submit_block_header_local_success(self, mock_contract_util, mock_contract):
        """Test successful block header submission in local mode."""
        source_chain_id = 1
        block_number = 12345
        block_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        tx_hash = b'\x12\x34\x56\x78'
        
        # Setup mocks
        mock_transact = MagicMock()
        mock_transact.transact = MagicMock(return_value=tx_hash)
        mock_contract.functions.storeBlockHeader.return_value = mock_transact
        
        # Mock successful receipt
        mock_contract_util.w3.eth.wait_for_transaction_receipt.return_value = {
            'status': 1,
            'blockNumber': 12346
        }
        
        with patch.object(BlockSubmitter, '_load_rofl_adapter_abi', return_value=[]):
            submitter = BlockSubmitter(
                contract_util=mock_contract_util,
                rofl_util=None,  # Local mode
                source_chain_id=source_chain_id,
                contract_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb7"
            )
            submitter.contract = mock_contract
            
            result = await submitter.submit_block_header(block_number, block_hash)
            
            assert result is True
            mock_contract.functions.storeBlockHeader.assert_called_once_with(
                source_chain_id, block_number, block_hash
            )
            mock_transact.transact.assert_called_once_with({
                'gas': 300000,
                'gasPrice': Wei(1000000000)
            })
            mock_contract_util.w3.eth.wait_for_transaction_receipt.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_submit_block_header_local_failure(self, mock_contract_util, mock_contract):
        """Test failed block header submission in local mode (transaction reverted)."""
        source_chain_id = 1
        block_number = 12345
        block_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        tx_hash = b'\x12\x34\x56\x78'
        
        # Setup mocks
        mock_transact = MagicMock()
        mock_transact.transact = MagicMock(return_value=tx_hash)
        mock_contract.functions.storeBlockHeader.return_value = mock_transact
        
        # Mock failed receipt (status = 0)
        mock_contract_util.w3.eth.wait_for_transaction_receipt.return_value = {
            'status': 0,
            'blockNumber': 12346
        }
        
        with patch.object(BlockSubmitter, '_load_rofl_adapter_abi', return_value=[]):
            submitter = BlockSubmitter(
                contract_util=mock_contract_util,
                rofl_util=None,  # Local mode
                source_chain_id=source_chain_id,
                contract_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb7"
            )
            submitter.contract = mock_contract
            
            result = await submitter.submit_block_header(block_number, block_hash)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_submit_block_header_exception_handling(self, mock_contract_util, mock_rofl_util, mock_contract):
        """Test exception handling during submission."""
        source_chain_id = 1
        block_number = 12345
        block_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        # Setup mock to raise exception
        mock_contract.functions.storeBlockHeader.side_effect = Exception("Test error")
        
        with patch.object(BlockSubmitter, '_load_rofl_adapter_abi', return_value=[]):
            submitter = BlockSubmitter(
                contract_util=mock_contract_util,
                rofl_util=mock_rofl_util,
                source_chain_id=source_chain_id,
                contract_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb7"
            )
            submitter.contract = mock_contract
            
            result = await submitter.submit_block_header(block_number, block_hash)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_submit_block_header_local_transaction_error(self, mock_contract_util, mock_contract):
        """Test exception during local transaction submission."""
        source_chain_id = 1
        block_number = 12345
        block_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        # Setup mock to raise exception during transact
        mock_transact = MagicMock()
        mock_transact.transact.side_effect = Exception("Transaction failed")
        mock_contract.functions.storeBlockHeader.return_value = mock_transact
        
        with patch.object(BlockSubmitter, '_load_rofl_adapter_abi', return_value=[]):
            submitter = BlockSubmitter(
                contract_util=mock_contract_util,
                rofl_util=None,  # Local mode
                source_chain_id=source_chain_id,
                contract_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb7"
            )
            submitter.contract = mock_contract
            
            result = await submitter.submit_block_header(block_number, block_hash)
            
            assert result is False