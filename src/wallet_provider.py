import os
import uuid
from dataclasses import dataclass
from typing import Iterable

SUPPORTED_CHAINS = {
    "SOLANA": "SOL",
    "TRON": "USDT-TRC20",
    "ETHEREUM": "USDT-ERC20",
}


@dataclass
class Deposit:
    user_id: int
    chain: str
    address: str
    tx_id: str
    amount: float
    currency: str


class WalletProvider:
    def generate_address(self, user_id: int, chain: str) -> str:
        raise NotImplementedError

    def fetch_new_deposits(self, addresses: Iterable[tuple[int, str, str]]) -> list[Deposit]:
        raise NotImplementedError


class MockWalletProvider(WalletProvider):
    def __init__(self) -> None:
        self.prefix = os.getenv("MOCK_WALLET_PREFIX", "DEMO")

    def generate_address(self, user_id: int, chain: str) -> str:
        token = uuid.uuid4().hex[:12]
        return f"{self.prefix}-{chain}-{user_id}-{token}"

    def fetch_new_deposits(self, addresses: Iterable[tuple[int, str, str]]) -> list[Deposit]:
        return []


def get_wallet_provider() -> WalletProvider:
    return MockWalletProvider()
