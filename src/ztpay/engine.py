from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .auth import verify
from .fraud.rules import fraud_findings
from .fraud.scoring import decide
from .ledger import LEDGER, Ledger
from .policies import evaluate_hard_policies


def _audit_path() -> Path:
    preferred = Path(__file__).resolve().parents[2] / "data" / "audit.jsonl"
    try:
        preferred.parent.mkdir(parents=True, exist_ok=True)
        preferred.touch(exist_ok=True)
        return preferred
    except OSError:
        return Path("/tmp/ztpay-audit.jsonl")


_prev = "0" * 64


def _audit(rec: dict) -> dict:
    global _prev
    rec = {**rec, "ts": datetime.now(timezone.utc).isoformat(), "prev_hash": _prev}
    body = json.dumps(rec, sort_keys=True, default=str)
    rec["entry_hash"] = hashlib.sha256(body.encode()).hexdigest()
    try:
        with _audit_path().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
    except OSError:
        pass
    _prev = rec["entry_hash"]
    return rec


def process_request(
    action: str,
    api_key: str,
    signature: str,
    body: dict,
    ledger: Ledger | None = None,
    commit: bool = True,
) -> dict:
    ledger = ledger or LEDGER
    ok, why, keyrec = verify(api_key, signature, body)
    result = {
        "action": action,
        "api_key": api_key,
        "decision": "deny",
        "score": 0.0,
        "reasons": [],
        "findings": [],
        "balances": None,
    }
    if not ok:
        result["reasons"] = [why]
        if commit:
            _audit({**result, "body": body})
        return result

    hard, hard_reasons = evaluate_hard_policies(action, keyrec, body, ledger)
    if hard == "deny":
        result["reasons"] = hard_reasons
        if commit:
            _audit({**result, "body": body})
        return result

    findings = fraud_findings(action, keyrec, body, ledger)
    fraud_decision, score = decide(findings)
    result["findings"] = findings
    result["score"] = score

    if fraud_decision == "hold":
        result["decision"] = "hold"
        result["reasons"] = [f["reason"] for f in findings]
        result["balances"] = dict(ledger.balances)
        if commit:
            _audit({**result, "body": body})
        return result

    # allow — apply ledger if committing
    merchant = keyrec["merchant_id"]
    if commit:
        idem = str(body.get("idempotency_key") or "")
        nonce = str(body.get("nonce") or "")
        if idem:
            ledger.used_idempotency.add(idem)
        if nonce:
            ledger.used_nonces.add(nonce)
        if action == "receive":
            amount = float(body.get("amount_ghs") or 0)
            src = str(body.get("src_wallet") or "W-CUST-1")
            ledger.debit(src, amount)
            ledger.credit(merchant, amount)
        elif action == "send":
            amount = float(body.get("amount_ghs") or 0)
            dest = str(body.get("dest_wallet") or "")
            ok_deb, msg, _ = ledger.debit(merchant, amount)
            if not ok_deb:
                result["decision"] = "deny"
                result["reasons"] = [msg]
                _audit({**result, "body": body})
                return result
            ledger.credit(dest, amount)
            ledger.sent_today[merchant] = ledger.sent_today.get(merchant, 0.0) + amount
            ledger.seen_destinations.setdefault(merchant, set()).add(dest)
        result["balances"] = dict(ledger.balances)

    result["decision"] = "allow"
    result["reasons"] = ["policy_ok"]
    if commit:
        _audit({**result, "body": body})
    return result


def resolve_hold(decision: str, original: dict, ledger: Ledger | None = None) -> dict:
    """Operator override on a held send."""
    ledger = ledger or LEDGER
    body = original.get("body") or {}
    api_key = original.get("api_key")
    from .keys import KEYS

    rec = KEYS.get(api_key)
    out = {"decision": decision, "action": original.get("action"), "api_key": api_key}
    if decision == "approve" and rec and original.get("action") == "send":
        amount = float(body.get("amount_ghs") or 0)
        dest = str(body.get("dest_wallet") or "")
        ok_deb, msg, _ = ledger.debit(rec["merchant_id"], amount)
        if not ok_deb:
            out["decision"] = "deny"
            out["reasons"] = [msg]
        else:
            ledger.credit(dest, amount)
            ledger.seen_destinations.setdefault(rec["merchant_id"], set()).add(dest)
            out["reasons"] = ["operator_approved"]
    else:
        out["reasons"] = ["operator_rejected"]
    _audit({**out, "body": body})
    return out
