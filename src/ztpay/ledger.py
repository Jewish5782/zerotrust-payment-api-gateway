from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Ledger:
    balances: dict[str, float] = field(default_factory=lambda: {
        "MER-A": 50000.0,
        "MER-B": 12000.0,
        "MER-C": 8000.0,
        "W-CUST-1": 300.0,
        "W-CUST-2": 150.0,
        "W-NEW-DEST": 0.0,
    })
    seen_destinations: dict[str, set[str]] = field(default_factory=lambda: {
        "MER-A": {"W-CUST-1", "W-CUST-2"},
        "MER-B": {"W-CUST-1"},
        "MER-C": set(),
    })
    sent_today: dict[str, float] = field(default_factory=dict)
    used_idempotency: set[str] = field(default_factory=set)
    used_nonces: set[str] = field(default_factory=set)

    def credit(self, account: str, amount: float) -> float:
        self.balances[account] = self.balances.get(account, 0.0) + amount
        return self.balances[account]

    def debit(self, account: str, amount: float) -> tuple[bool, str, float]:
        bal = self.balances.get(account, 0.0)
        if amount > bal:
            return False, "insufficient_funds", bal
        self.balances[account] = bal - amount
        return True, "ok", self.balances[account]


LEDGER = Ledger()
