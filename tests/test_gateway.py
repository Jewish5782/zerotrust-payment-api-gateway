from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ztpay.engine import process_request
from ztpay.ledger import Ledger
from ztpay.scenarios import all_scenarios


def test_scenarios_match_expected():
    ledger = Ledger()
    for case in all_scenarios():
        times = 2 if case.get("run_twice") else 1
        out = {}
        for _ in range(times):
            out = process_request(
                case["action"], case["api_key"], case["signature"], case["body"],
                ledger=ledger, commit=True,
            )
        assert out["decision"] == case["expect"], (case["name"], out)


def test_hmac_reject():
    ledger = Ledger()
    out = process_request(
        "send",
        "pk_merchant_a",
        "nope",
        {"amount_ghs": 10, "dest_wallet": "W-CUST-1", "idempotency_key": "x", "nonce": "y", "ts": 1_725_000_000},
        ledger=ledger,
    )
    assert out["decision"] == "deny"
    assert "bad_hmac" in out["reasons"]
