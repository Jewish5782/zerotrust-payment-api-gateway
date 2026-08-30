from __future__ import annotations

from ..ledger import Ledger


def fraud_findings(action: str, keyrec: dict, body: dict, ledger: Ledger) -> list[dict]:
    if action != "send":
        return []
    findings: list[dict] = []
    merchant = keyrec["merchant_id"]
    dest = str(body.get("dest_wallet") or "")
    amount = float(body.get("amount_ghs") or 0)
    known = ledger.seen_destinations.get(merchant, set())

    if dest and dest not in known and amount >= 1500:
        findings.append({
            "detector": "new_destination_high_amount",
            "severity": 0.82,
            "reason": f"First send from {merchant} to {dest} for GHS {amount:,.0f}",
        })
    elif dest and dest not in known and amount >= 400:
        findings.append({
            "detector": "new_destination",
            "severity": 0.48,
            "reason": f"First send from {merchant} to {dest}",
        })

    burst = float(body.get("sends_last_5min") or 0)
    dests = int(body.get("unique_dests_last_5min") or 0)
    if burst >= 6 or dests >= 5:
        findings.append({
            "detector": "payout_burst",
            "severity": 0.80,
            "reason": f"{burst:.0f} sends / {dests} destinations in 5 minutes",
        })

    if float(body.get("received_last_10min") or 0) >= 2000 and amount >= 1500:
        findings.append({
            "detector": "pass_through_mule",
            "severity": 0.75,
            "reason": "Large receive window followed by large send-out",
        })

    return findings
