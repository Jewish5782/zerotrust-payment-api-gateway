#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from ztpay.engine import process_request
from ztpay.ledger import LEDGER
from ztpay.scenarios import all_scenarios


def main() -> None:
    print("=" * 64)
    print("Zero-Trust Payment API  —  offline scenario runner")
    print("Lab prototype. Not a Hubtel production gateway.")
    print("=" * 64)
    ok = 0
    n = 0
    for case in all_scenarios():
        times = 2 if case.get("run_twice") else 1
        out = {}
        for _ in range(times):
            out = process_request(case["action"], case["api_key"], case["signature"], case["body"])
        n += 1
        match = out["decision"] == case["expect"]
        ok += int(match)
        flag = "OK" if match else "MISMATCH"
        print(f"\n[{flag}] {case['name']}")
        print(f"      got={out['decision']} expect={case['expect']} score={out['score']}")
        for r in out["reasons"]:
            print(f"      - {r}")
    print("\n" + "-" * 64)
    print(f"Scenario checks: {ok}/{n} matched expected decision")
    print("Merchant balances:", {k: v for k, v in LEDGER.balances.items() if k.startswith('MER')})
    print("\nOperator desk:")
    print("  python3 -m uvicorn ztpay.server:app --app-dir src --port 8512")


if __name__ == "__main__":
    main()
