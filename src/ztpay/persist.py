from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "ztpay.db"


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path or DEFAULT_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL DEFAULT (datetime('now')),
            action TEXT NOT NULL,
            api_key TEXT,
            decision TEXT NOT NULL,
            score REAL,
            reasons TEXT,
            body TEXT,
            open_hold INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS ledger (
            account TEXT PRIMARY KEY,
            balance REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS used_keys (
            kind TEXT NOT NULL,
            value TEXT NOT NULL,
            PRIMARY KEY (kind, value)
        );
        CREATE TABLE IF NOT EXISTS audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL DEFAULT (datetime('now')),
            action TEXT NOT NULL,
            detail TEXT
        );
        """
    )
    if conn.execute("SELECT COUNT(*) c FROM ledger").fetchone()["c"] == 0:
        for acct, bal in {
            "MER-A": 50000.0, "MER-B": 12000.0, "MER-C": 8000.0,
            "W-CUST-1": 300.0, "W-CUST-2": 150.0, "W-NEW-DEST": 0.0,
        }.items():
            conn.execute("INSERT INTO ledger(account, balance) VALUES(?,?)", (acct, bal))
    conn.commit()
    return conn


def save_result(conn: sqlite3.Connection, action: str, api_key: str, body: dict, result: dict) -> int:
    cur = conn.execute(
        """
        INSERT INTO requests(action, api_key, decision, score, reasons, body, open_hold)
        VALUES(?,?,?,?,?,?,?)
        """,
        (
            action, api_key, result["decision"], result.get("score") or 0,
            json.dumps(result.get("reasons") or []), json.dumps(body),
            1 if result["decision"] == "hold" else 0,
        ),
    )
    conn.execute(
        "INSERT INTO audit(action, detail) VALUES(?,?)",
        (result["decision"], json.dumps({"action": action, "api_key": api_key})),
    )
    conn.commit()
    return cur.lastrowid


def list_holds(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM requests WHERE open_hold=1 ORDER BY id DESC").fetchall()
    return [_req(r) for r in rows]


def list_requests(conn: sqlite3.Connection, limit: int = 40) -> list[dict]:
    rows = conn.execute("SELECT * FROM requests ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [_req(r) for r in rows]


def _req(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"],
        "ts": r["ts"],
        "action": r["action"],
        "api_key": r["api_key"],
        "decision": r["decision"],
        "score": r["score"],
        "reasons": json.loads(r["reasons"] or "[]"),
        "body": json.loads(r["body"] or "{}"),
        "open_hold": r["open_hold"],
    }


def close_hold(conn: sqlite3.Connection, req_id: int, decision: str) -> dict | None:
    row = conn.execute("SELECT * FROM requests WHERE id=?", (req_id,)).fetchone()
    if not row or not row["open_hold"]:
        return None
    conn.execute("UPDATE requests SET open_hold=0, decision=? WHERE id=?", (decision, req_id))
    conn.execute("INSERT INTO audit(action, detail) VALUES(?,?)", (decision, json.dumps({"id": req_id})))
    conn.commit()
    out = _req(row)
    out["decision"] = decision
    return out


def ledger_rows(conn: sqlite3.Connection) -> list[dict]:
    return [{"account": r["account"], "balance": r["balance"]} for r in conn.execute("SELECT * FROM ledger ORDER BY account")]


def set_balance(conn: sqlite3.Connection, account: str, balance: float) -> None:
    conn.execute(
        "INSERT INTO ledger(account, balance) VALUES(?,?) ON CONFLICT(account) DO UPDATE SET balance=excluded.balance",
        (account, balance),
    )


def commit_quiet(conn: sqlite3.Connection) -> None:
    try:
        conn.commit()
    except sqlite3.Error:
        pass
