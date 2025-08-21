import json
import typing
import httpx
from web3.types import TxParams


class RoflUtility:
    ROFL_SOCKET_PATH = "/run/rofl-appd.sock"

    def __init__(self, url: str = ""):
        self.url = url

    def _appd_post(self, path: str, payload: typing.Any) -> typing.Any:
        transport = None
        if self.url and not self.url.startswith('http'):
            transport = httpx.HTTPTransport(uds=self.url)
            print(f"Using HTTP socket: {self.url}")
        elif not self.url:
            transport = httpx.HTTPTransport(uds=self.ROFL_SOCKET_PATH)
            print(f"Using unix domain socket: {self.ROFL_SOCKET_PATH}")

        client = httpx.Client(transport=transport)

        url = self.url if self.url and self.url.startswith('http') else "http://localhost"
        print(f"  Posting {json.dumps(payload)} to {url+path}")
        response = client.post(url + path, json=payload, timeout=None)
        response.raise_for_status()
        return response.json()

    def fetch_key(self, key_id: str) -> str:
        payload = {
            "key_id": key_id,
            "kind": "secp256k1",
        }

        path = "/rofl/v1/keys/generate"
        print(f"Fetching oracle key from {path}")
        
        result = self._appd_post(path, payload)
        return result["key"]

    def submit_tx(self, tx: TxParams) -> str:
        # Extract and format transaction fields with proper type handling
        to_address = tx.get("to", "")
        # Handle ChecksumAddress or any address type
        to_address = str(to_address) if to_address else ""
        to_address = to_address.removeprefix("0x")
        
        tx_data = tx.get("data", "")
        if isinstance(tx_data, (str, bytes)):
            if isinstance(tx_data, bytes):
                tx_data = tx_data.hex()
            tx_data = tx_data.removeprefix("0x") if isinstance(tx_data, str) else tx_data
        
        payload = {
            "tx": {
                "kind": "eth",
                "data": {
                    "gas_limit": tx.get("gas", 300000),
                    "to": to_address,
                    "value": tx.get("value", 0),
                    "data": tx_data,
                },
            },
            "encrypt": False,
        }

        path = '/rofl/v1/tx/sign-submit'
        
        print(f"Submitting transaction to {path}")
        print(f"  Transaction params received: {tx}")
        print(f"  Formatted payload: {json.dumps(payload, indent=2)}")

        result = self._appd_post(path, payload)
        print(f"  ROFL response: {json.dumps(result, indent=2)}")
        
        # Return the raw data field - let the caller handle interpretation
        return result.get("data", "")
