import requests
import json
from typing import Dict, List, Optional, Any
import base64
import base58

from src.config import Config


class SolanaClient:
    def __init__(self, settings: Config):
        self.rpc_url = settings.SOLANA_RPC_URL
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def _rpc_call(self, method: str, params: List[Any] = None) -> Dict[str, Any]:
        """Make RPC call to Solana node"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or []
        }

        response = self.session.post(self.rpc_url, json=payload)
        response.raise_for_status()

        result = response.json()
        if 'error' in result:
            raise Exception(f"RPC Error: {result['error']}")

        return result.get('result')

    def get_balance(self, wallet_address: str) -> float:
        """Get SOL balance for wallet address"""
        result = self._rpc_call("getBalance", [wallet_address])
        return result['value'] / 1e9  # Convert lamports to SOL

    def get_account_info(self, account_address: str) -> Optional[Dict[str, Any]]:
        """Get account information"""
        result = self._rpc_call("getAccountInfo", [
            account_address,
            {"encoding": "base64"}
        ])
        return result['value'] if result else None

    def get_token_balance(self, token_account: str) -> float:
        """Get SPL token balance"""
        result = self._rpc_call("getTokenAccountBalance", [token_account])
        return float(result['value']['amount']) / (10 ** result['value']['decimals'])

    def get_token_accounts(self, owner: str, mint: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get token accounts owned by address"""
        params = [owner, {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}]
        if mint:
            params[1]["mint"] = mint

        result = self._rpc_call("getTokenAccountsByOwner", params)
        return result['value']

    def get_transaction(self, signature: str) -> Optional[Dict[str, Any]]:
        """Get transaction details by signature"""
        result = self._rpc_call("getTransaction", [
            signature,
            {"encoding": "json", "maxSupportedTransactionVersion": 0}
        ])
        return result

    def get_signatures(self, address: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get transaction signatures for address"""
        result = self._rpc_call("getSignaturesForAddress", [
            address,
            {"limit": limit}
        ])
        return result

    def get_recent_blockhash(self) -> str:
        """Get recent blockhash"""
        result = self._rpc_call("getRecentBlockhash")
        return result['value']['blockhash']

    def get_latest_blockhash(self) -> Dict[str, Any]:
        """Get latest blockhash"""
        result = self._rpc_call("getLatestBlockhash")
        return result['value']

    def send_transaction(self, transaction: str) -> str:
        """Send signed transaction"""
        result = self._rpc_call("sendTransaction", [
            transaction,
            {"encoding": "base64", "skipPreflight": False}
        ])
        return result

    def simulate_transaction(self, transaction: str) -> Dict[str, Any]:
        """Simulate transaction"""
        result = self._rpc_call("simulateTransaction", [
            transaction,
            {"encoding": "base64"}
        ])
        return result

    def get_slot(self) -> int:
        """Get current slot"""
        return self._rpc_call("getSlot")

    def get_block_height(self) -> int:
        """Get current block height"""
        return self._rpc_call("getBlockHeight")

    def get_cluster_nodes(self) -> List[Dict[str, Any]]:
        """Get cluster node information"""
        return self._rpc_call("getClusterNodes")

    def get_program_accounts(self, program_id: str, filters: Optional[List[Dict]] = None) -> List[Dict[str, Any]]:
        """Get accounts owned by program"""
        params = [program_id, {"encoding": "base64"}]
        if filters:
            params[1]["filters"] = filters

        result = self._rpc_call("getProgramAccounts", params)
        return result

    def get_multiple_accounts(self, accounts: List[str]) -> List[Optional[Dict[str, Any]]]:
        """Get multiple account info in single call"""
        result = self._rpc_call("getMultipleAccounts", [
            accounts,
            {"encoding": "base64"}
        ])
        return result['value']

    def request_airdrop(self, pubkey: str, lamports: int) -> str:
        """Request airdrop (devnet/testnet only)"""
        result = self._rpc_call("requestAirdrop", [pubkey, lamports])
        return result

    def get_fee_for_message(self, message: str) -> int:
        """Get fee calculation for message"""
        result = self._rpc_call("getFeeForMessage", [message])
        return result['value']

    def get_minimum_balance_for_rent_exemption(self, data_length: int) -> int:
        """Get minimum balance for rent exemption"""
        result = self._rpc_call("getMinimumBalanceForRentExemption", [data_length])
        return result

    def is_blockhash_valid(self, blockhash: str) -> bool:
        """Check if blockhash is valid"""
        result = self._rpc_call("isBlockhashValid", [blockhash])
        return result['value']


# Usage examples
if __name__ == "__main__":
    # Initialize client
    client = SolanaClient("https://api.mainnet-beta.solana.com")

    # Example wallet address
    wallet = "11111111111111111111111111111112"

    try:
        # Get balance
        balance = client.get_balance(wallet)
        print(f"Balance: {balance} SOL")

        # Get account info
        account = client.get_account_info(wallet)
        print(f"Account: {account}")

        # Get current slot
        slot = client.get_slot()
        print(f"Current slot: {slot}")

    except Exception as e:
        print(f"Error: {e}")