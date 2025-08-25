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

    def __init__(self, network_name: str = "", secret: str = ""):
        """
        Initialize the ContractUtility.
        
        Args:
            network_name: Name of the network to connect to (optional for ABI-only mode)
            secret: Private key for transactions (optional for ABI-only mode)
        """
        if network_name and secret:
            # Full initialization for contract interaction
            networks = {
                "sapphire": "https://sapphire.oasis.io",
                "sapphire-testnet": "https://testnet.sapphire.oasis.io",
                "sapphire-localnet": "http://localhost:8545",
            }
            self.network = networks.get(network_name, network_name)
            self.w3 = self.setup_web3_middleware(secret)
        else:
            # ABI-only mode - no network connection needed
            self.network = None
            self.w3 = None

    def setup_web3_middleware(self, secret: str) -> Web3:
        if not all([secret]):
            raise Warning(
                "Missing required environment variables. Please set PRIVATE_KEY."
            )

        account: LocalAccount = Account.from_key(secret)
        provider = (
            Web3.WebsocketProvider(self.network)
            if self.network.startswith("ws:")
            else Web3.HTTPProvider(self.network)
        )
        w3 = Web3(provider)
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
