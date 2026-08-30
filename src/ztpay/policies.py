from __future__ import annotations

from .ledger import Ledger


HARD_FAIL = "deny"
HOLD = "hold"
ALLOW = "allow"


def evaluate_hard_policies(action: str, keyrec: dict, body: dict, ledger: Ledger) -> tuple[str, list[str]]:
    reasons: list[str] = []
    scopes = keyrec["scopes"]

    if action not in scopes:
        return HARD_FAIL, [f"scope_missing: key cannot call '{action}'"]

    idem = str(body.get("idempotency_key") or "")
    nonce = str(body.get("nonce") or "")
    ts = int(body.get("ts") or 0)

    if action in {"send", "receive"} and not idem:
        return HARD_FAIL, ["idempotency_key required on money movement"]

    if idem and idem in ledger.used_idempotency:
        return HARD_FAIL, ["replay: idempotency_key already used"]

    if nonce and nonce in ledger.used_nonces:
        return HARD_FAIL, ["replay: nonce already used"]

    # demo clock is frozen around 1_725_000_000 in scenarios; reject clearly stale
    if ts and ts < 1_700_000_000:
        return HARD_FAIL, ["stale_timestamp"]

    if action == "send":
        amount = float(body.get("amount_ghs") or 0)
        dest = str(body.get("dest_wallet") or "")
        if amount <= 0:
            return HARD_FAIL, ["amount must be > 0"]
        if not dest:
            return HARD_FAIL, ["dest_wallet required"]
        if amount > keyrec["max_send_ghs"]:
            return HARD_FAIL, [
                f"over_per_tx_limit: {amount} > {keyrec['max_send_ghs']}"
            ]
        used = ledger.sent_today.get(keyrec["merchant_id"], 0.0) + amount
        if used > keyrec["daily_send_limit_ghs"]:
            return HARD_FAIL, [
                f"over_daily_limit: {used} > {keyrec['daily_send_limit_ghs']}"
            ]

    return ALLOW, reasons
