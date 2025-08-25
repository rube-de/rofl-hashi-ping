import json
from pathlib import Path

from eth_account import Account
from eth_account.signers.local import LocalAccount
from sapphirepy import sapphire
from web3 import Web3
from web3.middleware import construct_sign_and_send_raw_middleware


class ContractUtility:
    """
    Initializes the ContractUtility class.

    :param network_name: Name of the network to connect to
    :type network_name: str
    :return: None
    """

    def __init__(self, network_name: str, secret: str):
        networks = {
            "sapphire": "https://sapphire.oasis.io",
            "sapphire-testnet": "https://testnet.sapphire.oasis.io",
            "sapphire-localnet": "http://localhost:8545",
        }
        self.network = networks.get(network_name, network_name)
        self.w3 = self.setup_web3_middleware(secret)

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
        w3.middleware_onion.add(construct_sign_and_send_raw_middleware(account))
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
