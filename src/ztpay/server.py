from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .auth import sign
from .engine import process_request, resolve_hold
from .keys import KEYS
from .ledger import LEDGER
from . import persist

WEB = Path(__file__).resolve().parents[2] / "web"

app = FastAPI(
    title="Payment Policy Guard",
    description="Portfolio lab: hold risky partner payouts until a reviewer decides.",
    version="2.0.0",
)


class PaymentIn(BaseModel):
    api_key: str
    signature: str = ""
    amount_ghs: float = 0
    dest_wallet: str = ""
    src_wallet: str = ""
    idempotency_key: str = ""
    nonce: str = ""
    ts: int = 1_725_000_000
    sends_last_5min: float = 1
    unique_dests_last_5min: int = 1
    received_last_10min: float = 0
    sign_with_lab_secret: bool = False


def _run(action: str, req: PaymentIn) -> dict:
    body = req.model_dump()
    api_key = body.pop("api_key")
    signature = body.pop("signature")
    auto = body.pop("sign_with_lab_secret")
    if auto:
        rec = KEYS.get(api_key)
        if not rec:
            raise HTTPException(401, "unknown_api_key")
        signature = sign(rec["secret"], body)
    result = process_request(action, api_key, signature, body)
    conn = persist.connect()
    try:
        rid = persist.save_result(conn, action, api_key, body, result)
        if result.get("balances"):
            for acct, bal in result["balances"].items():
                persist.set_balance(conn, acct, bal)
        persist.commit_quiet(conn)
        result["id"] = rid
        return result
    finally:
        conn.close()


@app.get("/", response_class=HTMLResponse)
def desk():
    return (WEB / "index.html").read_text(encoding="utf-8")


@app.get("/health")
def health():
    return {"ok": True, "product": "payment-policy-guard", "mode": "portfolio-lab"}


@app.post("/v1/receive")
def receive(req: PaymentIn):
    return _run("receive", req)


@app.post("/v1/send")
def send(req: PaymentIn):
    return _run("send", req)


@app.post("/v1/balance")
def balance(req: PaymentIn):
    return _run("balance", req)


@app.get("/v1/holds")
def holds():
    conn = persist.connect()
    try:
        return persist.list_holds(conn)
    finally:
        conn.close()


@app.get("/v1/requests")
def requests(limit: int = 40):
    conn = persist.connect()
    try:
        return persist.list_requests(conn, limit)
    finally:
        conn.close()


@app.get("/v1/ledger")
def ledger():
    conn = persist.connect()
    try:
        rows = persist.ledger_rows(conn)
        return rows or [{"account": k, "balance": v} for k, v in LEDGER.balances.items()]
    finally:
        conn.close()


class HoldDecision(BaseModel):
    decision: str  # approve | reject


@app.post("/v1/holds/{req_id}")
def decide_hold(req_id: int, body: HoldDecision):
    if body.decision not in {"approve", "reject"}:
        raise HTTPException(400, "approve or reject")
    conn = persist.connect()
    try:
        held = persist.close_hold(conn, req_id, body.decision)
        if not held:
            raise HTTPException(404, "hold not found")
        resolve_hold(body.decision, {"action": held["action"], "api_key": held["api_key"], "body": held["body"]})
        for acct, bal in LEDGER.balances.items():
            persist.set_balance(conn, acct, bal)
        persist.commit_quiet(conn)
        return {"ok": True, "id": req_id, "decision": body.decision, "ledger": persist.ledger_rows(conn)}
    finally:
        conn.close()
