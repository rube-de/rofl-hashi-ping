import json
from pathlib import Path

from eth_account import Account
from eth_account.signers.local import LocalAccount
from sapphirepy import sapphire
from web3 import Web3
from web3.middleware import SignAndSendRawMiddlewareBuilder


class ContractUtility:
    """
    Utility for contract interaction and ABI loading.
    
    Can be used in two modes:
    1. Full mode: Initialize with network and secret for contract interaction
    2. ABI-only mode: Initialize with empty strings to just load ABIs
    """

    def __init__(self, rpc_url: str = "", secret: str = ""):
        """
        Initialize the ContractUtility.
        
        Args:
            rpc_url: RPC URL for the network (optional for ABI-only mode)
            secret: Private key for transactions (optional for ABI-only mode)
        """
        if rpc_url and secret:
            # Full initialization for contract interaction
            self.rpc_url = rpc_url
            self.w3 = self.setup_web3_middleware(secret)
        else:
            # ABI-only mode - no network connection needed
            self.rpc_url = None
            self.w3 = None

    def setup_web3_middleware(self, secret: str) -> Web3:
        if not secret:
            raise ValueError("Private key is required for contract interaction")

        account: LocalAccount = Account.from_key(secret)
        w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        w3.middleware_onion.add(SignAndSendRawMiddlewareBuilder.build(account))
        w3 = sapphire.wrap(w3, account)
        w3.eth.default_account = account.address
        return w3

    def get_contract_abi(self, contract_name: str) -> list:
        """Fetches ABI of the given contract from the contracts folder"""
        contract_path = (
            Path(__file__).parent.parent.parent.parent
            / "contracts"
            / f"{contract_name}.json"
        ).resolve()
        
        with contract_path.open() as file:
            contract_data = json.load(file)

        return contract_data["abi"]
