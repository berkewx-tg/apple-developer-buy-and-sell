import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS balances (
    user_id INTEGER NOT NULL,
    currency TEXT NOT NULL,
    amount REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, currency),
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS deposit_addresses (
    user_id INTEGER NOT NULL,
    chain TEXT NOT NULL,
    address TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, chain),
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    chain TEXT NOT NULL,
    address TEXT NOT NULL,
    tx_id TEXT NOT NULL UNIQUE,
    amount REAL NOT NULL,
    currency TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS sell_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    payout_currency TEXT NOT NULL,
    payout_address TEXT NOT NULL,
    account_email TEXT NOT NULL,
    account_password TEXT NOT NULL,
    contact_phone TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
"""


@dataclass
class User:
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]


class Database:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self.connection.executescript(DB_SCHEMA)
        self.connection.commit()

    def ensure_user(self, telegram_id: int, username: Optional[str], first_name: Optional[str], last_name: Optional[str]) -> User:
        cursor = self.connection.execute(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = cursor.fetchone()
        if row:
            return User(
                id=row["id"],
                telegram_id=row["telegram_id"],
                username=row["username"],
                first_name=row["first_name"],
                last_name=row["last_name"],
            )

        created_at = datetime.utcnow().isoformat()
        cursor = self.connection.execute(
            "INSERT INTO users (telegram_id, username, first_name, last_name, created_at) VALUES (?, ?, ?, ?, ?)",
            (telegram_id, username, first_name, last_name, created_at),
        )
        self.connection.commit()
        return User(
            id=cursor.lastrowid,
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )

    def set_deposit_address(self, user_id: int, chain: str, address: str) -> None:
        created_at = datetime.utcnow().isoformat()
        self.connection.execute(
            "INSERT OR REPLACE INTO deposit_addresses (user_id, chain, address, created_at) VALUES (?, ?, ?, ?)",
            (user_id, chain, address, created_at),
        )
        self.connection.commit()

    def get_deposit_address(self, user_id: int, chain: str) -> Optional[str]:
        cursor = self.connection.execute(
            "SELECT address FROM deposit_addresses WHERE user_id = ? AND chain = ?",
            (user_id, chain),
        )
        row = cursor.fetchone()
        if row:
            return row["address"]
        return None

    def list_deposit_addresses(self) -> list[tuple[int, str, str]]:
        cursor = self.connection.execute(
            "SELECT user_id, chain, address FROM deposit_addresses"
        )
        return [(row["user_id"], row["chain"], row["address"]) for row in cursor.fetchall()]

    def add_balance(self, user_id: int, currency: str, amount: float) -> None:
        self.connection.execute(
            "INSERT INTO balances (user_id, currency, amount) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, currency) DO UPDATE SET amount = amount + ?",
            (user_id, currency, amount, amount),
        )
        self.connection.commit()

    def get_balance(self, user_id: int, currency: str) -> float:
        cursor = self.connection.execute(
            "SELECT amount FROM balances WHERE user_id = ? AND currency = ?",
            (user_id, currency),
        )
        row = cursor.fetchone()
        return float(row["amount"]) if row else 0.0

    def record_deposit(self, user_id: int, chain: str, address: str, tx_id: str, amount: float, currency: str) -> bool:
        created_at = datetime.utcnow().isoformat()
        try:
            self.connection.execute(
                "INSERT INTO deposits (user_id, chain, address, tx_id, amount, currency, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, chain, address, tx_id, amount, currency, created_at),
            )
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def create_sell_request(
        self,
        user_id: int,
        payout_currency: str,
        payout_address: str,
        account_email: str,
        account_password: str,
        contact_phone: str,
    ) -> int:
        created_at = datetime.utcnow().isoformat()
        cursor = self.connection.execute(
            "INSERT INTO sell_requests (user_id, payout_currency, payout_address, account_email, account_password, contact_phone, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, payout_currency, payout_address, account_email, account_password, contact_phone, created_at),
        )
        self.connection.commit()
        return cursor.lastrowid
