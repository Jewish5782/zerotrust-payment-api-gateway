from __future__ import annotations

from .auth import sign
from .keys import KEYS


TS = 1_725_000_000


def signed(api_key: str, body: dict) -> tuple[str, dict]:
    sig = sign(KEYS[api_key]["secret"], body)
    return sig, body


def all_scenarios() -> list[dict]:
    """Named demo cases. Expected decision is what the engine should return."""
    cases = []

    body = {
        "amount_ghs": 80,
        "dest_wallet": "W-CUST-1",
        "idempotency_key": "good-001",
        "nonce": "n-good-001",
        "ts": TS,
        "sends_last_5min": 1,
        "unique_dests_last_5min": 1,
    }
    sig, body = signed("pk_merchant_a", body)
    cases.append({
        "name": "Good known-destination payout",
        "action": "send",
        "api_key": "pk_merchant_a",
        "signature": sig,
        "body": body,
        "expect": "allow",
    })

    body = {
        "amount_ghs": 40,
        "src_wallet": "W-CUST-1",
        "idempotency_key": "recv-001",
        "nonce": "n-recv-001",
        "ts": TS,
    }
    sig, body = signed("pk_merchant_a", body)
    cases.append({
        "name": "Good receive (customer deposit)",
        "action": "receive",
        "api_key": "pk_merchant_a",
        "signature": sig,
        "body": body,
        "expect": "allow",
    })

    body = {
        "amount_ghs": 200,
        "dest_wallet": "W-CUST-1",
        "idempotency_key": "scope-001",
        "nonce": "n-scope-001",
        "ts": TS,
    }
    sig, body = signed("pk_merchant_b_receive_only", body)
    cases.append({
        "name": "Receive-only key tries to send",
        "action": "send",
        "api_key": "pk_merchant_b_receive_only",
        "signature": sig,
        "body": body,
        "expect": "deny",
    })

    body = {
        "amount_ghs": 90,
        "dest_wallet": "W-CUST-2",
        "idempotency_key": "replay-001",
        "nonce": "n-replay-001",
        "ts": TS,
    }
    sig, body = signed("pk_merchant_a", body)
    cases.append({
        "name": "Replay same idempotency key",
        "action": "send",
        "api_key": "pk_merchant_a",
        "signature": sig,
        "body": body,
        "expect": "deny",
        "run_twice": True,
    })

    body = {
        "amount_ghs": 8000,
        "dest_wallet": "W-CUST-1",
        "idempotency_key": "limit-001",
        "nonce": "n-limit-001",
        "ts": TS,
    }
    sig, body = signed("pk_merchant_a", body)
    cases.append({
        "name": "Over per-transaction limit",
        "action": "send",
        "api_key": "pk_merchant_a",
        "signature": sig,
        "body": body,
        "expect": "deny",
    })

    body = {
        "amount_ghs": 2500,
        "dest_wallet": "W-NEW-DEST",
        "idempotency_key": "hold-001",
        "nonce": "n-hold-001",
        "ts": TS,
        "sends_last_5min": 1,
        "unique_dests_last_5min": 1,
    }
    sig, body = signed("pk_merchant_a", body)
    cases.append({
        "name": "New destination + high amount → hold",
        "action": "send",
        "api_key": "pk_merchant_a",
        "signature": sig,
        "body": body,
        "expect": "hold",
    })

    body = {
        "amount_ghs": 1800,
        "dest_wallet": "W-NEW-DEST",
        "idempotency_key": "mule-001",
        "nonce": "n-mule-001",
        "ts": TS,
        "received_last_10min": 4000,
        "sends_last_5min": 7,
        "unique_dests_last_5min": 6,
    }
    sig, body = signed("pk_merchant_c", body)
    cases.append({
        "name": "Pass-through mule + payout burst → hold",
        "action": "send",
        "api_key": "pk_merchant_c",
        "signature": sig,
        "body": body,
        "expect": "hold",
    })

    body = {
        "amount_ghs": 50,
        "dest_wallet": "W-CUST-1",
        "idempotency_key": "bad-sig",
        "nonce": "n-bad-sig",
        "ts": TS,
    }
    cases.append({
        "name": "Tampered HMAC",
        "action": "send",
        "api_key": "pk_merchant_a",
        "signature": "deadbeef",
        "body": body,
        "expect": "deny",
    })

    return cases
